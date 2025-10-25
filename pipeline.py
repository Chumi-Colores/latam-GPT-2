import requests
import time
import logging
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl

from model import (
    Base,
    engine,
    Session,
    Work,
    Author,
    Edition,
    Publisher,
    Category,
    Language,
    Country
)

TARGET_SUBJECTS = ["american_authors", "canadian_authors"]
WORKS_LIMIT_PER_SUBJECT = 1000
API_BASE_URL = "https://openlibrary.org"
USER_AGENT = "LibraryETL/1.0 (Python requests; contact: cibqsm@gmail.com)"
HEADERS = {"User-Agent": USER_AGENT}
RATE_LIMIT_DELAY = 0.1

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ApiAuthorRef(BaseModel):
    key: str  # /authors/OL19690A
    name: str

class ApiWork(BaseModel):
    key: str  # /works/OL55649W
    title: str
    authors: List[ApiAuthorRef]
    first_publish_year: Optional[int] = None
    subject: Optional[List[str]] = None  # Estas son nuestras "categorías"


# Modelo para la respuesta completa de la API de Temas
class ApiSubjectResponse(BaseModel):
    works: List[ApiWork]


# Modelo para el idioma en la API de Ediciones
class ApiLanguageRef(BaseModel):
    key: str  # /languages/eng


# Modelo para una Edición individual de la API de Ediciones
class ApiEdition(BaseModel):
    key: str  # /books/OL1012111M
    title: Optional[str] = None
    isbn_10: Optional[List[str]] = None
    isbn_13: Optional[List[str]] = None
    publishers: Optional[List[str]] = None
    languages: Optional[List[ApiLanguageRef]] = None


# Modelo para la respuesta de la API de Ediciones
class ApiEditionsResponse(BaseModel):
    entries: List[ApiEdition]


# --- Clase de Cliente de API ---

class OpenLibraryClient:
    """Maneja las llamadas a la API, el rate limiting y la validación."""

    def __init__(self):
        # Usar una sesión para reutilizar conexiones
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _get(self, url: str) -> Optional[dict]:
        """Método GET genérico con rate limiting y manejo de errores."""
        time.sleep(RATE_LIMIT_DELAY)  # Respetar el rate limit
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()  # Lanza error si es 4xx o 5xx
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.warning(f"Error en API (Request): {e}")
            return None
        except requests.exceptions.JSONDecodeError as e:
            logging.warning(f"Error en API (JSON Decode): {e}")
            return None

    def get_works_for_subject(self, subject: str, limit: int) -> Optional[ApiSubjectResponse]:
        """Paso 1: Obtiene las obras para un tema."""
        url = f"{API_BASE_URL}/subjects/{subject}.json?limit={limit}"
        logging.info(f"Buscando obras para el tema: {subject}")
        data = self._get(url)
        if data:
            try:
                return ApiSubjectResponse(**data)
            except Exception as e:
                logging.error(f"Error validando datos (Pydantic) de Tema: {e}")
        return None

    def get_editions_for_work(self, work_key: str) -> Optional[ApiEditionsResponse]:
        """Paso 4: Obtiene las ediciones para una obra."""
        url = f"{API_BASE_URL}{work_key}/editions.json?limit=50"
        logging.info(f"Buscando ediciones para la obra: {work_key}")
        data = self._get(url)
        if data:
            try:
                return ApiEditionsResponse(**data)
            except Exception as e:
                logging.error(f"Error validando datos (Pydantic) de Edición: {e}")
        return None

    # NOTA: Omitimos get_author_details por simplicidad,
    # ya que los datos de país son muy inconsistentes en la API.
    # Usaremos una simplificación (ver pipeline).


def get_or_create(session: Session, model, defaults: dict = None, **kwargs):
    """
    Función de utilidad para buscar una instancia o crearla si no existe.
    Esto es clave para la idempotencia.
    """
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        # **kwargs contiene las claves de búsqueda (ej. name="...")
        # defaults contiene el resto de campos (ej. code="...")
        params = {**kwargs, **(defaults or {})}
        instance = model(**params)
        session.add(instance)
        return instance, True


def run_pipeline():
    """Ejecuta el pipeline de ETL completo."""

    # 0. Inicializar la base de datos y las tablas
    Base.metadata.create_all(engine)

    client = OpenLibraryClient()

    with Session(engine) as session:

        # --- SIMPLIFICACIÓN ---
        # El país de un autor es un dato muy sucio en la API.
        # Dado que partimos de "American Authors", crearemos y
        # asignaremos "United States" a todos los autores de este tema.
        country_usa, _ = get_or_create(
            session,
            Country,
            code="US",
            defaults={"name": "United States"}
        )
        session.commit()  # Cometer para que el país tenga un ID

        for subject in TARGET_SUBJECTS:

            # 1. Obtener Obras del tema
            subject_data = client.get_works_for_subject(subject, limit=WORKS_LIMIT_PER_SUBJECT)
            if not subject_data:
                logging.warning(f"No se pudieron obtener obras para el tema {subject}. Saltando.")
                continue

            logging.info(f"Procesando {len(subject_data.works)} obras para '{subject}'...")

            for i, work_data in enumerate(subject_data.works):

                # Envolvemos cada obra en un try/except y una transacción.
                # Si una obra falla, hacemos rollback y continuamos con la siguiente.
                try:
                    # 2. Verificar si la Obra ya existe
                    db_work = session.query(Work).filter_by(openlibrary_id=work_data.key).first()
                    if db_work:
                        logging.info(f"Obra '{work_data.title}' ya existe. Saltando.")
                        continue

                    logging.info(f"Procesando Obra {i + 1}/{len(subject_data.works)}: {work_data.title}")

                    # 3. Procesar Autores
                    db_authors = []
                    for author_ref in work_data.authors:
                        db_author, _ = get_or_create(
                            session,
                            Author,
                            openlibrary_id=author_ref.key,
                            defaults={"name": author_ref.name, "country": country_usa}
                        )
                        db_authors.append(db_author)

                    # 4. Procesar Categorías (Subjects)
                    db_categories = []
                    if work_data.subject:
                        for cat_name in work_data.subject[:10]:  # Limitar a 10 categorías
                            # Limpiar y truncar para la DB
                            clean_name = cat_name.strip()[:100]
                            db_cat, _ = get_or_create(session, Category, name=clean_name)
                            db_categories.append(db_cat)

                    # 5. Crear la Obra (Work)
                    db_work = Work(
                        openlibrary_id=work_data.key,
                        title=work_data.title,
                        first_publish_year=work_data.first_publish_year,
                        authors=db_authors,  # SQLAlchemy maneja la M:N
                        categories=db_categories  # SQLAlchemy maneja la M:N
                    )
                    session.add(db_work)

                    # 6. Obtener y procesar Ediciones
                    editions_data = client.get_editions_for_work(work_data.key)
                    if not editions_data:
                        continue  # Continuar sin ediciones

                    for edition_data in editions_data.entries:

                        # Verificar si la Edición ya existe
                        if session.query(Edition).filter_by(openlibrary_id=edition_data.key).first():
                            continue

                        # 6a. Obtener/Crear Editorial (Publisher)
                        db_publisher = None
                        if edition_data.publishers:
                            # Tomar solo el primer editor
                            pub_name = edition_data.publishers[0].strip()[:255]
                            db_publisher, _ = get_or_create(session, Publisher, name=pub_name)

                        # 6b. Obtener/Crear Idioma (Language)
                        db_language = None
                        if edition_data.languages:
                            # Tomar solo el primer idioma
                            lang_key = edition_data.languages[0].key.split('/')[-1]  # /languages/eng -> eng
                            lang_key = lang_key.strip()[:3]
                            db_language, _ = get_or_create(
                                session,
                                Language,
                                code=lang_key,
                                defaults={"name": lang_key.upper()}  # No tenemos el nombre, usamos el código
                            )

                        # 6c. Crear la Edición (Edition)
                        new_edition = Edition(
                            openlibrary_id=edition_data.key,
                            isbn_10=edition_data.isbn_10[0] if edition_data.isbn_10 else None,
                            isbn_13=edition_data.isbn_13[0] if edition_data.isbn_13 else None,
                            work=db_work,  # Relación N:1
                            publisher=db_publisher,  # Relación N:1
                            language=db_language  # Relación N:1
                        )
                        session.add(new_edition)

                    # 7. Cometer la transacción para ESTA obra y todas sus ediciones
                    session.commit()

                except Exception as e:
                    logging.error(f"Fallo al procesar la obra {work_data.key}: {e}")
                    session.rollback()  # Revertir cambios de esta obra fallida

    logging.info("Pipeline completado.")


if __name__ == "__main__":
    run_pipeline()

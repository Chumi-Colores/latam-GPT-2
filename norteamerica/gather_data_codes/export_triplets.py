"""
Exportador de Grafo de Conocimiento (Knowledge Graph).

Lee la base de datos SQLite poblada y genera un archivo CSV que contiene
todas las tripletas ⟨sujeto, relacion, objeto⟩ basadas en las 7
relaciones definidas.
"""

import csv
import logging
from sqlalchemy.orm import joinedload, Session
from model import (
    engine,
    Work,
    Author,
    Edition,
    Category,
    Country,
    Language,
    Publisher
)

OUTPUT_FILE = "../data/knowledge_graph.csv"


def export_triplets():
    """
    Consulta la base de datos para cada una de las 7 relaciones
    y escribe las tripletas resultantes en un archivo CSV.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f"Iniciando exportación de tripletas a {OUTPUT_FILE}...")

    total_triplets = 0

    # Abre la sesión de la base de datos y el archivo CSV
    with Session(engine) as session, open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Escribir la cabecera del CSV
        writer.writerow(['sujeto', 'relacion', 'objeto'])

        # --- Relación 1: Libro, tiene_categoría, Categoría ---
        logging.info("Procesando: 1. Libro -> tiene_categoría -> Categoría")
        triplets_r1 = []
        rel = "tiene_categoría"
        # Usamos joinedload para cargar 'categories' eficientemente (evita N+1 consultas)
        query_r1 = session.query(Work).options(joinedload(Work.categories))
        for work in query_r1.all():
            for category in work.categories:
                triplets_r1.append((work.title, rel, category.name))

        writer.writerows(triplets_r1)
        total_triplets += len(triplets_r1)

        # --- Relación 2: Libro, fue_publicado_en, Año de publicación ---
        logging.info("Procesando: 2. Libro -> fue_publicado_en -> Año")
        triplets_r2 = []
        rel = "fue_publicado_en"
        query_r2 = session.query(Work).filter(Work.first_publish_year.isnot(None))
        for work in query_r2.all():
            triplets_r2.append((work.title, rel, work.first_publish_year))

        writer.writerows(triplets_r2)
        total_triplets += len(triplets_r2)

        # --- Relación 3: Autor, es_autor_de_la_obra, Obra ---
        logging.info("Procesando: 3. Autor -> es_autor_de_la_obra -> Obra")
        triplets_r3 = []
        rel = "es_autor_de_la_obra"
        query_r3 = session.query(Author).options(joinedload(Author.works))
        for author in query_r3.all():
            for work in author.works:
                triplets_r3.append((author.name, rel, work.title))

        writer.writerows(triplets_r3)
        total_triplets += len(triplets_r3)

        # --- Relación 4: ISBN/Edición, fue_publicado_por, Editorial ---
        logging.info("Procesando: 4. Edición -> fue_publicado_por -> Editorial")
        triplets_r4 = []
        rel = "fue_publicado_por"
        query_r4 = session.query(Edition).options(joinedload(Edition.publisher)).filter(
            Edition.publisher_id.isnot(None))
        for edition in query_r4.all():
            isbn = edition.isbn_13 if edition.isbn_13 else edition.isbn_10
            if isbn:
                triplets_r4.append((isbn, rel, edition.publisher.name))

        writer.writerows(triplets_r4)
        total_triplets += len(triplets_r4)

        # --- Relación 5: Libro, tiene, ISBN/Edición ---
        logging.info("Procesando: 5. Libro -> tiene_edicion -> Edición")
        triplets_r5 = []
        rel = "tiene_edicion"  # Usamos un nombre más específico
        # Esta consulta obtiene la relación desde la Edición hacia la Obra
        query_r5 = session.query(Edition).options(joinedload(Edition.work))
        for edition in query_r5.all():
            # El sujeto es el Libro (Work), el objeto es la Edición (Edition)
            isbn = edition.isbn_13 if edition.isbn_13 else edition.isbn_10
            if isbn:
                triplets_r5.append((edition.work.title, rel, isbn))

        writer.writerows(triplets_r5)
        total_triplets += len(triplets_r5)

        # --- Relación 6: Autor, es_de, país ---
        logging.info("Procesando: 6. Autor -> es_de -> País")
        triplets_r6 = []
        rel = "es_de"
        query_r6 = session.query(Author).options(joinedload(Author.country)).filter(Author.country_id.isnot(None))
        for author in query_r6.all():
            triplets_r6.append((author.name, rel, author.country.name))

        writer.writerows(triplets_r6)
        total_triplets += len(triplets_r6)

        # --- Relación 7: ISBN/Edición, está_escrito_en, idioma ---
        logging.info("Procesando: 7. Edición -> esta_escrito_en -> Idioma")
        triplets_r7 = []
        rel = "esta_escrito_en"
        query_r7 = session.query(Edition).options(joinedload(Edition.language)).filter(Edition.language_id.isnot(None))
        for edition in query_r7.all():
            # Usamos 'name' que en el pipeline guardamos como el código (ej. "eng")
            isbn = edition.isbn_13 if edition.isbn_13 else edition.isbn_10
            if isbn:
                triplets_r7.append((isbn, rel, edition.language.name))

        writer.writerows(triplets_r7)
        total_triplets += len(triplets_r7)

    logging.info(f"¡Exportación completada! Se generaron {total_triplets} tripletas en {OUTPUT_FILE}.")


if __name__ == "__main__":
    export_triplets()

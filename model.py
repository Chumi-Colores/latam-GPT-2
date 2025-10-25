from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    Session,
)
from sqlalchemy import (
    create_engine,
    String,
    ForeignKey,
    Table,
    Column,
    Integer
)

DB_URL = "sqlite:///library_sqlite.db"

engine = create_engine(DB_URL, echo=False)


class Base(DeclarativeBase):
    pass

# Relacion 3: Autor <-> Obra (M:N)
work_author_association = Table(
    "work_author",
    Base.metadata,
    Column("work_id", Integer, ForeignKey("work.id"), primary_key=True),
    Column("author_id", Integer, ForeignKey("author.id"), primary_key=True),
)

# Relacion 1: Obra <-> Categoria (M:N)
work_category_association = Table(
    "work_category",
    Base.metadata,
    Column("work_id", Integer, ForeignKey("work.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("category.id"), primary_key=True),
)


class Publisher(Base):
    __tablename__ = "publisher"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    editions: Mapped[list[Edition]] = relationship(back_populates="publisher")


class Category(Base):
    __tablename__ = "category"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    works: Mapped[list[Work]] = relationship(
        secondary=work_category_association, back_populates="categories"
    )


class Language(Base):
    __tablename__ = "language"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(3), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    # Sin comillas en 'Edition'
    editions: Mapped[list[Edition]] = relationship(back_populates="language")


class Country(Base):
    __tablename__ = "country"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(2), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    authors: Mapped[list[Author]] = relationship(back_populates="country")



class Author(Base):
    __tablename__ = "author"
    id: Mapped[int] = mapped_column(primary_key=True)
    openlibrary_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))

    # Relación 6: Autor, es_de, país (N:1)
    country_id: Mapped[int | None] = mapped_column(ForeignKey("country.id"))
    country: Mapped[Country | None] = relationship(back_populates="authors")

    # Relación 3: Autor, es_autor_de_la_obra, Obra (M:N)
    works: Mapped[list[Work]] = relationship(
        secondary=work_author_association, back_populates="authors"
    )


class Work(Base):
    __tablename__ = "work"
    id: Mapped[int] = mapped_column(primary_key=True)
    openlibrary_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))

    # Relación 2: Libro, fue_publicado_en, Año de publicación (1:1)
    first_publish_year: Mapped[int | None]

    # Relación 5: Libro, tiene, ISBN/Edición (1:N)
    editions: Mapped[list[Edition]] = relationship(back_populates="work")

    # Relación 3: Autor, es_autor_de_la_obra, Obra (M:N)
    authors: Mapped[list[Author]] = relationship(
        secondary=work_author_association, back_populates="works"
    )

    # Relación 1: Libro, tiene_categoría, Categoría (M:N)
    categories: Mapped[list[Category]] = relationship(
        secondary=work_category_association, back_populates="works"
    )


class Edition(Base):  # La "Edición" física o ISBN
    __tablename__ = "edition"
    id: Mapped[int] = mapped_column(primary_key=True)
    openlibrary_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    isbn_10: Mapped[str | None] = mapped_column(String(10), index=True)
    isbn_13: Mapped[str | None] = mapped_column(String(13), index=True)

    # Relación 5: Libro, tiene, ISBN/Edición (N:1)
    work_id: Mapped[int] = mapped_column(ForeignKey("work.id"))
    work: Mapped[Work] = relationship(back_populates="editions")

    # Relación 4: ISBN/Edición, fue_publicado_por, Editorial (N:1)
    publisher_id: Mapped[int | None] = mapped_column(ForeignKey("publisher.id"))
    publisher: Mapped[Publisher | None] = relationship(back_populates="editions")

    # Relación 7: ISBN/Edición, está_escrito_en, idioma (N:1)
    language_id: Mapped[int | None] = mapped_column(ForeignKey("language.id"))
    language: Mapped[Language | None] = relationship(back_populates="editions")



def create_database_and_tables():
    """Crea el archivo de la base de datos y todas las tablas."""
    print("Creando tablas para SQLite...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Tablas creadas exitosamente.")


def run_example():
    """Demostración de cómo insertar y consultar datos. (Ficticios)"""

    with Session(engine) as session:
        # 1. Limpiar datos de corridas anteriores (opcional)
        session.query(Edition).delete()
        session.query(Work).delete()
        session.query(Author).delete()
        session.query(Publisher).delete()
        session.query(Language).delete()
        session.query(Country).delete()
        session.query(Category).delete()
        session.commit()

        # 2. Crear Entidades
        print("Creando entidades...")
        country_usa = Country(code="US", name="United States")
        lang_eng = Language(code="eng", name="English")
        pub_ace = Publisher(name="Ace Books")
        cat_scifi = Category(name="Science Fiction")

        author_frank = Author(
            openlibrary_id="OL23919A",
            name="Frank Herbert",
            country=country_usa
        )

        work_dune = Work(
            openlibrary_id="OL45883W",
            title="Dune",
            first_publish_year=1965,
            authors=[author_frank],  # Relación 3 (M:N)
            categories=[cat_scifi]  # Relación 1 (M:N)
        )

        edition_dune_pb = Edition(
            openlibrary_id="OL1012111M",
            isbn_13="9780441172719",
            work=work_dune,  # Relación 5 (N:1)
            publisher=pub_ace,  # Relación 4 (N:1)
            language=lang_eng  # Relación 7 (N:1)
        )

        # 3. Añadir a la sesión y hacer commit
        session.add_all([
            country_usa, lang_eng, pub_ace, cat_scifi,
            author_frank, work_dune, edition_dune_pb
        ])
        session.commit()
        print("Datos insertados.")

        # 4. Consultar los datos
        print("\n--- Consultando datos ---")

        # SQLAlchemy 2.0 style query
        stmt = sa.select(Work).where(Work.title == "Dune")
        retrieved_work = session.scalars(stmt).one()

        print(f"Obra: {retrieved_work.title} ({retrieved_work.first_publish_year})")

        # Acceder a relaciones M:N
        author = retrieved_work.authors[0]
        print(f"Autor: {author.name}")
        print(f"Categoria: {retrieved_work.categories[0].name}")


        # Acceder a relación N:1 desde el autor
        print(f"País del Autor: {author.country.name}")  # Relación 6

        # Acceder a relación 1:N
        edition = retrieved_work.editions[0]
        print(f"Edición ISBN: {edition.isbn_13}")

        # Acceder a relaciones N:1 desde la edición
        print(f"Editorial: {edition.publisher.name}")
        print(f"Idioma: {edition.language.name}")


if __name__ == "__main__":
    create_database_and_tables()
    run_example()

import pandas as pd
import random

import pandas as pd
import random

def generar_preguntas_razonadas(csv_path, out_path, n_por_tipo=100):
    df = pd.read_csv(csv_path)

    autores_por_libro = {row["object"]: row["subject"] for _, row in df[df["relation"]=="es autor de la obra"].iterrows()}
    pais_por_autor = {row["subject"]: row["object"] for _, row in df[df["relation"]=="es de nacionalidad"].iterrows()}
    anio_por_libro = {row["subject"]: row["object"] for _, row in df[df["relation"]=="es del año"].iterrows()}
    genero_por_libro = {row["subject"]: row["object"] for _, row in df[df["relation"]=="pertenece al género"].iterrows()}

    libro_por_isbn = {row["subject"]: row["object"] for _, row in df[df["relation"]=="es un codigo ISBN para el libro"].iterrows()}
    editorial_por_isbn = {row["subject"]: row["object"] for _, row in df[df["relation"]=="es un codigo ISBN de una edicion publicada por"].iterrows()}

    # --- Pregunta 1: ¿Quién escribió el libro X? ---
    p1 = []
    for libro, autor in autores_por_libro.items():
        p1.append({
            "tipo": "P1",
            "pregunta": f"¿Quién escribió el libro {libro}?",
            "respuesta": autor
        })

    # --- Pregunta 2: ¿De qué país es la persona Y? ---
    p2 = []
    for autor, pais in pais_por_autor.items():
        p2.append({
            "tipo": "P2",
            "pregunta": f"¿De qué país es la persona {autor}?",
            "respuesta": pais
        })

    # --- Pregunta 3: ¿De qué país es el autor del libro X? ---
    p3 = []
    for libro, autor in autores_por_libro.items():
        if autor in pais_por_autor:
            p3.append({
                "tipo": "P3",
                "pregunta": f"¿De qué país es el autor del libro {libro}?",
                "respuesta": pais_por_autor[autor]
            })

    # --- Pregunta 4: ¿De qué año es el libro X? ---
    p4 = []
    for libro, anio in anio_por_libro.items():
        p4.append({
            "tipo": "P4",
            "pregunta": f"¿De qué año es el libro {libro}?",
            "respuesta": str(anio)
        })

    # --- Pregunta 5: Dime el género o el tópico principal del libro X ---
    p5 = []
    # Agrupar todos los géneros por libro
    generos_agrupados = (
        df[df["relation"] == "pertenece al género"]
        .groupby("subject")["object"]
        .apply(lambda x: list(set(x)))
        .to_dict()
    )

    for libro, generos in generos_agrupados.items():
        p5.append({
            "tipo": "P5",
            "pregunta": f"Dime el género o el tópico principal del libro {libro}",
            # Une los géneros en una sola respuesta
            "respuesta": ", ".join(sorted(set(map(str, generos))))
        })

    # --- Pregunta 6: Dime alguna editorial que haya publicado el libro X ---
    p6 = []

    isbn_por_libro = (
        df[df["relation"] == "es un codigo ISBN para el libro"]
        .groupby("object")["subject"]  # agrupa todos los ISBN asociados al mismo libro
        .apply(list)
        .to_dict()
    )

    editoriales_por_isbn = (
        df[df["relation"] == "es un codigo ISBN de una edicion publicada por"]
        .groupby("subject")["object"]
        .apply(lambda x: list(set(x)))
        .to_dict()
    )

    for libro, isbns in isbn_por_libro.items():
        editoriales = []
        for isbn in isbns:
            if isbn in editoriales_por_isbn:
                editoriales.extend(editoriales_por_isbn[isbn])
        if editoriales:
            p6.append({
                "tipo": "P6",
                "pregunta": f"Dime alguna editorial que haya publicado el libro {libro}",
                "respuesta": ", ".join(sorted(set(map(str, editoriales))))
            })

    todas = p1 + p2 + p3 + p4 + p5 + p6
    df_all = pd.DataFrame(todas)
    df_final = df_all.groupby("tipo").apply(lambda x: x.sample(min(len(x), n_por_tipo), random_state=42)).reset_index(drop=True)

    df_final.to_csv(out_path, index=False)
    print(f"✅ Generadas {len(df_final)} preguntas en {out_path}")

# Ejemplo de uso
generar_preguntas_razonadas("triplets_europe.csv", "preguntas_respuestas_6tipos.csv", n_por_tipo=100)

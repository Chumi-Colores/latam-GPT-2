import os
import pandas as pd

from typing import List
def clear_duplicates_and_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza espacios, elimina duplicados y devuelve solo columnas básicas.

    - Limpia espacios en subject y object.
    - Elimina duplicados usando las columnas disponibles entre
      [subject, relation, object, country, source].
    - Devuelve solo [subject, relation, object].
    """
    # Normalización de espacios
    for col in ("subject", "object"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    # Conjunto de columnas para deduplicar (tolerante a faltantes)
    dedup_cols = [c for c in ["subject", "relation", "object", "country", "source"] if c in df.columns]
    if dedup_cols:
        df = df.drop_duplicates(subset=dedup_cols)
    else:
        df = df.drop_duplicates()

    # Salida simplificada
    base_cols = [c for c in ["subject", "relation", "object"] if c in df.columns]
    df_simple = df[base_cols].copy()
    return df_simple
    #  df_simple.to_csv(new_file_spain, index=False)


def keep_oldest_year_per_book(df: pd.DataFrame) -> pd.DataFrame:
    """
    Lee un CSV con columnas 'subject', 'relation', 'object'
    y deja solo la fila con la fecha más antigua para cada libro (subject).
    Guarda el resultado en un nuevo CSV.
    """
    # Leer CSV
    # df = pd.read_csv(csv_path)

    # Filtrar solo las tripletas de tipo 'es del año' (si no existe la columna, devolver tal cual)
    if "relation" not in df.columns or "object" not in df.columns or "subject" not in df.columns:
        return df.copy()

    df_years = df[df["relation"] == "es del año"].copy()

    # Convertir 'object' a número (por si está como texto)
    df_years["year_num"] = pd.to_numeric(df_years["object"], errors="coerce")
    # Quitar filas sin año válido
    df_years = df_years.dropna(subset=["year_num"])  # evita errores con idxmin en vacíos o NaN

    # Obtener la fila con el año más antiguo por libro
    if len(df_years) == 0:
        # No hay años válidos; devolvemos el DF original sin cambios
        return df.copy()
    df_oldest = df_years.loc[df_years.groupby("subject")["year_num"].idxmin()]

    # Unir con el resto de las tripletas que no son de tipo 'es del año'
    df_rest = df[df["relation"] != "es del año"]
    df_final = pd.concat([df_rest, df_oldest], ignore_index=True)
    df_final = df_final.drop(columns=["year_num"])
    return df_final
    # Guardar nuevo CSV
    # df_final.to_csv(out_path, index=False)
    # print(f"✅ Archivo guardado: {out_path}")

def _safe_country_from_path(path: str) -> str:
    """Obtiene el nombre del país desde el nombre de archivo, sin extensión.

    Reemplaza espacios por guiones bajos para el archivo de salida.
    """
    name = os.path.splitext(os.path.basename(path))[0]
    return name.replace(" ", "_")


def process_folder(input_dir: str, output_dir: str) -> List[str]:
    """Procesa todos los CSV de input_dir y escribe resultados en output_dir.

    Devuelve la lista de rutas de salida generadas.
    """
    os.makedirs(output_dir, exist_ok=True)

    outputs: List[str] = []
    # Iterar por CSVs
    for fname in os.listdir(input_dir):
        if not fname.lower().endswith(".csv"):
            continue
        in_path = os.path.join(input_dir, fname)
        country_key = _safe_country_from_path(in_path)
        out_path = os.path.join(output_dir, f"triples_{country_key}.csv")

        # Leer y procesar
        df_in = pd.read_csv(in_path)
        df_clean = clear_duplicates_and_columns(df_in)
        df_final = keep_oldest_year_per_book(df_clean)
        df_final.to_csv(out_path, index=False)
        outputs.append(out_path)
        print(f"✔ Procesado: {in_path} -> {out_path} ({len(df_final)} filas)")

    return outputs


def main():
    input_dir = os.path.join("eu_books_prueba_por_pais")
    output_dir = os.path.join("Real Datasets")
    generated = process_folder(input_dir, output_dir)
    print(f"✅ Archivos generados: {len(generated)}")



if __name__ == "__main__":
    main()    # df_italy = pd.read_csv("c:/Users/Casa/Desktop/Desafio IA/eu_books_triples_italy.csv")
    # new_file_italy = "c:/Users/Casa/Desktop/Desafio IA/Clean Datasets/eu_books_triples_italy_cleaned.csv"
    # clear_duplicates_and_columns(df_italy, new_file_italy)

    # df_uk = pd.read_csv("c:/Users/Casa/Desktop/Desafio IA/eu_books_triples_uk.csv")
    # new_file_uk = "c:/Users/Casa/Desktop/Desafio IA/Clean Datasets/eu_books_triples_uk_cleaned.csv"
    # clear_duplicates_and_columns(df_uk, new_file_uk)
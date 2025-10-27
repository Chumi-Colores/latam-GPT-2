from obtener_tripletas import build_publication_date_and_category_triplets
import pandas as pd
import json
import csv
# scripts para obtener fecha de publicacion y categorias de los libros

def obtener_json_autores_libros(triplets_df, checkpoint_row=0):
    
    json_autores_libros = {}
    for index, row in triplets_df.iterrows():
        if index < checkpoint_row:
            continue
        
        if row["relation"] == "es autor de la obra":
            if row["source"] not in json_autores_libros:
                json_autores_libros[row["source"]] = [row["target"]]
            else:
                json_autores_libros[row["source"]].append(row["target"])
    return json_autores_libros


def add_triplets_to_csv(triplets_faltantes, output_file="./tripletas/tripletas_faltantes.csv"):
    
    with open(output_file, mode="a", newline="") as f:
        writer = csv.writer(f)
        for triplet in triplets_faltantes:
            writer.writerow(triplet)

def construir_tripletas_faltantes(json_autores_libros):
    for autor, libros in json_autores_libros.items():
        
        try:
            tripletas = build_publication_date_and_category_triplets(autor, libros)
        
        except Exception as e:
            continue
        
        if not tripletas:
            continue
        
        add_triplets_to_csv(tripletas, output_file="./tripletas/tripletas_faltantes.csv")

    
if __name__ == "__main__":
    triplets_df = pd.read_csv("tripletas/tripletas.csv")
    json_autores_libros = obtener_json_autores_libros(triplets_df)
    construir_tripletas_faltantes(json_autores_libros)

    


import obtener_tripletas
import pandas as pd
import csv

file_countries = ["chilenos", "argentinos", "peruanos", "bolivianos", "uruguayos", "paraguayos", "ecuatorianos", "colombianos", "venezolanos"]
nationalities = ["chilena", "argentina", "peruana", "boliviana", "uruguaya", "paraguaya", "ecuatoriana", "colombiana", "venezolana"]


for country_file, nationality in zip(file_countries, nationalities):
        
    output_file = f"tripletas/tripletas_{country_file}.csv"
        
    file_name = f"autores_faltantes/autores_faltantes_{country_file}.csv"

    df = pd.read_csv(file_name)
    authors = df["author"].dropna().tolist()

    with open(output_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for author in authors:
            try:
                triplets = obtener_tripletas.build_triplets_for_author(author, nationality)
                if triplets:
                    writer.writerows(triplets)
            except Exception as e:
                continue

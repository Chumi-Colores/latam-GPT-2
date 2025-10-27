import pandas as pd

file_countries = ["chilenos", "argentinos", "peruanos", "bolivianos", "uruguayos", "paraguayos", "ecuatorianos", "colombianos", "venezolanos"]

#Obtener autores más importantes que no estaban en la categoria de escritores de wikipedia
for country in file_countries:

    most_important = pd.read_csv(f"./autores_mas_importantes/autores_mas_importantes_{country}.csv")
    all_authors = pd.read_csv(f"./autores/escritores_{country}.csv")
    
    important_authors = set(most_important["author"].dropna().unique())
    all_authors_set = set(all_authors["author"].dropna().unique())

    missing_authors = important_authors - all_authors_set
    
    missing_df = pd.DataFrame(sorted(list(missing_authors)), columns=["author"])
    
    output_path = f"./autores_faltantes/autores_faltantes_{country}.csv"
    missing_df.to_csv(output_path, index=False, encoding="utf-8")
    
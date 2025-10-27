import pandas as pd

file_countries = ["chilenos", "argentinos", "peruanos", "bolivianos", "uruguayos", "paraguayos", "ecuatorianos", "colombianos", "venezolanos"]

#Quitar isbn repetidos
for country in file_countries:

    triplet_file = f"./tripletas/tripletas_{country}.csv"
    
    df = pd.read_csv(triplet_file)
    isbn_df = df[df["relation"].str.contains("ISBN", na= False)]
    isbn_df = isbn_df.drop_duplicates(subset=["source", "relation"])    
    
    non_isbn_df = df[~df["relation"].str.contains("ISBN", na= False)]
    filtered_df = pd.concat([non_isbn_df, isbn_df], ignore_index=True)
    
    filtered_df.to_csv(triplet_file, index=False)
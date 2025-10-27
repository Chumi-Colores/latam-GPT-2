import pandas as pd

file_countries = ["chilenos", "argentinos", "peruanos", "bolivianos", "uruguayos", "paraguayos", "ecuatorianos", "colombianos", "venezolanos"]
country_names = ["Chile", "Argentina", "Peru", "Bolivia", "Uruguay", "Paraguay", "Ecuador", "Colombia", "Venezuela"]

publishers = set()

statistics_df = pd.DataFrame(columns = ["Numero de Libros", "Numero de Autores", "Numero de Ediciones Distintas"])

for country_file, country in zip(file_countries, country_names):
    
    triplets_df = pd.read_csv(f"tripletas/tripletas_{country_file}.csv")
    
    
    authors = set()
    books = set()
    editions = set()
    for index, row in triplets_df.iterrows():
        
        if row["relation"] == "es de nacionalidad":
            authors.add(row["source"])
        
        if row["relation"] == "es un codigo ISBN de una edicion publicada por":
            publishers.add(row["target"])
    
        if row["relation"] == "es autor de la obra":
            books.add(row["target"])
        
        if row["relation"] == "es un codigo ISBN de una edicion publicada por":
            editions.add(row["source"])
            publishers.add(row["target"])
    
        
    statistics_df.loc[country] = [len(books), len(authors), len(editions)]
    

statistics_df.to_csv("estadisticas.csv", index=True)

# hacer >> total_editoriales.txt
print(len(publishers))

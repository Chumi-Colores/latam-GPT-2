import pandas as pd
import json

triplets = pd.read_csv("tripletas/tripletas.csv")
df_book_names = triplets[triplets["relation"] == "es autor de la obra"]
df_book_isbns = triplets[triplets["relation"] == "es un codigo ISBN para el libro"]
df_publishers = triplets[triplets["relation"] == "es un codigo ISBN de una edicion publicada por"]
df_categories = triplets[triplets["relation"] == "pertenece a la categoria"]
df_book_publishing_dates = triplets[triplets["relation"] == "fue publicada en el año"]

final_json = {}
isbn_to_book_name = {}


for index, row in df_book_names.iterrows():
    book_name = row["target"]
    author = row["source"]
    if book_name not in final_json:
        final_json[book_name] = {}
        
        final_json[book_name]["editoriales"] = []
        final_json[book_name]["categorias"] = []
        final_json[book_name]["fecha"] = None
        final_json[book_name]["autores"] = author

for index, row in df_book_isbns.iterrows():
    book_name = row["target"]
    
    edition = row["source"]
        
    isbn_to_book_name[edition] = book_name
for index, row in df_publishers.iterrows():
    
    isbn = row["source"]
    book_name = isbn_to_book_name.get(isbn, None)
    publisher = row["target"]
    
    if type(publisher) != str:
        continue
    
    if book_name in final_json:
        if publisher not in final_json[book_name]["editoriales"]:
            final_json[book_name]["editoriales"].append(publisher)
            
for index, row in df_categories.iterrows():
    book_name = row["source"]
    category = row["target"]
    
    if book_name in final_json:
        if category not in final_json[book_name]["categorias"]:
            final_json[book_name]["categorias"].append(category)
            

for index, row in df_book_publishing_dates.iterrows():
    book_name = row["source"]
    year = row["target"]
    
    if book_name in final_json:
        final_json[book_name]["fecha"] = year            
            

with open("relaciones.json", "w") as outfile:
    json.dump(final_json, outfile)
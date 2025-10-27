import pandas as pd

#Filtrar categorias repetidas luego del filtro
triplets_df = pd.read_csv("tripletas/tripletas.csv")

category_df = triplets_df[triplets_df["relation"] == "pertenece a la categoria"]
category_df = category_df.drop_duplicates(subset=["source", "target"])    
    
non_category_df = triplets_df[triplets_df["relation"] != "pertenece a la categoria"]
filtered_df = pd.concat([non_category_df, category_df], ignore_index=True)

filtered_df.to_csv("tripletas/tripletas.csv", index=False)
    
    
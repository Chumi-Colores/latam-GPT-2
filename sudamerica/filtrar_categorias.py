import pandas as pd


category_mappings = pd.read_csv("mapeos_categorias.csv")
triplets_df = pd.read_csv("tripletas/tripletas.csv")

category_dict = {row["categoria"]:row["categoria_amplia"] for index, row in category_mappings.iterrows()}

#mapear categorias a categorias amplias
for index, row in triplets_df.iterrows():
    if row["relation"] == "pertenece a la categoria":
        category = row["target"]    
    else:
        continue
    
    if category in category_dict:
        
        if category_dict[category] == "No es categoria":
            triplets_df = triplets_df.drop(index)
        else:
            triplets_df.at[index, "target"] = category_dict[category]
            

triplets_df.to_csv("tripletas/tripletas.csv", index=False)
    
    
import pandas as pd

file_countries = ["chilenos", "argentinos", "peruanos", "bolivianos", "uruguayos", "paraguayos", "ecuatorianos", "colombianos", "venezolanos"]

#Combinar las tripletas de los paises
df = pd.DataFrame(columns = ["source","relation","target"])
for country in file_countries:

    triplet_file = f"./tripletas/tripletas_{country}.csv"
    
    triplet_df = pd.read_csv(triplet_file)
    df = pd.concat([triplet_df, df], ignore_index=False)
    
df.to_csv("tripletas/tripletas.csv", index=False)
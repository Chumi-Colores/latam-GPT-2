import pandas as pd


df = pd.read_csv("tripletas/tripletas.csv")
df = df[df["relation"] == "pertenece a la categoria"]
df = df[["target"]]
df = df.drop_duplicates()
print(df)
df.to_csv("categorias.csv", index=False)
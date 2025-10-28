import pandas as pd
import json

triplets = pd.read_csv("tripletas/tripletas.csv")
book_relations = json.loads(open("relaciones_libros.json").read())


import pandas as pd
import random
import json

NUMBER_OF_QUESTIONS_PER_CATEGORY = 100

triplets = pd.read_csv("tripletas/tripletas.csv")
book_relations = json.loads(open("relaciones.json").read())

df_author_names = triplets[triplets["relation"] == "es autor de la obra"]
df_author_names = df_author_names[["source"]].drop_duplicates()

book_names = list(book_relations.keys())

# Preguntas de autoría
rows_list = []
visited_books = set()
for i in range(NUMBER_OF_QUESTIONS_PER_CATEGORY):
    
    book_name = random.choice(book_names) 
    while book_name in visited_books:
        book_name = random.choice(book_names)
    
    visited_books.add(book_name)

    true_author = book_relations[book_name]["autor"]

    false_alternatives = []
    while len(false_alternatives) < 3:
        false_author = random.choice(df_author_names["source"].values)
        if false_author != true_author:
            false_alternatives.append(false_author)
    
    alternatives = [true_author] + false_alternatives
    random.shuffle(alternatives)
    
    first_question = f"¿Quién es el autor de la obra {book_name}?; Responde con una de estas opciones: (a) {alternatives[0]}, (b) {alternatives[1]}, (c) {alternatives[2]}, (d) {alternatives[3]}"

    rows_list.append({"pregunta": first_question, "respuesta": true_author})

df_authorship_questions = pd.DataFrame(rows_list)

df_authorship_questions.to_csv("preguntas/preguntas_autoria.csv", index=False)


# Preguntas de nacionalidad

nationality_map = {"chilena": "Chile", 
                   "argentina": "Argentina", 
                   "peruana": "Peru", 
                   "boliviana": "Bolivia", 
                   "uruguaya": "Uruguay", ""
                   "paraguaya": "Paraguay", ""
                   "ecuatoriana": "Ecuador", 
                   "colombiana": "Colombia", 
                   "venezolana": "Venezuela"}

rows_list = []
visited_books = set()
for i in range(NUMBER_OF_QUESTIONS_PER_CATEGORY):
    book_name = random.choice(book_names) 
    while book_name in visited_books:
        book_name = random.choice(book_names)
    
    visited_books.add(book_name)

    nationality = book_relations[book_name]["nacionalidad"]
    country = nationality_map[nationality]

    first_question = f"De qué país es el autor de la obra {book_name}?"

    rows_list.append({"pregunta": first_question, "respuesta": country})

df_nationality_questions = pd.DataFrame(rows_list)

df_nationality_questions.to_csv("preguntas/preguntas_nacionalidad.csv", index=False)


#Preguntas fecha de publicación

rows_list = []
visited_books = set()
for i in range(NUMBER_OF_QUESTIONS_PER_CATEGORY):
    book_name = random.choice(book_names) 
    while book_name in visited_books or book_relations[book_name]["fecha"] == None:
        book_name = random.choice(book_names)
    
    visited_books.add(book_name)

    year = book_relations[book_name]["fecha"]

    first_question = f"En cual año fue publicada la obra {book_name}?"

    rows_list.append({"pregunta": first_question, "respuesta": year})

df_year_questions = pd.DataFrame(rows_list)

df_year_questions.to_csv("preguntas/preguntas_fecha_publicacion.csv", index=False)




# Preguntas de categoría
rows_list = []
visited_books = set()
for i in range(NUMBER_OF_QUESTIONS_PER_CATEGORY):
    book_name = random.choice(book_names) 
    while book_name in visited_books or book_relations[book_name]["categorias"] == []:
        book_name = random.choice(book_names)
    
    visited_books.add(book_name)

    categories = book_relations[book_name]["categorias"]

    first_question = f"A qué categoría pertenece la obra {book_name}?"

    second_question = f"Estas son las categorias a las que pertenece la obra: {', '.join(categories)}. ¿Respondiste bien? Responde con sí o no."
    
    rows_list.append({"primera pregunta": first_question, "segunda pregunta": second_question})


df_category_questions = pd.DataFrame(rows_list)

df_category_questions.to_csv("preguntas/preguntas_categoria.csv", index=False)


# Preguntas editoriales
rows_list = []
visited_books = set()
for i in range(NUMBER_OF_QUESTIONS_PER_CATEGORY):
    book_name= random.choice(book_names)
    while book_name in visited_books or book_relations[book_name]["editoriales"] == []:
        book_name = random.choice(book_names)
    
    visited_books.add(book_name)

    editoriales = book_relations[book_name]["editoriales"]

    first_question = f"Dime alguna editorial que haya publicado la obra {book_name}?"

    second_question = f"Estas son las editoriales que han publicado la obra: {', '.join(editoriales)}. ¿Respondiste bien? Responde con sí o no."
    
    rows_list.append({"primera pregunta": first_question, "segunda pregunta": second_question})


df_publisher_questions = pd.DataFrame(rows_list)

df_publisher_questions.to_csv("preguntas/preguntas_editoriales.csv", index=False)
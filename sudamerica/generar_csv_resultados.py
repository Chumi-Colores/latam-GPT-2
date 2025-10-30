import pandas as pd
import json

df_authorship_questions = pd.read_csv("preguntas/preguntas_autoria.csv")
df_year_questions = pd.read_csv("preguntas/preguntas_fecha_publicacion.csv")
df_nationality_questions = pd.read_csv("preguntas/preguntas_nacionalidad.csv")
df_publisher_questions = pd.read_csv("preguntas/preguntas_editoriales.csv")
df_category_questions = pd.read_csv("preguntas/preguntas_categoria.csv")

authorship_correct_indices = json.loads(open("evaluacion_modelos/gemeni/autoria.json").read())["indices_correctas"]
year_correct_indices = json.loads(open("evaluacion_modelos/gemeni/fecha.json").read())["indices_correctas"]
nationality_correct_indices = json.loads(open("evaluacion_modelos/gemeni/nacionalidad.json").read())["indices_correctas"]
publisher_correct_indices = json.loads(open("evaluacion_modelos/gemeni/editoriales.json").read())["indices_correctas"]
category_correct_indices = json.loads(open("evaluacion_modelos/gemeni/categoria.json").read())["indices_correctas"]

df_evaluation = pd.DataFrame(columns=["Tipo de pregunta", "pregunta", "respuesta correcta", "primer prompt", "segundo prompt", "score"])


    
df_accuracies = pd.DataFrame([{"Tipo de pregunta": "P1", "porcentaje correctas": len(authorship_correct_indices) / 100}])
df_accuracies = pd.concat([df_accuracies, pd.DataFrame([{"Tipo de pregunta": "P2", "porcentaje correctas": len(nationality_correct_indices) / 100}])])
df_accuracies = pd.concat([df_accuracies, pd.DataFrame([{"Tipo de pregunta": "P3", "porcentaje correctas": len(year_correct_indices) / 100}])])
df_accuracies = pd.concat([df_accuracies, pd.DataFrame([{"Tipo de pregunta": "P4", "porcentaje correctas": len(category_correct_indices) / 100}])])
df_accuracies = pd.concat([df_accuracies, pd.DataFrame([{"Tipo de pregunta": "P5", "porcentaje correctas": len(publisher_correct_indices) / 100}])])
df_accuracies.to_csv("evaluacion_modelos/gemeni/porcentaje_aciertos.csv", index=False)


for index, row in df_authorship_questions.iterrows():
    df_row = pd.DataFrame([{
        "Tipo de pregunta": "P1",
        "pregunta": row["pregunta"],
        "respuesta correcta": row["respuesta"],
        "primer prompt": None,
        "segundo prompt": None,
        "score": 1 if index in authorship_correct_indices else 0
        }])
    
    df_evaluation = pd.concat([df_evaluation, df_row], ignore_index=True)



for index, row in df_nationality_questions.iterrows():
    
    df_row = pd.DataFrame([{
        "Tipo de pregunta": "P2",
        "pregunta": row["pregunta"],
        "respuesta correcta": row["respuesta"],
        "primer prompt": None,
        "segundo prompt": None,
        "score": 1 if index in nationality_correct_indices else 0
        }])
    
    df_evaluation = pd.concat([df_evaluation, df_row], ignore_index=True)
    



for index, row in df_year_questions.iterrows():
    
    df_row = pd.DataFrame([{
        "Tipo de pregunta": "P3",
        "pregunta": row["pregunta"],
        "respuesta correcta": row["respuesta"],
        "primer prompt": None,
        "segundo prompt": None,
        "score": 1 if index in year_correct_indices else 0
        }])
    
    df_evaluation = pd.concat([df_evaluation, df_row], ignore_index=True)


for index, row in df_category_questions.iterrows():
    
    df_row = pd.DataFrame([{
        "Tipo de pregunta": "P4",
        "pregunta": None,
        "respuesta correcta": None,
        "primer prompt": row["primera pregunta"],
        "segundo prompt": row["segunda pregunta"],
        "score": 1 if index in year_correct_indices else 0
        }])
    
    df_evaluation = pd.concat([df_evaluation, df_row], ignore_index=True)


for index, row in df_publisher_questions.iterrows():
    
    df_row = pd.DataFrame([{
        "Tipo de pregunta": "P5",
        "pregunta": None,
        "respuesta correcta": None,
        "primer prompt": row["primera pregunta"],
        "segundo prompt": row["segunda pregunta"],
        "score": 1 if index in publisher_correct_indices else 0
        }])
    
    df_evaluation = pd.concat([df_evaluation, df_row], ignore_index=True)



df_evaluation.to_csv("evaluacion_modelos/gemeni/evaluacion.csv", index=False)

import google.genai as genai
import dotenv
import os
import pandas as pd
import time
import json


dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")

client = genai.Client(api_key=API_KEY) 


df_year_questions = pd.read_csv("preguntas/preguntas_fecha_publicacion.csv")
df_nationality_questions = pd.read_csv("preguntas/preguntas_nacionalidad.csv")
df_publisher_questions = pd.read_csv("preguntas/preguntas_editoriales.csv")

def evaluar_preguntas_autoria(checkpoint_index = 0, correct_answers = 0, wrong_answers = 0, correct_indices = [], incorret_indices = []):

    df_authorship_questions = pd.read_csv("preguntas/preguntas_autoria.csv")
    
    correct_answers = correct_answers
    wrong_answers = wrong_answers
    correct_indices = correct_indices
    incorret_indices = incorret_indices
    for index, row in df_authorship_questions.iterrows():
        
        if index < checkpoint_index:
            continue
        
        question = row["pregunta"]
        true_answer = row["respuesta"]
        
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=question
            )
        except Exception as e:
            print(e)
            if "429" in str(e):
                print("Limite de peticiones alcanzado, esperando 1 minuto")
                time.sleep(60)
                evaluar_preguntas_autoria(checkpoint_index = index, 
                                          correct_answers = correct_answers, 
                                          wrong_answers = wrong_answers, 
                                          correct_indices = correct_indices, 
                                          incorret_indices = incorret_indices)
                return
        
        model_response = response.text
        print("Respuesta real:",true_answer)
        print("Respuesta del modelo:",model_response)
        
        if true_answer.lower() in model_response.lower():
            correct_answers += 1
            correct_indices.append(index)
            print("Correcto")
        else:
            wrong_answers += 1
            incorret_indices.append(index)
            print("Incorrecto")
        
        time.sleep(1)
    
    with open("evaluacion_modelos/gemeni/autoria.json", "w") as f:
        resultados = {"correctas": correct_answers, "incorrectas": wrong_answers, "indices_correctas": correct_indices, "indices_incorrectas": incorret_indices}
        json.dump(resultados, f)

    return

def evaluar_preguntas_categoria(checkpoint_index = 0, correct_answers = 0, wrong_answers = 0, correct_indices = [], incorret_indices = []):

    df_category_questions = pd.read_csv("preguntas/preguntas_categoria.csv")
    
    correct_answers = correct_answers
    wrong_answers = wrong_answers
    correct_indices = correct_indices
    incorret_indices = incorret_indices
    for index, row in df_category_questions.iterrows():
        
        if index < checkpoint_index:
            continue
        
        primera_pregunta = row["primera pregunta"]
        segunda_pregunta = row["segunda pregunta"]
        
        try:
            
            first_prompt = primera_pregunta + ". Entrega solo una categoria"
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=first_prompt
            )
            
            model_answer = response.text
            
            prompt_followup = f"Tu respuesta a la pregunta {first_prompt} fue {model_answer}. {segunda_pregunta}"
            
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt_followup
            )
            
        except Exception as e:    
            print(e)
            if "429" in str(e):
                print("Limite de peticiones alcanzado, esperando 1 minuto")
                time.sleep(60)
                
                with open("checkpoint_categoria.json", "w") as f:
                    resultados = {"correctas": correct_answers, "incorrectas": wrong_answers, "indices_correctas": correct_indices, "indices_incorrectas": incorret_indices}
                    json.dump(resultados, f)
                
                
                evaluar_preguntas_categoria(checkpoint_index = index, 
                                          correct_answers = correct_answers, 
                                          wrong_answers = wrong_answers, 
                                          correct_indices = correct_indices, 
                                          incorret_indices = incorret_indices)
                return
            
        model_response = response.text
        print("Respuesta del modelo: ",model_response)
        
        if "si" in model_response.lower() or "sí" in model_response.lower():
            correct_answers += 1
            correct_indices.append(index)
            print("Correcto")
            
        else:
            wrong_answers += 1
            incorret_indices.append(index)
            print("Incorrecto")
            
            
        time.sleep(1)
    
    with open("evaluacion_modelos/gemeni/categoria.json", "w") as f:
        resultados = {"correctas": correct_answers, "incorrectas": wrong_answers, "indices_correctas": correct_indices, "indices_incorrectas": incorret_indices}
        json.dump(resultados, f)

    return
    
            

         
def evaluar_preguntas_fecha(checkpoint_index = 0, correct_answers = 0, decade_correct_answers = 0, wrong_answers = 0, correct_indices = [], decade_correct_indices = [], incorret_indices = []):
    
    df_year_questions = pd.read_csv("preguntas/preguntas_fecha_publicacion.csv")
    
    correct_answers = correct_answers
    decade_correct_answers = decade_correct_answers
    wrong_answers = wrong_answers
    correct_indices = correct_indices
    decade_correct_indices = decade_correct_indices
    incorret_indices = incorret_indices
    
    for index, row in df_year_questions.iterrows():
        
        if index < checkpoint_index:
            continue
        
        question = row["pregunta"]
        true_answer = int(row["respuesta"])
        
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=question
            )
        except Exception as e:
            print(e)
            if "429" in str(e):
                print("Limite de peticiones alcanzado, esperando 1 minuto")
                time.sleep(60)
                
                with open("checkpoint_fecha.json", "w") as f:
                    resultados = {"correctas": correct_answers, 
                                  "incorrectas": wrong_answers, 
                                  "decade_correctas": decade_correct_answers,
                                  "indices_correctas": correct_indices, 
                                  "indices_decades_correctas": decade_correct_indices,
                                  "indices_incorrectas": incorret_indices
                                  }
                    json.dump(resultados, f)
                
                evaluar_preguntas_fecha(checkpoint_index = index,
                                        correct_answers = correct_answers, 
                                        decade_correct_answers = decade_correct_answers,
                                        wrong_answers = wrong_answers, 
                                        correct_indices = correct_indices, 
                                        decade_correct_indices = decade_correct_indices,
                                        incorret_indices = incorret_indices)
                return
        
        model_response = response.text
        print("Respuesta real:",true_answer)
        print("Respuesta del modelo:",model_response)
        
        #Parsear año
        import re
        year_match = re.search(r'\b(1[0-9]{3}|2[0-9]{3})\b', model_response)
        if year_match:
            model_response = int(year_match.group())
        else:
            model_response = 0
        
        # año dentro de la misma decada
        
        if true_answer == model_response:
            correct_answers += 1
            correct_indices.append(index)
            print("Correcto")
        
        elif (true_answer // 10) * 10 == model_response // 10 * 10:
            decade_correct_answers += 1
            decade_correct_indices.append(index)
            print("Decada correcta")
            
        else:
            wrong_answers += 1
            incorret_indices.append(index)
            print("Incorrecto")
        
        
        time.sleep(1)
    
    with open("evaluacion_modelos/gemeni/fecha.json", "w") as f:
        resultados = {"correctas": correct_answers, 
                      "incorrectas": wrong_answers, 
                      "decadas_correctas": decade_correct_answers,
                      "indices_correctas": correct_indices, 
                      "indices_decadas_correctas": decade_correct_indices,
                      "indices_incorrectas": incorret_indices}
        json.dump(resultados, f)

    return



if __name__ == "__main__":
    evaluar_preguntas_categoria()
    evaluar_preguntas_fecha()
    
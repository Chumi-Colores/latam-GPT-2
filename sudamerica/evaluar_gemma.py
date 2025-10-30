import ollama
import pandas as pd
import time
import json

def evaluar_preguntas_autoria(checkpoint_index=0, correct_answers=0, wrong_answers=0, correct_indices=[], incorret_indices=[]):

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
            response = ollama.chat(
                model="gemma3",
                messages=[{"role": "user", "content": question}]
            )
            model_response = response["message"]["content"]
        except Exception as e:
            print(e)
            print("Error en la petición, esperando 1 minuto")
            time.sleep(60)
            evaluar_preguntas_autoria(
                checkpoint_index=index,
                correct_answers=correct_answers,
                wrong_answers=wrong_answers,
                correct_indices=correct_indices,
                incorret_indices=incorret_indices
            )
            return

        print("Respuesta real:", true_answer)
        print("Respuesta del modelo:", model_response)

        if true_answer.lower() in model_response.lower():
            correct_answers += 1
            correct_indices.append(index)
            print("Correcto")
        else:
            wrong_answers += 1
            incorret_indices.append(index)
            print("Incorrecto")

        time.sleep(1)

    with open("evaluacion_modelos/gemma3/autoria.json", "w") as f:
        resultados = {
            "correctas": correct_answers,
            "incorrectas": wrong_answers,
            "indices_correctas": correct_indices,
            "indices_incorrectas": incorret_indices
        }
        json.dump(resultados, f)

    return


def evaluar_preguntas_categoria(checkpoint_index=0, correct_answers=0, wrong_answers=0, correct_indices=[], incorret_indices=[]):

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
            response = ollama.chat(
                model="gemma3",
                messages=[{"role": "user", "content": first_prompt}]
            )
            model_answer = response["message"]["content"]

            print("Respuesta al primer prompt:", model_answer)
            print("Segunda Pregunta", segunda_pregunta)
            
            prompt_followup = f"Tu respuesta a la pregunta {first_prompt} fue {model_answer}. {segunda_pregunta}"

            response = ollama.chat(
                model="gemma3",
                messages=[{"role": "user", "content": prompt_followup}]
            )

        except Exception as e:
            print(e)
            print("Error en la petición, esperando 1 minuto")
            time.sleep(60)

            with open("checkpoint_categoria.json", "w") as f:
                resultados = {
                    "correctas": correct_answers,
                    "incorrectas": wrong_answers,
                    "indices_correctas": correct_indices,
                    "indices_incorrectas": incorret_indices
                }
                json.dump(resultados, f)

            evaluar_preguntas_categoria(
                checkpoint_index=index,
                correct_answers=correct_answers,
                wrong_answers=wrong_answers,
                correct_indices=correct_indices,
                incorret_indices=incorret_indices
            )
            return

        model_response = response["message"]["content"]
        print("Respuesta del modelo:", model_response)

        if "si" in model_response.lower() or "sí" in model_response.lower():
            correct_answers += 1
            correct_indices.append(index)
            print("Correcto")

        else:
            wrong_answers += 1
            incorret_indices.append(index)
            print("Incorrecto")

        time.sleep(1)

    with open("evaluacion_modelos/gemma3/categoria.json", "w") as f:
        resultados = {
            "correctas": correct_answers,
            "incorrectas": wrong_answers,
            "indices_correctas": correct_indices,
            "indices_incorrectas": incorret_indices
        }
        json.dump(resultados, f)

    return


def evaluar_preguntas_fecha(checkpoint_index=0, correct_answers=0, decade_correct_answers=0, wrong_answers=0, correct_indices=[], decade_correct_indices=[], incorret_indices=[]):

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
            response = ollama.chat(
                model="gemma3",
                messages=[{"role": "user", "content": question}]
            )
            model_response = response["message"]["content"]
        except Exception as e:
            print(e)
            print("Error en la petición, esperando 1 minuto")
            time.sleep(60)

            with open("checkpoint_fecha.json", "w") as f:
                resultados = {
                    "correctas": correct_answers,
                    "incorrectas": wrong_answers,
                    "decade_correctas": decade_correct_answers,
                    "indices_correctas": correct_indices,
                    "indices_decades_correctas": decade_correct_indices,
                    "indices_incorrectas": incorret_indices
                }
                json.dump(resultados, f)

            evaluar_preguntas_fecha(
                checkpoint_index=index,
                correct_answers=correct_answers,
                decade_correct_answers=decade_correct_answers,
                wrong_answers=wrong_answers,
                correct_indices=correct_indices,
                decade_correct_indices=decade_correct_indices,
                incorret_indices=incorret_indices
            )
            return

        print("Respuesta real:", true_answer)
        print("Respuesta del modelo:", model_response)

        import re
        year_match = re.search(r'\b(1[0-9]{3}|2[0-9]{3})\b', model_response)
        if year_match:
            model_response = int(year_match.group())
        else:
            model_response = 0

        if true_answer == model_response:
            correct_answers += 1
            correct_indices.append(index)
            print("Correcto")

        elif (true_answer // 10) * 10 == (model_response // 10) * 10:
            decade_correct_answers += 1
            decade_correct_indices.append(index)
            print("Decada correcta")

        else:
            wrong_answers += 1
            incorret_indices.append(index)
            print("Incorrecto")

        time.sleep(1)

    with open("evaluacion_modelos/gemma3/fecha.json", "w") as f:
        resultados = {
            "correctas": correct_answers,
            "incorrectas": wrong_answers,
            "decadas_correctas": decade_correct_answers,
            "indices_correctas": correct_indices,
            "indices_decadas_correctas": decade_correct_indices,
            "indices_incorrectas": incorret_indices
        }
        json.dump(resultados, f)

    return


def evaluar_preguntas_nacionalidad(checkpoint_index=0, correct_answers=0, wrong_answers=0, correct_indices=[], incorret_indices=[]):

    df_nationality_questions = pd.read_csv("preguntas/preguntas_nacionalidad.csv")

    correct_answers = correct_answers
    wrong_answers = wrong_answers
    correct_indices = correct_indices
    incorret_indices = incorret_indices
    for index, row in df_nationality_questions.iterrows():

        if index < checkpoint_index:
            continue

        question = row["pregunta"] + ". Responde solo con el nombre de un país y nada más."
        true_answer = row["respuesta"]

        try:
            response = ollama.chat(
                model="gemma3",
                messages=[{"role": "user", "content": question}]
            )
            model_response = response["message"]["content"]
        except Exception as e:
            print(e)
            print("Error en la petición, esperando 1 minuto")
            time.sleep(60)

            with open("checkpoint_nacionalidad.json", "w") as f:
                resultados = {
                    "correctas": correct_answers,
                    "incorrectas": wrong_answers,
                    "indices_correctas": correct_indices,
                    "indices_incorrectas": incorret_indices
                }
                json.dump(resultados, f)

            evaluar_preguntas_nacionalidad(
                checkpoint_index=index,
                correct_answers=correct_answers,
                wrong_answers=wrong_answers,
                correct_indices=correct_indices,
                incorret_indices=incorret_indices
            )
            return

        print("Respuesta real:", true_answer)
        print("Respuesta del modelo:", model_response)

        if true_answer.lower() == model_response.lower():
            correct_answers += 1
            correct_indices.append(index)
            print("Correcto")

        else:
            wrong_answers += 1
            incorret_indices.append(index)
            print("Incorrecto")

        time.sleep(1)

    with open("evaluacion_modelos/gemma3/nacionalidad.json", "w") as f:
        resultados = {
            "correctas": correct_answers,
            "incorrectas": wrong_answers,
            "indices_correctas": correct_indices,
            "indices_incorrectas": incorret_indices
        }
        json.dump(resultados, f)

    return


def evaluar_preguntas_editoriales(checkpoint_index=0, correct_answers=0, wrong_answers=0, correct_indices=[], incorret_indices=[]):
    df_publisher_questions = pd.read_csv("preguntas/preguntas_editoriales.csv")

    correct_answers = correct_answers
    wrong_answers = wrong_answers
    correct_indices = correct_indices
    incorret_indices = incorret_indices
    for index, row in df_publisher_questions.iterrows():

        if index < checkpoint_index:
            continue

        primera_pregunta = row["primera pregunta"]
        segunda_pregunta = row["segunda pregunta"]

        try:
            first_prompt = primera_pregunta + ". Entrega solo una editorial."
            response = ollama.chat(
                model="gemma3",
                messages=[{"role": "user", "content": first_prompt}]
            )
            model_answer = response["message"]["content"]

            print("Respuesta al primer prompt:", model_answer)
            print("Segunda Pregunta", segunda_pregunta)
            prompt_followup = f"Tu respuesta a la pregunta {first_prompt} fue {model_answer}. {segunda_pregunta}"

            response = ollama.chat(
                model="gemma3",
                messages=[{"role": "system", "content": prompt_followup}]
            )

        except Exception as e:
            print(e)
            print("Error en la petición, esperando 1 minuto")
            time.sleep(60)

            with open("checkpoint_editoriales.json", "w") as f:
                resultados = {
                    "correctas": correct_answers,
                    "incorrectas": wrong_answers,
                    "indices_correctas": correct_indices,
                    "indices_incorrectas": incorret_indices
                }
                json.dump(resultados, f)

            evaluar_preguntas_editoriales(
                checkpoint_index=index,
                correct_answers=correct_answers,
                wrong_answers=wrong_answers,
                correct_indices=correct_indices,
                incorret_indices=incorret_indices
            )
            return

        model_response = response["message"]["content"]
        print("Respuesta del modelo:", model_response)

        if "si" in model_response.lower() or "sí" in model_response.lower():
            correct_answers += 1
            correct_indices.append(index)
            print("Correcto")

        else:
            wrong_answers += 1
            incorret_indices.append(index)
            print("Incorrecto")

        time.sleep(1)

    with open("evaluacion_modelos/gemma3/editoriales.json", "w") as f:
        resultados = {
            "correctas": correct_answers,
            "incorrectas": wrong_answers,
            "indices_correctas": correct_indices,
            "indices_incorrectas": incorret_indices
        }
        json.dump(resultados, f)

    return


if __name__ == "__main__":
    evaluar_preguntas_editoriales()
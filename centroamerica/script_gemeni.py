import google.genai as genai
import dotenv
import os
import json
import time


#Obtener API KEY en https://aistudio.google.com/welcome
#pip install google-generativeai
# Crear .env con API_KEY=

def ask_author_country_from_work_title(question, answers, client) -> int:
    prompt = question
    answer = answers[0]
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )
    print("Response:", response.text)
    if answer.lower() in response.text.lower():
        return 1
    return 0

def ask_author_name_from_work_title(question, answers, client) -> int:
    prompt = question
    answer = answers[0]
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )
    return ask_another_model_if_question_was_correctly_answered(question, response.text, answers, client)

def ask_publish_date_from_work_title(question, answers, client) -> float:
    prompt = question
    answer = answers[0]
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )
    if answer in response.text:
        return 1
    # check if at least the decade is correct
    if answer[:3] in response.text:
        return 0.5
    return 0

def ask_publisher_from_work_title(question, answers, client) -> int:
    prompt = question
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )
    return ask_another_model_if_question_was_correctly_answered(question, response.text, answers, client)

def ask_subjects_from_work_title(question, answers, client) -> int:
    prompt = question
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )
    return ask_another_model_if_question_was_correctly_answered(question, response.text, answers, client)

def ask_another_model_if_question_was_correctly_answered(question, first_model_response, answers, client) -> int:
    prompt = f"I asked my student the following question: '{question}'. The student answered: {first_model_response}'. The correct answer(s) is/are: {answers}. Does their response contain the correct answer or at least is it sufficiently close to the correct answer? Please respond with 'yes' or 'no'."
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )
    print("First model response:", first_model_response)
    print("Correct answers:", answers)
    print("Second model response:", response.text)
    print("-------------------------------------------")
    if "yes" in response.text.lower():
        return 1
    return 0

dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")

client = genai.Client(api_key=API_KEY)

def ask_all_questions_from_file(file_name, ask_function, client, prompts_per_question):
    with open(f"centroamerica/test_questions/{file_name}.json", "r", encoding="utf-8") as f:
        questions_data = json.load(f)
    total_questions = len(questions_data)
    correct_answers = 0
    i = 1
    for item in questions_data:
        if i % (10//prompts_per_question) == 0:
            time.sleep(59)
        print(f"question {i}")
        question = item["question"]
        answers = item["answers"]
        score = ask_function(question, answers, client)
        if score > 0:
            correct_answers += score
            print("Correct answer!")
        else:
            print("Incorrect answer.")
        i += 1
    print(f"{file_name}: {correct_answers}/{total_questions} correct answers.")
    return correct_answers, total_questions

correct_answers_5, total_questions_5 = ask_all_questions_from_file("subjects_from_work_title_questions", ask_subjects_from_work_title, client, 2)

total_correct_answers = (correct_answers_5)
total_questions = (total_questions_5)
print("=======================================")
print("FINAL RESULTS")
print(f"subjects from work title: {correct_answers_5}/{total_questions_5} correct answers.")
print(f"Overall: {total_correct_answers}/{total_questions} correct answers.")

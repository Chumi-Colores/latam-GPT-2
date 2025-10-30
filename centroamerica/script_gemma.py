import ollama
from enum import Enum
import json
import time

print(ollama.list())
""""
First install Ollama, then install ollama python library:
In one terminal run: ollama serve
In another terminal run: ollama pull gemma3:27b
Then run this script.
"""

def get_gemma_answer(prompt: str) -> str:
    
  response: ollama.ChatResponse = ollama.chat(model='gemma3:4b', messages=[
    {
      'role': 'user',
      'content': prompt,
    },
  ])
  return response['message']['content'].strip()


def make_question(question: str, question_type: str) -> str:
    suffix = ""
    if question_type == "author_name_from_work_title":
        suffix = "Respond only with the author's name(s)."
    elif question_type == "author_country_from_work_title":
        suffix = "Respond only with the author's country."
    elif question_type == "publish_date_from_work_title":
        suffix = "Respond only with the year."
    elif question_type == "subjects_from_work_title":
        suffix = "Respond only with one genre or subject."
    elif question_type == "publisher_from_work_title":
        suffix = "Respond only with one publisher's name."
    
    prompt = f"{question}. {suffix}"
    print("Prompt:", prompt)

    return get_gemma_answer(prompt)

def eval_answer(answer: str, question_type: str, expected_answer: str) -> bool:
    prompt = ""
    expected_answer = f"{expected_answer}"[1:-1].replace("'", "").replace('"', '')
    print("Model answer:", answer)
    print("Expected answer:", expected_answer)
    if question_type in ("author_country_from_work_title", "publish_date_from_work_title", "author_name_from_work_title"):
        prompt = f"Is '{answer}' the correct answer if the expected answer is {expected_answer}? Respond with 'Yes' or 'No'."    
    else:
        prompt = f"Is '{answer}' the correct answer if the expected answer is one of {expected_answer}? Respond with 'Yes' or 'No'."

    answer = get_gemma_answer(prompt)
    return True if 'yes' in answer.lower() else False

def ask_all_questions_from_file(file_name):
    with open(f"centroamerica/test_questions/{file_name}.json", "r", encoding="utf-8") as f:
        questions_data = json.load(f)
    i = 0
    score = 0
    for item in questions_data:
        print(f"question {i}")
        question = item["question"]
        answers = item["answers"]
        model_answer = make_question(question, file_name)
        is_correct = eval_answer(model_answer, file_name, answers)
        if is_correct:
            print("Correct answer!")
        else:
            print("Incorrect answer.")
        score += 1 if is_correct else 0
        time.sleep(1)

        i += 1
    print(f"Final score for {file_name}: {score}/{len(questions_data)}")

if __name__ == "__main__":
    ask_all_questions_from_file("subjects_from_work_title")


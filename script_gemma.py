from ollama import chat
from ollama import ChatResponse
from enum import Enum


""""
First install Ollama, then install ollama python library:
In one terminal run: ollama serve
In another terminal run: ollama pull gemma3:27b
Then run this script.
"""



class QuestionType(Enum):
    AUTHORS = "P1"
    COUNTRY = "P2"
    COUNTRY_AUTHOR = "P3"
    YEAR = "P4"
    GENRE = "P5"
    PUBLISHER = "P6"


def get_gemma_answer(prompt: str) -> str:
    
  response: ChatResponse = chat(model='gemma3:27b', messages=[
    {
      'role': 'user',
      'content': prompt,
    },
  ])
  return response['message']['content'].strip()


def make_question(question: str, question_type: QuestionType) -> str:
    suffix = ""
    if question_type == QuestionType.AUTHORS:
        suffix = "Respond only with the author's name(s)."
    elif question_type == QuestionType.COUNTRY:
        suffix = "Respond only with the country name."
    elif question_type == QuestionType.COUNTRY_AUTHOR:
        suffix = "Respond only with the country name."
    elif question_type == QuestionType.YEAR:
        suffix = "Respond only with the year."
    elif question_type == QuestionType.GENRE:
        suffix = "Respond only with one genre or subject."
    elif question_type == QuestionType.PUBLISHER:
        suffix = "Respond only with one publisher's name."
    
    promt = f"{question}. {suffix}"

    return get_gemma_answer(promt)

def eval_answer(answer: str, question_type: QuestionType, expected_answer: str) -> bool:
    promt = ""
    if question_type in (QuestionType.AUTHORS, QuestionType.YEAR, QuestionType.COUNTRY):
        promt = f"Is '{answer}' the correct answer if the expected answer is {expected_answer}? Respond with 'Yes' or 'No'."    
    else:
        promt = f"Is '{answer}' the correct answer if the expected answer is one of {expected_answer}? Respond with 'Yes' or 'No'."

    answer = get_gemma_answer(promt)
    return True if 'yes' in answer.lower() else False

if __name__ == "__main__":
    import pandas as pd
    from tqdm import tqdm

    eng_questions = pd.read_csv('Preguntas y Respuestas/preguntas_respuestas_6tipos.csv')

    answers = []
    for _, row in tqdm(eng_questions.iterrows(), total=len(eng_questions), desc="Procesando"):
        answer = make_question(row['pregunta'], QuestionType(row['tipo']))
        is_correct = eval_answer(answer, QuestionType(row['tipo']), row['respuesta'])
        answers.append({
            'question': row['pregunta'],
            'type': row['tipo'],    
            'expected_answer': row['respuesta'],
            'model_answer': answer,
            'is_correct': is_correct
        })

    answers_df = pd.DataFrame(answers)
    answers_df.to_csv('gemma3-27b_answers_eval.csv', index=False)

    print(answers_df.groupby('type')['is_correct'].mean())

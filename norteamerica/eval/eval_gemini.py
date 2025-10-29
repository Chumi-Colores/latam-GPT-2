from google import genai
from dotenv import load_dotenv
import os 
from enum import Enum
from time import sleep

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

class QuestionType(Enum):
    AUTHORS = "P1"
    COUNTRY = "P2"
    YEAR = "P3"
    GENRE = "P4"
    PUBLISHER = "P5"


def get_gemini_answer(prompt: str) -> str:
    retries = 5
    delay = 60 
    
    for i in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )
            return response.text
        
        except Exception as e:
            if "429" in str(e):
                if i == retries - 1:
                    print(f"Error 429: Rate limit exceeded after {retries} attempts. Aborting.")
                    raise e
                
                print(f"Error 429: Limit rate exceeded. Retrying in {delay} seconds...")
                sleep(delay)
                delay *= 2
            
            else:
                print(f"Error inesperado de la API: {e}")
                raise e
    
    raise Exception("Can't get response from Gemini API after multiple attempts.")


def make_question(question: str, question_type: QuestionType) -> str:
    suffix = ""
    if question_type == QuestionType.AUTHORS:
        suffix = "Respond only with the author's name(s)."
    elif question_type == QuestionType.COUNTRY:
        suffix = "Respond only with the country name."
    elif question_type == QuestionType.YEAR:
        suffix = "Respond only with the year."
    elif question_type == QuestionType.GENRE:
        suffix = "Respond only with one genre or subject."
    elif question_type == QuestionType.PUBLISHER:
        suffix = "Respond only with one publisher's name."
    
    promt = f"{question}. {suffix}"

    return get_gemini_answer(promt)

def eval_answer(answer: str, question_type: QuestionType, expected_answer: str) -> bool:
    promt = ""
    if question_type in (QuestionType.AUTHORS, QuestionType.YEAR, QuestionType.COUNTRY):
        promt = f"Is '{answer}' the correct answer if the expected answer is {expected_answer}? Respond with 'Yes' or 'No'."    
    else:
        promt = f"Is '{answer}' the correct answer if the expected answer is one of {expected_answer}? Respond with 'Yes' or 'No'."

    answer = get_gemini_answer(promt)
    return True if 'yes' in answer.lower() else False

if __name__ == "__main__":
    import pandas as pd
    from tqdm import tqdm

    eng_questions = pd.read_csv('../data/questions_eng.csv')
    
    answesrs = []
    for _, row in tqdm(eng_questions.iterrows(), total=len(eng_questions), desc="Procesando"):
        answer = make_question(row['Question'], QuestionType(row['Type']))
        sleep(10)
        is_correct = eval_answer(answer, QuestionType(row['Type']), row['Answer'])
        answesrs.append({
            'question': row['Question'],
            'type': row['Type'],
            'expected_answer': row['Answer'],
            'model_answer': answer,
            'is_correct': is_correct
        })
        sleep(10)

    answers_df = pd.DataFrame(answesrs)
    answers_df.to_csv('./results/gemini_answers_eval.csv', index=False)

    print(answers_df.groupby('type')['is_correct'].mean())

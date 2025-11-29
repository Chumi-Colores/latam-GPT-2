from ollama import chat
from ollama import ChatResponse
from enum import Enum
import re
from unidecode import unidecode


""""
First install Ollama, then install ollama python library:
In one terminal run: ollama serve
In another terminal run: ollama pull gemma3:27b
Then run this script.
"""



class QuestionType(Enum):
    AUTHORS = "P1"
    COUNTRY = "P2"
    YEAR = "P3"
    GENRE = "P4"
    PUBLISHER = "P5"


# ---------------- Normalización y alias de países (multi-idioma) ----------------
COUNTRY_ALIASES = {
    "belgium": ["belgium","belgica","belgique","belgio","belgie","belgien","belgië","belgicka","belgia","belgia (pl)","belgická","belga","belgas"],
    "united kingdom": ["united kingdom","uk","u.k.","reino unido","gran bretaña","great britain","britain","gb","uk (britain)","britanico","británico","british","inglaterra","english","inglés","inglesa","británico","britanica"],
    "spain": ["spain","españa","espana","spanien","espagne","spagna","español","espanol","española","espanola"],
    "france": ["france","francia","frankreich","franca","frança","francés","frances","francesa"],
    "germany": ["germany","alemania","deutschland","allemagne","germania","alemán","aleman","alemana"],
    "italy": ["italy","italia","italien","italie","italiano","italiana"],
    "portugal": ["portugal","portogallo","portugués","portugues","portuguesa"],
    "switzerland": ["switzerland","suiza","schweiz","suisse","svizzera","suizo","suiza","suizos"],
    "austria": ["austria","österreich","autriche","austríaco","austriaco","austríaca","austriaca"],
    "poland": ["poland","polonia","polen","pologne","polacco","polaco","polaca"],
    "sweden": ["sweden","suecia","schweden","suède","svezia","sueco","sueca"],
    "netherlands": ["netherlands","países bajos","paises bajos","niederlande","pays-bas","paesi bassi","holanda","holandés","holandes","holandesa","dutch"],
}


def _normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = unidecode(str(s).strip().lower())
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _canonical_country(name: str) -> str:
    n = _normalize_text(name)
    for canon, aliases in COUNTRY_ALIASES.items():
        al_norm = [_normalize_text(a) for a in aliases] + [canon]
        if n == canon or n in al_norm:
            return canon
    return n


def country_match(model_text: str, expected_country_text: str) -> bool:
    mt = _normalize_text(model_text)
    canon = _canonical_country(expected_country_text)
    aliases = [_normalize_text(a) for a in COUNTRY_ALIASES.get(canon, [])] + [canon]
    # Coincidencia por inclusión para capturar frases como "es de España" o gentilicios
    return any(a in mt for a in aliases)


def get_gemma_answer(prompt: str) -> str:
    
  response: ChatResponse = chat(model='gemma3:latest', messages=[
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
    elif question_type == QuestionType.YEAR:
        suffix = "Respond only with the year."
    elif question_type == QuestionType.GENRE:
        suffix = "Respond only with one genre or subject."
    elif question_type == QuestionType.PUBLISHER:
        suffix = "Respond only with one publisher's name."
    
    promt = f"{question}. {suffix}"

    return get_gemma_answer(promt)

def eval_answer(answer: str, question_type: QuestionType, expected_answer: str) -> bool:
    # Regla específica para países: comparar con alias multi-idioma sin usar el modelo
    if question_type == QuestionType.COUNTRY:
        return country_match(answer, expected_answer)

    # Para autores y año: usar comparación directa con el LLM como estaba
    promt = ""
    if question_type in (QuestionType.AUTHORS, QuestionType.YEAR):
        promt = f"Is '{answer}' the correct answer if the expected answer is {expected_answer}? Respond with 'Yes' or 'No'."
    else:
        promt = f"Is '{answer}' the correct answer if the expected answer is one of {expected_answer}? Respond with 'Yes' or 'No'."

    validation = get_gemma_answer(promt)
    return True if 'yes' in validation.lower() else False

if __name__ == "__main__":
    import pandas as pd
    from tqdm import tqdm

    eng_questions = pd.read_csv('Preguntas y Respuestas/preguntas_respuestas_europe.csv')
    # eng_questions = pd.read_csv('Preguntas y Respuestas/preguntas_short.csv')

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
    answers_df.to_csv('gemma3_europa.csv', index=False)

    print(answers_df.groupby('type')['is_correct'].mean())

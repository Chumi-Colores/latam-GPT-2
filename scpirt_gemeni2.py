import os, time, re, json
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from unidecode import unidecode
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# =============== CONFIGURACIÓN ===============
MODEL_NAME = "models/gemini-2.5-flash"   # rápido y económico; puedes usar "gemini-1.5-pro" para mayor calidad
TEMPERATURE = 0.2                 # respuestas concisas/estables
MAX_OUTPUT_TOKENS = 256           # suficiente
LANG = "es"                       # idioma de respuesta esperado

API_KEY = os.getenv("API_KEY")
assert API_KEY, "Falta API_KEY en variables de entorno"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(
    MODEL_NAME,
    generation_config={
        "temperature": TEMPERATURE,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    },
)

COUNTRY_ALIASES = {
    "belgium": ["belgium","belgica","belgique","belgio","belgie","belgien","belgië","belgicka","belgia","belgia (pl)","belgická"],  # incluye varios idiomas comunes
    "united kingdom": ["united kingdom","uk","u.k.","reino unido","gran bretaña","great britain","britain","gb","uk (britain)","britanico","británico","british"],
    "spain": ["spain","españa","espana","spanien","espagne","spagna"],
    "france": ["france","francia","frankreich","franca","frança"],
    "germany": ["germany","alemania","deutschland","allemagne","germania"],
    "italy": ["italy","italia","italien","italie"],
    "portugal": ["portugal","portugual","portogallo","portugalf"],
    "switzerland": ["switzerland","suiza","schweiz","suisse","svizzera"],
    "austria": ["austria","österreich","autriche","austria (it)"],
    "poland": ["poland","polonia","polen","pologne","polonia (it)"],
    "sweden": ["sweden","suecia","schweden","suède","svezia"],
    "netherlands": ["netherlands","países bajos","paises bajos","niederlande","pays-bas","paesi bassi"],
    # agrega los que uses…
}

# =============== UTILIDADES ===============
def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = s.strip().lower()
    s = unidecode(s)    # quita tildes
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)  # saca signos
    s = re.sub(r"\s+", " ", s).strip()
    return s

def split_multi_answer(s: str):
    """
    Convierte 'A, B, C' en lista ['a','b','c'] normalizada
    Sirve para géneros/editoriales múltiples.
    """
    if s is None:
        return []
    parts = re.split(r"[;,/|]| y | o ", str(s))
    parts = [normalize_text(p) for p in parts if normalize_text(p)]
    return list(dict.fromkeys(parts))  # sin duplicados, preservando orden

def canonical_country(name: str) -> str:
    n = normalize_text(name)
    for canon, aliases in COUNTRY_ALIASES.items():
        if n == canon or n in [normalize_text(a) for a in aliases]:
            return canon
    return n  # si no lo mapeamos, usa tal cual

def eval_country(model_text: str, gold_text: str) -> int:
    mt = normalize_text(model_text)
    canon = canonical_country(gold_text)
    # acepta cualquiera de los alias del país esperado
    aliases = [normalize_text(a) for a in COUNTRY_ALIASES.get(canon, [])] + [canon]
    return int(any(a in mt for a in aliases))

# =============== EVALUADORES POR TIPO ===============
def eval_contains_any(model_text: str, gold_text: str) -> int:
    """
    Devuelve 1 si la respuesta del modelo contiene (normalizada) el gold.
    Útil para nacionalidad, autor, año, cuando la gold es única.
    """
    mt = normalize_text(model_text)
    gt = normalize_text(gold_text)
    return int(gt in mt)

def eval_any_of_list(model_text: str, gold_multi: str) -> int:
    """
    Devuelve 1 si la respuesta del modelo contiene al menos UNO de los
    elementos en gold_multi (lista codificada como string).
    Útil para géneros o editoriales múltiples.
    """
    mt = normalize_text(model_text)
    gold_list = split_multi_answer(gold_multi)
    return int(any(g in mt for g in gold_list))

# =============== PROMPTS POR TIPO ===============
PROMPTS = {
    # P1 ¿Quién escribió el libro {libro}?
    "P1": "¿Quién escribió el libro «{libro}»?",
    # P2 ¿De qué país es la persona {autor}?
    "P2": "¿De qué país es la persona «{autor}»?",
    # P3 ¿De qué país es el autor del libro {libro}?
    "P3": "¿De qué país es el autor del libro «{libro}»?",
    # P4 ¿De qué año es el libro {libro}?
    "P4": "¿De qué año es el libro «{libro}»?",
    # P5 Dime el género o tópico del libro {libro}
    "P5": "Menciona el género o tópico principal del libro «{libro}».",
    # P6 Dime alguna editorial del libro {libro}
    "P6": "Menciona alguna editorial que haya publicado el libro «{libro}».",
}

# =============== LLAMADA AL MODELO ===============
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from collections import deque
import time, re, random


CALLS = deque()  # timestamps de las últimas llamadas

def rate_limit(calls_per_min=8):
    now = time.time()
    while CALLS and now - CALLS[0] > 60:
        CALLS.popleft()
    if len(CALLS) >= calls_per_min:
        sleep = 60 - (now - CALLS[0]) + 0.1
        time.sleep(max(0, sleep))
    CALLS.append(time.time())

class QuotaError(Exception):
    pass

def _parse_retry_delay_seconds(msg: str, default=20):
    m = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", msg, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"Please retry in ([\d.]+)s", msg, re.I)
    if m:
        return int(float(m.group(1)))
    return default

@retry(reraise=True,
       stop=stop_after_attempt(8),
       wait=wait_exponential(multiplier=1, min=2, max=60),
       retry=retry_if_exception_type(QuotaError))
def ask_llm(prompt: str) -> str:
    # 1) respeta cupo/minuto ANTES de llamar
    rate_limit(calls_per_min=8)  # ajusta según tu plan

    try:
        resp = model.generate_content(prompt)
    except Exception as e:
        msg = str(e)
        if "429" in msg or "quota" in msg.lower():
            delay = _parse_retry_delay_seconds(msg, default=20)
            # respetar delay indicado por la API + jitter para evitar thundering herd
            time.sleep(delay + random.uniform(0, 3))
            raise QuotaError(msg)
        raise

    # reconstruir texto si .text viene vacío
    txt = (getattr(resp, "text", None) or "").strip()
    if not txt:
        chunks = []
        for cand in getattr(resp, "candidates", []) or []:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) if content else None
            if parts:
                for p in parts:
                    t = getattr(p, "text", None)
                    if t: chunks.append(t)
        txt = " ".join(chunks).strip()
    return txt or "[NO_TEXT]"

# =============== PIPELINE PRINCIPAL ===============
def evaluar(csv_qas_path: str, out_path: str):
    df = pd.read_csv(csv_qas_path)

    # Espera columnas: tipo, pregunta, respuesta
    assert {"tipo", "pregunta", "respuesta"}.issubset(df.columns), "CSV debe tener columnas: tipo, pregunta, respuesta"

    rows = []
    for i, row in df.iterrows():
        tipo = str(row["tipo"]).strip()
        pregunta = str(row["pregunta"])
        gold = str(row["respuesta"])

        # Construir prompt según tipo (reemplazar placeholders si aplica)
        # Para P1/P3/P4/P5/P6 las preguntas ya traen el libro/autor incrustado;
        # aun así, usamos la pregunta tal cual para el modelo.
        # Si quisieras inyectar título/autor explícito, puedes parsear entre comillas.
        prompt = pregunta
        # (opcional) usar plantilla PROMPTS por tipo si prefieres estandarizar salida:
        # ptempl = PROMPTS.get(tipo, "{q}")
        # prompt = ptempl.format(libro=..., autor=...)  # si parseas variables
        # En este ejemplo usaremos la pregunta directamente.
        t0 = time.time()
        print(f"Evaluando {i+1}/{len(df)} ({tipo}) ...", flush=True)

        try:
            model_answer = ask_llm(prompt)
            latency = time.time() - t0
            # Evaluación por tipo
            if model_answer == "[NO_TEXT]":
                rows.append({
                    "idx": i, "tipo": tipo, "pregunta": pregunta,
                    "respuesta_gold": gold, "respuesta_modelo": model_answer,
                    "score": 0, "rule": "no_text", "latency_s": None
                })
                continue
            if tipo in {"P1", "P4"}:
                score = eval_contains_any(model_answer, gold)
                rule = "contains(gold)"
            elif tipo in {"P2","P3"}:
                score = eval_country(model_answer, gold)
                rule = "country_alias_match"
            elif tipo == "P5":
                # Género(s) puede tener múltiples valores en gold (separados por coma)
                score = eval_any_of_list(model_answer, gold)
                rule = "contains(any(generos))"
            elif tipo == "P6":
                # Editorial(es) puede tener múltiples valores en gold
                score = eval_any_of_list(model_answer, gold)
                rule = "contains(any(editoriales))"
            else:
                score = 0
                rule = "unknown"

            rows.append({
                "idx": i,
                "tipo": tipo,
                "pregunta": pregunta,
                "respuesta_gold": gold,
                "respuesta_modelo": model_answer,
                "score": score,
                "rule": rule,
                "latency_s": round(latency, 3),
            })
        except Exception as e:
            rows.append({
                "idx": i,
                "tipo": tipo,
                "pregunta": pregunta,
                "respuesta_gold": gold,
                "respuesta_modelo": f"[ERROR] {e}",
                "score": 0,
                "rule": "exception",
                "latency_s": None,
            })

    out = pd.DataFrame(rows)
    out.to_csv(out_path, index=False)
    # Resumen por tipo
    resumen = out.groupby("tipo")["score"].mean().reset_index().rename(columns={"score":"accuracy"})
    print("\n=== Accuracy por tipo ===")
    print(resumen.to_string(index=False))
    print(f"\nGuardado: {out_path}")

if __name__ == "__main__":
    # ejemplo
    evaluar("preguntas_short.csv", "resultados_gemini.csv")
    # import google.generativeai as genai, os
    # genai.configure(api_key=os.getenv("API_KEY"))

    # for m in genai.list_models():
    #     if "generateContent" in m.supported_generation_methods:
    #         print(m.name)

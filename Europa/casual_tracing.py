from transformers import AutoModelForCausalLM, AutoTokenizer
from causal_tracer import CausalTracer
import os
import torch
import numpy as np
import pandas as pd
from typing import List, Dict

device = "cuda" if torch.cuda.is_available() else "cpu"

MODEL_NAME = "gpt2-large"
# model_name = "gpt2-large"
# model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")
# tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(device)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

tracer = CausalTracer(model, tokenizer)

# ------------- 1. Definir tus hechos -----------------

BASE_DIR = os.path.dirname(__file__)
TRIPLETS_PATH = os.path.join(BASE_DIR, "Scripts Desafio", "triplets_europe.csv")

df_europe = pd.read_csv(TRIPLETS_PATH)
RELACIONES_VALIDAS = [
    "es de nacionalidad",
    "es autor de la obra",
    "es del año",
]

df_europe_filtrado = df_europe[df_europe["relation"].isin(RELACIONES_VALIDAS)]


def convert_triplet_to_fact(row, idx):
    subject = row["subject"]
    relation = row["relation"]
    obj = row["object"]

    # === Generación automática de queries según la relación ===
    # Puedes agregar más plantillas por relación si quieres.
    if relation == "es de nacionalidad":
        prompt_es = f"{subject} es de nacionalidad"
        prompt_en = f"{subject} is a citizen of"
    elif relation == "es autor de la obra":
        prompt_es = f"{subject} es autor de la obra"
        prompt_en = f"{subject} is the author of the work"
    elif relation == "es del año":
        # Obra (subject) y año (object)
        prompt_es = f"La obra {subject} es del año"
        prompt_en = f"The work {subject} is from the year"
    # else:
    #     # fallback general
    #     prompt_es = f"{relation} {subject}"
    #     prompt_en = f"{subject} {relation}"

    return {
        "id": f"eu_{idx}",
        "region": "EUROPE",
        "subject": subject,
        "relation": relation,
        "object": obj,
        "base_prompts": {
            "es": prompt_es,
            "en": prompt_en
        },
        "expected_answer": obj
    }

FACTS_EUROPE = [
    convert_triplet_to_fact(row, idx)
    for idx, row in df_europe_filtrado.iterrows()
]

print(FACTS_EUROPE[:3])

# ------------- 2. Variantes de queries -----------------

def generate_queries(fact):
    subject = fact["subject"]
    relation = fact["relation"]
    obj = fact["object"]   # aquí 'obj' es la obra

    queries = []

    # --------- Relación: es de nacionalidad ----------
    if relation == "es de nacionalidad":

        # Español
        queries += [
            {"language": "es", "variant": "es_base",
             "prompt": f"{subject} es de nacionalidad"},
            {"language": "es", "variant": "es_pregunta",
             "prompt": f"¿De qué nacionalidad es {subject}?"},
            {"language": "es", "variant": "es_cloze",
             "prompt": f"La nacionalidad de {subject} es"}
        ]

        # Inglés: 
        queries += [
            {"language": "en", "variant": "en_base",
             "prompt": f"The nationality of {subject} is"},
            {"language": "en", "variant": "en_question",
             "prompt": f"{subject} is from"},
            {"language": "en", "variant": "en_country_of",
             "prompt": f"{subject} comes from"}
        ]

    # --------- Relación: es autor de la obra ----------
    elif relation == "es autor de la obra":

        # En este caso el modelo debe predecir el SUBJECT (el autor).
        # La obra aparece explícita en el prompt:
        # Ej: "¿Quién escribió la obra Composer and critic?"
        # Ej: "The author of Composer and critic is"

        # Español
        queries += [
            {"language": "es", "variant": "es_quien",
             "prompt": f"¿Quién escribió la obra {obj}?"},
            {"language": "es", "variant": "es_autor_de",
             "prompt": f"El autor de {obj} es"},
            {"language": "es", "variant": "es_cloze",
             "prompt": f"{obj} fue escrita por"}
        ]

        # Inglés: diseñados para que el siguiente token sea el autor
        queries += [
            {"language": "en", "variant": "en_author_of",
             "prompt": f"The author of {obj} is"},
            {"language": "en", "variant": "en_written_by",
             "prompt": f"{obj} was written by"},
            {"language": "en", "variant": "en_book_by",
             "prompt": f"The book {obj} is by"}
        ]

    # --------- Relación: es del año (obra → año) ----------
    elif relation == "es del año":

        # Español: el modelo debe predecir el AÑO (object)
        queries += [
            {"language": "es", "variant": "es_anio_de",
             "prompt": f"La obra {subject} es del año"},
            {"language": "es", "variant": "es_publicada_en",
             "prompt": f"La obra {subject} fue publicada en el año"},
            {"language": "es", "variant": "es_que_anio",
             "prompt": f"¿De qué año es la obra {subject}?"},
        ]

        # Inglés: igualmente, el modelo debe predecir el AÑO (object)
        queries += [
            {"language": "en", "variant": "en_from_year",
             "prompt": f"The work {subject} is from the year"},
            {"language": "en", "variant": "en_published_in",
             "prompt": f"The work {subject} was published in"},
            {"language": "en", "variant": "en_what_year",
             "prompt": f"In what year was the work {subject} published?"},
        ]

    # --------- Fallback (otras relaciones no definidas) ----------
    else:
        queries += [
            {"language": "es", "variant": "es_generic",
             "prompt": f"{subject} {relation}"},
            {"language": "en", "variant": "en_generic",
             "prompt": f"{subject} {relation}"}
        ]

    return queries

"""Funciones para correr causal tracing y resumir el flujo."""

def run_causal_trace(prompt: str,
                     subject: str,
                     kind: str = "mlp",
                     samples: int = 5,
                     batch_size: int = 2,
                     window: int = 7):
    """
    Envuelve CausalTracer.calculate_hidden_flow y devuelve el HiddenFlow.
    'subject' aquí es el span que el tracer usa como "clave" (tokens que se corrompen/restauran).
    """
    hidden_flow = tracer.calculate_hidden_flow(
        prompt,
        subject=subject,
        kind=kind,
        samples=samples,
        batch_size=batch_size,
        window=window,
    )
    return hidden_flow


def summarize_flow(flow) -> Dict:
    """
    Convierte el HiddenFlow en features numéricos para análisis.
    Hacemos algo simple: max y mean por capa.
    """
    scores = flow.scores.detach().cpu().numpy()  # shape approx (layers, tokens)
    layer_max = scores.max(axis=-1)              # max sobre tokens → [layers]
    layer_mean = scores.mean(axis=-1)            # mean sobre tokens → [layers]

    return {
        "layer_max": layer_max,
        "layer_mean": layer_mean,
        "n_layers": scores.shape[0],
        "n_tokens": scores.shape[1] if scores.ndim > 1 else 1,
        "answer": flow.answer,
        "subject_range": flow.subject_range,
        "kind": flow.kind,
        "input_tokens": flow.input_tokens,
    }


def get_tracer_subject(fact: Dict) -> str:
    """
    Define qué texto usamos como 'subject' para el tracer,
    dependiendo del tipo de relación.

    - Nacionalidad: usamos el sujeto (persona)
    - Autor de la obra: usamos la obra, porque es lo que aparece en la query
      y actúa como clave para recuperar al autor.
    """
    relation = fact["relation"]
    if relation == "es de nacionalidad":
        return fact["subject"]
    elif relation == "es autor de la obra":
        return fact["object"]
    elif relation == "es del año":
        # Usamos la obra (subject) porque es lo que aparece en el prompt
        return fact["subject"]
    else:
        # fallback genérico
        return fact["subject"]

def normalize_text(text: str) -> str:
    """Normaliza texto para comparación sencilla (minúsculas y sin espacios extremos)."""
    return text.strip().lower()


def is_answer_correct(answer: str, expected: str) -> bool:
    """Compara respuesta del modelo con la esperada usando una heurística simple."""
    if not answer or not expected:
        return False
    a = normalize_text(answer)
    e = normalize_text(expected)
    return e in a or a in e


def main(max_facts: int = 3, max_variants_per_fact: int = 2,
         output_path: str = "causal_traces_summary.csv") -> None:
    rows = []
    facts = FACTS_EUROPE[:max_facts]

    for fact in facts:
        fact_id = fact["id"]
        region = fact["region"]
        relation = fact["relation"]
        subject = fact["subject"]
        obj = fact["object"]
        expected_answer = fact["expected_answer"]

        tracer_subject = get_tracer_subject(fact)
        queries = generate_queries(fact)

        english_queries = [q for q in queries if q["language"] == "en"]

        for q_idx, q in enumerate(english_queries):
            if q_idx >= max_variants_per_fact:
                break

        # for q_idx, q in enumerate(queries):
        #     if q_idx >= max_variants_per_fact:
        #         break

            language = q["language"]
            variant = q["variant"]
            prompt = q["prompt"]
            

            print(
                f"Running trace | fact={fact_id} | region={region} | "
                f"rel={relation} | lang={language} | variant={variant}"
            )

            flow = run_causal_trace(
                prompt=prompt,
                subject=tracer_subject,
                kind="mlp",
                samples=2,
                batch_size=1,
                window=5,
            )
            summary = summarize_flow(flow)

            answer = summary["answer"] if summary["answer"] is not None else ""
            correct = is_answer_correct(str(answer), str(expected_answer))

            row = {
                "fact_id": fact_id,
                "region": region,
                "relation": relation,
                "subject": subject,
                "object": obj,
                "expected_answer": expected_answer,
                "tracer_subject": tracer_subject,
                "language": language,
                "variant": variant,
                "kind": summary["kind"],
                "answer": answer,
                "is_correct": correct,
                "n_layers": summary["n_layers"],
                "n_tokens": summary["n_tokens"],
                "mean_layer_max": float(summary["layer_max"].mean()),
                "max_layer_max": float(summary["layer_max"].max()),
                "mean_layer_mean": float(summary["layer_mean"].mean()),
                "max_layer_mean": float(summary["layer_mean"].max()),
            }

            rows.append(row)

    df_results = pd.DataFrame(rows)
    print(df_results.head())

    output_full_path = os.path.join(BASE_DIR, output_path)
    df_results.to_csv(output_full_path, index=False)
    print(f"Resultados guardados en {output_full_path}")


if __name__ == "__main__":
    # --- Debug: ver respuesta completa del modelo para un prompt de ejemplo ---
    # test_prompt = "La nacionalidad de Sigmund Freud es"
    # inputs = tokenizer(test_prompt, return_tensors="pt").to(device)
    # outputs = model.generate(**inputs, max_new_tokens=10)
    # generated = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:])
    # print("\n[DEBUG] Prompt:", test_prompt)
    # print("[DEBUG] Respuesta completa del modelo:", generated)

    main()

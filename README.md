# latam-GPT-2 — Evaluación de QA de libros europeos con Gemini

Este repositorio contiene scripts y datos para construir un conjunto de tripletas (sujeto–predicado–objeto) de libros europeos, generar preguntas/ respuestas a partir de dichas tripletas y evaluar un modelo de Gemini con esas preguntas. Incluye utilidades para limpiar y analizar tanto las tripletas como los resultados de los modelos.

## Estructura del repositorio

- `Real Datasets/` — Dataset por País: carpeta con las tripletas por país (CSV por país)
	- `triples_austria.csv`, `triples_belgium.csv`, ..., `triples_united_kingdom.csv`
- `triplets_europe.csv` — Tripletas de los países unidas en un único CSV.
- Preguntas y Respuestas (CSV en la raíz del repo):
	- `preguntas_respuestas_europe.csv` — Preguntas P1..P6 con su respuesta de referencia (gold).
	- `preguntas_short.csv` — Subconjunto pequeño de pruebas.
- Resultados de Modelos (CSV en la raíz del repo):
	- `resultados_gemini_europe` — Resultados de una corrida con Gemini.
- Resumen Análisis (sugerido): carpeta para almacenar salidas de análisis como `resultados_gemini2_resumen.csv` con el resumen por tipo de pregunta y total, y `real_datasets_summary` con analisis del dataset.

### Scripts principales

- `dataset_eu_books_alllangs_v1.py` — Genera tripletas de Europa consultando OpenLibrary y Wikidata.
- `preguntas.py` — Genera las preguntas P1..P6 y sus CSV a partir de las tripletas.
- `scpirt_gemeni2.py` — Evalúa el modelo de Gemini con las preguntas. Produce un CSV con columnas como: 
	- `tipo`, `pregunta`, `respuesta_gold`, `respuesta_modelo`, `score`, `rule`, `latency_s`, `finish_reason`, `safety_flags`.
	- Nota: cuando la API no devuelve texto (p. ej., por filtros de seguridad), se guarda el sentinel "[NO_TEXT]".
- `data_clear.py` — Limpieza de datos: utilidades para depurar tripletas o resultados.
- `data_analisis.py` — Análisis de datos (tripletas y/o resultados de modelos).
- `preguntas_analisis.py` — Analiza un CSV de resultados (p. ej., `resultados_gemini2.csv`) y calcula totales, aciertos (score=1) y porcentaje por tipo P1..P6.  

## Requisitos

- Python 3.10+
- Dependencias Python (principales):
	- `pandas`, `tenacity`, `unidecode`, `python-dotenv`, `google-generativeai`


## Configuración

Crea un archivo `.env` en la raíz con tu clave de Gemini:

```
API_KEY=tu_api_key_de_gemini
```

## Cómo usar

1) Generar/actualizar tripletas (opcional):

```powershell
python .\dataset_eu_books_alllangs_v1.py
```

2) Generar preguntas (opcional):

```powershell
python .\preguntas.py
```

3) Evaluar con Gemini y guardar resultados:

```powershell
python .\scpirt_gemeni2.py
```


4) Analizar resultados por tipo (P1..P6):

El resumen incluye, por cada `tipo` (P1..P6):
- `total` de preguntas
- `buenas` (score=1)
- `porcentaje` de acierto

## Notas y convenciones

- Tipos de pregunta (P1..P6) incluyen:
	- P1: Autor del libro
	- P2: País de una persona
	- P3: País del autor del libro
	- P4: Año del libro
	- P5: Género/tópico del libro
	- P6: Editorial del libro
- `score=1` indica respuesta correcta; `score=0`, incorrecta/no encontrada.
- Cuando la API no devuelve texto, se registra "[NO_TEXT]" y `finish_reason`/`safety_flags` ayudan a diagnosticar (p. ej., bloqueos de seguridad).

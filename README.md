# NorteAmerica

Repository for the NorteAmerica dataset and small processing pipeline used in the IIC3694 mid-term challenge.

This repository contains raw/exported files and the scripts used to generate a small knowledge-graph-style CSV and question files in English and Spanish, together with simple helper code for building / exporting triplets.

## Quick overview

- Project name: `latam-gpt-2`
- Purpose: collect and preprocess structured knowledge (triplets) and generate simple question sets derived from that knowledge for experimentation with generation / QA models.

This README documents the repository layout, what each script does, how to run things, and notes about environment and regeneration.

## Requirements

- Python: >= 3.12 (see `pyproject.toml`)
- Core dependencies (from `pyproject.toml`): pandas, pydantic, requests, sqlalchemy

Recommended: create and use a virtual environment before installing dependencies.

Example (zsh):

```bash
# create venv
uv venv -p 3.13
source .venv/bin/activate
# install dependencies
uv sync
```

## Repository structure

Top-level:

- `pyproject.toml` - project metadata and dependencies
- `README.md` - this file
- `norteamerica/` - package folder containing data and helper scripts

Inside `norteamerica/`:

- `data/`
	- `knowledge_graph.csv` - exported knowledge triplets.
	- `questions_eng.csv` - generated/derived question set in English.
	- `questions_esp.csv` - generated/derived question set in Spanish.

- `gather_data_codes/` - scripts used to fetch, transform, or generate the datasets
	- `export_triplets.py` - exports or serializes triplets into `knowledge_graph.csv`.
	- `create_questions.py` - generates `questions_eng.csv` and `questions_esp.csv` from the knowledge graph.
	- `model.py` - (lightweight) helper/model definitions (likely pydantic models or simple converters used by the pipeline).
	- `pipeline.py` - data gathering pipeline.

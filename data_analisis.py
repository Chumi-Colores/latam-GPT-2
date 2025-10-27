#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_analisis.py
-----------------
Analiza CSV(s) de tripletas y reporta:
 - Autores distintos (por país y totales)
 - Libros distintos (por ISBN normalizado; por país y totales)
 - Tripletas por país y total de tripletas

Soporta principalmente CSV con columnas: subject, relation, object
 - Autores: filas con relation == "es de nacionalidad" (subject es el autor)
 - ISBNs: filas con relation que empieza con "es un codigo ISBN" y subject que luce como ISBN

Fallback: si existe una columna 'isbn', también se contabiliza a partir de ella.

Uso (PowerShell):
	# Analizar un CSV individual
	python ".\\data_analisis.py" --csv "Real Datasets\\triples_spain.csv"

	# Resumen de la carpeta Real Datasets (por defecto)
	python ".\\data_analisis.py" --dir "Real Datasets" --out-summary "real_datasets_summary.csv"
"""

from __future__ import annotations

import argparse
import csv
import os
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple
import pandas as pd


def normalize_space(s: Optional[str]) -> Optional[str]:
	if s is None:
		return None
	return re.sub(r"\s+", " ", s).strip()


def looks_like_isbn(value: str) -> bool:
	if not value:
		return False
	s = value.replace("-", "").replace(" ", "").upper()
	if len(s) == 10 and re.fullmatch(r"[0-9]{9}[0-9X]", s):
		return True
	if len(s) == 13 and re.fullmatch(r"[0-9]{13}", s):
		return True
	return False


def normalize_isbn(value: str) -> Optional[str]:
	if not value:
		return None
	s = value.replace("-", "").replace(" ", "").upper()
	if len(s) == 10 and re.fullmatch(r"[0-9]{9}[0-9X]", s):
		return s
	if len(s) == 13 and re.fullmatch(r"[0-9]{13}", s):
		return s
	return None


def analyze_csv(path: str) -> Dict[str, object]:
	"""Analiza un CSV y devuelve conteos y sets útiles para agregación.

	Retorna un dict con:
	  - distinct_authors: int
	  - distinct_books_isbn: int
	  - triples: int (número de filas)
	  - authors_set: Set[str]
	  - isbns_set: Set[str]
	"""
	authors: Set[str] = set()
	isbns: Set[str] = set()
	triple_count = 0

	with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
		reader = csv.DictReader(f)
		headers = [h.strip() for h in (reader.fieldnames or [])]
		header_set = {h.lower() for h in headers}

		subject_col = "subject" if "subject" in header_set else None
		relation_col = "relation" if "relation" in header_set else None
		isbn_col = None
		# detectar columna isbn con variantes
		for cand in ("isbn", "isbn_13", "isbn_10"):
			if cand in header_set:
				isbn_col = cand
				break

		for row in reader:
			triple_count += 1
			# Autores por tripletas
			if subject_col and relation_col:
				relation = (row.get("relation") or "").strip()
				if relation == "es de nacionalidad":
					subj = normalize_space(row.get("subject") or "")
					if subj:
						authors.add(subj)

				# ISBN por tripletas (subject es ISBN en estas relaciones)
				if relation.startswith("es un codigo ISBN"):
					subj = (row.get("subject") or "").strip()
					norm = normalize_isbn(subj)
					if norm:
						isbns.add(norm)

			# Fallback por columna isbn explícita
			if isbn_col:
				raw = row.get(isbn_col)
				if raw:
					# puede venir separado por ; o ,
					parts: Iterable[str] = [p.strip() for p in re.split(r"[;,]", raw) if p.strip()]
					for p in parts:
						norm = normalize_isbn(p)
						if norm:
							isbns.add(norm)

	return {
		"distinct_authors": len(authors),
		"distinct_books_isbn": len(isbns),
		"triples": triple_count,
		"authors_set": authors,
		"isbns_set": isbns,
	}


def _country_from_filename(filename: str) -> str:
	"""Deriva el nombre del país a partir del nombre del archivo.

	Soporta varios patrones:
	  - Real Datasets: triples_{country}.csv
	  - Old Datasets: eu_books_triples_{country}.csv
	  - Old Clean Datasets: eu_books_triples_{country}_cleaned.csv
	"""
	base = os.path.basename(filename).lower()

	patterns = [
		r"^triples_([a-z_\- ]+)\.csv$",
		r"^eu_books_triples_([a-z_\- ]+)\.csv$",
		r"^eu_books_triples_([a-z_\- ]+)_cleaned\.csv$",
	]
	token: Optional[str] = None
	for pat in patterns:
		m = re.search(pat, base)
		if m:
			token = m.group(1)
			break
	if not token:
		return os.path.splitext(os.path.basename(filename))[0]

	token = token.replace("-", "_").replace(" ", "_")
	mapping = {
		"spain": "Spain",
		"france": "France",
		"germany": "Germany",
		"italy": "Italy",
		"netherlands": "Netherlands",
		"portugal": "Portugal",
		"belgium": "Belgium",
		"switzerland": "Switzerland",
		"uk": "United Kingdom",
		"united_kingdom": "United Kingdom",
	}
	return mapping.get(token, token.replace("_", " ").title())


def summarize_dir(dir_path: str) -> Tuple[List[Tuple[str, int, int, int]], Dict[str, int]]:
	"""Recorre los CSV en la carpeta y devuelve métricas por país y totales.

	Retorna:
	  - rows: [(Pais, #Autores, #ISBNs, #Tripletas)]
	  - totals: {distinct_authors, distinct_books_isbn, triples}
	"""
	rows: List[Tuple[str, int, int, int]] = []
	total_authors_set: Set[str] = set()
	total_isbns_set: Set[str] = set()
	total_triples = 0

	for name in sorted(os.listdir(dir_path)):
		if not name.lower().endswith(".csv"):
			continue
		full = os.path.join(dir_path, name)
		country = _country_from_filename(name)
		try:
			stats = analyze_csv(full)
			n_auth = int(stats.get("distinct_authors", 0))
			n_isbn = int(stats.get("distinct_books_isbn", 0))
			n_tri = int(stats.get("triples", 0))
			rows.append((country, n_auth, n_isbn, n_tri))

			# Agregar a totales por conjuntos y conteo de filas
			total_triples += n_tri
			total_authors_set |= set(stats.get("authors_set", set()))
			total_isbns_set |= set(stats.get("isbns_set", set()))
		except Exception:
			# Si algún archivo falla, seguimos con los demás
			continue

	totals = {
		"distinct_authors": len(total_authors_set),
		"distinct_books_isbn": len(total_isbns_set),
		"triples": total_triples,
	}
	return rows, totals


def write_summary_table(rows: List[Tuple[str, int, int, int]], out_path: str) -> None:
	with open(out_path, "w", encoding="utf-8", newline="") as f:
		w = csv.writer(f)
		w.writerow(["Pais", "Autores distintos", "ISBN distintos", "Tripletas"])
		for country, n_auth, n_isbn, n_tri in rows:
			w.writerow([country, n_auth, n_isbn, n_tri])


def combine_dir(dir_path: str, out_path: str, drop_duplicates: bool = True) -> int:
	"""Une todos los CSVs en dir_path en un solo CSV out_path.

	- Espera principalmente columnas [subject, relation, object].
	- Si drop_duplicates=True, elimina duplicados por [subject, relation, object].
	- Omite el propio archivo de salida si ya existe en el directorio.
	Retorna el número de filas escritas.
	"""
	frames: List[pd.DataFrame] = []
	out_base = os.path.basename(out_path).lower()
	for name in sorted(os.listdir(dir_path)):
		if not name.lower().endswith(".csv"):
			continue
		if name.lower() == out_base:
			# evitar auto-inclusión
			continue
		full = os.path.join(dir_path, name)
		try:
			df = pd.read_csv(full)
		except Exception:
			continue
		# Mantener columnas básicas si existen
		cols = [c for c in ("subject", "relation", "object") if c in df.columns]
		if cols:
			df = df[cols].copy()
		frames.append(df)

	if not frames:
		# crear CSV vacío con encabezados básicos
		pd.DataFrame(columns=["subject", "relation", "object"]).to_csv(out_path, index=False)
		return 0

	all_df = pd.concat(frames, ignore_index=True)
	# Asegurar columnas
	for c in ("subject", "relation", "object"):
		if c not in all_df.columns:
			all_df[c] = None
	all_df = all_df[["subject", "relation", "object"]]

	if drop_duplicates:
		all_df = all_df.drop_duplicates(subset=["subject", "relation", "object"], ignore_index=True)

	os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
	all_df.to_csv(out_path, index=False)
	return len(all_df)


def main() -> None:
	parser = argparse.ArgumentParser(description="Analiza CSV(s) y reporta autores, ISBNs y tripletas (por país y totales). También puede combinar archivos en uno solo.")
	parser.add_argument("--csv", help="Ruta a un CSV individual para análisis puntual")
	parser.add_argument("--dir", default="Real Datasets", help="Carpeta con CSVs por país (por defecto: 'Real Datasets')")
	parser.add_argument("--out-summary", default="real_datasets_summary.csv", help="Ruta de salida para la tabla resumen (CSV)")
	parser.add_argument("--combine", action="store_true", help="Si se especifica, une todos los CSVs de --dir en un único archivo")
	parser.add_argument("--combine-out", default=os.path.join("Real Datasets", "triplets_europe.csv"), help="Ruta del CSV combinado (por defecto: 'Real Datasets/triplets_europe.csv')")
	args = parser.parse_args()

	if args.csv:
		stats = analyze_csv(args.csv)
		print(f"Autores distintos: {stats['distinct_authors']}")
		print(f"Libros distintos (ISBN): {stats['distinct_books_isbn']}")
		print(f"Tripletas: {stats['triples']}")
		return

	# Combinación de carpeta si se solicita
	if args.combine:
		dir_path = args.dir
		out_path = args.combine_out
		if not os.path.isdir(dir_path):
			raise SystemExit(f"La carpeta no existe: {dir_path}")
		n = combine_dir(dir_path, out_path, drop_duplicates=True)
		print(f"CSV combinado creado: {out_path} ({n} filas)")
		return

	# Resumen de carpeta (por defecto, 'Real Datasets')
	dir_path = args.dir
	if not os.path.isdir(dir_path):
		raise SystemExit(f"La carpeta no existe: {dir_path}")

	rows, totals = summarize_dir(dir_path)

	# Mostrar tabla en consola
	print("Pais | Autores distintos | ISBN distintos | Tripletas")
	for country, n_auth, n_isbn, n_tri in rows:
		print(f"{country} | {n_auth} | {n_isbn} | {n_tri}")

	# Totales
	print("\nTotales:")
	print(f"Autores distintos (global): {totals['distinct_authors']}")
	print(f"ISBN distintos (global): {totals['distinct_books_isbn']}")
	print(f"Tripletas totales: {totals['triples']}")

	# Guardar CSV
	write_summary_table(rows, args.out_summary)
	print(f"\nTabla guardada en: {args.out_summary}")


def view_data():
	# Intentar primero con el nuevo resumen
	candidates = ["real_datasets_summary.csv", "clean_datasets_summary.csv"]
	data_summary = next((p for p in candidates if os.path.exists(p)), None)
	if not data_summary:
		print("No se encontró un archivo de resumen. Ejecuta el script con --dir para generarlo.")
		return

	with open(data_summary, "r", encoding="utf-8", newline="") as f:
		reader = csv.reader(f)
		rows = list(reader)

	# Mostrar contenido
	for row in rows:
		print(row)

	# Sumar totales (ignorando encabezado)
	def _to_int(x: str) -> int:
		try:
			return int(x)
		except Exception:
			return 0

	# Detectar si la tabla tiene 4 columnas (nuevo formato) o 3 (antiguo)
	has_triples = False
	if rows and rows[0]:
		header = [c.lower() for c in rows[0]]
		has_triples = any("triple" in c for c in header)

	data_rows = [r for r in rows[1:] if r and len(r) >= (4 if has_triples else 3)]
	numero_autores_totales = sum(_to_int(r[1]) for r in data_rows)
	numero_libros_totales = sum(_to_int(r[2]) for r in data_rows)

	print(f"Número total de autores distintos (suma por país): {numero_autores_totales}")
	print(f"Número total de libros distintos (ISBN, suma por país): {numero_libros_totales}")

	if has_triples:
		numero_tripletas_totales = sum(_to_int(r[3]) for r in data_rows)
		print(f"Número total de tripletas: {numero_tripletas_totales}")
if __name__ == "__main__":
	main()
	view_data()


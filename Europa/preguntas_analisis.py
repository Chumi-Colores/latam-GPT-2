import argparse
import os
import sys
import pandas as pd


def analizar(csv_path: str, out_path: str | None = None):
	if not os.path.exists(csv_path):
		raise FileNotFoundError(f"No se encontró el archivo: {csv_path}")

	# Carga robusta del CSV (UTF-8 por defecto)
	df = pd.read_csv(csv_path, encoding="utf-8")

	# Validar columnas mínimas
	cols_necesarias = {"tipo", "score"}
	if not cols_necesarias.issubset(df.columns):
		faltan = cols_necesarias - set(df.columns)
		raise ValueError(f"Faltan columnas en el CSV: {', '.join(faltan)}")

	# Convertir score a 0/1 por seguridad
	df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int)

	# Orden fijo P1..P6 si existen
	orden = [f"P{i}" for i in range(1, 7)]
	if "tipo" in df.columns:
		df["tipo"] = pd.Categorical(df["tipo"], categories=orden, ordered=True)

	resumen = (
		df.groupby("tipo", dropna=True, observed=False)
		  .agg(total=("score", "size"), buenas=("score", lambda s: (s == 1).sum()))
		  .reset_index()
	)
	if not resumen.empty:
		resumen["porcentaje"] = (resumen["buenas"] * 100.0 / resumen["total"]).round(2)

	# Agregar fila total general
	total = int(len(df))
	buenas_total = int((df["score"] == 1).sum())
	porcentaje_total = round(buenas_total * 100.0 / total, 2) if total > 0 else 0.0

	# Mostrar por consola
	print("\n=== Resultados por tipo (P1..P6) ===")
	if resumen.empty:
		print("No hay datos para agrupar por 'tipo'.")
	else:
		print(resumen.to_string(index=False))

	print("\n=== Resultado global ===")
	print(f"Total preguntas: {total}")
	print(f"Buenas (score=1): {buenas_total}")
	print(f"Accuracy global: {porcentaje_total}%")

	# Guardar CSV de salida si se indicó o usar uno por defecto junto al input
	if out_path is None:
		base, ext = os.path.splitext(csv_path)
		out_path = base + "_resumen.csv"

	salida = resumen.copy()
	# Añadimos una fila de resumen global con tipo='TOTAL'
	fila_total = pd.DataFrame({
		"tipo": ["TOTAL"],
		"total": [total],
		"buenas": [buenas_total],
		"porcentaje": [porcentaje_total],
	})
	salida = pd.concat([salida, fila_total], ignore_index=True)
	salida.to_csv(out_path, index=False, encoding="utf-8")
	print(f"\nResumen guardado en: {out_path}")


def main(argv=None):
	parser = argparse.ArgumentParser(description="Análisis de resultados por tipo (P1..P6)")
	parser.add_argument(
		"--input",
		"-i",
		default="resultados_gemini2.csv",
		help="Ruta al CSV de resultados (por defecto: resultados_gemini2.csv)",
	)
	parser.add_argument(
		"--output",
		"-o",
		default=None,
		help="Ruta al CSV de resumen (por defecto: <input>_resumen.csv)",
	)
	args = parser.parse_args(argv)

	analizar(args.input, args.output)


if __name__ == "__main__":
	main()


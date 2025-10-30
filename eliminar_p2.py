import argparse
import os
import shutil
import sys

import pandas as pd


def eliminar_p2(csv_path: str, backup: bool = True, renumerar: bool = True) -> tuple[int, int, int]:
	if not os.path.exists(csv_path):
		raise FileNotFoundError(f"No se encontró el archivo: {csv_path}")

	# Backup opcional
	backup_path = None
	if backup:
		base, ext = os.path.splitext(csv_path)
		backup_path = f"{base}_backup{ext}"
		shutil.copyfile(csv_path, backup_path)

	df = pd.read_csv(csv_path, encoding="utf-8")
	if "tipo" not in df.columns:
		raise ValueError("El CSV no contiene la columna 'tipo'.")

	total_antes = len(df)
	eliminados = int((df["tipo"] == "P2").sum())
	df_filtrado = df[df["tipo"] != "P2"].copy()

	# Renumerar tipos si se solicita: P3->P2, P4->P3, P5->P4, P6->P5
	if renumerar:
		mapping = {"P3": "P2", "P4": "P3", "P5": "P4", "P6": "P5"}
		if "tipo" in df_filtrado.columns:
			df_filtrado["tipo"] = df_filtrado["tipo"].replace(mapping)
	total_despues = len(df_filtrado)

	# Guardar en el mismo archivo (in-place)
	df_filtrado.to_csv(csv_path, index=False, encoding="utf-8")

	return total_antes, eliminados, total_despues


def main(argv=None):
	parser = argparse.ArgumentParser(description="Eliminar filas de tipo P2 de un CSV de resultados y renumerar P3->P2, P4->P3, P5->P4, P6->P5.")
	parser.add_argument(
		"--input",
		"-i",
		required=True,
		help="Ruta al archivo CSV (por ejemplo, 'Resultados de Modelos/resultados_gemini_europe.csv')",
	)
	parser.add_argument(
		"--no-backup",
		action="store_true",
		help="No crear respaldo antes de sobrescribir el CSV.",
	)
	parser.add_argument(
		"--no-renum",
		action="store_true",
		help="No renumerar tipos (por defecto sí se renumera: P3->P2 ... P6->P5).",
	)
	args = parser.parse_args(argv)

	total_antes, eliminados, total_despues = eliminar_p2(
		args.input,
		backup=(not args.no_backup),
		renumerar=(not args.no_renum),
	)
	print(f"Archivo: {args.input}")
	print(f"Filas antes:   {total_antes}")
	print(f"Eliminadas P2: {eliminados}")
	print(f"Filas después: {total_despues}")


if __name__ == "__main__":
	main()


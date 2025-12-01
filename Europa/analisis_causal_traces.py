import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = os.path.dirname(__file__)  # carpeta donde está este script
CSV_PATH = os.path.join(BASE_DIR, "causal_traces_summary.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "Analisis Proyecto")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_data(path: str = CSV_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def resumen_global(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "mean_layer_max",
        "max_layer_max",
        "mean_layer_mean",
        "max_layer_mean",
    ]
    group_cols = ["region", "language", "relation", "variant"]
    summary = (
        df.groupby(group_cols)[cols]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    summary.to_csv(os.path.join(OUTPUT_DIR, "resumen_causal_traces_por_condicion.csv"), index=False)
    return summary


def plot_por_region_idioma(df: pd.DataFrame) -> None:
    """Curvas de activación media por capa, separadas por región e idioma.

    Requiere que el CSV original tenga columnas por capa o que `n_layers` sea fijo
    y `layer_max`/`layer_mean` estén expandidos. Aquí usamos solo agregados globales
    como aproximación: barras por grupo.
    """
    plt.figure(figsize=(8, 5))
    sns.barplot(
        data=df,
        x="region",
        y="mean_layer_max",
        hue="language",
        errorbar="sd",
    )
    plt.title("Mean layer max por región e idioma")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "mean_layer_max_region_idioma.png"))
    plt.close()

    plt.figure(figsize=(8, 5))
    sns.barplot(
        data=df,
        x="region",
        y="mean_layer_mean",
        hue="language",
        errorbar="sd",
    )
    plt.title("Mean layer mean por región e idioma")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "mean_layer_mean_region_idioma.png"))
    plt.close()


def plot_por_variant(df: pd.DataFrame) -> None:
    plt.figure(figsize=(10, 5))
    sns.barplot(
        data=df,
        x="variant",
        y="mean_layer_max",
        hue="language",
        errorbar="sd",
    )
    plt.title("Mean layer max por tipo de query (variant)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "mean_layer_max_por_variant.png"))
    plt.close()


def main() -> None:
    print(f"Leyendo datos desde {CSV_PATH}")
    df = load_data()
    print(f"Filas cargadas: {len(df)}")

    summary = resumen_global(df)
    print("Resumen por región/idioma/relación/variant guardado en 'Resumen Analisis'.")

    # Para las gráficas usamos el dataframe original (no el resumen agrupado),
    # porque seaborn calcula barras con error por grupo.
    if "region" in df.columns and "language" in df.columns:
        plot_por_region_idioma(df)
        print("Gráficas por región e idioma guardadas en 'Resumen Analisis'.")

    if "variant" in df.columns:
        plot_por_variant(df)
        print("Gráficas por variant guardadas en 'Resumen Analisis'.")


if __name__ == "__main__":
    main()

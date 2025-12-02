import os

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


BASE_DIR = os.path.dirname(__file__)
LAYERS_PATH = os.path.join(BASE_DIR, "causal_traces_layers.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "Analisis Proyecto")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def cargar_datos(path: str = LAYERS_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Unificar relaciones temporales equivalentes bajo una misma etiqueta
    if "relation" in df.columns:
        df["relation_unificada"] = df["relation"].replace(
            {
                "es del año": "es/fue del año",
                "fue publicada en el año": "es/fue del año",
            }
        )
    else:
        df["relation_unificada"] = None

    print(f"Datos de capas leídos desde {path}")
    print(f"Filas cargadas: {len(df)}")
    return df


def curvas_por_region(df: pd.DataFrame) -> None:
    """Curvas promedio layer_max por capa, separadas por región."""
    if "region" not in df.columns:
        print("No se encontró 'region' en el DataFrame; se omite curvas_por_region.")
        return

    resumen = (
        df.groupby(["region", "layer_idx"], as_index=False)["layer_max"]
        .mean()
        .rename(columns={"layer_max": "mean_layer_max"})
    )

    plt.figure(figsize=(8, 5))
    sns.lineplot(
        data=resumen,
        x="layer_idx",
        y="mean_layer_max",
        hue="region",
        marker="o",
    )
    plt.title("Curvas de layer_max promedio por capa y región")
    plt.xlabel("Índice de capa")
    plt.ylabel("layer_max promedio")
    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "curvas_layer_max_por_region.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Figura guardada en {out_path}")


def curvas_por_region_y_relacion(df: pd.DataFrame) -> None:
    """Curvas promedio layer_max por capa, separadas por región y relación."""
    if "region" not in df.columns or "relation_unificada" not in df.columns:
        print("No se encontraron 'region'/'relation_unificada' en el DataFrame; se omite curvas_por_region_y_relacion.")
        return

    resumen = (
        df.groupby(["region", "relation_unificada", "layer_idx"], as_index=False)["layer_max"]
        .mean()
        .rename(columns={"layer_max": "mean_layer_max"})
    )

    # Una figura por relación
    relaciones = resumen["relation_unificada"].unique()
    for rel in relaciones:
        sub = resumen[resumen["relation_unificada"] == rel]
        plt.figure(figsize=(8, 5))
        sns.lineplot(
            data=sub,
            x="layer_idx",
            y="mean_layer_max",
            hue="region",
            marker="o",
        )
        plt.title(f"Curvas de layer_max por capa, región y relación = {rel}")
        plt.xlabel("Índice de capa")
        plt.ylabel("layer_max promedio")
        plt.tight_layout()
        safe_rel = str(rel).replace("/", "-")
        out_path = os.path.join(OUTPUT_DIR, f"curvas_layer_max_region_rel_{safe_rel}.png")
        plt.savefig(out_path)
        plt.close()
        print(f"Figura guardada en {out_path}")


def curvas_por_variant(df: pd.DataFrame, region: str | None = None) -> None:
    """Curvas promedio layer_max por capa, separadas por variant (opcionalmente filtrando región)."""
    if "variant" not in df.columns:
        print("No se encontró 'variant' en el DataFrame; se omite curvas_por_variant.")
        return

    df_plot = df
    if region is not None:
        df_plot = df_plot[df_plot["region"] == region]
        if df_plot.empty:
            print(f"Sin datos para la región {region} en curvas_por_variant.")
            return

    resumen = (
        df_plot.groupby(["variant", "layer_idx"], as_index=False)["layer_max"]
        .mean()
        .rename(columns={"layer_max": "mean_layer_max"})
    )

    plt.figure(figsize=(10, 6))
    sns.lineplot(
        data=resumen,
        x="layer_idx",
        y="mean_layer_max",
        hue="variant",
        marker="o",
    )
    titulo = "Curvas de layer_max por capa y variant"
    if region is not None:
        titulo += f" (región = {region})"
    plt.title(titulo)
    plt.xlabel("Índice de capa")
    plt.ylabel("layer_max promedio")
    plt.tight_layout()

    suffix = f"_{region}" if region is not None else ""
    out_path = os.path.join(OUTPUT_DIR, f"curvas_layer_max_por_variant{suffix}.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Figura guardada en {out_path}")


def main() -> None:
    df = cargar_datos()

    curvas_por_region(df)
    curvas_por_region_y_relacion(df)
    curvas_por_variant(df, region="Europe")
    curvas_por_variant(df, region="Latin America")


if __name__ == "__main__":
    main()

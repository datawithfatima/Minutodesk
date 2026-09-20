"""Limpia el export crudo de tickets antes de entrenar el clasificador.

Lee data/tickets_historicos_raw.csv, se queda solo con las columnas
relevantes para el clasificador, limpia el HTML de la descripción y
descarta filas sin tipo o sin texto útil. Guarda el resultado en
data/tickets_historicos.csv (nombre que espera train_classifier.py).

Ejecutar desde backend/: python -m app.ml.prepare_dataset
"""
import html
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_PATH = PROJECT_ROOT / "data" / "tickets_historicos_raw.csv"
OUT_PATH = PROJECT_ROOT / "data" / "tickets_historicos.csv"

COLUMNAS_ORIGEN = {
    "ID": "id",
    "Seleccione una opción para la respectiva atención.": "tipo",
    "Categoría": "categoria",
    "Descripción": "texto",
}

TAG_RE = re.compile(r"<[^>]+>")


def limpiar_texto(texto: str) -> str:
    sin_tags = TAG_RE.sub(" ", texto)
    sin_entidades = html.unescape(sin_tags)
    return sin_entidades.strip()


def preparar() -> None:
    df = pd.read_csv(RAW_PATH, encoding="utf-8-sig")
    df = df[list(COLUMNAS_ORIGEN.keys())].rename(columns=COLUMNAS_ORIGEN)

    df["tipo"] = df["tipo"].fillna("").str.strip()
    df["categoria"] = df["categoria"].fillna("").str.strip()
    df["texto"] = df["texto"].fillna("").apply(limpiar_texto)

    total = len(df)

    sin_tipo = df["tipo"] == ""
    descartados_tipo = int(sin_tipo.sum())
    df = df[~sin_tipo]

    sin_texto = df["texto"] == ""
    descartados_texto = int(sin_texto.sum())
    df = df[~sin_texto]

    final = len(df)
    pct_sin_categoria = (df["categoria"] == "").mean() * 100 if final else 0.0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)

    print(f"Filas totales en el archivo original: {total}")
    print(f"Descartadas por falta de tipo: {descartados_tipo}")
    print(f"Descartadas por texto vacío: {descartados_texto}")
    print(f"Filas finales en el CSV limpio: {final}")
    print(f"Porcentaje sin categoría: {pct_sin_categoria:.1f}%")
    print(f"Guardado en: {OUT_PATH}")


if __name__ == "__main__":
    preparar()

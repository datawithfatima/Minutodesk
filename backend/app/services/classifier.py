"""Carga el vectorizador y los clasificadores entrenados una sola vez, al
importar el módulo, y expone clasificar_ticket() para el flujo de creación de
tickets, además de las métricas medidas al entrenar (metricas.json).
"""
import json
from pathlib import Path

import joblib

from app.ml.train_classifier import preprocesar_texto

MODEL_DIR = Path(__file__).resolve().parent.parent / "ml" / "model"

_vectorizer = joblib.load(MODEL_DIR / "tfidf_vectorizer.joblib")
_modelo_tipo = joblib.load(MODEL_DIR / "modelo_tipo.joblib")
_modelo_categoria = joblib.load(MODEL_DIR / "modelo_categoria.joblib")


def cargar_metricas() -> dict:
    """Métricas de la última corrida de entrenamiento; vacío si no existen."""
    try:
        return json.loads((MODEL_DIR / "metricas.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def categorias_clasificables() -> list[str]:
    """Categorías que el modelo sabe predecir ("Otros" al final), para ofrecerlas al elegir."""
    nombres = sorted(c for c in _modelo_categoria.classes_ if c != "Otros")
    return nombres + ["Otros"] if "Otros" in set(_modelo_categoria.classes_) else nombres


def sugerir(texto: str, k: int = 3) -> dict:
    """Sugerencia para mostrar a la persona mientras escribe: tipo, categoría y las
    `k` categorías más probables. `confiable` indica si la confianza de la categoría
    alcanza el umbral con el que se midió la precisión objetivo."""
    vector = _vectorizer.transform([preprocesar_texto(texto)])
    proba_tipo = _modelo_tipo.predict_proba(vector)[0]
    proba_cat = _modelo_categoria.predict_proba(vector)[0]

    orden = proba_cat.argsort()[::-1][:k]
    umbral = cargar_metricas().get("categoria", {}).get("umbral")
    confianza = float(proba_cat.max())
    return {
        "tipo": str(_modelo_tipo.classes_[proba_tipo.argmax()]),
        "confianza_tipo": float(proba_tipo.max()),
        "categoria": str(_modelo_categoria.classes_[proba_cat.argmax()]),
        "confianza": confianza,
        "confiable": umbral is not None and confianza >= umbral,
        "alternativas": [
            {"categoria": str(_modelo_categoria.classes_[i]), "confianza": float(proba_cat[i])}
            for i in orden
        ],
    }


def clasificar_ticket(texto: str) -> dict:
    vector = _vectorizer.transform([preprocesar_texto(texto)])

    proba_tipo = _modelo_tipo.predict_proba(vector)[0]
    proba_categoria = _modelo_categoria.predict_proba(vector)[0]

    return {
        "tipo": _modelo_tipo.classes_[proba_tipo.argmax()],
        "categoria": _modelo_categoria.classes_[proba_categoria.argmax()],
        # La confianza guardada es la de la categoría: es la que está bien calibrada.
        # La del tipo (Incidencia vs Solicitud) casi no se distingue de un 50/50.
        "confianza": float(proba_categoria.max()),
        "confianza_tipo": float(proba_tipo.max()),
    }

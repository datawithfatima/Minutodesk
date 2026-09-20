"""Carga el vectorizador y los clasificadores entrenados (Fase 2) una sola
vez, al importar el módulo, y expone clasificar_ticket() para el flujo de
creación de tickets.
"""
from pathlib import Path

import joblib

from app.ml.train_classifier import preprocesar_texto

MODEL_DIR = Path(__file__).resolve().parent.parent / "ml" / "model"

_vectorizer = joblib.load(MODEL_DIR / "tfidf_vectorizer.joblib")
_modelo_tipo = joblib.load(MODEL_DIR / "modelo_tipo.joblib")
_modelo_categoria = joblib.load(MODEL_DIR / "modelo_categoria.joblib")


def clasificar_ticket(texto: str) -> dict:
    vector = _vectorizer.transform([preprocesar_texto(texto)])

    proba_tipo = _modelo_tipo.predict_proba(vector)[0]
    proba_categoria = _modelo_categoria.predict_proba(vector)[0]

    tipo = _modelo_tipo.classes_[proba_tipo.argmax()]
    categoria = _modelo_categoria.classes_[proba_categoria.argmax()]
    confianza = (proba_tipo.max() + proba_categoria.max()) / 2

    return {
        "tipo": tipo,
        "categoria": categoria,
        "confianza": float(confianza),
    }

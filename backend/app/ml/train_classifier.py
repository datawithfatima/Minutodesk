"""Entrena los clasificadores TF-IDF + SVM para tipo y categoría de tickets.

Lee data/tickets_historicos.csv (generado por prepare_dataset.py), mide la
precisión con validación cruzada, entrena un vectorizador TF-IDF compartido y
dos clasificadores CalibratedClassifierCV (LinearSVC) —uno para tipo, otro para
categoría— y los guarda en backend/app/ml/model/ junto con metricas.json
(precisión y umbral de confianza). El reporte detallado queda en
data/reporte_clasificador.md.

Ejecutar desde backend/: python -m app.ml.train_classifier
"""
import json
import re
import string
import unicodedata
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = PROJECT_ROOT / "data" / "tickets_historicos.csv"
REPORTE_PATH = PROJECT_ROOT / "data" / "reporte_clasificador.md"
MODEL_DIR = Path(__file__).resolve().parent / "model"

PRECISION_OBJETIVO = 0.80
MIN_EJEMPLOS_POR_CLASE = 5  # menos que esto no se puede aprender ni evaluar
FOLDS = 5
UMBRALES = [round(float(u), 2) for u in np.arange(0.30, 0.96, 0.05)]
MIN_TICKETS_UMBRAL = 30  # un umbral solo es creíble si lo respalda una muestra mínima

def quitar_tildes(texto: str) -> str:
    """Quita acentos y normaliza la ñ->n (ej. contraseña/contrasena deben
    contar como la misma palabra para el clasificador). Es el criterio
    estándar de normalización de texto en buscadores/clasificadores en
    español; se acepta el riesgo mínimo de casos como año/ano porque en
    un ticket real la palabra siempre viene acompañada de contexto."""
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


# Lista manual de stopwords en español (nltk/spacy no están en requirements.txt).
# Se normaliza sin tildes porque preprocesar_texto() quita tildes antes de filtrar.
_STOPWORDS_CON_TILDES = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por",
    "un", "para", "con", "no", "una", "su", "al", "lo", "como", "más", "pero",
    "sus", "le", "ya", "o", "este", "sí", "porque", "esta", "entre", "cuando",
    "muy", "sin", "sobre", "también", "me", "hasta", "hay", "donde", "quien",
    "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra",
    "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mí", "antes",
    "algunos", "qué", "unos", "yo", "otro", "otras", "otra", "él", "tanto",
    "esa", "estos", "mucho", "quienes", "nada", "muchos", "cual", "poco",
    "ella", "estar", "estas", "algunas", "algo", "nosotros", "mi", "mis",
    "tú", "te", "ti", "tu", "tus", "ellas", "nosotras", "vosotros", "vosotras",
    "os", "es", "son", "fue", "ser", "está", "están",
}
STOPWORDS_ES = {quitar_tildes(w) for w in _STOPWORDS_CON_TILDES}

PUNTUACION_RE = re.compile(f"[{re.escape(string.punctuation)}¿¡«»]")
ESPACIOS_RE = re.compile(r"\s+")


def preprocesar_texto(texto: str) -> str:
    texto = quitar_tildes(texto.lower())
    texto = PUNTUACION_RE.sub(" ", texto)
    palabras = [p for p in texto.split() if p not in STOPWORDS_ES]
    return ESPACIOS_RE.sub(" ", " ".join(palabras)).strip()


def agrupar_clases_raras(y: pd.Series) -> pd.Series:
    """Las categorías con menos de MIN_EJEMPLOS_POR_CLASE ejemplos no se pueden
    aprender ni evaluar: se agrupan en "Otros" en vez de perder esos tickets."""
    conteos = y.value_counts()
    raras = conteos[conteos < MIN_EJEMPLOS_POR_CLASE].index
    if len(raras):
        print(f"Aviso: {len(raras)} categoría(s) con menos de {MIN_EJEMPLOS_POR_CLASE} ejemplos se agrupan en 'Otros'.")
    return y.where(~y.isin(raras), "Otros")


def construir_vectorizador() -> FeatureUnion:
    """TF-IDF de palabras (1-2) y de caracteres (2-5): los caracteres toleran
    errores de tipeo y variantes, útiles con textos cortos y poco cuidados."""
    return FeatureUnion([
        ("palabras", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ("caracteres", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
    ])


def construir_modelo() -> CalibratedClassifierCV:
    # Calibrado: convierte la salida del SVM en probabilidades confiables.
    return CalibratedClassifierCV(LinearSVC(C=1.0, class_weight="balanced"), cv=3)


def evaluar_cv(nombre: str, textos: pd.Series, y: pd.Series) -> tuple[dict, str]:
    """Validación cruzada de 5 pliegues: cada ticket se predice sin haber sido
    visto en el entrenamiento. Mucho más fiable que un solo corte train/test con
    pocos datos. Devuelve (métricas, texto del reporte)."""
    pipe = Pipeline([("v", construir_vectorizador()), ("m", construir_modelo())])
    cv = StratifiedKFold(FOLDS, shuffle=True, random_state=42)
    proba = cross_val_predict(pipe, textos, y, cv=cv, method="predict_proba")
    clases = np.array(sorted(y.unique()))
    pred = clases[proba.argmax(axis=1)]
    conf = proba.max(axis=1)
    acierto = pred == y.values

    por_umbral = []
    for u in UMBRALES:
        m = conf >= u
        if m.sum():
            por_umbral.append({
                "umbral": u,
                "cobertura": round(float(m.mean()), 4),
                "precision": round(float(acierto[m].mean()), 4),
                "tickets": int(m.sum()),
            })
    # Menor umbral (= mayor cobertura) con precisión >= objetivo y muestra suficiente.
    elegido = next(
        (p for p in por_umbral if p["precision"] >= PRECISION_OBJETIVO and p["tickets"] >= MIN_TICKETS_UMBRAL),
        None,
    )
    metricas = {
        "tickets": int(len(y)),
        "clases": int(len(clases)),
        "accuracy": round(float(acierto.mean()), 4),
        "f1_macro": round(float(f1_score(y, pred, average="macro", zero_division=0)), 4),
        "umbral": elegido["umbral"] if elegido else None,
        "precision_en_umbral": elegido["precision"] if elegido else None,
        "cobertura_en_umbral": elegido["cobertura"] if elegido else None,
        "por_umbral": por_umbral,
    }

    lineas = [f"## {nombre}", "", f"Tickets: {metricas['tickets']} · Clases: {metricas['clases']}",
              f"Precisión global (validación cruzada {FOLDS} pliegues): {metricas['accuracy']:.1%}",
              f"F1 macro: {metricas['f1_macro']:.3f}", "", "```",
              classification_report(y, pred, zero_division=0), "```", "",
              "Precisión según la confianza del modelo:", ""]
    lineas += [f"- confianza ≥ {p['umbral']:.2f}: cobertura {p['cobertura']:.0%}, precisión {p['precision']:.1%}" for p in por_umbral]
    return metricas, "\n".join(lineas)


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    df["texto_limpio"] = df["texto"].fillna("").apply(preprocesar_texto)
    df = df[df["texto_limpio"] != ""]

    df_tipo = df
    df_cat = df[df["categoria"].notna() & (df["categoria"] != "")].copy()
    df_cat["categoria"] = agrupar_clases_raras(df_cat["categoria"])

    metricas_tipo, reporte_tipo = evaluar_cv("Tipo", df_tipo["texto_limpio"], df_tipo["tipo"])
    metricas_cat, reporte_cat = evaluar_cv("Categoría", df_cat["texto_limpio"], df_cat["categoria"])
    print(reporte_tipo, "\n")
    print(reporte_cat, "\n")

    for nombre, m in (("tipo", metricas_tipo), ("categoría", metricas_cat)):
        if m["accuracy"] < PRECISION_OBJETIVO:
            print(f"ADVERTENCIA: la precisión global de '{nombre}' ({m['accuracy']:.1%}) está por debajo de la meta del {PRECISION_OBJETIVO:.0%}.")
    if metricas_cat["umbral"] is not None:
        print(
            f"Categoría: con confianza ≥ {metricas_cat['umbral']:.2f} la precisión es "
            f"{metricas_cat['precision_en_umbral']:.1%} y cubre el {metricas_cat['cobertura_en_umbral']:.0%} de los tickets."
        )

    # Modelos finales: se entrenan con todos los datos (la validación cruzada ya midió el rendimiento).
    vectorizer = construir_vectorizador().fit(df["texto_limpio"])
    modelo_tipo = construir_modelo().fit(vectorizer.transform(df_tipo["texto_limpio"]), df_tipo["tipo"])
    modelo_categoria = construir_modelo().fit(vectorizer.transform(df_cat["texto_limpio"]), df_cat["categoria"])

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, MODEL_DIR / "tfidf_vectorizer.joblib")
    joblib.dump(modelo_tipo, MODEL_DIR / "modelo_tipo.joblib")
    joblib.dump(modelo_categoria, MODEL_DIR / "modelo_categoria.joblib")
    (MODEL_DIR / "metricas.json").write_text(
        json.dumps(
            {
                "entrenado_en": datetime.now().isoformat(timespec="seconds"),
                "objetivo_precision": PRECISION_OBJETIVO,
                "metodo": f"validación cruzada de {FOLDS} pliegues",
                "tipo": {k: v for k, v in metricas_tipo.items() if k != "por_umbral"},
                "categoria": metricas_cat,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    REPORTE_PATH.write_text(
        f"# Reporte del clasificador\n\nGenerado: {datetime.now():%Y-%m-%d %H:%M}\n\n{reporte_tipo}\n\n{reporte_cat}\n",
        encoding="utf-8",
    )
    print(f"\nModelos guardados en: {MODEL_DIR}\nReporte completo: {REPORTE_PATH}")


if __name__ == "__main__":
    main()

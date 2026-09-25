"""Entrena los clasificadores TF-IDF + SVM para tipo y categoría de tickets.

Lee data/tickets_historicos.csv (generado por prepare_dataset.py), entrena un
vectorizador TF-IDF compartido y dos clasificadores CalibratedClassifierCV
(LinearSVC) —uno para tipo, otro para categoría— y los guarda en
backend/app/ml/model/.

Ejecutar desde backend/: python -m app.ml.train_classifier
"""
import re
import string
import unicodedata
from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = PROJECT_ROOT / "data" / "tickets_historicos.csv"
MODEL_DIR = Path(__file__).resolve().parent / "model"

UMBRAL_PRECISION = 0.80
MIN_EJEMPLOS_POR_CLASE = 2  # mínimo para poder hacer train/test split

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


def filtrar_clases_raras(df: pd.DataFrame, columna: str) -> pd.DataFrame:
    """Descarta filas de clases con menos de MIN_EJEMPLOS_POR_CLASE ejemplos:
    con 1 solo ejemplo no hay forma de repartirlo entre train y test."""
    conteos = df[columna].value_counts()
    raras = conteos[conteos < MIN_EJEMPLOS_POR_CLASE].index.tolist()
    if raras:
        n_filas = int(df[columna].isin(raras).sum())
        print(
            f"Aviso: se excluyen {len(raras)} clase(s) de '{columna}' con menos de "
            f"{MIN_EJEMPLOS_POR_CLASE} ejemplos ({n_filas} fila(s)): {raras}"
        )
        df = df[~df[columna].isin(raras)]
    return df


def entrenar_y_evaluar(nombre, X_train, y_train, X_test, y_test):
    # cv no puede superar el número de ejemplos de la clase más pequeña del train.
    cv = max(2, min(5, y_train.value_counts().min()))
    modelo = CalibratedClassifierCV(estimator=LinearSVC(), cv=cv)
    modelo.fit(X_train, y_train)

    y_pred = modelo.predict(X_test)
    precision = accuracy_score(y_test, y_pred)

    print(f"\n=== Modelo de {nombre} (cv={cv}) ===")
    print(classification_report(y_test, y_pred, zero_division=0))
    print(f"Precisión global de {nombre}: {precision:.4f}")

    if precision < UMBRAL_PRECISION:
        print(
            f"ADVERTENCIA: la precisión de '{nombre}' ({precision:.2%}) está por debajo "
            f"del umbral de {UMBRAL_PRECISION:.0%}. Prueba ajustar el parámetro C de "
            "LinearSVC o revisar el balance de clases."
        )

    return modelo


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    df["texto_limpio"] = df["texto"].fillna("").apply(preprocesar_texto)

    # Modelo de tipo: usa todas las filas (tipo nunca viene vacío).
    df_tipo = filtrar_clases_raras(df, "tipo")
    X_tipo_train_txt, X_tipo_test_txt, y_tipo_train, y_tipo_test = train_test_split(
        df_tipo["texto_limpio"], df_tipo["tipo"],
        test_size=0.2, stratify=df_tipo["tipo"], random_state=42,
    )

    # Modelo de categoría: solo filas con categoria no vacía.
    df_cat = df[df["categoria"].notna() & (df["categoria"] != "")]
    df_cat = filtrar_clases_raras(df_cat, "categoria")
    X_cat_train_txt, X_cat_test_txt, y_cat_train, y_cat_test = train_test_split(
        df_cat["texto_limpio"], df_cat["categoria"],
        test_size=0.2, stratify=df_cat["categoria"], random_state=42,
    )

    # Vectorizador TF-IDF compartido, ajustado sobre el train de tipo (el más grande).
    vectorizer = TfidfVectorizer()
    X_tipo_train = vectorizer.fit_transform(X_tipo_train_txt)
    X_tipo_test = vectorizer.transform(X_tipo_test_txt)
    X_cat_train = vectorizer.transform(X_cat_train_txt)
    X_cat_test = vectorizer.transform(X_cat_test_txt)

    modelo_tipo = entrenar_y_evaluar(
        "tipo", X_tipo_train, y_tipo_train, X_tipo_test, y_tipo_test
    )
    modelo_categoria = entrenar_y_evaluar(
        "categoría", X_cat_train, y_cat_train, X_cat_test, y_cat_test
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, MODEL_DIR / "tfidf_vectorizer.joblib")
    joblib.dump(modelo_tipo, MODEL_DIR / "modelo_tipo.joblib")
    joblib.dump(modelo_categoria, MODEL_DIR / "modelo_categoria.joblib")
    print(f"\nModelos guardados en: {MODEL_DIR}")


if __name__ == "__main__":
    main()

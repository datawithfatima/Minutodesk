"""Cifras de los objetivos 2 y 3 de la tesis, leídas de la base sin modificarla.

Uso (desde backend/):  venv\\Scripts\\python.exe scripts\\cifras_objetivos.py

Objetivo 2: % de consultas de primer nivel que Minutito resolvería, según la
evaluación experta de los tickets nuevos (Datos históricos → Evaluación de Minutito).
Se da también el resultado en el grupo apartado: tickets cuya solución nunca se anotó,
así que Minutito no aprendió de ellos en ningún momento.

Objetivo 3: reducción del tiempo medio de resolución en las incidencias, comparando el
tiempo real con el simulado dentro de la misma muestra (services/simulacion_tiempos.py).
"""
import json
import sqlite3
import sys
from math import sqrt
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlmodel import Session, create_engine  # noqa: E402

from app.services.simulacion_tiempos import simular  # noqa: E402

DB = BACKEND / "minutodesk.db"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confianza al 95 % para una proporción (útil con muestras chicas)."""
    if not n:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    margen = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return round(centro - margen, 3), round(centro + margen, 3)


def objetivo_2(con: sqlite3.Connection) -> dict:
    filas = con.execute(
        "SELECT veredicto, solucion_esperada IS NOT NULL FROM evaluacion_minutito WHERE respuesta IS NOT NULL"
    ).fetchall()

    def medir(sub):
        si = sum(v == "resuelve" for v, _ in sub)
        no = sum(v == "no_resuelve" for v, _ in sub)
        n = si + no
        return {
            "resuelve": si,
            "no_resuelve": no,
            "no_aplica": sum(v == "no_aplica" for v, _ in sub),
            "sin_evaluar": sum(v is None for v, _ in sub),
            "pct": round(si / n, 4) if n else None,
            "ic95": wilson(si, n),
        }

    return {
        "meta": 0.30,
        "todos_dejando_uno_fuera": medir(filas),
        "grupo_apartado_nunca_visto": medir([f for f in filas if not f[1]]),
        "prueba_controlada": dict(
            con.execute("SELECT COALESCE(veredicto, 'sin_evaluar'), COUNT(*) FROM prueba_minutito GROUP BY 1").fetchall()
        ),
    }


def main() -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    engine = create_engine(f"sqlite:///file:{DB}?mode=ro&uri=true")
    with Session(engine) as s:
        sim = simular(s)
    print(json.dumps({"objetivo_2": objetivo_2(con), "objetivo_3": sim}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

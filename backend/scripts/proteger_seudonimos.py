"""Pasa los seudónimos ya guardados del hash anterior (SHA-256 sin clave) al HMAC con
clave secreta. Los alias no cambian: solo cambia la «huella» con la que se reconoce a
cada persona. Necesita los nombres originales, así que lee los CSV de la empresa
(columnas «Solicitante» y «Asignado a»). Se puede repetir sin efecto. Desde backend/:

    python scripts/proteger_seudonimos.py ../data/tickets.csv [otro.csv ...]

Sin argumentos usa todos los .csv de la carpeta data/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app.database import engine, init_db  # noqa: E402
from app.models import Seudonimo  # noqa: E402
from app.services.anonimizar import clave_antigua, proteger_claves_antiguas  # noqa: E402

COLUMNAS = {"Solicitante": "solicitante", "Asignado a": "tecnico"}


def leer(ruta: Path) -> pd.DataFrame:
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(ruta, dtype=str, keep_default_na=False, sep=None, engine="python", encoding=codificacion)
            df.columns = [c.strip() for c in df.columns]
            return df
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"No se pudo leer {ruta}")


if __name__ == "__main__":
    rutas = [Path(a) for a in sys.argv[1:]] or sorted((Path(__file__).resolve().parents[2] / "data").glob("*.csv"))
    if not rutas:
        raise SystemExit("No encontré archivos CSV. Pasa la ruta del CSV de la empresa.")
    nombres = []
    for ruta in rutas:
        df = leer(ruta)
        for columna, tipo in COLUMNAS.items():
            if columna in df.columns:
                nombres += [(n.strip(), tipo) for n in df[columna] if n.strip()]
    init_db()
    with Session(engine) as session:
        cambiadas = proteger_claves_antiguas(session, nombres)
        total = len(session.exec(select(Seudonimo)).all())
        pendientes = {clave_antigua(n, t) for n, t in nombres}
        sin_pasar = sum(1 for s in session.exec(select(Seudonimo)).all() if s.clave in pendientes)
    print(f"Seudónimos protegidos ahora: {cambiadas}. Total en la base: {total}. Aún con el hash anterior: {sin_pasar}.")

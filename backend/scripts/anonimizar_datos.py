"""Anonimiza los datos de la empresa que ya están en la base (histórico y tickets de la
carga masiva): nombres por alias y, en las descripciones, correos, cédulas, teléfonos
y nombres completos. Se puede repetir sin efecto. Desde backend/:

    python scripts/anonimizar_datos.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.database import engine, init_db
from app.services.anonimizar import anonimizar_base

if __name__ == "__main__":
    init_db()
    with Session(engine) as session:
        cambios = anonimizar_base(session)
    print(f"Histórico: {cambios['historico']} tickets anonimizados. Carga masiva: {cambios['tickets']}.")

"""Pobla la base con clientes de ejemplo para probar el resto del sistema
sin datos reales. Ejecutar desde backend/: python scripts/seed_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.database import engine, init_db
from app.models import Cliente

CLIENTES_EJEMPLO = [
    Cliente(nombre="Ana Torres", area="Contabilidad"),
    Cliente(nombre="Luis Vargas", area="Obra Civil"),
    Cliente(nombre="Maria Salazar", area="Ventas"),
]


def seed() -> None:
    init_db()
    with Session(engine) as session:
        session.add_all(CLIENTES_EJEMPLO)
        session.commit()
    print(f"Insertados {len(CLIENTES_EJEMPLO)} clientes de ejemplo.")


if __name__ == "__main__":
    seed()

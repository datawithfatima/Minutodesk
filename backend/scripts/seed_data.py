"""Pobla la base con clientes de ejemplo (3 colaboradores + 1 técnico) para
probar el resto del sistema sin datos reales. Todos comparten la contraseña
"minutodesk123" — es solo para desarrollo local, no usar en producción.
Ejecutar desde backend/: python scripts/seed_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.database import engine, init_db
from app.models import Cliente
from app.services.auth import hashear_password

PASSWORD_DEMO = "minutodesk123"

CLIENTES_EJEMPLO = [
    Cliente(
        nombre="Ana Torres",
        area="Contabilidad",
        email="ana.torres@ejemplo.com",
        password_hash=hashear_password(PASSWORD_DEMO),
        rol="colaborador",
    ),
    Cliente(
        nombre="Luis Vargas",
        area="Obra Civil",
        email="luis.vargas@ejemplo.com",
        password_hash=hashear_password(PASSWORD_DEMO),
        rol="colaborador",
    ),
    Cliente(
        nombre="Maria Salazar",
        area="Ventas",
        email="maria.salazar@ejemplo.com",
        password_hash=hashear_password(PASSWORD_DEMO),
        rol="colaborador",
    ),
    Cliente(
        nombre="Carlos Sanchez",
        area="Sistemas",
        email="carlos.sanchez@ejemplo.com",
        password_hash=hashear_password(PASSWORD_DEMO),
        rol="tecnico",
    ),
]


def seed() -> None:
    init_db()
    with Session(engine) as session:
        session.add_all(CLIENTES_EJEMPLO)
        session.commit()
    print(f"Insertados {len(CLIENTES_EJEMPLO)} usuarios de ejemplo (contraseña: {PASSWORD_DEMO}).")


if __name__ == "__main__":
    seed()

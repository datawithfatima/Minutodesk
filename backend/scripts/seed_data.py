"""Crea el catálogo de áreas y cuentas de demostración.

Uso (desde backend/):
    python scripts/seed_data.py
    python scripts/seed_data.py --admin-email tu@correo.com --admin-nombre "Tu Nombre"

Sin argumentos crea un administrador de demostración con contraseña conocida
(solo para desarrollo local). Con --admin-email crea el administrador SIN
contraseña y le envía el enlace de activación a ese correo (o lo guarda en
backend/correos_enviados/ si no hay SMTP configurado).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database import engine, init_db
from app.models import Area, Cliente
from app.services import correo, tokens_acceso
from app.services.auth import hashear_password

PASSWORD_DEMO = "minutodesk123"

AREAS = ["Administración", "Contabilidad", "Obra Civil", "Ventas", "Marketing", "Sistemas"]

CUENTAS_DEMO = [
    ("Administrador Demo", "admin@ejemplo.com", "Sistemas", "administrador"),
    ("Carlos Sánchez", "carlos.sanchez@ejemplo.com", "Sistemas", "tecnico"),
    ("Ana Torres", "ana.torres@ejemplo.com", "Contabilidad", "usuario"),
    ("Luis Vargas", "luis.vargas@ejemplo.com", "Obra Civil", "usuario"),
    ("María Salazar", "maria.salazar@ejemplo.com", "Ventas", "usuario"),
]


def seed(admin_email: str | None, admin_nombre: str) -> None:
    init_db()
    with Session(engine) as session:
        if session.exec(select(Cliente)).first() is not None:
            print("La base ya tiene usuarios; no se hizo ningún cambio.")
            return

        areas = {}
        for nombre in AREAS:
            area = Area(nombre=nombre)
            session.add(area)
            areas[nombre] = area
        session.commit()
        for area in areas.values():
            session.refresh(area)

        for nombre, email, area, rol in CUENTAS_DEMO:
            if admin_email and rol == "administrador":
                continue
            session.add(
                Cliente(
                    nombre=nombre,
                    email=email,
                    area_id=areas[area].id,
                    rol=rol,
                    password_hash=hashear_password(PASSWORD_DEMO),
                )
            )
        session.commit()

        if admin_email:
            admin = Cliente(
                nombre=admin_nombre,
                email=admin_email.strip().lower(),
                area_id=areas["Sistemas"].id,
                rol="administrador",
            )
            session.add(admin)
            session.commit()
            session.refresh(admin)
            token = tokens_acceso.generar(
                session, admin, "activacion", tokens_acceso.MINUTOS_ACTIVACION
            )
            modo = correo.enviar_activacion(admin.email, admin.nombre, token)
            destino = "a tu correo" if modo == "smtp" else "en backend/correos_enviados/"
            print(f"Administrador creado sin contraseña: enlace de activación enviado {destino}.")
        else:
            print(f"Administrador de demostración: admin@ejemplo.com / {PASSWORD_DEMO}")

        print(f"Áreas creadas: {len(AREAS)}. Cuentas de demostración (contraseña {PASSWORD_DEMO}):")
        for nombre, email, _area, rol in CUENTAS_DEMO:
            if not (admin_email and rol == "administrador"):
                print(f"  - {rol:<13} {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email")
    parser.add_argument("--admin-nombre", default="Administrador")
    args = parser.parse_args()
    seed(args.admin_email, args.admin_nombre)

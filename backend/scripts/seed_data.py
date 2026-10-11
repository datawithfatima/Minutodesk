"""Crea el catálogo de áreas y el primer administrador.

Uso (desde backend/):
    python scripts/seed_data.py --admin-email tu@correo.com --admin-nombre "Tu Nombre"
    python scripts/seed_data.py --demo

Con --admin-email crea el administrador SIN contraseña y le envía el enlace de
activación a ese correo (o lo guarda en backend/correos_enviados/ si no hay SMTP
configurado). El resto de cuentas las crea ese administrador desde la página.

--demo agrega cuentas de demostración con contraseña conocida (solo para
desarrollo local). Sin --admin-email, también crea un administrador de demostración.
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


def seed(admin_email: str | None, admin_nombre: str, demo: bool) -> None:
    if not admin_email and not demo:
        print("Indica --admin-email tu@correo.com (o --demo para cuentas de prueba).")
        return
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

        if demo:
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

        print(f"Áreas creadas: {len(AREAS)}.")
        if demo:
            print(f"Cuentas de demostración (contraseña {PASSWORD_DEMO}):")
            for nombre, email, _area, rol in CUENTAS_DEMO:
                if not (admin_email and rol == "administrador"):
                    print(f"  - {rol:<13} {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email")
    parser.add_argument("--admin-nombre", default="Administrador")
    parser.add_argument("--demo", action="store_true", help="agrega cuentas de demostración")
    args = parser.parse_args()
    seed(args.admin_email, args.admin_nombre, args.demo)

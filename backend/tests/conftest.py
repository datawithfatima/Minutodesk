import os
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

os.environ.setdefault("MINUTITO_PRECALENTAR", "0")  # las pruebas no cargan el modelo
os.environ.setdefault("SEUDONIMOS_KEY", "clave-solo-para-pruebas")  # no crea backend/.clave_seudonimos

from app.database import get_session
from app.main import app
from app.models import Area, Cliente
from app.routers.auth import fallos_por_ip, intentos_fallidos, recuperaciones_por_ip
from app.routers.minutito import mensajes_recientes, respondiendo
from app.services import asignacion, correo
from app.services.auth import hashear_password

PASSWORD = "Clave12345"

# Tabla de técnicos por sistema con nombres ficticios: la real vive fuera del repositorio
# (backend/tecnicos_por_categoria.json) y las pruebas no dependen de ella.
TABLA_DE_PRUEBA = {
    "Power BI": ["Ana Mora"],
    "Office": ["Gabriel Ruiz", "Sofía Luna"],
    "Internet": ["Gabriel Ruiz", "Sofía Luna"],
    "Interpro": ["Gabriel Ruiz", "Sofía Luna"],
    "Salesforce": ["Pedro Vera"],
    "Webdox": ["Pedro Vera", "Marta Gil"],
    "Otros": [asignacion.TODOS],
}


@pytest.fixture(autouse=True)
def tabla_de_tecnicos(monkeypatch):
    monkeypatch.setattr(asignacion, "TECNICOS_POR_CATEGORIA", TABLA_DE_PRUEBA)


@pytest.fixture()
def engine():
    motor = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    # Igual que la base real: SQLite no valida claves foráneas si no se piden.
    @event.listens_for(motor, "connect")
    def _activar_claves_foraneas(dbapi_connection, _registro):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(motor)
    return motor


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture()
def correos(tmp_path, monkeypatch):
    """Redirige los correos a una carpeta temporal y evita cualquier SMTP real."""
    monkeypatch.setattr(correo, "DIRECTORIO_SALIDA", tmp_path)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    return tmp_path


@pytest.fixture()
def client(engine, correos):
    def _sesion():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _sesion
    intentos_fallidos.clear()  # el freno de inicio de sesión no pasa de una prueba a otra
    fallos_por_ip.clear()
    recuperaciones_por_ip.clear()
    mensajes_recientes.clear()
    respondiendo.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def crear_cuenta(session):
    def _crear(email, rol="usuario", nombre=None, password=PASSWORD, area="Sistemas", activo=True):
        existente = session.exec(select(Area).where(Area.nombre == area)).first()
        if existente is None:
            existente = Area(nombre=area)
            session.add(existente)
            session.commit()
            session.refresh(existente)
        cliente = Cliente(
            nombre=nombre or email.split("@")[0],
            email=email,
            area_id=existente.id,
            rol=rol,
            activo=activo,
            password_hash=hashear_password(password) if password else None,
        )
        session.add(cliente)
        session.commit()
        session.refresh(cliente)
        return cliente

    return _crear


@pytest.fixture()
def entrar(client):
    def _entrar(email, password=PASSWORD):
        respuesta = client.post("/auth/login", json={"email": email, "password": password})
        assert respuesta.status_code == 200, respuesta.text
        return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}

    return _entrar


def token_del_ultimo_correo(carpeta) -> str:
    archivos = sorted(carpeta.glob("*.txt"))
    assert archivos, "no se generó ningún correo"
    return re.search(r"token=([\w-]+)", archivos[-1].read_text(encoding="utf-8")).group(1)

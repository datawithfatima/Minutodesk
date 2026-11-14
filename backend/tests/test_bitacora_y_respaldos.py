"""Bitácora de auditoría (middleware) y respaldos de la base."""
import sqlite3

from sqlmodel import select

from app.models import Auditoria
from app.services import respaldo

from .test_acceso_y_roles import _crear_ticket


def _acciones(session):
    session.expire_all()
    return [a for a in session.exec(select(Auditoria).order_by(Auditoria.id)).all()]


def test_la_bitacora_registra_quien_hizo_que_sin_contrasenas(client, crear_cuenta, entrar, session):
    crear_cuenta("u@ejemplo.com", "usuario", nombre="Ana")
    crear_cuenta("t@ejemplo.com", "tecnico", nombre="Tito")
    crear_cuenta("adm@ejemplo.com", "administrador", nombre="Admin")

    assert client.post("/auth/login", json={"email": "u@ejemplo.com", "password": "mala123456"}).status_code == 401
    usuario, tecnico, admin = entrar("u@ejemplo.com"), entrar("t@ejemplo.com"), entrar("adm@ejemplo.com")
    ticket = _crear_ticket(client, usuario)
    client.patch(f"/tickets/{ticket['id']}", json={"prioridad": "Alta"}, headers=tecnico)
    assert client.get("/admin/bitacora", headers=tecnico).status_code == 403
    client.get("/minutito/conversaciones/actual", headers=usuario)  # consulta: no se registra

    registros = _acciones(session)
    claves = [a.accion for a in registros]
    assert claves[0] == "inicio_sesion_fallido" and registros[0].actor == "u@ejemplo.com" and not registros[0].exito
    assert claves.count("inicio_sesion") == 3
    creado = next(a for a in registros if a.accion == "ticket_creado")
    assert creado.actor == "Ana" and creado.entidad_id == ticket["id"]
    assert "(" in creado.detalle and "no puedo imprimir" not in creado.detalle  # el texto no se copia
    cambio = next(a for a in registros if a.accion == "ticket_actualizado")
    assert cambio.actor == "Tito" and cambio.detalle == "prioridad: Alta"
    # El técnico intentó entrar a una pantalla de administrador: queda como intento sin permiso.
    assert not any("password" in (a.detalle or "").lower() for a in registros)

    datos = client.get("/admin/bitacora", params={"accion": "ticket_actualizado"}, headers=admin).json()
    assert datos["total"] == 1 and datos["registros"][0]["descripcion"] == f"Actualizó el ticket #{ticket['id']}"
    assert client.get("/admin/bitacora", headers=usuario).status_code == 403


def test_respaldo_consistente_y_poda(tmp_path, monkeypatch):
    origen = tmp_path / "origen.db"
    con = sqlite3.connect(origen)
    con.execute("create table t (x int)")
    con.execute("insert into t values (42)")
    con.commit()
    con.close()
    carpeta = tmp_path / "respaldos"
    monkeypatch.setenv("RESPALDO_CONSERVAR", "2")

    assert respaldo.hace_falta(carpeta)
    hecho = respaldo.crear(origen=origen, directorio=carpeta)
    assert sqlite3.connect(carpeta / hecho["nombre"]).execute("select x from t").fetchone() == (42,)
    assert not respaldo.hace_falta(carpeta)

    # Se conservan los 2 automáticos más recientes; los manuales no se borran solos.
    for nombre in ("minutodesk-20260101-000000.db", "minutodesk-20260102-000000.db", "minutodesk-20260101-000000-manual.db"):
        (carpeta / nombre).write_bytes(b"")
    respaldo.crear(origen=origen, directorio=carpeta)
    nombres = {r["nombre"] for r in respaldo.listar(carpeta)}
    assert "minutodesk-20260101-000000.db" not in nombres and "minutodesk-20260102-000000.db" not in nombres
    assert "minutodesk-20260101-000000-manual.db" in nombres
    assert respaldo.ruta("../minutodesk.db", carpeta) is None


def test_solo_el_administrador_maneja_respaldos(client, crear_cuenta, entrar, tmp_path, monkeypatch):
    crear_cuenta("t@ejemplo.com", "tecnico")
    crear_cuenta("adm@ejemplo.com", "administrador")
    origen = tmp_path / "base.db"
    sqlite3.connect(origen).execute("create table t (x int)").connection.commit()
    monkeypatch.setattr(respaldo, "DIRECTORIO", tmp_path / "respaldos")
    monkeypatch.setattr(respaldo, "DIRECTORIO_BASE", tmp_path)
    monkeypatch.setattr(respaldo, "sqlite_file_name", "base.db")
    tecnico, admin = entrar("t@ejemplo.com"), entrar("adm@ejemplo.com")

    assert client.post("/admin/respaldos", headers=tecnico).status_code == 403
    hecho = client.post("/admin/respaldos", headers=admin).json()
    assert hecho["manual"] is True
    assert client.get("/admin/respaldos", headers=admin).json()["respaldos"][0]["nombre"] == hecho["nombre"]
    assert client.get(f"/admin/respaldos/{hecho['nombre']}", headers=admin).status_code == 200
    assert client.get("/admin/respaldos/otra-cosa.db", headers=admin).status_code == 404

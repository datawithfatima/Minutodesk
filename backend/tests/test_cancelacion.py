"""Cancelar tickets: solo el personal, con motivo, sin contar como resuelto, y la
migración que habilita el estado en una base creada con la versión anterior."""
from sqlalchemy import create_engine as crear_motor
from sqlmodel import select

from app.database import _permitir_estado_cancelado
from app.models import EventoGamificacion, Ticket

from .test_acceso_y_roles import _crear_ticket


def _preparar(client, crear_cuenta, entrar):
    crear_cuenta("u@ejemplo.com", "usuario")
    crear_cuenta("t@ejemplo.com", "tecnico")
    usuario, tecnico = entrar("u@ejemplo.com"), entrar("t@ejemplo.com")
    return usuario, tecnico, _crear_ticket(client, usuario)


def _cancelar(client, headers, ticket_id, motivo="El usuario lo resolvió por su cuenta"):
    return client.post(f"/tickets/{ticket_id}/cancelar", json={"motivo": motivo}, headers=headers)


def test_el_tecnico_cancela_con_motivo_y_queda_en_el_historial(client, crear_cuenta, entrar):
    usuario, tecnico, ticket = _preparar(client, crear_cuenta, entrar)

    r = _cancelar(client, tecnico, ticket["id"], "  Duplicado   del ticket #3 ")
    assert r.status_code == 200, r.text
    cancelado = r.json()
    assert cancelado["estado"] == "cancelado"
    assert cancelado["motivo_cancelacion"] == "Duplicado del ticket #3"
    assert cancelado["cerrado_en"] is not None and cancelado["resuelto_por"] is None

    historial = client.get(f"/tickets/{ticket['id']}/historial", headers=usuario).json()
    assert historial[-1]["estado_nuevo"] == "cancelado"
    assert historial[-1]["motivo"] == "Duplicado del ticket #3"
    assert historial[-1]["cambiado_por"] == "t"
    # El usuario ve el motivo en su ticket.
    assert client.get(f"/tickets/{ticket['id']}", headers=usuario).json()["motivo_cancelacion"]


def test_solo_el_personal_cancela_y_siempre_con_motivo(client, crear_cuenta, entrar):
    usuario, tecnico, ticket = _preparar(client, crear_cuenta, entrar)

    assert _cancelar(client, usuario, ticket["id"]).status_code == 403
    assert _cancelar(client, tecnico, ticket["id"], "   ").status_code == 400
    assert _cancelar(client, tecnico, ticket["id"], "x" * 501).status_code == 400
    # Por PATCH no se puede: así nunca queda un cancelado sin motivo.
    r = client.patch(f"/tickets/{ticket['id']}", json={"estado": "cancelado"}, headers=tecnico)
    assert r.status_code == 400 and "motivo" in r.json()["detail"]
    assert client.get(f"/tickets/{ticket['id']}", headers=tecnico).json()["estado"] == "abierto"


def test_no_se_cancela_un_ticket_resuelto_ni_dos_veces(client, crear_cuenta, entrar):
    _, tecnico, ticket = _preparar(client, crear_cuenta, entrar)
    otro = _crear_ticket(client, entrar("u@ejemplo.com"))

    client.patch(f"/tickets/{ticket['id']}", json={"estado": "resuelto"}, headers=tecnico)
    assert _cancelar(client, tecnico, ticket["id"]).status_code == 409
    assert _cancelar(client, tecnico, otro["id"]).status_code == 200
    assert _cancelar(client, tecnico, otro["id"]).status_code == 409


def test_un_cancelado_se_puede_reabrir_y_pierde_el_motivo(client, crear_cuenta, entrar):
    _, tecnico, ticket = _preparar(client, crear_cuenta, entrar)
    _cancelar(client, tecnico, ticket["id"])

    r = client.patch(f"/tickets/{ticket['id']}", json={"estado": "abierto"}, headers=tecnico)
    assert r.status_code == 200
    assert r.json()["estado"] == "abierto"
    assert r.json()["motivo_cancelacion"] is None and r.json()["cerrado_en"] is None


def test_un_cancelado_no_admite_chat_ni_archivos_del_usuario(client, crear_cuenta, entrar):
    usuario, tecnico, ticket = _preparar(client, crear_cuenta, entrar)
    _cancelar(client, tecnico, ticket["id"])

    r = client.post(f"/tickets/{ticket['id']}/chat", json={"mensaje": "sigue fallando"}, headers=usuario)
    assert r.status_code == 409
    r = client.post(
        f"/tickets/{ticket['id']}/adjuntos",
        content=b"hola",
        headers={**usuario, "X-Nombre-Archivo": "nota.txt"},
    )
    assert r.status_code == 409 and "cancelado" in r.json()["detail"]


def test_cancelar_no_da_puntos_ni_cuenta_como_resuelto(client, crear_cuenta, entrar, session):
    usuario, tecnico, ticket = _preparar(client, crear_cuenta, entrar)
    resuelto = _crear_ticket(client, usuario, "no me abre el correo de outlook")
    _cancelar(client, tecnico, ticket["id"])
    # El otro lo resolvió Minutito con la confirmación del usuario.
    t = session.get(Ticket, resuelto["id"])
    t.estado, t.resuelto_por = "resuelto", "minutito"
    session.add(t)
    session.commit()

    resumen = client.get("/reportes/resumen", headers=tecnico).json()
    assert resumen["cancelados"] == 1 and resumen["resueltos"] == 1 and resumen["total"] == 2
    # La autonomía se mide sobre los tickets que sí necesitaban solución.
    assert resumen["pct_resolucion_autonoma"] == 100.0
    puntos = session.exec(select(EventoGamificacion).where(EventoGamificacion.ticket_id == ticket["id"])).all()
    assert puntos == []
    filtrados = client.get("/tickets", params={"estado": "cancelado"}, headers=tecnico).json()
    assert [f["id"] for f in filtrados] == [ticket["id"]]


# ---------- migración de una base creada antes del estado «cancelado» ----------

ESQUEMA_ANTERIOR = """CREATE TABLE ticket (
	id INTEGER NOT NULL,
	cliente_id INTEGER NOT NULL,
	tecnico_id INTEGER,
	texto VARCHAR NOT NULL,
	tipo_predicho VARCHAR,
	categoria_predicha VARCHAR,
	confianza_clasificacion FLOAT,
	estado VARCHAR NOT NULL,
	resuelto_por VARCHAR,
	creado_en DATETIME NOT NULL,
	cerrado_en DATETIME, tipo TEXT, categoria TEXT, clasificacion_confirmada BOOLEAN NOT NULL DEFAULT 0, prioridad TEXT NOT NULL DEFAULT 'Normal', datos_alta TEXT,
	PRIMARY KEY (id),
	CONSTRAINT ck_ticket_estado CHECK (estado IN ('abierto','en_proceso','resuelto')),
	CONSTRAINT ck_ticket_resuelto_por CHECK (resuelto_por IS NULL OR resuelto_por IN ('minutito','tecnico')),
	FOREIGN KEY(cliente_id) REFERENCES cliente (id)
)"""


def test_la_base_anterior_acepta_cancelado_sin_perder_datos_ni_referencias(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'vieja.db'}")
    with motor.begin() as c:
        c.exec_driver_sql("CREATE TABLE cliente (id INTEGER PRIMARY KEY, nombre TEXT)")
        c.exec_driver_sql(ESQUEMA_ANTERIOR)
        c.exec_driver_sql("CREATE INDEX ix_ticket_estado ON ticket (estado)")
        c.exec_driver_sql(
            "CREATE TABLE historial_estado_ticket (id INTEGER PRIMARY KEY, "
            "ticket_id INTEGER NOT NULL REFERENCES ticket (id), estado_nuevo TEXT)"
        )
        c.exec_driver_sql("INSERT INTO cliente VALUES (1, 'Ana')")
        c.exec_driver_sql(
            "INSERT INTO ticket (id, cliente_id, texto, estado, creado_en) "
            "VALUES (7, 1, 'impresora', 'abierto', '2026-10-01 10:00:00')"
        )
        c.exec_driver_sql("INSERT INTO historial_estado_ticket VALUES (1, 7, 'abierto')")

    _permitir_estado_cancelado(motor)
    _permitir_estado_cancelado(motor)  # una segunda vez no hace nada

    with motor.begin() as c:
        sql = c.exec_driver_sql("SELECT sql FROM sqlite_master WHERE name='ticket'").scalar()
        assert "'cancelado'" in sql and "ck_ticket_resuelto_por" in sql
        assert c.exec_driver_sql("SELECT texto, prioridad FROM ticket WHERE id=7").one() == ("impresora", "Normal")
        c.exec_driver_sql("UPDATE ticket SET estado='cancelado' WHERE id=7")
        indices = {f[0] for f in c.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='index'")}
        assert "ix_ticket_estado" in indices
        # El historial sigue apuntando al mismo ticket y la regla de estados se mantiene.
        assert c.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
        assert c.exec_driver_sql("SELECT ticket_id FROM historial_estado_ticket").scalar() == 7
    with motor.begin() as c:
        try:
            c.exec_driver_sql("UPDATE ticket SET estado='perdido' WHERE id=7")
            assert False, "la regla CHECK debía rechazar un estado desconocido"
        except Exception as e:  # noqa: BLE001 - IntegrityError de SQLite
            assert "CHECK" in str(e)

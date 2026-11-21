"""Tomar y liberar tickets: el ticket queda a nombre de quien lo toma o le responde
primero, los demás técnicos no pueden quitárselo y solo él (o el administrador) lo suelta,
siempre con un motivo."""
import pytest
from fastapi import HTTPException
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Area, AsignacionTicket, Auditoria, Cliente, Ticket
from app.services import toma

# La tabla de técnicos de prueba (conftest.py): Power BI → Ana Mora; Webdox → Pedro Vera, Marta Gil.

LIBERAR = {"motivo": "otra_area", "detalle": "Es un tema de licencias, no de Power BI"}


@pytest.fixture()
def equipo(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    ana = crear_cuenta("ana@ejemplo.com", "tecnico", nombre="Ana Mora")
    luis = crear_cuenta("luis@ejemplo.com", "tecnico", nombre="Luis Paredes")
    adm = crear_cuenta("adm@ejemplo.com", "administrador", nombre="Admin Obra")
    return {
        "ana": ana,
        "luis": luis,
        "adm": adm,
        "h_usr": entrar("usr@ejemplo.com"),
        "h_ana": entrar("ana@ejemplo.com"),
        "h_luis": entrar("luis@ejemplo.com"),
        "h_adm": entrar("adm@ejemplo.com"),
    }


def _crear(client, h, categoria="Power BI"):
    r = client.post(
        "/tickets",
        json={"texto": "El tablero de ventas no carga", "tipo": "Incidencia o problema técnico", "categoria": categoria},
        headers=h,
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_el_sugerido_aun_no_esta_tomado_y_cualquiera_lo_puede_tomar(client, equipo):
    t = _crear(client, equipo["h_usr"])
    assert t["tecnico_id"] == equipo["ana"].id and t["tomado_en"] is None  # solo sugerido

    r = client.post(f"/tickets/{t['id']}/tomar", headers=equipo["h_luis"])
    assert r.status_code == 200, r.text
    assert r.json()["tecnico_id"] == equipo["luis"].id
    assert r.json()["tomado_en"] is not None
    assert r.json()["estado"] == "en_proceso"


def test_un_ticket_tomado_no_lo_toma_ni_lo_cambia_otro_tecnico(client, equipo):
    t = _crear(client, equipo["h_usr"])
    assert client.post(f"/tickets/{t['id']}/tomar", headers=equipo["h_ana"]).status_code == 200
    h = equipo["h_luis"]

    r = client.post(f"/tickets/{t['id']}/tomar", headers=h)
    assert r.status_code == 409 and "Ana Mora" in r.json()["detail"]
    assert client.patch(f"/tickets/{t['id']}", json={"tecnico_id": equipo["luis"].id}, headers=h).status_code == 403
    assert client.patch(f"/tickets/{t['id']}", json={"estado": "resuelto"}, headers=h).status_code == 403
    assert client.post(f"/tickets/{t['id']}/cancelar", json={"motivo": "No aplica ya"}, headers=h).status_code == 403
    assert client.post(f"/tickets/{t['id']}/liberar", json=LIBERAR, headers=h).status_code == 403
    r = client.post(f"/tickets/{t['id']}/mensajes", json={"texto": "Hola, lo reviso yo"}, headers=h)
    assert r.status_code == 403
    assert client.get(f"/tickets/{t['id']}", headers=h).json()["tecnico_id"] == equipo["ana"].id


def test_la_primera_respuesta_toma_el_ticket(client, equipo, session):
    t = _crear(client, equipo["h_usr"])
    r = client.post(f"/tickets/{t['id']}/mensajes", json={"texto": "Hola, ya lo reviso"}, headers=equipo["h_luis"])
    assert r.status_code == 200, r.text
    d = client.get(f"/tickets/{t['id']}", headers=equipo["h_luis"]).json()
    assert d["tecnico_id"] == equipo["luis"].id and d["tomado_en"] is not None
    assert d["estado"] == "en_proceso"
    # La toma implícita también queda en la bitácora y en el historial de asignación.
    fila = session.exec(select(Auditoria).where(Auditoria.accion == "ticket_tomado")).one()
    assert fila.actor_id == equipo["luis"].id and fila.entidad_id == t["id"] and "al responder" in fila.descripcion
    historial = client.get(f"/tickets/{t['id']}/asignaciones", headers=equipo["h_adm"]).json()
    assert [(h["accion"], h["via"], h["tecnico"]) for h in historial] == [("tomado", "respuesta", "Luis Paredes")]
    # El solicitante sigue pudiendo escribir.
    assert client.post(f"/tickets/{t['id']}/mensajes", json={"texto": "Gracias"}, headers=equipo["h_usr"]).status_code == 200


def test_pasar_a_en_proceso_tambien_lo_toma(client, equipo):
    t = _crear(client, equipo["h_usr"])
    r = client.patch(f"/tickets/{t['id']}", json={"estado": "en_proceso"}, headers=equipo["h_luis"]).json()
    assert r["tecnico_id"] == equipo["luis"].id and r["tomado_en"] is not None
    r = client.patch(f"/tickets/{t['id']}", json={"estado": "en_proceso"}, headers=equipo["h_ana"])
    assert r.status_code == 403


def test_quien_lo_atiende_sigue_trabajando_normal(client, equipo):
    t = _crear(client, equipo["h_usr"])
    h = equipo["h_ana"]
    client.post(f"/tickets/{t['id']}/tomar", headers=h)
    assert client.post(f"/tickets/{t['id']}/tomar", headers=h).status_code == 200  # ya era suyo: no falla
    assert client.post(f"/tickets/{t['id']}/mensajes", json={"texto": "Ya casi"}, headers=h).status_code == 200
    r = client.patch(f"/tickets/{t['id']}", json={"prioridad": "Alta"}, headers=h)
    assert r.status_code == 200
    r = client.patch(f"/tickets/{t['id']}", json={"estado": "resuelto"}, headers=h).json()
    assert r["estado"] == "resuelto" and r["tecnico_id"] == equipo["ana"].id
    # Una sola toma registrada aunque pulsó dos veces y respondió.
    historial = client.get(f"/tickets/{t['id']}/asignaciones", headers=h).json()
    assert [x["accion"] for x in historial] == ["tomado"]


def test_liberar_exige_motivo_y_lo_sugiere_a_otro(client, equipo, crear_cuenta, entrar):
    pedro = crear_cuenta("pedro@ejemplo.com", "tecnico", nombre="Pedro Vera")
    marta = crear_cuenta("marta@ejemplo.com", "tecnico", nombre="Marta Gil")
    h_pedro = entrar("pedro@ejemplo.com")
    t = _crear(client, equipo["h_usr"], "Webdox")
    assert t["tecnico_id"] == pedro.id
    client.post(f"/tickets/{t['id']}/tomar", headers=h_pedro)

    assert client.post(f"/tickets/{t['id']}/liberar", json={"motivo": "carga", "detalle": ""}, headers=h_pedro).status_code == 400
    assert client.post(f"/tickets/{t['id']}/liberar", json={"motivo": "x", "detalle": "Sin tiempo hoy"}, headers=h_pedro).status_code == 400
    r = client.post(f"/tickets/{t['id']}/liberar", json={"motivo": "carga", "detalle": "Tengo tres críticos hoy"}, headers=h_pedro)
    assert r.status_code == 200, r.text
    t2 = r.json()
    assert t2["estado"] == "abierto" and t2["tomado_en"] is None
    assert t2["tecnico_id"] == marta.id  # el otro técnico de Webdox, nunca el mismo

    historial = client.get(f"/tickets/{t['id']}/asignaciones", headers=equipo["h_adm"]).json()
    assert historial[-1]["accion"] == "liberado" and historial[-1]["tecnico"] == "Pedro Vera"
    assert historial[-1]["motivo_titulo"] == "Tengo demasiados tickets pendientes"
    estados = client.get(f"/tickets/{t['id']}/historial", headers=equipo["h_adm"]).json()
    assert estados[-1]["estado_nuevo"] == "abierto" and "Tengo tres críticos hoy" in estados[-1]["motivo"]


def test_si_no_hay_otro_tecnico_del_sistema_queda_sin_asignar(client, equipo):
    t = _crear(client, equipo["h_usr"])  # Power BI: solo Ana
    client.post(f"/tickets/{t['id']}/tomar", headers=equipo["h_ana"])
    r = client.post(f"/tickets/{t['id']}/liberar", json=LIBERAR, headers=equipo["h_ana"]).json()
    assert r["tecnico_id"] is None and r["tomado_en"] is None
    # Ya libre, otro técnico lo puede tomar.
    assert client.post(f"/tickets/{t['id']}/tomar", headers=equipo["h_luis"]).status_code == 200


def test_no_se_libera_un_ticket_que_nadie_tomo(client, equipo):
    t = _crear(client, equipo["h_usr"])
    assert client.post(f"/tickets/{t['id']}/liberar", json=LIBERAR, headers=equipo["h_ana"]).status_code == 409


def test_el_tecnico_no_lo_pasa_a_otro_sin_liberarlo(client, equipo):
    t = _crear(client, equipo["h_usr"])
    client.post(f"/tickets/{t['id']}/tomar", headers=equipo["h_ana"])
    r = client.patch(f"/tickets/{t['id']}", json={"tecnico_id": equipo["luis"].id}, headers=equipo["h_ana"])
    assert r.status_code == 409 and "libéralo" in r.json()["detail"]


def test_el_administrador_reasigna_y_puede_actuar_sin_quitarselo(client, equipo):
    t = _crear(client, equipo["h_usr"])
    client.post(f"/tickets/{t['id']}/tomar", headers=equipo["h_ana"])
    ha = equipo["h_adm"]

    # El administrador escribe y cambia la prioridad: el ticket sigue siendo de Ana.
    assert client.post(f"/tickets/{t['id']}/mensajes", json={"texto": "Ana, revisa esto"}, headers=ha).status_code == 200
    r = client.patch(f"/tickets/{t['id']}", json={"prioridad": "Crítica"}, headers=ha).json()
    assert r["tecnico_id"] == equipo["ana"].id

    # Reasignar a Luis: queda tomado a su nombre y Ana ya no lo puede cambiar.
    r = client.patch(f"/tickets/{t['id']}", json={"tecnico_id": equipo["luis"].id}, headers=ha).json()
    assert r["tecnico_id"] == equipo["luis"].id and r["tomado_en"] is not None
    assert client.post(f"/tickets/{t['id']}/tomar", headers=equipo["h_ana"]).status_code == 409
    historial = client.get(f"/tickets/{t['id']}/asignaciones", headers=ha).json()
    assert [(x["accion"], x["tecnico"], x["por"]) for x in historial][-1] == ("reasignado", "Luis Paredes", "Admin Obra")

    # El administrador también puede liberarlo.
    assert client.post(f"/tickets/{t['id']}/liberar", json=LIBERAR, headers=ha).status_code == 200


def test_tomar_y_liberar_quedan_en_la_bitacora(client, equipo, session):
    t = _crear(client, equipo["h_usr"])
    client.post(f"/tickets/{t['id']}/tomar", headers=equipo["h_ana"])
    client.post(f"/tickets/{t['id']}/tomar", headers=equipo["h_luis"])  # 409: no se registra
    client.post(f"/tickets/{t['id']}/liberar", json=LIBERAR, headers=equipo["h_ana"])
    filas = session.exec(select(Auditoria).where(Auditoria.entidad_id == t["id"]).order_by(Auditoria.id)).all()
    claves = [(f.accion, f.actor) for f in filas if f.accion in ("ticket_tomado", "ticket_liberado")]
    assert claves == [("ticket_tomado", "Ana Mora"), ("ticket_liberado", "Ana Mora")]


def test_dos_tecnicos_tomando_a_la_vez_solo_gana_uno(tmp_path):
    """Las dos sesiones leen el ticket libre antes de que ninguna escriba (lo que pasa con
    dos clics simultáneos). La segunda en escribir recibe 409 y el ticket queda del primero."""
    motor = create_engine(f"sqlite:///{tmp_path / 'carrera.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(motor)
    with Session(motor) as s:
        area = Area(nombre="Sistemas")
        s.add(area)
        s.commit()
        personas = [Cliente(nombre=n, email=f"{n}@x.com", area_id=area.id, rol=r) for n, r in
                    (("usr", "usuario"), ("ana", "tecnico"), ("luis", "tecnico"))]
        s.add_all(personas)
        s.commit()
        ticket = Ticket(cliente_id=personas[0].id, texto="No imprime", estado="abierto")
        s.add(ticket)
        s.commit()
        ids = [p.id for p in personas] + [ticket.id]

    s_ana, s_luis = Session(motor), Session(motor)
    try:
        t_ana, t_luis = s_ana.get(Ticket, ids[3]), s_luis.get(Ticket, ids[3])
        assert t_ana.tomado_en is None and t_luis.tomado_en is None  # los dos lo ven libre
        assert toma.tomar(s_ana, t_ana, s_ana.get(Cliente, ids[1]), via="boton") is True
        s_ana.commit()
        with pytest.raises(HTTPException) as error:
            toma.tomar(s_luis, t_luis, s_luis.get(Cliente, ids[2]), via="boton")
        assert error.value.status_code == 409 and "ana" in error.value.detail
        s_luis.rollback()
    finally:
        s_ana.close()
        s_luis.close()
    with Session(motor) as s:
        assert s.get(Ticket, ids[3]).tecnico_id == ids[1]
        assert len(s.exec(select(AsignacionTicket)).all()) == 1

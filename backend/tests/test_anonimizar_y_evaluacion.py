"""Anonimización de los datos de la empresa y evaluación simulada de Minutito."""
from datetime import datetime

from sqlmodel import select

from app.models import Seudonimo, Ticket, TicketHistorico
from app.services import evaluacion_minutito
from app.services.anonimizar import anonimizar_base


def _ticket_cargado(session, cliente_id, id_externo, texto, solicitante="Beto Ruiz"):
    t = Ticket(cliente_id=cliente_id, texto=texto, id_externo=id_externo, solicitante_externo=solicitante,
               tipo="Incidencia o problema técnico", categoria="Internet", clasificacion_confirmada=True)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def test_anonimizar_reemplaza_nombres_correos_y_numeros_de_forma_estable(session, crear_cuenta):
    usuario = crear_cuenta("x@ejemplo.com")
    session.add(TicketHistorico(
        id_externo="1", estado="Completado", creado_en=datetime(2026, 1, 1), solicitante="Beto Ruíz",
        asignado_a="Tito Pérez",
        descripcion="Hola, soy Beto Ruiz, mi correo es beto.ruiz@empresa.com y mi celular 0991234567. Cédula 0912345678",
    ))
    session.commit()
    t = _ticket_cargado(session, usuario.id, "100", "Por favor Tito Perez revise la laptop", solicitante="BETO RUIZ")

    assert anonimizar_base(session) == {"historico": 1, "tickets": 1}
    h = session.exec(select(TicketHistorico)).one()
    assert (h.solicitante, h.asignado_a) == ("Solicitante 001", "Técnico 01")
    assert h.descripcion == "Hola, soy [persona], mi correo es [correo] y mi celular [número]. Cédula [número]"
    session.refresh(t)
    assert t.solicitante_externo == "Solicitante 001"  # la misma persona, el mismo alias
    assert t.texto == "Por favor [persona] revise la laptop"
    # en la base no queda el nombre, solo su hash
    assert all("beto" not in s.clave for s in session.exec(select(Seudonimo)).all())
    assert anonimizar_base(session) == {"historico": 0, "tickets": 0}  # repetirlo no cambia nada


def test_evaluacion_simulada_no_toca_el_ticket_y_calcula_el_porcentaje(
    session, crear_cuenta, client, entrar, monkeypatch
):
    usuario = crear_cuenta("x@ejemplo.com")
    crear_cuenta("adm@ejemplo.com", "administrador")
    tickets = [_ticket_cargado(session, usuario.id, str(i), f"No tengo internet {i}") for i in range(3)]
    monkeypatch.setattr(evaluacion_minutito, "responder", lambda historial: (f"Pasos para: {historial[-1][1]}", False))

    assert evaluacion_minutito.generar_pendientes(session) == {"generadas": 3, "pendientes": 0, "error": None}
    assert evaluacion_minutito.generar_pendientes(session)["generadas"] == 0  # no repite

    h = entrar("adm@ejemplo.com")
    datos = client.get("/reportes/evaluacion-minutito", headers=h).json()
    assert datos["con_respuesta"] == 3 and datos["sin_evaluar"] == 3 and datos["pct_resolveria"] is None
    ids = [i["id"] for i in datos["items"]]
    for evaluacion_id, veredicto in zip(ids, ["resuelve", "no_resuelve", "no_aplica"]):
        r = client.post(f"/admin/evaluacion-minutito/{evaluacion_id}", json={"veredicto": veredicto}, headers=h)
        assert r.status_code == 200
    assert client.post(f"/admin/evaluacion-minutito/{ids[0]}", json={"veredicto": "quizas"}, headers=h).status_code == 400

    datos = client.get("/reportes/evaluacion-minutito", headers=h).json()
    assert datos["pct_resolveria"] == 0.5  # 1 de 2 de primer nivel; «no aplica» no cuenta
    # la evaluación no crea interacciones ni cambia el estado del ticket
    session.refresh(tickets[0])
    assert tickets[0].estado == "abierto"
    assert client.get(f"/tickets/{tickets[0].id}/interacciones", headers=h).json() == []


def test_evaluacion_solo_para_el_administrador(client, crear_cuenta, entrar):
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h = entrar("tec@ejemplo.com")
    assert client.get("/reportes/evaluacion-minutito", headers=h).status_code == 403
    assert client.post("/admin/evaluacion-minutito/generar", headers=h).status_code == 403
    assert client.patch("/admin/evaluacion-minutito/1/solucion", json={"solucion": "x"}, headers=h).status_code == 403


def test_solucion_esperada_se_guarda_sin_tocar_la_respuesta_de_minutito(
    session, crear_cuenta, client, entrar, monkeypatch
):
    usuario = crear_cuenta("x@ejemplo.com")
    crear_cuenta("adm@ejemplo.com", "administrador")
    _ticket_cargado(session, usuario.id, "1", "No tengo internet")
    monkeypatch.setattr(evaluacion_minutito, "responder", lambda historial: ("Reinicia el router.", False))
    evaluacion_minutito.generar_pendientes(session)
    h = entrar("adm@ejemplo.com")
    eid = client.get("/reportes/evaluacion-minutito", headers=h).json()["items"][0]["id"]

    r = client.patch(f"/admin/evaluacion-minutito/{eid}/solucion", json={"solucion": "  Revisar el cable de red  "}, headers=h)
    assert r.status_code == 200
    item = client.get("/reportes/evaluacion-minutito", headers=h).json()["items"][0]
    assert (item["solucion_esperada"], item["respuesta"]) == ("Revisar el cable de red", "Reinicia el router.")

    client.patch(f"/admin/evaluacion-minutito/{eid}/solucion", json={"solucion": "   "}, headers=h)
    assert client.get("/reportes/evaluacion-minutito", headers=h).json()["items"][0]["solucion_esperada"] is None
    assert client.patch(f"/admin/evaluacion-minutito/{eid}/solucion", json={"solucion": "x" * 2001}, headers=h).status_code == 400
    assert client.patch("/admin/evaluacion-minutito/999/solucion", json={"solucion": "x"}, headers=h).status_code == 404


def test_limpiar_texto_quita_menciones_y_nombres_antes_de_la_cedula():
    from app.services.anonimizar import limpiar_texto

    assert limpiar_texto("Ingreso de Danny Briones C.I. # 0912345678", []) == "Ingreso de [persona] C.I. # [número]"
    assert limpiar_texto("@Robert Vasquez revisa esto", []) == "@[persona] revisa esto"
    # sin nombre ni dato personal, el texto no cambia
    assert limpiar_texto("No tengo internet en la oficina, ci ves algo", []) == "No tengo internet en la oficina, ci ves algo"

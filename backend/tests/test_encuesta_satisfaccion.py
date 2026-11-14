"""Encuesta de satisfacción: solo quien abrió el ticket, solo resuelto, una por ticket
(se puede cambiar) y el resumen que ve el personal en Reportes."""
from .test_acceso_y_roles import _crear_ticket


def _preparar(client, crear_cuenta, entrar):
    crear_cuenta("u@ejemplo.com", "usuario", nombre="Ana Usuaria")
    crear_cuenta("otro@ejemplo.com", "usuario")
    crear_cuenta("t@ejemplo.com", "tecnico", nombre="Tito Técnico")
    usuario, tecnico = entrar("u@ejemplo.com"), entrar("t@ejemplo.com")
    return usuario, tecnico, _crear_ticket(client, usuario)


def _calificar(client, headers, ticket_id, estrellas=5, comentario=None):
    return client.post(
        f"/tickets/{ticket_id}/encuesta", json={"estrellas": estrellas, "comentario": comentario}, headers=headers
    )


def test_solo_se_califica_un_ticket_resuelto_y_por_quien_lo_abrio(client, crear_cuenta, entrar):
    usuario, tecnico, ticket = _preparar(client, crear_cuenta, entrar)

    assert _calificar(client, usuario, ticket["id"]).status_code == 409  # todavía abierto
    client.patch(f"/tickets/{ticket['id']}", json={"estado": "resuelto"}, headers=tecnico)

    assert _calificar(client, tecnico, ticket["id"]).status_code == 403
    assert _calificar(client, entrar("otro@ejemplo.com"), ticket["id"]).status_code == 403
    assert _calificar(client, usuario, ticket["id"], estrellas=0).status_code == 400
    assert _calificar(client, usuario, ticket["id"], estrellas=6).status_code == 400

    pendientes = client.get("/encuestas/pendientes", headers=usuario).json()
    assert [p["ticket_id"] for p in pendientes] == [ticket["id"]]

    r = _calificar(client, usuario, ticket["id"], 4, "  Rápido y amable ")
    assert r.status_code == 200, r.text
    assert r.json()["estrellas"] == 4 and r.json()["comentario"] == "Rápido y amable"
    assert client.get("/encuestas/pendientes", headers=usuario).json() == []

    # Puede cambiar su calificación: sigue habiendo una sola.
    assert _calificar(client, usuario, ticket["id"], 2).json()["actualizado_en"] is not None
    assert client.get(f"/tickets/{ticket['id']}/encuesta", headers=tecnico).json()["estrellas"] == 2


def test_el_personal_ve_el_resumen_y_el_usuario_no(client, crear_cuenta, entrar):
    usuario, tecnico, ticket = _preparar(client, crear_cuenta, entrar)
    segundo = _crear_ticket(client, usuario)
    for t in (ticket, segundo):
        client.patch(f"/tickets/{t['id']}", json={"estado": "resuelto"}, headers=tecnico)
    _calificar(client, usuario, ticket["id"], 5, "Excelente")

    assert client.get("/reportes/satisfaccion", headers=usuario).status_code == 403
    resumen = client.get("/reportes/satisfaccion", headers=tecnico).json()
    assert resumen["respuestas"] == 1 and resumen["promedio"] == 5
    assert resumen["tasa_respuesta_pct"] == 50.0
    assert resumen["reparto"][0] == {"estrellas": 5, "total": 1}
    assert resumen["por_tecnico"][0]["tecnico"] == "Tito Técnico"
    assert resumen["comentarios"][0]["comentario"] == "Excelente"


def test_el_correo_de_resuelto_invita_a_calificar_sin_correos_extra(client, crear_cuenta, entrar, correos):
    usuario, tecnico, ticket = _preparar(client, crear_cuenta, entrar)
    antes = len(list(correos.glob("*.txt")))
    client.patch(f"/tickets/{ticket['id']}", json={"estado": "resuelto"}, headers=tecnico)
    nuevos = sorted(correos.glob("*.txt"))[antes:]
    assert len(nuevos) == 1
    assert "califica la atención" in nuevos[0].read_text(encoding="utf-8")

"""Respuestas predefinidas del personal y vínculo de tickets duplicados."""
from .test_acceso_y_roles import _crear_ticket


def _preparar(client, crear_cuenta, entrar):
    crear_cuenta("u@ejemplo.com", "usuario", nombre="Ana Pérez")
    crear_cuenta("t@ejemplo.com", "tecnico", nombre="Tito Ruiz")
    crear_cuenta("t2@ejemplo.com", "tecnico", nombre="Otro Técnico")
    crear_cuenta("adm@ejemplo.com", "administrador")
    return entrar("u@ejemplo.com"), entrar("t@ejemplo.com"), entrar("t2@ejemplo.com"), entrar("adm@ejemplo.com")


def test_respuestas_predefinidas(client, crear_cuenta, entrar):
    usuario, tecnico, otro, admin = _preparar(client, crear_cuenta, entrar)
    ticket = _crear_ticket(client, usuario)

    assert client.get("/respuestas-predefinidas", headers=usuario).status_code == 403
    iniciales = client.get("/respuestas-predefinidas", headers=tecnico).json()
    assert len(iniciales) == 5  # las de ejemplo, una sola vez
    assert len(client.get("/respuestas-predefinidas", headers=tecnico).json()) == 5

    r = client.post("/respuestas-predefinidas", json={"titulo": "Mía", "texto": "Hola {nombre}, ticket {ticket} con {tecnico}."}, headers=tecnico)
    mia = r.json()
    assert r.status_code == 200 and mia["editable"]
    assert client.patch(f"/respuestas-predefinidas/{mia['id']}", json={"titulo": "Ajena"}, headers=otro).status_code == 403
    assert client.patch(f"/respuestas-predefinidas/{mia['id']}", json={"titulo": "De admin"}, headers=admin).status_code == 200

    usada = client.post(f"/tickets/{ticket['id']}/respuesta-predefinida", json={"predefinida_id": mia["id"]}, headers=otro).json()
    assert usada["texto"] == f"Hola Ana, ticket {ticket['id']} con Otro Técnico."
    lista = client.get("/respuestas-predefinidas", headers=tecnico).json()
    assert lista[0]["id"] == mia["id"] and lista[0]["usos"] == 1  # las más usadas primero

    assert client.delete(f"/respuestas-predefinidas/{mia['id']}", headers=tecnico).status_code == 200
    assert all(p["id"] != mia["id"] for p in client.get("/respuestas-predefinidas", headers=tecnico).json())


def test_vincular_duplicado_lo_cancela_con_motivo(client, crear_cuenta, entrar):
    usuario, tecnico, _, _ = _preparar(client, crear_cuenta, entrar)
    principal = _crear_ticket(client, usuario, "La impresora del piso 3 no imprime nada")
    duplicado = _crear_ticket(client, usuario, "No imprime la impresora del piso 3")
    _crear_ticket(client, usuario, "Necesito acceso a SAP para el módulo de compras")

    sugeridos = client.get(f"/tickets/{duplicado['id']}/posibles-duplicados", headers=tecnico).json()
    assert [s["id"] for s in sugeridos] == [principal["id"]]
    assert client.get(f"/tickets/{duplicado['id']}/posibles-duplicados", headers=usuario).status_code == 403

    assert client.post(f"/tickets/{duplicado['id']}/vincular", json={"principal_id": duplicado["id"]}, headers=tecnico).status_code == 400
    r = client.post(f"/tickets/{duplicado['id']}/vincular", json={"principal_id": principal["id"]}, headers=tecnico)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "cancelado" and r.json()["motivo_cancelacion"] == f"Duplicado del ticket #{principal['id']}"
    assert r.json()["duplicado_de_id"] == principal["id"]
    assert client.get(f"/tickets/{principal['id']}", headers=usuario).json()["duplicados"] == [duplicado["id"]]
    # Un principal no puede volverse duplicado de otro, ni encadenar.
    otro = _crear_ticket(client, usuario, "Otro problema distinto")
    assert client.post(f"/tickets/{principal['id']}/vincular", json={"principal_id": otro["id"]}, headers=tecnico).status_code == 400
    assert client.post(f"/tickets/{otro['id']}/vincular", json={"principal_id": duplicado["id"]}, headers=tecnico).status_code == 400

    assert client.delete(f"/tickets/{duplicado['id']}/vincular", headers=tecnico).json()["duplicado_de_id"] is None

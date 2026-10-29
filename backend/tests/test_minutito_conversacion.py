"""Minutito conversa antes de que exista un ticket; se resuelve o se crea el ticket desde ahí."""
import json

from app.services import minutito_chat


def _respuestas(monkeypatch, partes):
    monkeypatch.setattr(minutito_chat, "responder_en_vivo", lambda historial: iter(partes))


def _enviar(client, h, conv_id, texto):
    r = client.post(f"/minutito/conversaciones/{conv_id}/mensajes", json={"texto": texto}, headers=h)
    assert r.status_code == 200, r.text
    return [json.loads(linea) for linea in r.text.splitlines() if linea]


def test_conversar_sin_ticket_y_resolver_suma_puntos_y_cuenta_como_autonoma(client, crear_cuenta, entrar, monkeypatch):
    crear_cuenta("ana@ejemplo.com")
    h = entrar("ana@ejemplo.com")
    conv = client.post("/minutito/conversaciones", headers=h).json()
    assert client.post(f"/minutito/conversaciones/{conv['id']}/resolver", headers=h).status_code == 400  # sin hablar

    _respuestas(monkeypatch, ["Prueba ", "reiniciar el **router**."])
    eventos = _enviar(client, h, conv["id"], "no tengo wifi")
    assert "".join(e.get("delta", "") for e in eventos) == "Prueba reiniciar el **router**."
    assert eventos[-1]["fin"] is True and eventos[-1]["ofrece_ticket"] is False

    actual = client.get("/minutito/conversaciones/actual", headers=h).json()
    assert [(m["rol"], m["texto"]) for m in actual["mensajes"]] == [
        ("usuario", "no tengo wifi"),
        ("minutito", "Prueba reiniciar el **router**."),
    ]
    assert client.get("/tickets", headers=h).json() == []  # conversar no crea tickets

    r = client.post(f"/minutito/conversaciones/{conv['id']}/resolver", headers=h)
    assert r.status_code == 200 and r.json()["estado"] == "resuelta"
    assert client.get("/minutito/conversaciones/actual", headers=h).json() is None
    assert client.get("/auth/yo", headers=h).json()["puntos"] == 10
    resumen = client.get("/reportes/resumen", headers=h).json()
    assert (resumen["conversaciones_minutito"], resumen["conversaciones_resueltas"]) == (1, 1)
    assert resumen["pct_resolucion_autonoma"] == 100.0
    # terminada, ya no se puede seguir
    assert client.post(f"/minutito/conversaciones/{conv['id']}/mensajes", json={"texto": "hola"}, headers=h).status_code == 409


def test_la_marca_de_ticket_nunca_llega_a_la_pantalla(monkeypatch):
    class Parte:
        def __init__(self, t):
            self.message = type("M", (), {"content": t})()

    monkeypatch.setattr(minutito_chat, "_llamar", lambda m, stream: iter(map(Parte, ["Eso lo hace el equipo. [OFRE", "CER_TIC", "KET]"])))
    texto = "".join(minutito_chat.responder_en_vivo([("usuario", "necesito una laptop")]))
    assert texto == "Eso lo hace el equipo. "
    assert minutito_chat.separar_marca("Listo. [OFRECER_TICKET]") == ("Listo.", True)


def test_crear_ticket_desde_la_conversacion_la_enlaza(client, crear_cuenta, entrar, monkeypatch):
    crear_cuenta("ana@ejemplo.com")
    crear_cuenta("beto@ejemplo.com")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h, h_beto, h_tec = entrar("ana@ejemplo.com"), entrar("beto@ejemplo.com"), entrar("tec@ejemplo.com")
    conv = client.post("/minutito/conversaciones", headers=h).json()
    _respuestas(monkeypatch, ["Eso lo hace el equipo de sistemas."])
    eventos = _enviar(client, h, conv["id"], "necesito una laptop nueva para un ingreso")
    assert eventos[-1]["fin"]

    monkeypatch.setattr(minutito_chat, "resumir_para_ticket", lambda historial: "Necesito una laptop nueva para el ingreso de un colaborador.")
    borrador = client.post(f"/minutito/conversaciones/{conv['id']}/borrador", headers=h).json()
    assert borrador["texto"].startswith("Necesito una laptop") and borrador["sugerencia"]["categoria"]

    # nadie más puede usar la conversación para crear su ticket
    otro = client.post("/tickets", json={"texto": "otra cosa diferente", "conversacion_id": conv["id"]}, headers=h_beto)
    assert otro.status_code == 404
    r = client.post("/tickets", json={"texto": borrador["texto"], "conversacion_id": conv["id"]}, headers=h)
    assert r.status_code == 200, r.text
    ticket_id = r.json()["id"]

    enlazada = client.get(f"/minutito/tickets/{ticket_id}", headers=h_tec).json()  # el técnico la ve
    assert enlazada["estado"] == "ticket" and len(enlazada["mensajes"]) == 2
    assert client.get(f"/minutito/tickets/{ticket_id}", headers=h_beto).status_code == 404
    resumen = client.get("/reportes/resumen", headers=h).json()
    assert (resumen["conversaciones_minutito"], resumen["conversaciones_resueltas"], resumen["pct_resolucion_autonoma"]) == (1, 0, 0.0)
    # resuelto por un técnico después de intentar con Minutito: 3 puntos
    client.patch(f"/tickets/{ticket_id}", json={"estado": "resuelto"}, headers=h_tec)
    assert client.get("/auth/yo", headers=h).json()["puntos"] == 3


def test_minutito_caido_avisa_y_la_conversacion_sigue_abierta(client, crear_cuenta, entrar, monkeypatch):
    crear_cuenta("ana@ejemplo.com")
    h = entrar("ana@ejemplo.com")
    conv = client.post("/minutito/conversaciones", headers=h).json()

    def caido(historial):
        raise minutito_chat.MinutitoNoDisponible("sin ollama")
        yield  # noqa: unreachable — lo vuelve generador

    monkeypatch.setattr(minutito_chat, "responder_en_vivo", caido)
    eventos = _enviar(client, h, conv["id"], "no imprime")
    assert "error" in eventos[-1]
    assert client.get("/minutito/conversaciones/actual", headers=h).json()["estado"] == "abierta"


def test_conversacion_ajena_no_se_ve(client, crear_cuenta, entrar):
    crear_cuenta("ana@ejemplo.com")
    crear_cuenta("beto@ejemplo.com")
    conv = client.post("/minutito/conversaciones", headers=entrar("ana@ejemplo.com")).json()
    h_beto = entrar("beto@ejemplo.com")
    assert client.get(f"/minutito/conversaciones/{conv['id']}", headers=h_beto).status_code == 404
    assert client.post(f"/minutito/conversaciones/{conv['id']}/mensajes", json={"texto": "x"}, headers=h_beto).status_code == 404


def test_limite_de_mensajes_a_minutito(client, crear_cuenta, entrar, monkeypatch):
    from app.routers import minutito

    crear_cuenta("ana@ejemplo.com")
    h = entrar("ana@ejemplo.com")
    conv = client.post("/minutito/conversaciones", headers=h).json()
    _respuestas(monkeypatch, ["ok"])
    monkeypatch.setattr(minutito, "MAX_MENSAJES_POR_MINUTO", 2)
    _enviar(client, h, conv["id"], "uno")
    _enviar(client, h, conv["id"], "dos")
    r = client.post(f"/minutito/conversaciones/{conv['id']}/mensajes", json={"texto": "tres"}, headers=h)
    assert r.status_code == 429
    # con una respuesta en curso tampoco se acepta otra
    minutito.mensajes_recientes.clear()
    minutito.respondiendo.add(client.get("/auth/yo", headers=h).json()["id"])
    assert client.post(f"/minutito/conversaciones/{conv['id']}/mensajes", json={"texto": "x"}, headers=h).status_code == 429

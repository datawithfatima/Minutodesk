"""Minutito conversa antes de que exista un ticket; se resuelve o se crea el ticket desde ahí."""
import json

from app.services import minutito_chat
from app.services.catalogos import TIPO_INCIDENCIA, TIPO_SOLICITUD


def _respuestas(monkeypatch, partes):
    monkeypatch.setattr(minutito_chat, "responder_en_vivo", lambda historial, casos=None: iter(partes))


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
    # una solicitud no es de primer nivel: no cuenta para el objetivo 2; una incidencia sí
    for tipo, esperado in [(TIPO_SOLICITUD, (0, None)), (TIPO_INCIDENCIA, (1, 0.0))]:
        client.patch(f"/tickets/{ticket_id}", json={"tipo": tipo}, headers=h_tec)
        resumen = client.get("/reportes/resumen", headers=h).json()
        assert (resumen["conversaciones_primer_nivel"], resumen["pct_primer_nivel"]) == esperado
    # resuelto por un técnico después de intentar con Minutito: 3 puntos
    client.patch(f"/tickets/{ticket_id}", json={"estado": "resuelto"}, headers=h_tec)
    assert client.get("/auth/yo", headers=h).json()["puntos"] == 3


def test_minutito_caido_avisa_y_la_conversacion_sigue_abierta(client, crear_cuenta, entrar, monkeypatch):
    crear_cuenta("ana@ejemplo.com")
    h = entrar("ana@ejemplo.com")
    conv = client.post("/minutito/conversaciones", headers=h).json()

    def caido(historial, casos=None):
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


def test_mis_conversaciones_resueltas_para_el_historico(client, crear_cuenta, entrar, monkeypatch):
    crear_cuenta("ana@ejemplo.com")
    crear_cuenta("beto@ejemplo.com")
    h = entrar("ana@ejemplo.com")
    conv = client.post("/minutito/conversaciones", headers=h).json()
    _respuestas(monkeypatch, ["Reinicia el router."])
    _enviar(client, h, conv["id"], "no tengo internet en la oficina")
    client.post(f"/minutito/conversaciones/{conv['id']}/resolver", headers=h)
    client.post("/minutito/conversaciones", headers=h)  # otra, abierta

    resueltas = client.get("/minutito/conversaciones", params={"estado": "resuelta"}, headers=h).json()
    assert [(c["id"], c["primera_pregunta"]) for c in resueltas] == [(conv["id"], "no tengo internet en la oficina")]
    assert client.get("/minutito/conversaciones", headers=entrar("beto@ejemplo.com")).json() == []


def test_imagenes_en_la_conversacion_avisan_al_modelo_y_pasan_al_ticket(client, crear_cuenta, entrar, monkeypatch, tmp_path):
    from app.routers import adjuntos

    from app.services import ocr

    monkeypatch.setattr(adjuntos, "DIRECTORIO_ARCHIVOS", tmp_path / "uploads")
    monkeypatch.setattr(ocr, "leer_texto", lambda ruta: "Error 0x800CCC0E")
    crear_cuenta("ana@ejemplo.com")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h, h_tec = entrar("ana@ejemplo.com"), entrar("tec@ejemplo.com")
    conv = client.post("/minutito/conversaciones", headers=h).json()

    def subir(nombre, contenido=b"png"):
        return client.post(
            f"/minutito/conversaciones/{conv['id']}/imagenes",
            content=contenido,
            headers={**h, "X-Nombre-Archivo": nombre, "Content-Type": "application/octet-stream"},
        )

    assert subir("informe.pdf").status_code == 400  # solo imágenes
    assert subir("vacia.png", b"").status_code == 400
    assert client.post(f"/minutito/conversaciones/{conv['id']}/mensajes", json={"texto": " "}, headers=h).status_code == 400

    quitada = subir("otra.png").json()
    assert client.delete(f"/minutito/conversaciones/{conv['id']}/imagenes/{quitada['id']}", headers=h).status_code == 204
    assert subir("error.png").status_code == 200

    vistos = {}

    def falso(historial, casos=None):
        vistos["historial"] = list(historial)
        return iter(["¿Qué mensaje te aparece?"])

    monkeypatch.setattr(minutito_chat, "responder_en_vivo", falso)
    eventos = _enviar(client, h, conv["id"], "")  # solo la imagen, sin texto
    assert eventos[-1]["fin"]
    rol, texto = vistos["historial"][-1]
    # el modelo recibe el texto que el OCR leyó en la captura
    assert rol == "usuario" and "error.png" in texto and "Error 0x800CCC0E" in texto

    actual = client.get("/minutito/conversaciones/actual", headers=h).json()
    assert actual["mensajes"][0]["imagenes"] == ["error.png"] and actual["mensajes"][0]["texto"] == ""
    # ya enviada, no se puede quitar
    assert client.delete(f"/minutito/conversaciones/{conv['id']}/imagenes/1", headers=h).status_code == 404

    assert subir("dos.png").status_code == 200
    assert subir("tres.png").status_code == 200
    assert subir("cuatro.png").status_code == 409  # mismo límite que los adjuntos de un ticket

    r = client.post("/tickets", json={"texto": "El sistema muestra un error al abrir", "conversacion_id": conv["id"]}, headers=h)
    assert r.status_code == 200, r.text
    archivos = client.get(f"/tickets/{r.json()['id']}/adjuntos", headers=h_tec).json()
    assert [a["nombre_original"] for a in archivos] == ["error.png"]  # solo las que se enviaron
    descarga = client.get(f"/adjuntos/{archivos[0]['id']}", headers=h_tec)
    assert descarga.status_code == 200 and descarga.content == b"png"


def test_ocr_lee_el_texto_de_una_captura(tmp_path):
    import os

    import pytest

    from app.services import ocr

    if os.name != "nt":
        pytest.skip("el OCR usa el de Windows")
    imagen = tmp_path / "vacia.png"
    imagen.write_bytes(b"no es una imagen")
    assert ocr.leer_texto(imagen) == ""  # un archivo que no se puede leer no rompe nada

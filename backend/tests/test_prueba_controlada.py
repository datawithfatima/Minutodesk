"""Prueba controlada: un colaborador simulado conversa con Minutito y el equipo califica."""
from types import SimpleNamespace

from app.services import minutito_chat, prueba_controlada
from app.services.escenarios_prueba import ESCENARIOS


def _modelo(monkeypatch, colaborador, minutito):
    """Simula Ollama: `colaborador` y `minutito` son listas de respuestas en orden."""
    colaborador, minutito = list(colaborador), list(minutito)

    def llamar(mensajes, stream):
        return SimpleNamespace(message=SimpleNamespace(content=colaborador.pop(0)))

    monkeypatch.setattr(minutito_chat, "_llamar", llamar)
    monkeypatch.setattr(minutito_chat, "responder", lambda historial, casos=None: minutito.pop(0))


def test_conversacion_termina_cuando_el_colaborador_dice_que_funciono(session, monkeypatch):
    _modelo(
        monkeypatch,
        ["no me sale ninguna red wifi", "ya lo desactivé y funcionó, gracias [RESUELTO]"],
        [("Revisa si tienes el modo avión activado.", False)],
    )
    historial, termino = prueba_controlada.simular(session, ESCENARIOS[1])
    assert termino == "resuelto"
    assert historial == [
        ("usuario", "no me sale ninguna red wifi"),
        ("minutito", "Revisa si tienes el modo avión activado."),
        ("usuario", "ya lo desactivé y funcionó, gracias"),
    ]


def test_conversacion_con_ticket_o_sin_cierre(session, monkeypatch):
    _modelo(monkeypatch, ["no imprime", "dale, créalo [TICKET]"], [("Eso lo revisa el equipo, ¿creo el ticket?", True)])
    historial, termino = prueba_controlada.simular(session, ESCENARIOS[4])
    assert termino == "ticket" and historial[-1] == ("usuario", "dale, créalo")

    # ofrece el ticket pero junto con el paso correcto: el colaborador lo prueba
    _modelo(monkeypatch, ["no imprime", "cancelé la cola y salió [RESUELTO]"], [("Cancela la cola de impresión. Si no, creo el ticket.", True)])
    assert prueba_controlada.simular(session, ESCENARIOS[4])[1] == "resuelto"

    _modelo(monkeypatch, ["no imprime", "sigue igual", "nada, sigue igual"], [("Paso 1", False), ("Paso 2", False), ("Paso 3", False)])
    historial, termino = prueba_controlada.simular(session, ESCENARIOS[4])
    assert termino == "sin_cierre" and [r for r, _ in historial].count("minutito") == 3


def test_generar_evaluar_y_porcentaje(session, client, crear_cuenta, entrar, monkeypatch):
    monkeypatch.setattr(prueba_controlada, "ESCENARIOS", ESCENARIOS[:3])
    monkeypatch.setattr(prueba_controlada, "_por_clave", lambda: {e.clave: e for e in ESCENARIOS[:3]})
    monkeypatch.setattr(prueba_controlada, "simular", lambda session, e: ([("usuario", e.situacion), ("minutito", "ok")], "resuelto"))
    assert prueba_controlada.generar_pendientes(session) == {"generadas": 3, "pendientes": 0, "error": None}
    assert prueba_controlada.generar_pendientes(session)["generadas"] == 0  # no repite

    crear_cuenta("adm@ejemplo.com", "administrador")
    h = entrar("adm@ejemplo.com")
    datos = client.get("/reportes/prueba-controlada", headers=h).json()
    assert datos["generadas"] == 3 and datos["sin_evaluar"] == 3
    ids = [i["id"] for i in datos["items"]]
    for pid, veredicto in zip(ids, ["resuelve", "resuelve", "no_resuelve"]):
        assert client.post(f"/admin/prueba-controlada/{pid}", json={"veredicto": veredicto}, headers=h).status_code == 200
    assert client.get("/reportes/prueba-controlada", headers=h).json()["pct_resolveria"] == 0.6667

    prueba_controlada.generar_pendientes(session, todas=True)  # vuelve a correr y borra las marcas
    assert client.get("/reportes/prueba-controlada", headers=h).json()["sin_evaluar"] == 3


def test_prueba_controlada_solo_para_el_administrador(client, crear_cuenta, entrar):
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h = entrar("tec@ejemplo.com")
    assert client.get("/reportes/prueba-controlada", headers=h).status_code == 403
    assert client.post("/admin/prueba-controlada/generar", headers=h).status_code == 403

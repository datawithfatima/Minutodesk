"""La voz de Minutito: limpieza de respuestas, respuestas directas, fichas de pasos y el
orden en que se decide cómo contestar."""
import random

import pytest

from app.models import InteraccionMinutito
from app.services import assistant
from app.services.conocimiento import (
    FICHAS,
    buscar_ficha,
    ficha_ya_dada,
    respuesta_con_ficha,
    respuesta_directa,
)


# ---------- limpiar_respuesta ----------

def test_quita_el_markdown_que_en_el_chat_se_veria_literal():
    t = "**Verifica** tu conexión.\n## Pasos\n* Reinicia\n- Prueba `ipconfig`"
    r = assistant.limpiar_respuesta(t)
    assert "*" not in r and "#" not in r and "`" not in r
    assert "Verifica tu conexión." in r and "• Reinicia" in r and "• Prueba ipconfig" in r


def test_quita_muletillas_de_manual():
    t = (
        "Entendido. Para tratar este problema, te propongo lo siguiente:\n"
        "1. Reinicia el equipo.\n"
        "Si tienes alguna otra duda, no dudes en escribirme. Estaré encantado de ayudarte."
    )
    r = assistant.limpiar_respuesta(t)
    for frase in ("Entendido", "Para tratar este problema", "no dudes", "encantado", "otra duda"):
        assert frase.lower() not in r.lower(), frase
    assert "1. Reinicia el equipo." in r


def test_corrige_errores_tipicos_del_modelo():
    assert "escalar el caso" in assistant.limpiar_respuesta("Puedo escalera el caso a un técnico")
    assert "escalar tu caso" in assistant.limpiar_respuesta("Voy a escalare tu caso")
    assert assistant.limpiar_respuesta("hola! ¿en qué te ayudo?").startswith("¡Hola!")


def test_una_respuesta_cortada_a_media_frase_se_recorta_a_la_ultima_oracion():
    cortada = "Prueba reiniciar el equipo. Si no funciona, revisa la conexión a la red y luego intenta abri"
    assert assistant.limpiar_respuesta(cortada, cortada=True) == "Prueba reiniciar el equipo."
    assert assistant.limpiar_respuesta("Listo.", cortada=False) == "Listo."


def test_una_respuesta_demasiado_larga_se_recorta_por_lineas():
    larga = "\n".join(f"{i}. " + "palabra " * 20 for i in range(1, 10))
    r = assistant.limpiar_respuesta(larga)
    assert len(r.split()) <= assistant.MAX_PALABRAS
    assert r.rstrip().endswith("palabra") and r.count("\n") >= 1  # corta en líneas completas


def test_la_apertura_de_relleno_se_cambia_por_una_variada():
    t = "Parece que tienes un problema con la impresora.\n1. Reinicia.\n2. Revisa el papel."
    r = assistant._variar_apertura(t, azar=random.Random(1))
    assert not r.lower().startswith("parece que") and r.split("\n")[0] in assistant._APERTURAS
    assert "1. Reinicia." in r
    # una pregunta suelta antes de los pasos también se reemplaza
    q = "¿Qué documentos intentas imprimir?\n1. Reinicia."
    assert assistant._variar_apertura(q, azar=random.Random(1)).split("\n")[0] in assistant._APERTURAS
    # sin pasos debajo, la pregunta se queda: puede ser la respuesta
    assert assistant._variar_apertura("¿Qué mensaje sale?") == "¿Qué mensaje sale?"


def test_con_pasos_se_quita_el_voy_a_escalar_suelto_pero_no_si_no_hay_pasos():
    con_pasos = "1. Reinicia.\n2. Revisa.\nSi no funciona, voy a escalar tu caso a un técnico."
    assert "escalar" not in assistant._sin_escalamiento_prematuro(con_pasos)
    sin_pasos = "Eso lo ve el equipo: voy a escalar tu caso a un técnico."
    assert "voy a escalar" in assistant._sin_escalamiento_prematuro(sin_pasos)


def test_decir_un_tecnico_al_cerrar_no_cuenta_como_derivar_el_caso():
    assert not assistant._contiene_alguna("Si sigue igual, lo revisa un técnico.", assistant.FRASES_ESCALAMIENTO)
    assert assistant._contiene_alguna("Listo, voy a escalar tu caso.", assistant.FRASES_ESCALAMIENTO)


# ---------- respuestas directas ----------

@pytest.mark.parametrize(
    "mensaje, contiene",
    [
        ("hola", "¡"),
        ("Buenas tardes!", "¡"),
        ("gracias", "ayuda|aquí|Con gusto|nada|estamos"),
        ("¿Esto es un robot? con quien hablo", "asistente virtual"),
        ("eres una persona real?", "asistente virtual"),
        ("quiero hablar con una persona", "voy a escalar"),
        ("Necesito que me den acceso a Power BI", "voy a escalar"),
        ("necesito permisos para la carpeta de contabilidad", "voy a escalar"),
        ("necesito instalar Adobe", "voy a escalar"),
        ("hay que dar de alta un usuario nuevo", "Gestión de usuarios y accesos"),
    ],
)
def test_respuestas_directas_sin_pasar_por_el_modelo(mensaje, contiene):
    import re

    r = respuesta_directa(mensaje, azar=random.Random(0))
    assert r is not None, mensaje
    assert re.search(contiene, r, re.IGNORECASE), (mensaje, r)


@pytest.mark.parametrize(
    "mensaje",
    [
        "no puedo acceder al sistema de facturación",  # es un problema, no un pedido de acceso
        "me aparece acceso denegado en la carpeta",
        "la impresora no imprime",
        "hola, no me funciona el correo",  # saluda pero trae el problema: va con la ficha
        "",
    ],
)
def test_lo_que_trae_un_problema_no_se_responde_con_una_frase_fija(mensaje):
    assert respuesta_directa(mensaje) is None


def test_las_respuestas_directas_varian_y_nunca_afirman_ser_humano():
    saludos = {respuesta_directa("hola", azar=random.Random(n)) for n in range(30)}
    assert len(saludos) >= 3  # no suena siempre igual
    identidad = {respuesta_directa("eres un robot?", azar=random.Random(n)) for n in range(10)}
    assert all("asistente virtual" in r.lower() for r in identidad)


# ---------- fichas ----------

@pytest.mark.parametrize(
    "mensaje, tema",
    [
        ("No puedo abrir OneDrive, me pide iniciar sesion", "OneDrive"),
        ("Olvidé mi contraseña del correo", "contraseña olvidada"),
        ("la contraseña no me funciona, dice incorrecta", "contraseña o acceso a una cuenta"),
        ("La impresora del piso 2 no imprime", "impresora"),
        ("no me funciona el micrófono en Teams", "videollamadas (Teams, Zoom)"),
        ("mi laptop va muy lenta", "equipo lento"),
        ("no tengo internet", "internet o Wi-Fi"),
        ("no me conecta la VPN desde casa", "VPN"),
        ("Excel se cierra solo", "Office (Excel, Word, PowerPoint)"),
    ],
)
def test_cada_problema_comun_encuentra_su_ficha(mensaje, tema):
    ficha = buscar_ficha(mensaje)
    assert ficha is not None and ficha.tema == tema, (mensaje, ficha and ficha.tema)


def test_un_problema_desconocido_no_tiene_ficha():
    assert buscar_ficha("no me carga el sistema de facturación") is None


def test_la_respuesta_de_una_ficha_trae_pasos_verificados_numerados_y_variados():
    ficha = buscar_ficha("la impresora no imprime")
    respuestas = {respuesta_con_ficha(ficha, azar=random.Random(n)) for n in range(40)}
    assert len(respuestas) >= 4  # aperturas y cierres distintos
    for r in respuestas:
        assert all(f"{i}. " in r for i in (1, 2, 3)) and "4. " not in r
        assert ficha.pasos[0] in r and "*" not in r


def test_los_pasos_de_una_ficha_no_se_repiten_en_la_misma_conversacion():
    ficha = buscar_ficha("la impresora no imprime")
    primera = respuesta_con_ficha(ficha)
    assert ficha_ya_dada(ficha, [primera]) and not ficha_ya_dada(ficha, ["otra cosa"])


def test_ninguna_ficha_pide_datos_sensibles_ni_tiene_formato():
    for f in FICHAS:
        for paso in f.pasos:
            assert "*" not in paso and len(paso.split()) <= 40, paso
            assert "pídele tu contraseña" not in paso.lower()


# ---------- cómo decide qué contestar ----------

def _modelo_falso(monkeypatch, texto="Prueba reiniciar el sistema."):
    llamadas = []

    def falso(*args, **kwargs):
        llamadas.append(kwargs.get("options"))
        return type("R", (), {"message": type("M", (), {"content": texto})(), "done_reason": "stop"})()

    monkeypatch.setattr(assistant._cliente, "chat", falso)
    return llamadas


def test_saludos_y_fichas_no_llaman_al_modelo(monkeypatch):
    llamadas = _modelo_falso(monkeypatch)
    assert assistant.generar_respuesta([], "hola", "hola")
    assert "1. " in assistant.generar_respuesta([], "la impresora no imprime", "la impresora no imprime")
    assert llamadas == []  # respuesta instantánea, y sirve aunque Ollama esté apagado


def test_si_los_pasos_ya_se_dieron_la_conversacion_sigue_con_el_modelo(monkeypatch):
    llamadas = _modelo_falso(monkeypatch, "¿Qué mensaje sale exactamente?")
    primera = assistant.generar_respuesta([], "la impresora no imprime", "la impresora no imprime")
    historial = [InteraccionMinutito(ticket_id=1, mensaje_cliente="la impresora no imprime", respuesta_minutito=primera)]
    r = assistant.generar_respuesta(historial, "sigue igual, la impresora no imprime", "la impresora no imprime")
    assert r == "¿Qué mensaje sale exactamente?" and len(llamadas) == 1


def test_lo_desconocido_va_al_modelo_con_opciones_y_sin_ejemplos_que_copiar(monkeypatch):
    llamadas = _modelo_falso(monkeypatch, "**Revisa** el módulo.")
    r = assistant.generar_respuesta([], "no me carga el sistema de facturación", "no me carga el sistema de facturación")
    assert r == "Revisa el módulo."  # limpia el markdown
    assert llamadas[0]["num_predict"] == assistant.OPCIONES_OLLAMA["num_predict"]
    mensajes = assistant._armar_mensajes([], "hola", "hola")
    assert [m["role"] for m in mensajes] == ["system", "system", "user"]  # sin turnos de ejemplo
    assert "No inventes" in mensajes[1]["content"]


def test_el_prompt_prohibe_pedir_contrasenas_y_negar_ser_un_asistente_virtual():
    p = assistant.PROMPT_SISTEMA
    assert "Nunca pidas contraseñas" in p and "asistente virtual" in p
    assert "Nunca digas que eres humano" in p

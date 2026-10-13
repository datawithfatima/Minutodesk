"""Asistente conversacional "Minutito": no se entrena, se configura por
prompt sobre un modelo local servido por Ollama.

La voz de Minutito se logra con dos piezas: el prompt (cómo habla y qué hace) y un
limpiador de la respuesta (`limpiar_respuesta`) que quita lo que delata a una IA
genérica: formato markdown, muletillas de manual y errores típicos del modelo.
No se usan ejemplos de conversación en el prompt: con un modelo de 3B parámetros
los copia al pie de la letra (frases, nombres inventados).
"""
import html
import random
import re

import httpx
import ollama
from sqlmodel import Session, select

from app.models import InteraccionMinutito, Ticket
from app.services.conocimiento import (
    buscar_ficha,
    ficha_ya_dada,
    respuesta_con_ficha,
    respuesta_directa,
)

MODELO_OLLAMA = "llama3.2:3b"
TIMEOUT_SEGUNDOS = 90  # sin tope, un Ollama colgado deja la petición esperando para siempre

# Respuestas cortas y estables: menos texto también es menos espera en un equipo sin GPU.
OPCIONES_OLLAMA = {
    "temperature": 0.5,
    "top_p": 0.9,
    "repeat_penalty": 1.1,
    "num_predict": 240,
}
MAX_PALABRAS = 150

_cliente = ollama.Client(timeout=TIMEOUT_SEGUNDOS)


class AsistenteNoDisponible(Exception):
    """Ollama apagado, sin el modelo instalado, o sin responder a tiempo."""


PROMPT_SISTEMA = """Eres Minutito, el asistente virtual de soporte de sistemas de MinutoDesk. Chateas con compañeros que tienen un problema con su computador, sus programas o sus accesos.

Cómo respondes:
1. Una frase corta y natural para empezar. Nunca empieces con "Parece que", "Entiendo que" ni "Veo que", ni repitas lo que dijo la persona; sin "Entendido", "Claro que sí" ni "Para tratar este problema".
2. Luego 2 o 3 pasos numerados, concretos para ESE problema, cada uno en una línea corta ("1. ...").
3. Si hace falta, cierra con una frase breve. No preguntes si se resolvió: la pantalla ya lo pregunta.

Reglas:
- Español cercano, de tú, sin sonar a manual. Máximo 70 palabras.
- Sin formato: nada de asteriscos, negritas, títulos ni viñetas.
- Ortografía correcta (ñ y tildes) aunque la persona escriba sin ellas.
- Si solo saludan, saluda en una frase y pregunta en qué los ayudas. No repitas el saludo si la conversación ya empezó.
- Si piden algo que solo puede hacer el equipo (accesos, permisos, licencias, altas, instalar programas), no inventes pasos: di que se lo dejas al equipo de sistemas.
- Si no entiendes el problema, haz una sola pregunta corta.
- Nunca pidas contraseñas, códigos ni datos personales. No inventes nombres de personas, plazos ni políticas.
- Si preguntan quién eres: eres Minutito, el asistente virtual de soporte, y si prefieren hablar con una persona ofreces pasar el caso al equipo. Nunca digas que eres humano ni "como asistente de IA"."""

# Solo esta frase cuenta como derivar el caso. Decir «un técnico lo revisará» al cerrar una
# respuesta no es derivar: la persona todavía debe poder confirmar si le sirvió.
FRASES_ESCALAMIENTO = ["voy a escalar", "no puedo resolver esto"]
FRASES_PIDE_HUMANO = [
    "hablar con una persona",
    "hablar con un humano",
    "quiero un técnico",
    "quiero hablar con alguien",
]

HISTORIAL_MAXIMO = 5


def _contiene_alguna(texto: str, frases: list[str]) -> bool:
    texto = texto.lower()
    return any(frase in texto for frase in frases)


# ---------- limpieza de la respuesta ----------

_RELLENO = [
    r"est(?:a|á)r(?:e|é) encantad[oa] de ayudarte[^.!?\n]*[.!?]?",
    r"espero que (?:esto|esta información|estos pasos|esta respuesta) te (?:sea[n]? de ayuda|ayude[n]?|sirva[n]?)[^.!?\n]*[.!?]?",
    r"no dudes en (?:escribirme|contactarme|preguntar|consultarme)[^.!?\n]*[.!?]?",
    r"si tienes (?:alguna|más) (?:otra )?(?:pregunta|duda|consulta)[^.!?\n]*[.!?]?",
    r"cualquier (?:otra )?(?:duda|consulta)[^.!?\n]*[.!?]?",
    r"disculpa(?:s)? por (?:la|las) (?:incomodidad|molestias?)[^.!?\n]*[.!?]?",
    r"como asistente (?:virtual |de ia |de inteligencia artificial )?[^,.\n]{0,40},\s*",
    r"(?:aqu[ií] te dejo|te dejo|te propongo|a continuaci[oó]n te|te recomiendo)[^.:\n]{0,50}(?:pasos|siguiente|opciones)[^.:\n]{0,25}:\s*",
]
_INICIO_DE_MANUAL = re.compile(
    r"^\s*(?:entendido|claro que s[ií]|por supuesto|con gusto|perfecto|de acuerdo)[.,!:]\s*"
    r"|^\s*para (?:tratar|resolver|solucionar|abordar) (?:este|ese|tu) (?:problema|caso|inconveniente)[^.:\n]*[.:]\s*",
    re.IGNORECASE,
)
_ESCALAR_MAL = re.compile(r"\bescal(?:era|are|aré|ara)\s+(?=(?:el|tu)\s+caso)", re.IGNORECASE)


def _recortar(texto: str, max_palabras: int = MAX_PALABRAS) -> str:
    """Corta por líneas completas (o por oración) si la respuesta se pasa de larga."""
    if len(texto.split()) <= max_palabras:
        return texto
    salida, total = [], 0
    for linea in texto.split("\n"):
        palabras = len(linea.split())
        if total + palabras > max_palabras and salida:
            break
        salida.append(linea)
        total += palabras
    return "\n".join(salida).strip()


def _cortar_en_ultima_oracion(texto: str) -> str:
    """Si el modelo se quedó sin espacio a media frase, quita la frase incompleta."""
    fin = max(texto.rfind("."), texto.rfind("!"), texto.rfind("?"), texto.rfind("\n"))
    if fin >= 15:  # hay al menos una frase completa: se queda hasta ahí
        return texto[: fin + 1].rstrip()
    return texto.rstrip(" ,;:") + "…"


def limpiar_respuesta(texto: str, cortada: bool = False) -> str:
    """Quita el markdown, las muletillas de manual y los errores típicos del modelo.

    `cortada` indica que el modelo se detuvo por el límite de longitud (no por haber terminado)."""
    t = html.unescape(texto or "").replace("\r\n", "\n")

    # Formato que en el chat se vería literal: **negrita**, _cursiva_, # títulos, `código`.
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t, flags=re.DOTALL)
    t = re.sub(r"__(.+?)__", r"\1", t, flags=re.DOTALL)
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", t)
    t = t.replace("`", "")
    t = re.sub(r"(?m)^\s*[*•]\s+", "- ", t)
    t = re.sub(r"(?m)^\s*-\s+", "• ", t)
    t = t.replace("*", "")

    # Muletillas (las del inicio pueden venir encadenadas: «Entendido. Para tratar este problema...»).
    anterior = None
    while anterior != t:
        anterior = t
        t = _INICIO_DE_MANUAL.sub("", t)
    for patron in _RELLENO:
        t = re.sub(patron, "", t, flags=re.IGNORECASE)
    t = _ESCALAR_MAL.sub("escalar ", t)
    t = re.sub(r"(?i)^\s*hola!", "¡Hola!", t)

    # Espacios y líneas.
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" +([,.;:!?])", r"\1", t)
    t = re.sub(r"\n[ \t]+", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()

    if cortada:
        t = _cortar_en_ultima_oracion(t)
    t = _recortar(t)
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    return t


# ---------- conversación ----------

def _contexto_de_tema(*textos: str) -> str:
    """Pasos verificados del tema si lo conocemos; si no, cómo comportarse sin ellos."""
    ficha = buscar_ficha(*textos)
    if ficha is None:
        return (
            "Para este caso no tienes pasos de referencia. Si el problema es claro, da como máximo "
            "2 pasos muy básicos (reiniciar, revisar la conexión); si no, haz una sola pregunta corta "
            "para entenderlo mejor. No inventes pasos."
        )
    pasos = "\n".join(f"{i}. {p}" for i, p in enumerate(ficha.pasos, 1))
    return (
        f"Tema de la conversación: {ficha.tema}. Pasos de referencia (correctos, en orden):\n{pasos}\n"
        "Si ya diste estos pasos antes en la conversación, no los repitas: pregunta qué mensaje "
        "exacto sale o qué pasa justo al intentarlo, y dile que si no se arregla lo revisa el equipo. "
        "Si es otra cosa, usa solo los pasos que apliquen. No agregues pasos que no estén aquí."
    )


_APERTURAS = [
    "Vamos a revisarlo.",
    "Probemos esto.",
    "Veamos qué pasa.",
    "Revisemos lo básico.",
    "Dale una mirada a esto.",
]
_APERTURA_GENERICA = re.compile(
    r"^\s*(?:(?:parece que|entiendo que|veo que|al parecer|comprendo que)[^\n]*|¿[^\n]*\?)\n+(?=\s*1[.)])",
    re.IGNORECASE,
)


def _variar_apertura(texto: str, azar: random.Random = random) -> str:
    """Cuando antes de los pasos hay una frase de relleno («Parece que tienes un problema con...»)
    o una pregunta suelta, la cambia por una apertura corta y distinta cada vez."""
    return _APERTURA_GENERICA.sub(azar.choice(_APERTURAS) + "\n", texto, count=1)


_ESCALAR_EN_UNA_ORACION = re.compile(r"[^.!?\n]*\bvoy a escalar\b[^.!?\n]*[.!?]?\s*", re.IGNORECASE)


def _sin_escalamiento_prematuro(texto: str) -> str:
    """Si el modelo dio pasos y además dijo «voy a escalar...», se quita esa frase: derivar el
    caso lo deciden los accesos/instalaciones (respuestas directas) o la persona al confirmar,
    no una frase suelta del modelo."""
    if re.search(r"(?m)^\s*1[.)]\s", texto):
        texto = _ESCALAR_EN_UNA_ORACION.sub("", texto).rstrip()
    return texto


def _armar_mensajes(
    historial: list[InteraccionMinutito], mensaje_cliente: str, texto_del_ticket: str = ""
) -> list[dict]:
    mensajes = [
        {"role": "system", "content": PROMPT_SISTEMA},
        {"role": "system", "content": _contexto_de_tema(mensaje_cliente, texto_del_ticket)},
    ]
    for interaccion in historial:
        mensajes.append({"role": "user", "content": interaccion.mensaje_cliente})
        mensajes.append({"role": "assistant", "content": interaccion.respuesta_minutito})
    mensajes.append({"role": "user", "content": mensaje_cliente})
    return mensajes


def generar_respuesta(
    historial: list[InteraccionMinutito], mensaje_cliente: str, texto_del_ticket: str = ""
) -> str:
    """Qué le responde Minutito a este mensaje, en orden de preferencia:

    1) Saludos, «¿eres un robot?», agradecimientos, pedir una persona y solicitudes de accesos o
       instalaciones no necesitan al modelo: se responden al instante y sin inventar nada.
    2) Si el mensaje trata un problema conocido, se responde con los pasos verificados de su
       ficha (el modelo no improvisa). Si esos pasos ya se dieron, sigue el modelo.
    3) Todo lo demás: el modelo, con el tema como pista y las reglas de voz del prompt.
    """
    directa = respuesta_directa(mensaje_cliente)
    if directa is not None:
        return directa

    ficha = buscar_ficha(mensaje_cliente)
    if ficha is not None and not ficha_ya_dada(ficha, [i.respuesta_minutito for i in historial]):
        return respuesta_con_ficha(ficha)

    mensajes = _armar_mensajes(historial, mensaje_cliente, texto_del_ticket)
    try:
        respuesta_ollama = _cliente.chat(model=MODELO_OLLAMA, messages=mensajes, options=OPCIONES_OLLAMA)
    except ollama.ResponseError as e:
        raise AsistenteNoDisponible(
            f"Ollama respondió con error (¿está instalado el modelo '{MODELO_OLLAMA}'?): {e}"
        ) from e
    except (ollama.RequestError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
        raise AsistenteNoDisponible(f"No se pudo hablar con Ollama: {e}") from e

    bruto = (respuesta_ollama.message.content or "").strip()
    cortada = getattr(respuesta_ollama, "done_reason", None) == "length"
    texto = _sin_escalamiento_prematuro(_variar_apertura(limpiar_respuesta(bruto, cortada=cortada)))
    if not texto:
        raise AsistenteNoDisponible("Ollama devolvió una respuesta vacía")
    return texto


def responder(ticket: Ticket, mensaje_cliente: str, session: Session) -> dict:
    historial = session.exec(
        select(InteraccionMinutito)
        .where(InteraccionMinutito.ticket_id == ticket.id)
        .order_by(InteraccionMinutito.creado_en.desc())
        .limit(HISTORIAL_MAXIMO)
    ).all()
    historial = list(reversed(historial))

    texto_respuesta = generar_respuesta(historial, mensaje_cliente, ticket.texto)

    # Minutito no decide si resolvió: solo avisa si derivó el caso a una persona. Que el
    # problema quedó resuelto lo confirma el usuario (marco_resuelto se pone al confirmar).
    escalado = _contiene_alguna(texto_respuesta, FRASES_ESCALAMIENTO) or _contiene_alguna(
        mensaje_cliente, FRASES_PIDE_HUMANO
    )

    interaccion = InteraccionMinutito(
        ticket_id=ticket.id,
        mensaje_cliente=mensaje_cliente,
        respuesta_minutito=texto_respuesta,
        marco_resuelto=False,
    )
    session.add(interaccion)
    session.commit()

    return {"respuesta": texto_respuesta, "escalado": escalado}

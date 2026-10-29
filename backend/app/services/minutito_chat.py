"""Minutito como asistente conversacional de soporte N1, al estilo de ChatGPT o Claude.

Conversa libremente sobre problemas de primer nivel, recuerda lo que ya se habló y da
pasos claros. Las fichas de conocimiento (conocimiento.py) ya no se devuelven tal cual:
se le pasan al modelo como pasos verificados de referencia para el tema.

Cuando el caso no es de primer nivel o ya no quedan opciones, el modelo termina su
respuesta con la marca MARCA_TICKET; el servidor la quita y avisa a la pantalla para que
ofrezca crear el ticket con la conversación. Corre en local con Ollama: nada sale del equipo.
"""
from typing import Iterable, Iterator

import httpx
import ollama

from app.services.conocimiento import buscar_ficha

MODELO_CHAT = "qwen2.5:7b"
TIMEOUT_SEGUNDOS = 240  # en un equipo sin GPU una respuesta larga puede tardar
OPCIONES = {"temperature": 0.4, "top_p": 0.9, "repeat_penalty": 1.05, "num_predict": 450}
HISTORIAL_MAXIMO = 20  # mensajes previos que se le pasan al modelo
MARCA_TICKET = "[OFRECER_TICKET]"

_cliente = ollama.Client(timeout=TIMEOUT_SEGUNDOS)


class MinutitoNoDisponible(Exception):
    """Ollama apagado, sin el modelo instalado o sin responder a tiempo."""


PROMPT = f"""Eres Minutito, el asistente virtual de soporte de primer nivel (N1) del área de sistemas de una constructora y promotora inmobiliaria. Conversas con colaboradores de la empresa, como lo haría un asistente tipo ChatGPT o Claude.

Cómo ayudas:
- Entiende bien el problema antes de dar pasos. Si falta información importante (qué mensaje sale, en qué equipo o programa, desde cuándo), haz una o dos preguntas concretas.
- Da pasos claros y en orden, explicando brevemente qué hace cada uno. Usa Markdown cuando ayude: listas numeradas y **negritas** para botones, menús u opciones.
- Recuerda lo que la persona ya probó y no repitas pasos que ya dio; propone el siguiente paso lógico.
- Sé conciso: máximo 120 palabras y como mucho 4 pasos. Tono cercano y profesional, de tú.
- Responde siempre en español, con buena ortografía, aunque la persona escriba sin tildes.

Tu alcance es el soporte de primer nivel: contraseñas y bloqueo de cuenta (guiando a la persona, nunca pidiéndole la contraseña), Wi-Fi e internet, VPN, impresoras, Office y correo, Teams y videollamadas, OneDrive y carpetas compartidas, navegador, lentitud del equipo, periféricos, y dudas de uso de programas.

Cuándo ofrecer un ticket:
- Si es una solicitud que solo puede atender el equipo de sistemas (equipos nuevos o reemplazos, monitores, licencias, accesos o permisos, crear o dar de baja usuarios, instalar programas, compras, daños físicos): NO des pasos ni le pidas a la persona revisar inventario o gestionar nada. Responde en 1 o 2 frases que eso lo gestiona el equipo de sistemas, pide solo los datos que falten para el ticket (para quién, para cuándo, qué necesita exactamente) y ofrece crearlo.
- Si ya probaron los pasos razonables y el problema sigue, ofrece crear el ticket.
- Cuando ofrezcas el ticket, termina tu respuesta con esta marca exacta en una línea aparte: {MARCA_TICKET}

Límites:
- Nunca pidas ni aceptes contraseñas, códigos de verificación ni datos personales.
- No inventes políticas, nombres de personas, plazos, teléfonos ni enlaces.
- Si preguntan algo que no es de soporte de sistemas, responde en una frase y recuerda que tu función es ayudar con soporte.
- Eres un asistente virtual, no una persona; si quieren hablar con alguien del equipo, ofrece crear el ticket."""

PROMPT_RESUMEN = """Con la conversación siguiente entre un colaborador y el asistente de soporte, redacta la descripción de un ticket para el equipo de sistemas.
- Escribe en primera persona, como si la escribiera el colaborador.
- Entre 2 y 4 oraciones: qué problema o solicitud tiene, en qué equipo o programa, y qué ya intentó.
- Solo el texto de la descripción, sin títulos, saludos ni formato."""


def _contexto(textos_usuario: list[str]) -> str | None:
    ficha = buscar_ficha(*textos_usuario[-3:])
    if ficha is None:
        return None
    pasos = "\n".join(f"{i}. {p}" for i, p in enumerate(ficha.pasos, 1))
    return (
        f"Pasos verificados por el equipo para el tema «{ficha.tema}». Úsalos como base si aplican "
        f"al caso, adaptándolos a la conversación:\n{pasos}"
    )


def armar_mensajes(historial: Iterable[tuple[str, str]]) -> list[dict]:
    """`historial`: pares (rol, texto) con rol «usuario» o «minutito», el último es la pregunta."""
    historial = list(historial)[-HISTORIAL_MAXIMO:]
    mensajes = [{"role": "system", "content": PROMPT}]
    contexto = _contexto([t for r, t in historial if r == "usuario"])
    if contexto:
        mensajes.append({"role": "system", "content": contexto})
    mensajes += [
        {"role": "user" if rol == "usuario" else "assistant", "content": texto} for rol, texto in historial
    ]
    return mensajes


def separar_marca(texto: str) -> tuple[str, bool]:
    """Quita la marca de ticket del texto y dice si estaba."""
    return texto.replace(MARCA_TICKET, "").strip(), MARCA_TICKET in texto


def _llamar(mensajes: list[dict], stream: bool):
    try:
        return _cliente.chat(model=MODELO_CHAT, messages=mensajes, options=OPCIONES, stream=stream)
    except ollama.ResponseError as e:
        raise MinutitoNoDisponible(f"Ollama respondió con error (¿está instalado '{MODELO_CHAT}'?): {e}") from e
    except (ollama.RequestError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
        raise MinutitoNoDisponible(f"No se pudo hablar con Ollama: {e}") from e


def responder(historial: Iterable[tuple[str, str]]) -> tuple[str, bool]:
    """Respuesta completa (sin ir mostrándola): (texto, ofrece_ticket)."""
    respuesta = _llamar(armar_mensajes(historial), stream=False)
    texto, ofrece = separar_marca(respuesta.message.content or "")
    if not texto:
        raise MinutitoNoDisponible("Ollama devolvió una respuesta vacía")
    return texto, ofrece


def responder_en_vivo(historial: Iterable[tuple[str, str]]) -> Iterator[str]:
    """Va entregando el texto a medida que el modelo lo escribe. Retiene lo que podría ser
    el comienzo de la marca de ticket para que nunca llegue a la pantalla."""
    pendiente = ""
    try:
        for parte in _llamar(armar_mensajes(historial), stream=True):
            pendiente += parte.message.content or ""
            pendiente = pendiente.replace(MARCA_TICKET, "")
            corte = pendiente.rfind("[")
            if corte != -1 and MARCA_TICKET.startswith(pendiente[corte:]):
                listo, pendiente = pendiente[:corte], pendiente[corte:]
            else:
                listo, pendiente = pendiente, ""
            if listo:
                yield listo
    except (ollama.ResponseError, ollama.RequestError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
        raise MinutitoNoDisponible(f"No se pudo hablar con Ollama: {e}") from e
    if pendiente and not MARCA_TICKET.startswith(pendiente):
        yield pendiente


def resumir_para_ticket(historial: Iterable[tuple[str, str]]) -> str:
    """Descripción del ticket redactada a partir de la conversación. Si Ollama no responde,
    se arma con lo que escribió la persona."""
    historial = list(historial)
    conversacion = "\n".join(
        f"{'Colaborador' if r == 'usuario' else 'Asistente'}: {t}" for r, t in historial
    )
    try:
        respuesta = _llamar(
            [{"role": "system", "content": PROMPT_RESUMEN}, {"role": "user", "content": conversacion}],
            stream=False,
        )
        texto = (respuesta.message.content or "").strip()
        if texto:
            return texto
    except MinutitoNoDisponible:
        pass
    return " ".join(t for r, t in historial if r == "usuario")

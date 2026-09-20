"""Asistente conversacional "Minutito": no se entrena, se configura por
prompt sobre un modelo local servido por Ollama.
"""
import ollama
from sqlmodel import Session, select

from app.models import InteraccionMinutito, Ticket

MODELO_OLLAMA = "llama3.2:3b"

PROMPT_SISTEMA = (
    "Eres Minutito, el asistente de soporte de sistemas de una empresa. "
    "Ayudas con consultas simples de primer nivel: restablecer contraseñas, dudas "
    "sobre uso de software estándar (correo, Office, VPN), y orientación básica de "
    "hardware. NO inventas políticas de la empresa ni prometes plazos. Si la consulta "
    "es compleja, poco clara, o el usuario pide explícitamente hablar con una persona, "
    "responde reconociendo que vas a escalar el caso a un técnico, sin intentar "
    "resolverlo tú. Sé breve y claro."
)

FRASES_ESCALAMIENTO = ["voy a escalar", "un técnico", "no puedo resolver esto"]
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


def _armar_mensajes(ticket: Ticket, historial: list[InteraccionMinutito], mensaje_cliente: str) -> list[dict]:
    contexto_ticket = (
        f"{PROMPT_SISTEMA}\n\nContexto del ticket: tipo predicho="
        f"{ticket.tipo_predicho or 'sin determinar'}, categoría predicha="
        f"{ticket.categoria_predicha or 'sin determinar'}."
    )
    mensajes = [{"role": "system", "content": contexto_ticket}]
    for interaccion in historial:
        mensajes.append({"role": "user", "content": interaccion.mensaje_cliente})
        mensajes.append({"role": "assistant", "content": interaccion.respuesta_minutito})
    mensajes.append({"role": "user", "content": mensaje_cliente})
    return mensajes


def responder(ticket: Ticket, mensaje_cliente: str, session: Session) -> dict:
    historial = session.exec(
        select(InteraccionMinutito)
        .where(InteraccionMinutito.ticket_id == ticket.id)
        .order_by(InteraccionMinutito.creado_en.desc())
        .limit(HISTORIAL_MAXIMO)
    ).all()
    historial = list(reversed(historial))

    mensajes = _armar_mensajes(ticket, historial, mensaje_cliente)
    respuesta_ollama = ollama.chat(model=MODELO_OLLAMA, messages=mensajes)
    texto_respuesta = respuesta_ollama.message.content

    marco_resuelto = not _contiene_alguna(
        texto_respuesta, FRASES_ESCALAMIENTO
    ) and not _contiene_alguna(mensaje_cliente, FRASES_PIDE_HUMANO)

    interaccion = InteraccionMinutito(
        ticket_id=ticket.id,
        mensaje_cliente=mensaje_cliente,
        respuesta_minutito=texto_respuesta,
        marco_resuelto=marco_resuelto,
    )
    session.add(interaccion)
    session.commit()

    return {"respuesta": texto_respuesta, "resuelto": marco_resuelto}

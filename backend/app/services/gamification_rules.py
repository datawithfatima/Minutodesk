"""Reglas de gamificación: otorga puntos cuando un ticket se resuelve,
según qué tanto usó la persona el autoservicio antes de escalar.
"""
from typing import Optional

from sqlmodel import Session, select

from app.models import Cliente, ConversacionMinutito, EventoGamificacion, InteraccionMinutito, Ticket

# Etapas de obra de «Mi obra» (ver services/obra.py).
NIVELES = [
    (0, 49, "Cimientos"),
    (50, 149, "Estructura"),
    (150, 299, "Acabados"),
    (300, None, "Entrega de llaves"),
]


def calcular_nivel(puntos: int) -> str:
    for minimo, maximo, nombre in NIVELES:
        if puntos >= minimo and (maximo is None or puntos <= maximo):
            return nombre
    return NIVELES[0][2]


def evaluar_evento(
    ticket: Ticket, cliente_id: int, session: Session
) -> Optional[EventoGamificacion]:
    # Un ticket da puntos una sola vez: si se reabre y se vuelve a resolver, no se premia de nuevo.
    ya_premiado = session.exec(
        select(EventoGamificacion.id).where(EventoGamificacion.ticket_id == ticket.id)
    ).first()
    if ya_premiado is not None:
        return None

    puntos = 0
    motivo = ""

    if ticket.resuelto_por == "minutito":
        puntos, motivo = 10, "Resuelto con autoservicio"
    elif ticket.resuelto_por == "tecnico":
        intento_autoservicio = session.exec(
            select(InteraccionMinutito).where(
                InteraccionMinutito.ticket_id == ticket.id
            )
        ).first() or session.exec(
            select(ConversacionMinutito).where(ConversacionMinutito.ticket_id == ticket.id)
        ).first()
        if intento_autoservicio is not None:
            puntos, motivo = 3, "Intentó autoservicio antes de escalar"

    if puntos == 0:
        return None

    evento = EventoGamificacion(
        cliente_id=cliente_id,
        ticket_id=ticket.id,
        puntos_otorgados=puntos,
        motivo=motivo,
    )
    session.add(evento)

    cliente = session.get(Cliente, cliente_id)
    if cliente is not None:
        cliente.puntos += puntos
        session.add(cliente)

    session.commit()
    session.refresh(evento)
    return evento

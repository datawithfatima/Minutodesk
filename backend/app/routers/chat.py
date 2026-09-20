from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from app.database import get_session
from app.models import InteraccionMinutito, Ticket
from app.schemas import ChatMensaje, ChatRespuesta
from app.services.assistant import responder

router = APIRouter()


@router.post("/{ticket_id}/chat", response_model=ChatRespuesta)
def chat_ticket(
    ticket_id: int, data: ChatMensaje, session: Session = Depends(get_session)
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    resultado = responder(ticket, data.mensaje, session)

    if resultado["resuelto"]:
        ticket.estado = "resuelto"
        ticket.resuelto_por = "minutito"
        ticket.cerrado_en = datetime.now()
    else:
        sin_resolver = session.exec(
            select(func.count())
            .select_from(InteraccionMinutito)
            .where(
                InteraccionMinutito.ticket_id == ticket_id,
                InteraccionMinutito.marco_resuelto == False,  # noqa: E712
            )
        ).one()
        if sin_resolver > 3:
            ticket.estado = "en_proceso"

    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    return ChatRespuesta(
        respuesta=resultado["respuesta"],
        resuelto=resultado["resuelto"],
        estado_ticket=ticket.estado,
    )

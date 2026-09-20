from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Ticket
from app.schemas import TicketCreate, TicketRead, TicketUpdate
from app.services.classifier import clasificar_ticket
from app.services.gamification_rules import evaluar_evento

router = APIRouter()


@router.post("", response_model=TicketRead)
def crear_ticket(data: TicketCreate, session: Session = Depends(get_session)):
    prediccion = clasificar_ticket(data.texto)

    ticket = Ticket(
        cliente_id=data.cliente_id,
        texto=data.texto,
        tipo_predicho=prediccion["tipo"],
        categoria_predicha=prediccion["categoria"],
        confianza_clasificacion=prediccion["confianza"],
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket


@router.get("", response_model=list[TicketRead])
def listar_tickets(
    estado: Optional[str] = None,
    categoria_predicha: Optional[str] = None,
    session: Session = Depends(get_session),
):
    query = select(Ticket)
    if estado is not None:
        query = query.where(Ticket.estado == estado)
    if categoria_predicha is not None:
        query = query.where(Ticket.categoria_predicha == categoria_predicha)
    return session.exec(query).all()


@router.get("/{ticket_id}", response_model=TicketRead)
def obtener_ticket(ticket_id: int, session: Session = Depends(get_session)):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketRead)
def actualizar_ticket(
    ticket_id: int, data: TicketUpdate, session: Session = Depends(get_session)
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    ya_estaba_resuelto = ticket.estado == "resuelto"

    if data.estado is not None:
        ticket.estado = data.estado
        if data.estado == "resuelto":
            ticket.cerrado_en = datetime.now()
    if data.resuelto_por is not None:
        ticket.resuelto_por = data.resuelto_por

    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    if not ya_estaba_resuelto and ticket.estado == "resuelto":
        evaluar_evento(ticket, ticket.cliente_id, session)

    return ticket

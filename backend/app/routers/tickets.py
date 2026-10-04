from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente, HistorialEstadoTicket, Ticket
from app.schemas import HistorialEstadoRead, TicketCreate, TicketRead, TicketUpdate
from app.services.auth import (
    es_personal,
    obtener_usuario_actual,
    requerir_personal,
)
from app.services.classifier import clasificar_ticket
from app.services.gamification_rules import evaluar_evento

router = APIRouter()

ESTADOS_VALIDOS = ("abierto", "en_proceso", "resuelto")
RESUELTO_POR_VALIDOS = ("minutito", "tecnico")


def registrar_estado(
    session: Session,
    ticket_id: int,
    anterior: Optional[str],
    nuevo: str,
    por_id: Optional[int],
) -> None:
    session.add(
        HistorialEstadoTicket(
            ticket_id=ticket_id,
            estado_anterior=anterior,
            estado_nuevo=nuevo,
            cambiado_por_id=por_id,
        )
    )


def _verificar_acceso(ticket: Ticket, usuario: Cliente) -> None:
    if not es_personal(usuario) and ticket.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este ticket")


@router.post("", response_model=TicketRead)
def crear_ticket(
    data: TicketCreate,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    prediccion = clasificar_ticket(data.texto)

    ticket = Ticket(
        cliente_id=usuario.id,
        texto=data.texto,
        tipo_predicho=prediccion["tipo"],
        categoria_predicha=prediccion["categoria"],
        confianza_clasificacion=prediccion["confianza"],
    )
    session.add(ticket)
    session.flush()
    registrar_estado(session, ticket.id, None, "abierto", usuario.id)
    session.commit()
    session.refresh(ticket)
    return ticket


@router.get("", response_model=list[TicketRead])
def listar_tickets(
    estado: Optional[str] = None,
    categoria_predicha: Optional[str] = None,
    cliente_id: Optional[int] = None,
    tecnico_id: Optional[int] = None,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    query = select(Ticket)
    if estado is not None:
        query = query.where(Ticket.estado == estado)
    if categoria_predicha is not None:
        query = query.where(Ticket.categoria_predicha == categoria_predicha)

    if es_personal(usuario):
        if cliente_id is not None:
            query = query.where(Ticket.cliente_id == cliente_id)
        if tecnico_id is not None:
            query = query.where(Ticket.tecnico_id == tecnico_id)
    else:
        # Un usuario final solo ve sus propios tickets, sin importar el filtro pedido.
        query = query.where(Ticket.cliente_id == usuario.id)

    return session.exec(query.order_by(Ticket.creado_en.desc())).all()


@router.get("/{ticket_id}", response_model=TicketRead)
def obtener_ticket(
    ticket_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    _verificar_acceso(ticket, usuario)
    return ticket


@router.get("/{ticket_id}/historial", response_model=list[HistorialEstadoRead])
def historial_del_ticket(
    ticket_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    _verificar_acceso(ticket, usuario)

    filas = session.exec(
        select(HistorialEstadoTicket)
        .where(HistorialEstadoTicket.ticket_id == ticket_id)
        .order_by(HistorialEstadoTicket.fecha, HistorialEstadoTicket.id)
    ).all()
    ids = {f.cambiado_por_id for f in filas if f.cambiado_por_id is not None}
    nombres = (
        {c.id: c.nombre for c in session.exec(select(Cliente).where(Cliente.id.in_(ids))).all()}
        if ids
        else {}
    )
    return [
        HistorialEstadoRead(
            id=f.id,
            estado_anterior=f.estado_anterior,
            estado_nuevo=f.estado_nuevo,
            cambiado_por_id=f.cambiado_por_id,
            cambiado_por=nombres.get(f.cambiado_por_id, "Minutito")
            if f.cambiado_por_id is not None
            else "Minutito",
            fecha=f.fecha,
        )
        for f in filas
    ]


@router.patch("/{ticket_id}", response_model=TicketRead)
def actualizar_ticket(
    ticket_id: int,
    data: TicketUpdate,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    if data.estado is not None and data.estado not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Estado no válido")
    if data.resuelto_por is not None and data.resuelto_por not in RESUELTO_POR_VALIDOS:
        raise HTTPException(status_code=400, detail="Valor de resuelto_por no válido")

    estado_anterior = ticket.estado
    ya_estaba_resuelto = estado_anterior == "resuelto"

    if data.estado is not None and data.estado != estado_anterior:
        ticket.estado = data.estado
        if data.estado == "resuelto":
            ticket.cerrado_en = datetime.now()
            ticket.resuelto_por = data.resuelto_por or "tecnico"
            if ticket.tecnico_id is None:
                ticket.tecnico_id = usuario.id
        else:
            ticket.cerrado_en = None
            ticket.resuelto_por = None
            if data.estado == "en_proceso":
                ticket.tecnico_id = usuario.id
        registrar_estado(session, ticket.id, estado_anterior, data.estado, usuario.id)
    elif data.resuelto_por is not None and ticket.estado == "resuelto":
        ticket.resuelto_por = data.resuelto_por

    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    if not ya_estaba_resuelto and ticket.estado == "resuelto":
        evaluar_evento(ticket, ticket.cliente_id, session)

    return ticket

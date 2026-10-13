import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente, InteraccionMinutito, Ticket
from app.routers.tickets import registrar_estado
from app.schemas import (
    ChatMensaje,
    ChatRespuesta,
    ConfirmacionRespuesta,
    ConfirmarResolucion,
    InteraccionRead,
)
from app.services.assistant import AsistenteNoDisponible, responder
from app.services.auth import es_personal, obtener_usuario_actual
from app.services.gamification_rules import evaluar_evento

logger = logging.getLogger(__name__)
router = APIRouter()

MENSAJE_NO_DISPONIBLE = (
    "Minutito no está disponible en este momento. Tu ticket quedó registrado "
    "y un técnico lo atenderá."
)
MENSAJE_RESUELTO = "¡Qué bueno que se resolvió! Cerramos tu ticket."
MENSAJE_PARA_TECNICO = "Entendido. Dejamos tu ticket abierto para que lo atienda un técnico."


def _verificar_acceso_ticket(ticket: Ticket, usuario: Cliente) -> None:
    if not es_personal(usuario) and ticket.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este ticket")


@router.get("/{ticket_id}/interacciones", response_model=list[InteraccionRead])
def listar_interacciones(
    ticket_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    _verificar_acceso_ticket(ticket, usuario)
    return session.exec(
        select(InteraccionMinutito)
        .where(InteraccionMinutito.ticket_id == ticket_id)
        .order_by(InteraccionMinutito.creado_en)
    ).all()


@router.post("/{ticket_id}/chat", response_model=ChatRespuesta)
def chat_ticket(
    ticket_id: int,
    data: ChatMensaje,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if ticket.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este ticket")

    if ticket.estado == "resuelto":
        raise HTTPException(status_code=409, detail="Este ticket ya está resuelto")
    if ticket.estado == "cancelado":
        raise HTTPException(status_code=409, detail="Este ticket fue cancelado por el equipo de soporte.")
    try:
        resultado = responder(ticket, data.mensaje, session)
    except AsistenteNoDisponible:
        # El ticket sigue abierto y sin cambios: lo atenderá una persona.
        logger.warning("Minutito no disponible para el ticket %s", ticket_id, exc_info=True)
        raise HTTPException(status_code=503, detail=MENSAJE_NO_DISPONIBLE)

    # El ticket no cambia de estado aquí: lo cierra el usuario al confirmar (o un técnico).
    return ChatRespuesta(
        respuesta=resultado["respuesta"],
        escalado=resultado["escalado"],
        requiere_confirmacion=not resultado["escalado"],
        estado_ticket=ticket.estado,
    )


@router.post("/{ticket_id}/confirmar-resolucion", response_model=ConfirmacionRespuesta)
def confirmar_resolucion(
    ticket_id: int,
    data: ConfirmarResolucion,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """El usuario dice si la ayuda de Minutito resolvió su problema.

    Solo así un ticket cuenta como «resuelto por Minutito»: la medición de resolución
    autónoma y los puntos de gamificación dependen de esta confirmación.
    """
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if ticket.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este ticket")

    if ticket.estado == "resuelto":
        if data.resuelto and ticket.resuelto_por == "minutito":  # repetir la confirmación no cambia nada
            return ConfirmacionRespuesta(estado_ticket="resuelto", mensaje=MENSAJE_RESUELTO)
        raise HTTPException(status_code=409, detail="Este ticket ya está resuelto")
    if ticket.estado != "abierto":
        raise HTTPException(status_code=409, detail="Un técnico ya está atendiendo este ticket")

    ultima = session.exec(
        select(InteraccionMinutito)
        .where(InteraccionMinutito.ticket_id == ticket_id)
        .order_by(InteraccionMinutito.creado_en.desc(), InteraccionMinutito.id.desc())
        .limit(1)
    ).first()
    if ultima is None:
        raise HTTPException(status_code=400, detail="Primero conversa con Minutito")

    if not data.resuelto:
        # Sigue abierto en la cola de los técnicos.
        return ConfirmacionRespuesta(estado_ticket=ticket.estado, mensaje=MENSAJE_PARA_TECNICO)

    estado_anterior = ticket.estado
    ticket.estado = "resuelto"
    ticket.resuelto_por = "minutito"
    ticket.cerrado_en = datetime.now()
    ultima.marco_resuelto = True
    registrar_estado(session, ticket.id, estado_anterior, ticket.estado, None)
    session.add_all([ticket, ultima])
    session.commit()
    session.refresh(ticket)

    evaluar_evento(ticket, ticket.cliente_id, session)
    return ConfirmacionRespuesta(estado_ticket=ticket.estado, mensaje=MENSAJE_RESUELTO)

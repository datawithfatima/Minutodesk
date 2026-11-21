"""«¿Quedó resuelto?»: ver y responder la confirmación de cierre de un ticket
(la lógica está en services/confirmacion.py)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, SQLModel

from app.database import get_session
from app.models import Cliente, ConfirmacionCierre, Ticket
from app.services import confirmacion
from app.services.auth import es_personal, obtener_usuario_actual

router = APIRouter()


class ConfirmacionRead(SQLModel):
    id: int
    respuesta: str
    resuelto_en: datetime
    vence_en: datetime
    comentario: Optional[str] = None
    respondido_en: Optional[datetime] = None
    puede_responder: bool = False


class ResponderConfirmacion(SQLModel):
    quedo_resuelto: bool
    comentario: Optional[str] = None


def _ticket(session: Session, ticket_id: int, usuario: Cliente) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if not es_personal(usuario) and ticket.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este ticket")
    return ticket


def _lectura(c: ConfirmacionCierre, ticket: Ticket, usuario: Cliente) -> ConfirmacionRead:
    return ConfirmacionRead(
        id=c.id,
        respuesta=c.respuesta,
        resuelto_en=c.resuelto_en,
        vence_en=c.vence_en,
        comentario=c.comentario,
        respondido_en=c.respondido_en,
        puede_responder=c.respuesta == "pendiente" and ticket.estado == "resuelto" and ticket.cliente_id == usuario.id,
    )


@router.get("/tickets/{ticket_id}/confirmacion-cierre", response_model=Optional[ConfirmacionRead])
def ver_confirmacion(
    ticket_id: int, usuario: Cliente = Depends(obtener_usuario_actual), session: Session = Depends(get_session)
):
    """La última confirmación del ticket (o nada si nunca la pidió)."""
    ticket = _ticket(session, ticket_id, usuario)
    c = confirmacion.ultima(session, ticket.id)
    return _lectura(c, ticket, usuario) if c else None


@router.post("/tickets/{ticket_id}/confirmacion-cierre", response_model=ConfirmacionRead)
def responder_confirmacion(
    ticket_id: int,
    data: ResponderConfirmacion,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    ticket = _ticket(session, ticket_id, usuario)
    c = confirmacion.responder(session, tareas, ticket, usuario, data.quedo_resuelto, data.comentario)
    return _lectura(c, ticket, usuario)

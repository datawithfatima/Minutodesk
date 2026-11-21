"""«¿Quedó resuelto?» (escenarios 3 y 5 de los plazos de seguimiento, 20/11/2026).

Cuando un técnico marca resuelto un ticket, a quien lo abrió le aparece «¿Quedó
resuelto?»:
- **Sí**: queda confirmado.
- **No** (con un comentario): el ticket vuelve a «En proceso» con el mismo técnico, en
  vez de tener que crear otro. El plazo sigue con el tiempo que le quedaba.
- **No contesta**: se confirma solo cuando pasa la ventana: la mitad de los días de SLA,
  con un mínimo de 2 y un tope de 5 (contados como el SLA, sin feriados).

El ticket sigue en estado «resuelto» mientras espera la respuesta, así que los reportes y
el plazo no cambian. Solo aplica a los tickets creados desde seguimiento.ACTIVO_DESDE y
que resolvió una persona del equipo (no Minutito).
"""
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, HTTPException
from sqlmodel import Session, select

from app.models import Cliente, ConfirmacionCierre, HistorialEstadoTicket, MensajeTicket, Ticket
from app.services import notificaciones, sla

VENTANA_MIN = 2 * sla.SEGUNDOS_DIA
VENTANA_TOPE = 5 * sla.SEGUNDOS_DIA
DIAS_SIN_SLA = 7
MIN_COMENTARIO = 5
MAX_COMENTARIO = 1000


def ventana(ticket: Ticket) -> float:
    dias = sla.dias_de_plazo(ticket) or DIAS_SIN_SLA
    return min(max(dias * sla.SEGUNDOS_DIA / 2, VENTANA_MIN), VENTANA_TOPE)


def aplica(ticket: Ticket) -> bool:
    from app.services.seguimiento import ACTIVO_DESDE  # aquí para evitar un import circular

    return ticket.creado_en >= ACTIVO_DESDE and not ticket.solicitante_externo


def ultima(session: Session, ticket_id: int) -> Optional[ConfirmacionCierre]:
    return session.exec(
        select(ConfirmacionCierre)
        .where(ConfirmacionCierre.ticket_id == ticket_id)
        .order_by(ConfirmacionCierre.resuelto_en.desc(), ConfirmacionCierre.id.desc())
    ).first()


def pendiente(session: Session, ticket_id: int) -> Optional[ConfirmacionCierre]:
    c = ultima(session, ticket_id)
    return c if c is not None and c.respuesta == "pendiente" else None


def al_cambiar_estado(session: Session, ticket: Ticket, anterior: str, ahora: Optional[datetime] = None) -> None:
    """Abre la espera de confirmación al resolver; la anula si el personal lo reabre. No hace commit."""
    ahora = ahora or datetime.now()
    abierta = pendiente(session, ticket.id)
    if abierta is not None and ticket.estado != "resuelto":
        abierta.respuesta = "anulado"
        abierta.respondido_en = ahora
        session.add(abierta)
    if ticket.estado == "resuelto" and anterior != "resuelto" and ticket.resuelto_por == "tecnico" and aplica(ticket):
        session.add(
            ConfirmacionCierre(
                ticket_id=ticket.id,
                tecnico_id=ticket.tecnico_id,
                resuelto_en=ahora,
                vence_en=sla.sumar_segundos_habiles(ahora, ventana(ticket)),
            )
        )


def responder(
    session: Session, tareas: BackgroundTasks, ticket: Ticket, usuario: Cliente, quedo_resuelto: bool,
    comentario: Optional[str],
) -> ConfirmacionCierre:
    if ticket.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="Solo quien abrió el ticket puede confirmarlo.")
    c = pendiente(session, ticket.id)
    if c is None or ticket.estado != "resuelto":
        raise HTTPException(status_code=409, detail="Este ticket no espera tu confirmación.")
    comentario = " ".join((comentario or "").split()) or None
    if comentario and len(comentario) > MAX_COMENTARIO:
        raise HTTPException(status_code=400, detail=f"El comentario es demasiado largo (máximo {MAX_COMENTARIO} caracteres).")
    ahora = datetime.now()
    c.respondido_en = ahora
    c.comentario = comentario
    if quedo_resuelto:
        c.respuesta = "confirmado"
        session.add(c)
        session.commit()
        session.refresh(c)
        return c

    if not comentario or len(comentario) < MIN_COMENTARIO:
        raise HTTPException(status_code=400, detail="Cuéntale al técnico qué sigue fallando (mínimo 5 caracteres).")
    c.respuesta = "rechazado"
    session.add(c)
    # Vuelve al mismo técnico, que lo sigue teniendo tomado.
    ticket.estado = "en_proceso"
    ticket.cerrado_en = None
    ticket.resuelto_por = None
    if ticket.tecnico_id is None and c.tecnico_id is not None:
        ticket.tecnico_id = c.tecnico_id
    if ticket.tecnico_id is not None:
        ticket.tecnico_manual = True
        ticket.tomado_en = ticket.tomado_en or ahora
    session.add(ticket)
    session.add(
        HistorialEstadoTicket(
            ticket_id=ticket.id, estado_anterior="resuelto", estado_nuevo="en_proceso",
            cambiado_por_id=usuario.id, motivo=f"No quedó resuelto: {comentario}",
        )
    )
    session.add(MensajeTicket(ticket_id=ticket.id, autor_id=usuario.id, texto=f"No quedó resuelto: {comentario}"))
    session.commit()
    session.refresh(c)
    session.refresh(ticket)
    notificaciones.no_quedo_resuelto(tareas, session, ticket, usuario, comentario)
    return c


def vencer(session: Session, ahora: datetime) -> int:
    """Confirma solas las esperas que pasaron su ventana. No hace commit."""
    vencidas = session.exec(
        select(ConfirmacionCierre).where(ConfirmacionCierre.respuesta == "pendiente", ConfirmacionCierre.vence_en <= ahora)
    ).all()
    for c in vencidas:
        ticket = session.get(Ticket, c.ticket_id)
        c.respuesta = "automatico" if ticket is not None and ticket.estado == "resuelto" else "anulado"
        c.respondido_en = ahora
        session.add(c)
    return len(vencidas)

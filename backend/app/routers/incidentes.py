"""Ticket principal y afectados: varios usuarios con el mismo problema
(la lógica está en services/incidentes.py). Solo para el personal."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from app.database import get_session
from app.models import Cliente, Ticket
from app.services import incidentes
from app.services.auth import requerir_personal

router = APIRouter()


class TicketVinculado(SQLModel):
    id: int
    texto: str
    estado: str
    solicitante: Optional[str] = None
    categoria: Optional[str] = None
    creado_en: datetime
    similitud: Optional[float] = None


class UnirAfectados(SQLModel):
    ids: list[int]


def _obtener(session: Session, ticket_id: int) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


def _lectura(session: Session, tickets: list[tuple[Ticket, Optional[float]]]) -> list[TicketVinculado]:
    ids = {t.cliente_id for t, _ in tickets}
    nombres = {c.id: c.nombre for c in session.exec(select(Cliente).where(Cliente.id.in_(ids)))} if ids else {}
    return [
        TicketVinculado(
            id=t.id,
            texto=t.texto[:200],
            estado=t.estado,
            solicitante=t.solicitante_externo or nombres.get(t.cliente_id),
            categoria=t.categoria or t.categoria_predicha,
            creado_en=t.creado_en,
            similitud=round(min(s, 1.0), 2) if s is not None else None,
        )
        for t, s in tickets
    ]


@router.get("/tickets/{ticket_id}/afectados", response_model=list[TicketVinculado])
def ver_afectados(ticket_id: int, _: Cliente = Depends(requerir_personal), session: Session = Depends(get_session)):
    ticket = _obtener(session, ticket_id)
    return _lectura(session, [(t, None) for t in incidentes.afectados(session, ticket.id)])


@router.get("/tickets/{ticket_id}/incidente-sugerido", response_model=list[TicketVinculado])
def incidente_sugerido(ticket_id: int, _: Cliente = Depends(requerir_personal), session: Session = Depends(get_session)):
    """Vacío salvo que haya 3 o más personas con un problema parecido en las últimas 48 h."""
    return _lectura(session, incidentes.sugerencia(session, _obtener(session, ticket_id)))


@router.post("/tickets/{ticket_id}/afectados", response_model=list[TicketVinculado])
def unir_afectados(
    ticket_id: int,
    data: UnirAfectados,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    principal = _obtener(session, ticket_id)
    incidentes.unir(session, tareas, principal, data.ids, usuario)
    return _lectura(session, [(t, None) for t in incidentes.afectados(session, principal.id)])


@router.delete("/tickets/{ticket_id}/afectado")
def separar_afectado(
    ticket_id: int, usuario: Cliente = Depends(requerir_personal), session: Session = Depends(get_session)
):
    ticket = _obtener(session, ticket_id)
    incidentes.separar(session, ticket, usuario)
    session.commit()
    return {"ok": True}

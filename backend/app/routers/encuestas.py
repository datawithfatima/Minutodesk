"""Encuesta de satisfacción: al resolverse un ticket, quien lo abrió califica la atención
(1 a 5 estrellas y un comentario opcional). El personal ve el resultado en Reportes.

No se envían correos aparte: el aviso de «ticket resuelto» que ya existía invita a
calificar. La encuesta no toca el clasificador, a Minutito ni los plazos (SLA).
"""
from collections import Counter, defaultdict
from datetime import datetime
from statistics import mean
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from app.database import get_session
from app.models import Cliente, EncuestaSatisfaccion, Ticket
from app.services import notificaciones
from app.services.auth import es_personal, obtener_usuario_actual, requerir_personal

router = APIRouter()

MAX_COMENTARIO = 1000


class EncuestaCreate(SQLModel):
    estrellas: int
    comentario: Optional[str] = None


class EncuestaRead(SQLModel):
    ticket_id: int
    estrellas: int
    comentario: Optional[str] = None
    creado_en: datetime
    actualizado_en: Optional[datetime] = None


class PendienteRead(SQLModel):
    ticket_id: int
    texto: str
    cerrado_en: Optional[datetime] = None


def _ticket(session: Session, ticket_id: int, usuario: Cliente) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if ticket.cliente_id != usuario.id and not es_personal(usuario):
        raise HTTPException(status_code=403, detail="No tienes acceso a este ticket")
    return ticket


def _de_ticket(session: Session, ticket_id: int) -> Optional[EncuestaSatisfaccion]:
    return session.exec(select(EncuestaSatisfaccion).where(EncuestaSatisfaccion.ticket_id == ticket_id)).first()


@router.get("/tickets/{ticket_id}/encuesta", response_model=Optional[EncuestaRead])
def ver_encuesta(
    ticket_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    _ticket(session, ticket_id, usuario)
    e = _de_ticket(session, ticket_id)
    return EncuestaRead.model_validate(e, from_attributes=True) if e else None


@router.post("/tickets/{ticket_id}/encuesta", response_model=EncuestaRead)
def responder_encuesta(
    ticket_id: int,
    data: EncuestaCreate,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Solo quien abrió el ticket, y solo si está resuelto. Si ya calificó, se actualiza."""
    ticket = _ticket(session, ticket_id, usuario)
    if ticket.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="Solo quien abrió el ticket puede calificar la atención.")
    if ticket.estado != "resuelto":
        raise HTTPException(status_code=409, detail="Podrás calificar la atención cuando el ticket esté resuelto.")
    if not 1 <= data.estrellas <= 5:
        raise HTTPException(status_code=400, detail="Elige de 1 a 5 estrellas.")
    comentario = (data.comentario or "").strip() or None
    if comentario and len(comentario) > MAX_COMENTARIO:
        raise HTTPException(status_code=400, detail=f"El comentario es demasiado largo (máximo {MAX_COMENTARIO}).")

    e = _de_ticket(session, ticket_id)
    primera_vez = e is None
    if e is None:
        e = EncuestaSatisfaccion(ticket_id=ticket.id, cliente_id=usuario.id, estrellas=data.estrellas)
    else:
        e.actualizado_en = datetime.now()
    e.estrellas = data.estrellas
    e.comentario = comentario
    e.tecnico_id = ticket.tecnico_id
    session.add(e)
    session.commit()
    session.refresh(e)
    if primera_vez:  # al cambiar la calificación no se vuelve a avisar
        notificaciones.encuesta_recibida(tareas, session, ticket, e.estrellas, e.comentario, usuario)
    return EncuestaRead.model_validate(e, from_attributes=True)


@router.get("/encuestas/pendientes", response_model=list[PendienteRead])
def encuestas_pendientes(
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Tickets resueltos de la persona que aún no calificó (los más recientes primero)."""
    calificados = select(EncuestaSatisfaccion.ticket_id)
    tickets = session.exec(
        select(Ticket)
        .where(Ticket.cliente_id == usuario.id, Ticket.estado == "resuelto", Ticket.id.not_in(calificados))
        .order_by(Ticket.cerrado_en.desc())
        .limit(20)
    ).all()
    return [PendienteRead(ticket_id=t.id, texto=t.texto[:160], cerrado_en=t.cerrado_en) for t in tickets]


def resumen_satisfaccion(session: Session) -> dict:
    """Promedio, reparto de estrellas, tasa de respuesta, promedio por técnico y los
    comentarios más recientes. También lo usa la exportación de reportes."""
    encuestas = session.exec(select(EncuestaSatisfaccion).order_by(EncuestaSatisfaccion.creado_en.desc())).all()
    # Se pueden calificar los resueltos que abrió una cuenta (no los de la carga masiva).
    ids_resueltos = set(
        session.exec(select(Ticket.id).where(Ticket.estado == "resuelto", Ticket.solicitante_externo.is_(None))).all()
    )
    respondidas = sum(1 for e in encuestas if e.ticket_id in ids_resueltos)
    reparto = Counter(e.estrellas for e in encuestas)

    ids = {e.tecnico_id for e in encuestas if e.tecnico_id} | {e.cliente_id for e in encuestas}
    nombres = (
        {c.id: c.nombre for c in session.exec(select(Cliente).where(Cliente.id.in_(ids))).all()} if ids else {}
    )
    por_tecnico: dict[Optional[int], list[int]] = defaultdict(list)
    for e in encuestas:
        por_tecnico[e.tecnico_id].append(e.estrellas)

    return {
        "respuestas": len(encuestas),
        "promedio": round(mean(e.estrellas for e in encuestas), 2) if encuestas else None,
        "satisfechos_pct": (
            round(100 * sum(e.estrellas >= 4 for e in encuestas) / len(encuestas), 1) if encuestas else None
        ),
        "resueltos_calificables": len(ids_resueltos),
        "tasa_respuesta_pct": round(100 * respondidas / len(ids_resueltos), 1) if ids_resueltos else None,
        "reparto": [{"estrellas": n, "total": reparto.get(n, 0)} for n in range(5, 0, -1)],
        "por_tecnico": sorted(
            (
                {
                    "tecnico": nombres.get(tid, "Sin técnico") if tid else "Sin técnico",
                    "respuestas": len(v),
                    "promedio": round(mean(v), 2),
                }
                for tid, v in por_tecnico.items()
            ),
            key=lambda x: (-x["respuestas"], x["tecnico"]),
        ),
        "comentarios": [
            {
                "ticket_id": e.ticket_id,
                "estrellas": e.estrellas,
                "comentario": e.comentario,
                "autor": nombres.get(e.cliente_id, ""),
                "fecha": e.actualizado_en or e.creado_en,
            }
            for e in encuestas
            if e.comentario
        ][:12],
    }


@router.get("/reportes/satisfaccion")
def reporte_de_satisfaccion(
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    """Solo personal (técnico o administrador)."""
    return resumen_satisfaccion(session)

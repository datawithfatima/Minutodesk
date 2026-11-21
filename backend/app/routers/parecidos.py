"""Antes de crear un ticket: ¿la persona ya tiene uno abierto casi igual?

El formulario consulta aquí con el texto que va a enviar. Si hay un ticket suyo abierto
parecido, se le muestra «Ya tienes el #X abierto» para que siga en ese (escenario 4 de
los plazos de seguimiento, 20/11/2026). Compara palabras como la búsqueda de duplicados
del personal (routers/respuestas.py); no usa el clasificador.
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session, SQLModel, select

from app.database import get_session
from app.models import Cliente, Ticket
from app.routers.respuestas import _palabras
from app.services.auth import obtener_usuario_actual

router = APIRouter()

ABIERTOS = ("abierto", "en_proceso")
UMBRAL = 0.4  # palabras en común / palabras de ambos
MIN_PALABRAS = 3  # con menos, cualquier parecido es casualidad
MAX_TEXTO = 5000


class TextoNuevo(SQLModel):
    texto: str
    categoria: str | None = None


class TicketParecido(SQLModel):
    id: int
    texto: str
    estado: str
    categoria: str | None = None
    creado_en: datetime
    similitud: float


@router.post("/tickets/parecidos-mios", response_model=list[TicketParecido])
def mis_tickets_parecidos(
    data: TextoNuevo,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Tickets abiertos de esta persona que se parecen al texto que va a enviar (hasta 3)."""
    base = _palabras(data.texto[:MAX_TEXTO])
    if len(base) < MIN_PALABRAS:
        return []
    propios = session.exec(
        select(Ticket).where(
            Ticket.cliente_id == usuario.id,
            Ticket.estado.in_(ABIERTOS),
            Ticket.solicitante_externo.is_(None),
            Ticket.duplicado_de_id.is_(None),
        )
    ).all()
    salida = []
    for t in propios:
        otras = _palabras(t.texto)
        if not otras:
            continue
        similitud = len(base & otras) / len(base | otras)
        if data.categoria and (t.categoria or t.categoria_predicha) == data.categoria:
            similitud += 0.1
        if similitud >= UMBRAL:
            salida.append(
                TicketParecido(
                    id=t.id,
                    texto=t.texto[:200],
                    estado=t.estado,
                    categoria=t.categoria or t.categoria_predicha,
                    creado_en=t.creado_en,
                    similitud=round(min(similitud, 1.0), 2),
                )
            )
    return sorted(salida, key=lambda x: -x.similitud)[:3]

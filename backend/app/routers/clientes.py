from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente, EventoGamificacion
from app.schemas import ClienteGamificacion
from app.services.gamification_rules import calcular_nivel

router = APIRouter()


@router.get("/{cliente_id}/gamificacion", response_model=ClienteGamificacion)
def obtener_gamificacion(cliente_id: int, session: Session = Depends(get_session)):
    cliente = session.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    historial = session.exec(
        select(EventoGamificacion)
        .where(EventoGamificacion.cliente_id == cliente_id)
        .order_by(EventoGamificacion.creado_en.desc())
    ).all()

    return ClienteGamificacion(
        puntos=cliente.puntos,
        nivel=calcular_nivel(cliente.puntos),
        historial=historial,
    )

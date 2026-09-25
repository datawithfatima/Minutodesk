from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente, EventoGamificacion
from app.schemas import ClienteGamificacion, ClienteRead
from app.services.auth import (
    obtener_usuario_actual,
    requerir_tecnico,
    verificar_acceso_cliente,
)
from app.services.gamification_rules import calcular_nivel

router = APIRouter()


@router.get("", response_model=list[ClienteRead])
def listar_clientes(
    usuario: Cliente = Depends(requerir_tecnico), session: Session = Depends(get_session)
):
    return session.exec(select(Cliente)).all()


@router.get("/{cliente_id}", response_model=ClienteRead)
def obtener_cliente(
    cliente_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    verificar_acceso_cliente(usuario, cliente_id)
    cliente = session.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.get("/{cliente_id}/gamificacion", response_model=ClienteGamificacion)
def obtener_gamificacion(
    cliente_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    verificar_acceso_cliente(usuario, cliente_id)

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

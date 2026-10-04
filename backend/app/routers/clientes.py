from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente, EventoGamificacion
from app.schemas import ClienteGamificacion, ClienteRead
from app.services.auth import (
    obtener_usuario_actual,
    requerir_personal,
    verificar_acceso_cliente,
)
from app.services.gamification_rules import calcular_nivel
from app.services.usuarios import a_cliente_read, mapa_areas

router = APIRouter()


@router.get("", response_model=list[ClienteRead])
def listar_clientes(
    usuario: Cliente = Depends(requerir_personal), session: Session = Depends(get_session)
):
    areas = mapa_areas(session)
    clientes = session.exec(select(Cliente).order_by(Cliente.nombre)).all()
    return [a_cliente_read(c, areas) for c in clientes]


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
    return a_cliente_read(cliente, mapa_areas(session))


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

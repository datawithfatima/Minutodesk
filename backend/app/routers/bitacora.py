"""Bitácora de auditoría y respaldos de la base de datos (solo administrador)."""
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.database import get_session
from app.models import Auditoria, Cliente
from app.services import respaldo
from app.services.auditoria import TITULOS
from app.services.auth import requerir_admin

router = APIRouter()

POR_PAGINA = 50


@router.get("/bitacora")
def ver_bitacora(
    accion: Optional[str] = None,
    actor_id: Optional[int] = None,
    q: Optional[str] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    solo_fallos: bool = False,
    pagina: int = 1,
    usuario: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    filtros = []
    if accion:
        filtros.append(Auditoria.accion == accion)
    if actor_id:
        filtros.append(Auditoria.actor_id == actor_id)
    if desde:
        filtros.append(Auditoria.fecha >= datetime.combine(desde, time.min))
    if hasta:
        filtros.append(Auditoria.fecha < datetime.combine(hasta + timedelta(days=1), time.min))
    if solo_fallos:
        filtros.append(Auditoria.exito == False)  # noqa: E712
    if q and q.strip():
        patron = f"%{q.strip()[:100]}%"
        filtros.append(
            or_(Auditoria.descripcion.ilike(patron), Auditoria.actor.ilike(patron), Auditoria.detalle.ilike(patron))
        )
    total = session.exec(select(func.count()).select_from(Auditoria).where(*filtros)).one()
    pagina = max(1, pagina)
    filas = session.exec(
        select(Auditoria)
        .where(*filtros)
        .order_by(Auditoria.fecha.desc(), Auditoria.id.desc())
        .offset((pagina - 1) * POR_PAGINA)
        .limit(POR_PAGINA)
    ).all()
    personas = session.exec(
        select(Auditoria.actor_id, Auditoria.actor).where(Auditoria.actor_id.is_not(None)).distinct()
    ).all()
    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "registros": [r.model_dump() for r in filas],
        "acciones": [{"clave": k, "titulo": v} for k, v in sorted(TITULOS.items(), key=lambda x: x[1])],
        "personas": sorted({pid: nombre or f"#{pid}" for pid, nombre in personas}.items(), key=lambda x: x[1]),
    }


@router.get("/respaldos")
def ver_respaldos(usuario: Cliente = Depends(requerir_admin)):
    return respaldo.estado()


@router.post("/respaldos")
def crear_respaldo(usuario: Cliente = Depends(requerir_admin)):
    try:
        return respaldo.crear(manual=True)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"No se pudo crear el respaldo: {error}")


@router.get("/respaldos/{nombre}")
def descargar_respaldo(nombre: str, usuario: Cliente = Depends(requerir_admin)):
    archivo = respaldo.ruta(nombre)
    if archivo is None:
        raise HTTPException(status_code=404, detail="Respaldo no encontrado")
    return FileResponse(archivo, media_type="application/octet-stream", filename=nombre)

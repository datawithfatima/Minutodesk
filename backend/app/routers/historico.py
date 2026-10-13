"""Consulta de los tickets importados del CSV (solo lectura, solo administrador).

Son tickets de la herramienta anterior: viven en su propia tabla y no se mezclan con
los de la plataforma (no cuentan en indicadores, ranking ni puntos, y no se editan).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.ml.train_classifier import quitar_tildes
from app.models import Cliente, TicketHistorico
from app.schemas import (
    HistoricoFiltros,
    HistoricoTicketDetalle,
    HistoricoTicketItem,
    HistoricoTicketLista,
)
from app.services.auth import requerir_admin

router = APIRouter()

LARGO_EXTRACTO = 160


def _extracto(descripcion: Optional[str]) -> Optional[str]:
    if not descripcion:
        return None
    una_linea = " ".join(descripcion.split())
    return una_linea if len(una_linea) <= LARGO_EXTRACTO else una_linea[:LARGO_EXTRACTO].rstrip() + "…"


def _item(t: TicketHistorico) -> HistoricoTicketItem:
    return HistoricoTicketItem(
        id=t.id,
        id_externo=t.id_externo,
        tipo=t.tipo,
        categoria=t.categoria,
        prioridad=t.prioridad,
        estado=t.estado,
        creado_en=t.creado_en,
        resuelto_en=t.resuelto_en,
        solicitante=t.solicitante,
        asignado_a=t.asignado_a,
        extracto=_extracto(t.descripcion),
    )


def _texto_buscable(t: TicketHistorico) -> str:
    partes = (t.id_externo, t.descripcion, t.categoria, t.solicitante, t.asignado_a)
    return quitar_tildes(" ".join(p for p in partes if p).lower())


@router.get("/tickets", response_model=HistoricoTicketLista)
def listar_tickets(
    q: Optional[str] = None,
    estado: Optional[str] = None,
    categoria: Optional[str] = None,
    prioridad: Optional[str] = None,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    todos = session.exec(select(TicketHistorico)).all()
    filtros = HistoricoFiltros(
        estados=sorted({t.estado for t in todos}),
        categorias=sorted({t.categoria for t in todos if t.categoria}),
        prioridades=sorted({t.prioridad for t in todos if t.prioridad}),
    )

    elegidos = [
        t
        for t in todos
        if (not estado or t.estado == estado)
        and (not categoria or t.categoria == categoria)
        and (not prioridad or t.prioridad == prioridad)
    ]
    if q and q.strip():
        buscado = quitar_tildes(q.strip().lower())  # sin distinguir mayúsculas ni tildes
        elegidos = [t for t in elegidos if buscado in _texto_buscable(t)]

    elegidos.sort(key=lambda t: t.creado_en, reverse=True)
    inicio = (pagina - 1) * por_pagina
    return HistoricoTicketLista(
        total=len(elegidos),
        pagina=pagina,
        por_pagina=por_pagina,
        items=[_item(t) for t in elegidos[inicio : inicio + por_pagina]],
        filtros=filtros,
    )


@router.get("/tickets/{ticket_id}", response_model=HistoricoTicketDetalle)
def obtener_ticket(
    ticket_id: int,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    t = session.get(TicketHistorico, ticket_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Ticket histórico no encontrado")
    return HistoricoTicketDetalle(**_item(t).model_dump(), descripcion=t.descripcion)

"""Indicadores. Un usuario final ve los de sus propios tickets; el personal, los de todos."""
from collections import Counter
from statistics import mean

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente, Ticket
from app.schemas import CategoriaConteo, ReporteResumen
from app.services.auth import es_personal, obtener_usuario_actual

router = APIRouter()


@router.get("/resumen", response_model=ReporteResumen)
def resumen(
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    consulta = select(Ticket)
    if not es_personal(usuario):
        consulta = consulta.where(Ticket.cliente_id == usuario.id)
    tickets = session.exec(consulta).all()

    total = len(tickets)
    por_estado = Counter(t.estado for t in tickets)
    resueltos = [t for t in tickets if t.estado == "resuelto"]
    por_minutito = sum(1 for t in resueltos if t.resuelto_por == "minutito")
    horas = [
        (t.cerrado_en - t.creado_en).total_seconds() / 3600 for t in resueltos if t.cerrado_en
    ]
    confianzas = [t.confianza_clasificacion for t in tickets if t.confianza_clasificacion is not None]
    categorias = Counter(t.categoria_predicha or "Sin categoría" for t in tickets)

    return ReporteResumen(
        total=total,
        abiertos=por_estado.get("abierto", 0),
        en_proceso=por_estado.get("en_proceso", 0),
        resueltos=len(resueltos),
        resueltos_por_minutito=por_minutito,
        resueltos_por_tecnico=len(resueltos) - por_minutito,
        pct_resolucion_autonoma=round(100 * por_minutito / total, 1) if total else 0.0,
        tiempo_medio_resolucion_horas=round(mean(horas), 1) if horas else None,
        confianza_media=round(100 * mean(confianzas), 1) if confianzas else None,
        por_categoria=[
            CategoriaConteo(categoria=c, total=n) for c, n in categorias.most_common(8)
        ],
    )

"""Indicadores. Un usuario final ve los de sus propios tickets; el personal, los de todos."""
from collections import Counter
from datetime import date, timedelta
from statistics import mean

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente, InteraccionMinutito, Ticket
from app.schemas import CategoriaConteo, ConteoEtiqueta, HistoricoResumen, ReporteResumen
from app.services.auth import (
    es_personal,
    obtener_usuario_actual,
    requerir_admin,
    requerir_personal,
)
from app.services.classifier import cargar_metricas
from app.services.historico import resumen_historico

router = APIRouter()


def _acierto_en_uso(session: Session) -> dict:
    """Acierto real del SVM con tickets creados en la plataforma: compara lo que sugirió
    con lo que la persona eligió o el personal corrigió. Es optimista si la persona
    acepta la sugerencia sin mirar; las correcciones del técnico lo equilibran."""
    tickets = session.exec(select(Ticket)).all()
    con_categoria = [t for t in tickets if t.categoria and t.categoria_predicha]
    con_tipo = [t for t in tickets if t.tipo and t.tipo_predicho]
    return {
        "tickets_categoria": len(con_categoria),
        "acierto_categoria": (
            round(sum(t.categoria == t.categoria_predicha for t in con_categoria) / len(con_categoria), 4)
            if con_categoria
            else None
        ),
        "tickets_tipo": len(con_tipo),
        "acierto_tipo": (
            round(sum(t.tipo == t.tipo_predicho for t in con_tipo) / len(con_tipo), 4) if con_tipo else None
        ),
    }


@router.get("/clasificador")
def clasificador(
    usuario: Cliente = Depends(requerir_admin), session: Session = Depends(get_session)
):
    """Precisión medida del clasificador (validación cruzada), su umbral de confianza y el
    acierto real en uso. Solo el administrador: el resto del personal ve métricas de
    tickets, no del modelo."""
    en_uso = _acierto_en_uso(session)
    metricas = cargar_metricas()
    if not metricas:
        return {"disponible": False, "en_uso": en_uso}
    return {"disponible": True, **metricas, "en_uso": en_uso}


@router.get("/clasificador/umbral")
def umbral_de_confianza(usuario: Cliente = Depends(requerir_personal)):
    """Solo el umbral, para avisar en cada ticket cuando la categoría es poco confiable."""
    return {"umbral": cargar_metricas().get("categoria", {}).get("umbral")}


@router.get("/historico", response_model=HistoricoResumen)
def historico(
    usuario: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    """Indicadores del histórico importado desde el CSV mensual (solo administrador)."""
    return resumen_historico(session)


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
    vigentes = total - por_estado.get("cancelado", 0)
    resueltos = [t for t in tickets if t.estado == "resuelto"]
    por_minutito = sum(1 for t in resueltos if t.resuelto_por == "minutito")
    horas = [
        (t.cerrado_en - t.creado_en).total_seconds() / 3600 for t in resueltos if t.cerrado_en
    ]
    confianzas = [t.confianza_clasificacion for t in tickets if t.confianza_clasificacion is not None]
    # La categoría que cuenta es la que eligió o confirmó la persona; si no, la predicha.
    categorias = Counter(t.categoria or t.categoria_predicha or "Sin categoría" for t in tickets)

    ids = [t.id for t in tickets]
    con_minutito = (
        len(set(session.exec(
            select(InteraccionMinutito.ticket_id).where(InteraccionMinutito.ticket_id.in_(ids))
        ).all()))
        if ids
        else 0
    )
    hoy = date.today()
    creados_por_dia = Counter(t.creado_en.date() for t in tickets)
    ultimos_dias = [
        ConteoEtiqueta(
            etiqueta=(hoy - timedelta(days=i)).isoformat(),
            total=creados_por_dia.get(hoy - timedelta(days=i), 0),
        )
        for i in range(13, -1, -1)
    ]

    return ReporteResumen(
        total=total,
        abiertos=por_estado.get("abierto", 0),
        en_proceso=por_estado.get("en_proceso", 0),
        resueltos=len(resueltos),
        cancelados=por_estado.get("cancelado", 0),
        resueltos_por_minutito=por_minutito,
        resueltos_por_tecnico=len(resueltos) - por_minutito,
        pct_resolucion_autonoma=round(100 * por_minutito / vigentes, 1) if vigentes else 0.0,
        tiempo_medio_resolucion_horas=round(mean(horas), 1) if horas else None,
        # Dato del modelo, no del ticket: solo lo ve el administrador.
        confianza_media=(
            round(100 * mean(confianzas), 1)
            if confianzas and usuario.rol == "administrador"
            else None
        ),
        por_categoria=[
            CategoriaConteo(categoria=c, total=n) for c, n in categorias.most_common(8)
        ],
        con_minutito=con_minutito,
        ultimos_dias=ultimos_dias,
    )

"""Simulación del tiempo de resolución con MinutoDesk (objetivo 3 de la tesis).

Línea base: el tiempo real de resolución del histórico (creación → fecha de solución).
Simulación: con los tickets nuevos cargados que ya se resolvieron, se reemplaza el tiempo
real por unos minutos en los que, según la evaluación experta, Minutito los habría
resuelto. Los que no se evaluaron cuentan como no resueltos por Minutito (supuesto
conservador). Se compara el promedio real con el simulado.
"""
from datetime import datetime
from statistics import mean, median
from typing import Optional

import numpy as np
from sqlmodel import Session, select

from app.models import EvaluacionMinutito, Ticket, TicketHistorico
from app.services.catalogos import TIPO_INCIDENCIA

META_REDUCCION = 0.20
MINUTOS_MINUTITO = 15  # lo que tarda una conversación con Minutito que resuelve


def _dias(inicio: datetime, fin: datetime) -> float:
    return max((fin - inicio).total_seconds() / 86400, 0.0)


def _habiles(inicio: datetime, fin: datetime) -> int:
    return int(np.busday_count(inicio.date(), fin.date())) if fin >= inicio else 0


def _resumen(dias: list[float]) -> dict:
    return {
        "tickets": len(dias),
        "media_dias": round(mean(dias), 2) if dias else None,
        "mediana_dias": round(median(dias), 2) if dias else None,
    }


def _base(fechas: list[tuple[datetime, datetime]]) -> dict:
    base = _resumen([_dias(a, b) for a, b in fechas])
    base["media_dias_habiles"] = round(mean(_habiles(a, b) for a, b in fechas), 2) if fechas else None
    return base


def _muestra(tickets: list[Ticket], veredictos: dict, minutos_minutito: int) -> dict:
    reales = [_dias(t.creado_en, t.cerrado_en) for t in tickets]
    minutito = [veredictos.get(t.id) == "resuelve" for t in tickets]
    simulados = [minutos_minutito / 1440 if resuelve else real for real, resuelve in zip(reales, minutito)]
    media_real = mean(reales) if reales else None
    media_simulada = mean(simulados) if simulados else None
    reduccion: Optional[float] = round((media_real - media_simulada) / media_real, 4) if media_real else None
    return {
        "tickets": len(tickets),
        "resueltos_por_minutito": sum(minutito),
        "sin_evaluar": sum(veredictos.get(t.id) is None for t in tickets),
        "media_real_dias": round(media_real, 2) if media_real is not None else None,
        "media_simulada_dias": round(media_simulada, 2) if media_simulada is not None else None,
        "reduccion": reduccion,
    }


def simular(session: Session, minutos_minutito: int = MINUTOS_MINUTITO) -> dict:
    """Simulación sobre todos los tickets y sobre las incidencias. El objetivo 3 se mide
    en las incidencias: es lo que Minutito atiende; las solicitudes y los accesos siempre
    los hace el equipo de sistemas, así que en el total la reducción tiene un techo bajo."""
    historico = [
        (h.creado_en, h.resuelto_en, h.tipo)
        for h in session.exec(
            select(TicketHistorico).where(
                TicketHistorico.resuelto_en != None, TicketHistorico.estado == "Completado"  # noqa: E711
            )
        ).all()
        # La fecha de solución viene sin hora: el mismo día cuenta como resuelto ese día.
        if h.resuelto_en >= h.creado_en or h.resuelto_en.date() == h.creado_en.date()
    ]
    veredictos = {
        e.ticket_id: e.veredicto for e in session.exec(select(EvaluacionMinutito)).all()
    }
    muestra = session.exec(
        select(Ticket).where(
            Ticket.id_externo != None, Ticket.estado == "resuelto", Ticket.cerrado_en != None  # noqa: E711
        )
    ).all()
    base_inc = [(a, b) for a, b, tipo in historico if tipo == TIPO_INCIDENCIA]
    total_dias = sum(_dias(a, b) for a, b, _ in historico)
    return {
        "meta": META_REDUCCION,
        "minutos_minutito": minutos_minutito,
        "linea_base_historico": _base([(a, b) for a, b, _ in historico]),
        "muestra": _muestra(muestra, veredictos, minutos_minutito),
        "incidencias": {
            "linea_base_historico": _base(base_inc),
            # Parte del tiempo total del histórico que se va en incidencias: el techo de
            # lo que Minutito puede reducir sobre todos los tickets.
            "parte_del_tiempo_total": round(sum(_dias(a, b) for a, b in base_inc) / total_dias, 4) if total_dias else None,
            "muestra": _muestra([t for t in muestra if t.tipo == TIPO_INCIDENCIA], veredictos, minutos_minutito),
        },
    }

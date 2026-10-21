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


def simular(session: Session, minutos_minutito: int = MINUTOS_MINUTITO) -> dict:
    historico = [
        (h.creado_en, h.resuelto_en)
        for h in session.exec(
            select(TicketHistorico).where(
                TicketHistorico.resuelto_en != None, TicketHistorico.estado == "Completado"  # noqa: E711
            )
        ).all()
        # La fecha de solución viene sin hora: el mismo día cuenta como resuelto ese día.
        if h.resuelto_en >= h.creado_en or h.resuelto_en.date() == h.creado_en.date()
    ]
    base = _resumen([_dias(a, b) for a, b in historico])
    base["media_dias_habiles"] = round(mean(_habiles(a, b) for a, b in historico), 2) if historico else None

    veredictos = {
        e.ticket_id: e.veredicto for e in session.exec(select(EvaluacionMinutito)).all()
    }
    muestra = session.exec(
        select(Ticket).where(
            Ticket.id_externo != None, Ticket.estado == "resuelto", Ticket.cerrado_en != None  # noqa: E711
        )
    ).all()
    reales = [_dias(t.creado_en, t.cerrado_en) for t in muestra]
    minutito = [veredictos.get(t.id) == "resuelve" for t in muestra]
    simulados = [
        minutos_minutito / 1440 if resuelve else real for real, resuelve in zip(reales, minutito)
    ]
    media_real = mean(reales) if reales else None
    media_simulada = mean(simulados) if simulados else None
    reduccion: Optional[float] = (
        round((media_real - media_simulada) / media_real, 4) if media_real else None
    )
    return {
        "meta": META_REDUCCION,
        "minutos_minutito": minutos_minutito,
        "linea_base_historico": base,
        "muestra": {
            "tickets": len(muestra),
            "resueltos_por_minutito": sum(minutito),
            "sin_evaluar": sum(veredictos.get(t.id) is None for t in muestra),
            "media_real_dias": round(media_real, 2) if media_real is not None else None,
            "media_simulada_dias": round(media_simulada, 2) if media_simulada is not None else None,
            "reduccion": reduccion,
        },
    }

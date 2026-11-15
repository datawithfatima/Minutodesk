"""Objetivo 3 medido en las incidencias del histórico (decisión de Fátima, 14/11/2026).

Los tickets nuevos cargados solo tenían 12 incidencias resueltas y la reducción del
tiempo dependía de 2. El histórico trae el tiempo real de resolución de 97 incidencias:
Minutito responde el texto de cada una, como si la persona se lo escribiera, y alguien
del equipo marca si eso la habría resuelto. Después se compara el tiempo real promedio
con el simulado (15 minutos para las que Minutito resolvería), igual que en
simulacion_tiempos.py. Las que no tienen texto o no se marcan cuentan como no resueltas.

El histórico solo entrenó al clasificador; Minutito aprende únicamente de las soluciones
anotadas en los tickets nuevos, así que estas incidencias son nuevas para él.
"""
import json
import logging
from datetime import datetime
from math import sqrt
from pathlib import Path
from statistics import mean, median
from typing import Optional

from sqlmodel import Session, select

from app.models import Cliente, EvaluacionHistorico, TicketHistorico
from app.services.casos_resueltos import casos_parecidos
from app.services.catalogos import TIPO_INCIDENCIA
from app.services.minutito_chat import MinutitoNoDisponible, responder
from app.services.simulacion_tiempos import META_REDUCCION, MINUTOS_MINUTITO, _dias

logger = logging.getLogger("minutodesk.evaluacion_historico")

VEREDICTOS = ("resuelve", "no_resuelve", "no_aplica")
# Respuestas generadas antes con scripts/minutito_historico.py: se cargan sin repetirlas.
RESPUESTAS_JSON = Path(__file__).resolve().parents[3] / "data" / "evaluacion_historico" / "respuestas.json"

progreso = {"en_curso": False, "hechas": 0, "total": 0}


def incidencias(session: Session) -> list[TicketHistorico]:
    """Las mismas de la línea base de incidencias en simulacion_tiempos.simular."""
    filas = session.exec(
        select(TicketHistorico)
        .where(
            TicketHistorico.resuelto_en != None,  # noqa: E711
            TicketHistorico.estado == "Completado",
            TicketHistorico.tipo == TIPO_INCIDENCIA,
        )
        .order_by(TicketHistorico.creado_en)
    ).all()
    return [h for h in filas if h.resuelto_en >= h.creado_en or h.resuelto_en.date() == h.creado_en.date()]


def _registros(session: Session) -> dict[int, EvaluacionHistorico]:
    return {e.historico_id: e for e in session.exec(select(EvaluacionHistorico)).all()}


def importar_respuestas_previas(session: Session) -> int:
    """Pasa a la base las respuestas que ya generó el script y aún no están."""
    if not RESPUESTAS_JSON.exists():
        return 0
    try:
        previas = json.loads(RESPUESTAS_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    hechos = _registros(session)
    nuevas = 0
    for h in incidencias(session):
        dato = previas.get(h.id_externo)
        if dato and h.id not in hechos:
            session.add(EvaluacionHistorico(historico_id=h.id, respuesta=dato["respuesta"], escalado=dato["escalado"]))
            nuevas += 1
    if nuevas:
        session.commit()
    return nuevas


def generar_pendientes(session: Session) -> dict:
    progreso.update(en_curso=True, hechas=0, total=0)
    try:
        importar_respuestas_previas(session)
        hechos = _registros(session)
        pendientes = [h for h in incidencias(session) if h.id not in hechos and (h.descripcion or "").strip()]
        progreso["total"] = len(pendientes)
        for h in pendientes:
            try:
                casos = casos_parecidos(session, [h.descripcion])
                texto, escala = responder([("usuario", h.descripcion)], casos=casos)
            except MinutitoNoDisponible as e:
                logger.warning("Minutito no disponible: %s", e)
                return {"error": str(e)}
            session.add(EvaluacionHistorico(historico_id=h.id, respuesta=texto, escalado=escala))
            session.commit()
            progreso["hechas"] += 1
        return {"error": None}
    finally:
        progreso["en_curso"] = False


def marcar(session: Session, evaluacion_id: int, veredicto: Optional[str], quien: Cliente) -> EvaluacionHistorico:
    if veredicto is not None and veredicto not in VEREDICTOS:
        raise ValueError("Veredicto no válido")
    registro = session.get(EvaluacionHistorico, evaluacion_id)
    if registro is None:
        raise LookupError("Evaluación no encontrada")
    registro.veredicto = veredicto
    registro.evaluado_por_id = quien.id if veredicto else None
    registro.evaluado_en = datetime.now() if veredicto else None
    session.add(registro)
    session.commit()
    session.refresh(registro)
    return registro


def _wilson(k: int, n: int, z: float = 1.96) -> Optional[list[float]]:
    if not n:
        return None
    p, den = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    m = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(c - m, 4), round(c + m, 4)]


def resumen(session: Session) -> dict:
    if not progreso["en_curso"]:
        importar_respuestas_previas(session)
    lista = incidencias(session)
    registros = _registros(session)
    veredicto = {h.id: (registros[h.id].veredicto if h.id in registros else None) for h in lista}
    reales = [_dias(h.creado_en, h.resuelto_en) for h in lista]
    simulados = [MINUTOS_MINUTITO / 1440 if veredicto[h.id] == "resuelve" else d for h, d in zip(lista, reales)]
    cuenta = {v: sum(x == v for x in veredicto.values()) for v in VEREDICTOS}
    primer_nivel = cuenta["resuelve"] + cuenta["no_resuelve"]
    media_real = mean(reales) if reales else None
    media_sim = mean(simulados) if simulados else None
    return {
        "meta": META_REDUCCION,
        "minutos_minutito": MINUTOS_MINUTITO,
        "incidencias": len(lista),
        "sin_texto": sum(not (h.descripcion or "").strip() for h in lista),
        "generadas": len(registros),
        "sin_evaluar": sum(veredicto[h.id] is None for h in lista if h.id in registros),
        **cuenta,
        "pct_resolveria": round(cuenta["resuelve"] / primer_nivel, 4) if primer_nivel else None,
        "ic95_resolveria": _wilson(cuenta["resuelve"], primer_nivel),
        "media_real_dias": round(media_real, 2) if media_real is not None else None,
        "media_simulada_dias": round(media_sim, 2) if media_sim is not None else None,
        "mediana_real_dias": round(median(reales), 2) if reales else None,
        "mediana_simulada_dias": round(median(simulados), 2) if simulados else None,
        "reduccion": round((media_real - media_sim) / media_real, 4) if media_real else None,
        "progreso": dict(progreso),
        "items": [
            {
                "id": registros[h.id].id,
                "id_externo": h.id_externo,
                "categoria": h.categoria,
                "texto": h.descripcion,
                "respuesta": registros[h.id].respuesta,
                "escalado": registros[h.id].escalado,
                "dias_reales": round(d, 2),
                "veredicto": registros[h.id].veredicto,
            }
            for h, d in zip(lista, reales)
            if h.id in registros
        ],
    }

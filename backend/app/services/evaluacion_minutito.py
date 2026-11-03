"""Evaluación simulada de Minutito con los tickets de la carga masiva.

Esos tickets se atendieron en la herramienta anterior, así que nadie habló con
Minutito. Para estimar cuánto habría resuelto solo, se le pasa a Minutito el texto
de cada ticket tal como lo escribió la persona y se guarda su respuesta. Después
alguien del equipo marca si esa respuesta lo habría resuelto.

Es una estimación por juicio experto, no la resolución autónoma real: no crea
interacciones ni cambia el ticket, y se reporta por separado.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.models import Cliente, EvaluacionMinutito, Ticket
from app.services.casos_resueltos import casos_parecidos
from app.services.minutito_chat import MinutitoNoDisponible, responder

logger = logging.getLogger("minutodesk.evaluacion")

VEREDICTOS = ("resuelve", "no_resuelve", "no_aplica")
META = 0.30
MAX_SOLUCION = 2000


def _pendientes(session: Session, todas: bool = False) -> list[Ticket]:
    evaluados = set() if todas else set(
        session.exec(select(EvaluacionMinutito.ticket_id).where(EvaluacionMinutito.error == None)).all()  # noqa: E711
    )
    tickets = session.exec(
        select(Ticket).where(Ticket.id_externo != None).order_by(Ticket.creado_en)  # noqa: E711
    ).all()
    return [t for t in tickets if t.id not in evaluados]


# Avance de la corrida en segundo plano, para que la pantalla lo muestre y no se lancen
# dos a la vez (las dos competirían por el mismo procesador).
progreso = {"en_curso": False, "hechas": 0, "total": 0}


def generar_pendientes(session: Session, *args, **kwargs) -> dict:
    progreso.update(en_curso=True, hechas=0, total=0)
    try:
        return _generar(session, *args, **kwargs)
    finally:
        progreso["en_curso"] = False


def _generar(session: Session, limite: Optional[int] = None, todas: bool = False) -> dict:
    """Pide a Minutito la respuesta para los tickets que aún no la tienen (o, con
    `todas`, vuelve a generarlas para que use los casos anotados desde entonces). Si
    Ollama no está disponible se detiene: lo que falte se completa en otra corrida."""
    hechos = 0
    pendientes = _pendientes(session, todas)
    progreso["total"] = len(pendientes[:limite])
    for ticket in pendientes[:limite]:
        registro = session.exec(
            select(EvaluacionMinutito).where(EvaluacionMinutito.ticket_id == ticket.id)
        ).first() or EvaluacionMinutito(ticket_id=ticket.id)
        try:
            # Como si la persona le escribiera a Minutito el texto de su ticket.
            # Aprende de los demás casos anotados, nunca del suyo (ver casos_resueltos.py).
            casos = casos_parecidos(session, [ticket.texto], excluir_ticket_id=ticket.id)
            respuesta, ofrece_ticket = responder([("usuario", ticket.texto)], casos=casos)
        except MinutitoNoDisponible as e:
            logger.warning("Minutito no disponible al evaluar: %s", e)
            return {"generadas": hechos, "pendientes": len(pendientes) - hechos, "error": str(e)}
        registro.respuesta = respuesta
        registro.veredicto = None  # una respuesta nueva se vuelve a evaluar
        registro.escalado = ofrece_ticket
        registro.error = None
        registro.generada_en = datetime.now()
        session.add(registro)
        session.commit()
        hechos += 1
        progreso["hechas"] = hechos
    return {"generadas": hechos, "pendientes": len(pendientes) - hechos, "error": None}


def marcar(session: Session, evaluacion_id: int, veredicto: Optional[str], quien: Cliente) -> EvaluacionMinutito:
    if veredicto is not None and veredicto not in VEREDICTOS:
        raise ValueError("Veredicto no válido")
    registro = session.get(EvaluacionMinutito, evaluacion_id)
    if registro is None or registro.respuesta is None:
        raise LookupError("Evaluación no encontrada")
    registro.veredicto = veredicto
    registro.evaluado_por_id = quien.id if veredicto else None
    registro.evaluado_en = datetime.now() if veredicto else None
    session.add(registro)
    session.commit()
    session.refresh(registro)
    return registro


def guardar_solucion(session: Session, evaluacion_id: int, solucion: Optional[str]) -> EvaluacionMinutito:
    """Anota qué se debía hacer en ese ticket, como referencia para el veredicto."""
    registro = session.get(EvaluacionMinutito, evaluacion_id)
    if registro is None:
        raise LookupError("Evaluación no encontrada")
    texto = (solucion or "").strip()
    if len(texto) > MAX_SOLUCION:
        raise ValueError(f"La solución es demasiado larga (máximo {MAX_SOLUCION} caracteres).")
    registro.solucion_esperada = texto or None
    session.add(registro)
    session.commit()
    session.refresh(registro)
    return registro


def resumen(session: Session) -> dict:
    filas = session.exec(
        select(EvaluacionMinutito, Ticket)
        .where(EvaluacionMinutito.ticket_id == Ticket.id)
        .order_by(Ticket.creado_en)
    ).all()
    con_respuesta = [(e, t) for e, t in filas if e.respuesta]
    cuenta = {v: sum(e.veredicto == v for e, _ in con_respuesta) for v in VEREDICTOS}
    primer_nivel = cuenta["resuelve"] + cuenta["no_resuelve"]
    return {
        "meta": META,
        "tickets_cargados": len(session.exec(select(Ticket.id).where(Ticket.id_externo != None)).all()),  # noqa: E711
        "con_respuesta": len(con_respuesta),
        "sin_evaluar": sum(e.veredicto is None for e, _ in con_respuesta),
        "con_solucion": sum(bool(e.solucion_esperada) for e, _ in filas),
        **cuenta,
        # Igual que la meta de la tesis: sobre las consultas de primer nivel.
        "pct_resolveria": round(cuenta["resuelve"] / primer_nivel, 4) if primer_nivel else None,
        "progreso": dict(progreso),
        "items": [
            {
                "id": e.id,
                "ticket_id": t.id,
                "id_externo": t.id_externo,
                "categoria": t.categoria,
                "texto": t.texto,
                "respuesta": e.respuesta,
                "escalado": e.escalado,
                "veredicto": e.veredicto,
                "solucion_esperada": e.solucion_esperada,
            }
            for e, t in con_respuesta
        ],
    }

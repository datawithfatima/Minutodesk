"""Revisor periódico del plazo: avisa al técnico cuando a un ticket abierto le queda el
20 % del tiempo y otra vez cuando venció. Cada aviso se manda una sola vez (Ticket.aviso_sla);
si cambia el tipo o la prioridad se vuelve a evaluar."""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.database import engine
from app.models import Ticket
from app.services import notificaciones, sla

logger = logging.getLogger("minutodesk.sla")

INTERVALO_SEGUNDOS = 10 * 60
ESPERA_INICIAL = 30


def revisar(session: Session, ahora: Optional[datetime] = None) -> int:
    """Envía los avisos que falten y devuelve cuántos mandó."""
    abiertos = list(session.exec(select(Ticket).where(Ticket.estado.in_(("abierto", "en_proceso")))))
    plazos = sla.calcular_varios(session, abiertos, ahora)
    enviados = 0
    for ticket in abiertos:
        plazo = plazos.get(ticket.id)
        if plazo is None:
            continue
        if plazo.vencido and ticket.aviso_sla != "vencido":
            tipo = "vencido"
        elif plazo.estado == "por_vencer" and ticket.aviso_sla is None:
            tipo = "por_vencer"
        else:
            continue
        notificaciones.sla_alerta(session, ticket, plazo.restante_segundos, tipo)
        ticket.aviso_sla = tipo
        session.add(ticket)
        enviados += 1
    session.commit()
    return enviados


def _revisar_con_sesion() -> int:
    with Session(engine) as session:
        return revisar(session)


async def bucle() -> None:
    await asyncio.sleep(ESPERA_INICIAL)
    while True:
        try:
            enviados = await asyncio.to_thread(_revisar_con_sesion)
            if enviados:
                logger.info("Avisos de plazo enviados: %s", enviados)
        except Exception:
            logger.exception("Falló la revisión de plazos")
        await asyncio.sleep(INTERVALO_SEGUNDOS)

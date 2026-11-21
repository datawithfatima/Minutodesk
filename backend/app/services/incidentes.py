"""Varios usuarios con el mismo problema: un ticket principal y sus afectados
(aprobado por Fátima el 20/11/2026).

El técnico marca un ticket como principal y le une los de otras personas como
**afectados** (a diferencia del duplicado del mismo usuario, que se cancela). Solo se
trabaja el principal: el plazo de cada afectado queda en pausa («Se atiende en el ticket
principal»), así que no vence ni cuenta como «sin avance». Cuando el principal se resuelve,
los afectados que siguen abiertos se resuelven con él y se avisa a cada persona; a cada
una le aparece «¿Quedó resuelto?» y, si dice que no, su ticket vuelve a su técnico.

Además, cuando hay 3 o más tickets parecidos de personas distintas abiertos en las
últimas 48 horas, se sugiere unirlos. El vínculo usa Ticket.duplicado_de_id.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import BackgroundTasks, HTTPException
from sqlmodel import Session, select

from app.models import Cliente, HistorialEstadoTicket, Ticket
from app.services import confirmacion, notificaciones, sla, toma

ESTADOS_FINALES = ("resuelto", "cancelado")
HORAS_SUGERENCIA = 48
MIN_PERSONAS = 3  # el ticket y al menos otros 2, de personas distintas
UMBRAL = 0.25


def _palabras(texto: str) -> set[str]:
    from app.routers.respuestas import _palabras as palabras  # misma comparación que los duplicados

    return palabras(texto)


def _similitud(base: set[str], ticket: Ticket, categoria: Optional[str]) -> float:
    otras = _palabras(ticket.texto)
    if not base or not otras:
        return 0.0
    valor = len(base & otras) / len(base | otras)
    if categoria and (ticket.categoria or ticket.categoria_predicha) == categoria:
        valor += 0.1
    return valor


def afectados(session: Session, principal_id: int) -> list[Ticket]:
    return list(session.exec(select(Ticket).where(Ticket.duplicado_de_id == principal_id).order_by(Ticket.id)))


def sugerencia(session: Session, ticket: Ticket) -> list[tuple[Ticket, float]]:
    """Tickets abiertos parecidos, de otras personas, de las últimas 48 h. Solo devuelve
    algo si entre todos suman al menos 3 personas distintas."""
    if ticket.duplicado_de_id is not None or ticket.estado in ESTADOS_FINALES:
        return []
    base = _palabras(ticket.texto)
    if not base:
        return []
    categoria = ticket.categoria or ticket.categoria_predicha
    desde = ticket.creado_en - timedelta(hours=HORAS_SUGERENCIA)
    hasta = max(ticket.creado_en, datetime.now()) + timedelta(hours=1)
    candidatos = session.exec(
        select(Ticket).where(
            Ticket.id != ticket.id,
            Ticket.cliente_id != ticket.cliente_id,
            Ticket.estado.not_in(ESTADOS_FINALES),
            Ticket.duplicado_de_id.is_(None),
            Ticket.creado_en >= desde,
            Ticket.creado_en <= hasta,
        )
    ).all()
    con_hijos = set(
        session.exec(select(Ticket.duplicado_de_id).where(Ticket.duplicado_de_id.is_not(None))).all()
    )
    parecidos = [
        (t, s) for t in candidatos if t.id not in con_hijos and (s := _similitud(base, t, categoria)) >= UMBRAL
    ]
    personas = {ticket.cliente_id} | {t.cliente_id for t, _ in parecidos}
    if len(personas) < MIN_PERSONAS:
        return []
    return sorted(parecidos, key=lambda x: -x[1])[:10]


def unir(
    session: Session, tareas: BackgroundTasks, principal: Ticket, ids: list[int], usuario: Cliente
) -> list[Ticket]:
    """Une los tickets `ids` al principal como afectados. Valida todo antes de cambiar nada."""
    toma.exigir_que_pueda_atender(session, principal, usuario)
    if principal.estado in ESTADOS_FINALES:
        raise HTTPException(status_code=409, detail="El ticket principal ya está cerrado.")
    if principal.duplicado_de_id is not None:
        raise HTTPException(
            status_code=400,
            detail=f"El ticket #{principal.id} ya está unido al #{principal.duplicado_de_id}: usa ese como principal.",
        )
    ids = list(dict.fromkeys(i for i in ids if i != principal.id))
    if not ids:
        raise HTTPException(status_code=400, detail="Elige al menos un ticket para unir.")
    tickets = []
    for i in ids:
        t = session.get(Ticket, i)
        if t is None:
            raise HTTPException(status_code=404, detail=f"No existe el ticket #{i}.")
        if t.estado in ESTADOS_FINALES:
            raise HTTPException(status_code=409, detail=f"El ticket #{i} ya está {t.estado}.")
        if t.duplicado_de_id is not None:
            raise HTTPException(status_code=400, detail=f"El ticket #{i} ya está unido al #{t.duplicado_de_id}.")
        if afectados(session, t.id):
            raise HTTPException(status_code=400, detail=f"El ticket #{i} ya es principal de otros.")
        tickets.append(t)

    for t in tickets:
        t.duplicado_de_id = principal.id
        session.add(t)
        if sla.pausa_activa(session, t.id) is None:
            sla.pausar(session, t, "principal", f"Se atiende en el ticket #{principal.id}", usuario.id)
    session.commit()
    for t in tickets:
        session.refresh(t)
        notificaciones._al_solicitante(
            tareas, session, t, usuario.id,
            asunto="se atiende junto con otros",
            titulo="Tu ticket se atiende junto con otros iguales",
            etiqueta="En proceso",
            tono="info",
            parrafos=[
                "Varias personas reportaron el mismo problema. Para resolverlo una sola vez, el equipo de "
                f"soporte lo atiende en el ticket #{principal.id}.",
                "No tienes que hacer nada: cuando se resuelva, te avisaremos y tu ticket se cerrará con él.",
            ],
        )
    return tickets


def separar(session: Session, ticket: Ticket, usuario: Cliente) -> None:
    """Quita a un afectado del principal: su plazo vuelve a correr. No hace commit."""
    if ticket.duplicado_de_id is None:
        raise HTTPException(status_code=400, detail="Este ticket no está unido a otro.")
    principal = session.get(Ticket, ticket.duplicado_de_id)
    if principal is not None:
        toma.exigir_que_pueda_atender(session, principal, usuario)
    ticket.duplicado_de_id = None
    session.add(ticket)
    pausa = sla.pausa_activa(session, ticket.id)
    if pausa is not None and pausa.motivo == "principal":
        sla.reanudar(session, pausa, usuario.id)


def resolver_afectados(session: Session, tareas: BackgroundTasks, principal: Ticket, usuario: Cliente) -> list[int]:
    """Al resolver el principal, resuelve con él a sus afectados abiertos y les avisa."""
    resueltos = []
    ahora = datetime.now()
    for t in afectados(session, principal.id):
        if t.estado in ESTADOS_FINALES:
            continue
        anterior = t.estado
        sla.cerrar_pausa_activa(session, t.id, usuario.id)
        t.estado = "resuelto"
        t.resuelto_por = "tecnico"
        t.cerrado_en = ahora
        if t.tecnico_id is None:
            t.tecnico_id = principal.tecnico_id or usuario.id
            t.tecnico_manual = True
        session.add(t)
        session.add(
            HistorialEstadoTicket(
                ticket_id=t.id, estado_anterior=anterior, estado_nuevo="resuelto", cambiado_por_id=usuario.id,
                motivo=f"Resuelto en el ticket principal #{principal.id}",
            )
        )
        confirmacion.al_cambiar_estado(session, t, anterior, ahora)
        resueltos.append(t)
    if not resueltos:
        return []
    session.commit()
    for t in resueltos:
        session.refresh(t)
        notificaciones._al_solicitante(
            tareas, session, t, usuario.id,
            asunto="¿quedó resuelto?" if confirmacion.aplica(t) else "fue resuelto",
            titulo="Se resolvió el problema que reportaste",
            etiqueta="Resuelto",
            tono="ok",
            parrafos=[
                f"El equipo de soporte resolvió el problema general (ticket #{principal.id}) y tu ticket "
                "se cerró con él.",
                "Entra a tu ticket y cuéntanos si a ti también te quedó bien: si no, vuelve a tu técnico "
                "sin que tengas que crear otro." if confirmacion.aplica(t) else
                "Si el problema sigue, crea un ticket nuevo y menciona este número.",
            ],
        )
    return [t.id for t in resueltos]

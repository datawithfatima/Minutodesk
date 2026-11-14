"""Correos que avisan de lo que pasa en un ticket.

A quien abrió el ticket: que se recibió, cada cambio de estado (en proceso, resuelto,
cancelado, reabierto) y cada mensaje del equipo de soporte. Al técnico: que le
asignaron un ticket y cada mensaje que escribe el usuario.

Nunca se avisa a la persona de lo que hizo ella misma, ni a cuentas desactivadas, ni
por tickets de la carga masiva (quien los pidió no tiene cuenta). Los correos se envían
en segundo plano (BackgroundTasks) para no demorar la respuesta de la aplicación; si el
SMTP falla, quedan guardados en backend/correos_enviados/ como los demás.
"""
import os
from typing import Optional

from fastapi import BackgroundTasks
from sqlmodel import Session

from sqlmodel import select

from app.models import Cliente, PausaSla, Ticket
from app.services import correo

MAX_EXTRACTO = 300


def _base() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def _enlace(ticket: Ticket, para_personal: bool, rol: str = "tecnico") -> str:
    if para_personal:
        seccion = "admin" if rol == "administrador" else "tecnico"
        return f"{_base()}/{seccion}/tickets/{ticket.id}"
    return f"{_base()}/usuario/tickets/{ticket.id}"


def _extracto(texto: str) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= MAX_EXTRACTO else texto[: MAX_EXTRACTO - 1] + "…"


def _primer_nombre(nombre: str) -> str:
    return (nombre or "").split()[0] if nombre else ""


def _destinatario(session: Session, cliente_id: Optional[int], actor_id: Optional[int]) -> Optional[Cliente]:
    if cliente_id is None or cliente_id == actor_id:
        return None
    persona = session.get(Cliente, cliente_id)
    if persona is None or not persona.activo or not persona.email:
        return None
    return persona


def _al_solicitante(
    tareas: BackgroundTasks, session: Session, ticket: Ticket, actor_id: Optional[int], asunto: str, parrafo: str
) -> None:
    if ticket.solicitante_externo:
        return
    persona = _destinatario(session, ticket.cliente_id, actor_id)
    if persona is None:
        return
    cuerpo = (
        f"Hola {_primer_nombre(persona.nombre)},\n\n"
        f"{parrafo}\n\n"
        f"Tu solicitud: «{_extracto(ticket.texto)}»\n\n"
        f"Puedes ver el ticket y responder aquí: {_enlace(ticket, False)}\n\n"
        "— Mesa de ayuda MinutoDesk"
    )
    tareas.add_task(correo.enviar_correo, persona.email, f"Ticket #{ticket.id}: {asunto}", cuerpo)


def _al_tecnico(
    tareas: BackgroundTasks, session: Session, ticket: Ticket, actor_id: Optional[int], asunto: str, parrafo: str
) -> None:
    persona = _destinatario(session, ticket.tecnico_id, actor_id)
    if persona is None:
        return
    cuerpo = (
        f"Hola {_primer_nombre(persona.nombre)},\n\n"
        f"{parrafo}\n\n"
        f"Ticket #{ticket.id} · {ticket.categoria or ticket.categoria_predicha or 'Sin categoría'} · "
        f"Prioridad {ticket.prioridad}\n"
        f"«{_extracto(ticket.texto)}»\n\n"
        f"Ábrelo aquí: {_enlace(ticket, True, persona.rol)}\n\n"
        "— Mesa de ayuda MinutoDesk"
    )
    tareas.add_task(correo.enviar_correo, persona.email, f"Ticket #{ticket.id}: {asunto}", cuerpo)


# ---------- eventos ----------

def ticket_creado(tareas: BackgroundTasks, session: Session, ticket: Ticket) -> None:
    _al_solicitante(
        tareas, session, ticket, None, "lo recibimos",
        f"Recibimos tu ticket #{ticket.id}. El equipo de soporte lo revisará y te avisaremos "
        "por este medio cada vez que haya novedades.",
    )
    _al_tecnico(
        tareas, session, ticket, None, "te lo asignaron",
        "Se creó un ticket nuevo y, por su sistema, quedaste como técnico sugerido.",
    )


def tecnico_asignado(tareas: BackgroundTasks, session: Session, ticket: Ticket, actor: Cliente) -> None:
    _al_tecnico(
        tareas, session, ticket, actor.id, "te lo asignaron",
        f"{actor.nombre} te asignó este ticket.",
    )


def estado_cambiado(
    tareas: BackgroundTasks, session: Session, ticket: Ticket, anterior: str, actor: Optional[Cliente]
) -> None:
    actor_id = actor.id if actor else None
    nuevo = ticket.estado
    if nuevo == "en_proceso":
        quien = actor.nombre if actor else "Un técnico"
        asunto, parrafo = "estamos trabajando en él", f"{quien}, del equipo de soporte, ya está trabajando en tu ticket."
    elif nuevo == "resuelto":
        asunto = "fue resuelto"
        parrafo = (
            "Tu ticket quedó resuelto. Si el problema sigue, respóndenos en el chat del ticket "
            "o crea uno nuevo."
        )
    elif nuevo == "cancelado":
        asunto = "fue cancelado"
        parrafo = "El equipo de soporte canceló tu ticket."
        if ticket.motivo_cancelacion:
            parrafo += f"\nMotivo: {ticket.motivo_cancelacion}"
    elif nuevo == "abierto" and anterior in ("resuelto", "cancelado"):
        asunto, parrafo = "se reabrió", "Tu ticket se reabrió y el equipo de soporte lo volverá a revisar."
    else:
        return
    _al_solicitante(tareas, session, ticket, actor_id, asunto, parrafo)


def _duracion(segundos: int) -> str:
    horas = abs(segundos) // 3600
    if horas < 24:
        return f"{horas} h"
    return f"{horas // 24} d {horas % 24} h"


def sla_pausado(tareas: BackgroundTasks, session: Session, ticket: Ticket, actor: Cliente, pausa: PausaSla) -> None:
    from app.services.sla import MOTIVOS_PAUSA  # aquí para evitar un import circular

    motivo = MOTIVOS_PAUSA.get(pausa.motivo, pausa.motivo)
    detalle = f"\n{pausa.detalle}" if pausa.detalle else ""
    _al_solicitante(
        tareas, session, ticket, actor.id, "en pausa",
        f"El equipo de soporte puso en pausa el plazo de tu ticket. Motivo: {motivo}.{detalle}\n\n"
        "El tiempo de atención no corre mientras dure la pausa; te avisaremos cuando se reanude.",
    )


def sla_reanudado(tareas: BackgroundTasks, session: Session, ticket: Ticket, actor: Cliente) -> None:
    _al_solicitante(
        tareas, session, ticket, actor.id, "se reanudó la atención",
        "La pausa terminó y el plazo de tu ticket volvió a correr.",
    )


def sla_alerta(session: Session, ticket: Ticket, restante_segundos: int, tipo: str) -> None:
    """Aviso directo (lo llama el revisor periódico, sin BackgroundTasks) al técnico
    asignado, o a los administradores si el ticket no tiene técnico."""
    if ticket.tecnico_id is not None:
        destinos = [p for p in [session.get(Cliente, ticket.tecnico_id)] if p is not None and p.activo]
    else:
        destinos = list(
            session.exec(select(Cliente).where(Cliente.rol == "administrador", Cliente.activo == True))  # noqa: E712
        )
    if tipo == "vencido":
        asunto = "plazo vencido"
        parrafo = f"El plazo de atención de este ticket venció hace {_duracion(restante_segundos)}."
    else:
        asunto = "plazo por vencer"
        parrafo = f"Al plazo de atención de este ticket le quedan {_duracion(restante_segundos)}."
    for persona in destinos:
        cuerpo = (
            f"Hola {_primer_nombre(persona.nombre)},\n\n{parrafo}\n\n"
            f"Ticket #{ticket.id} · {ticket.categoria or ticket.categoria_predicha or 'Sin categoría'} · "
            f"Prioridad {ticket.prioridad}\n«{_extracto(ticket.texto)}»\n\n"
            f"Ábrelo aquí: {_enlace(ticket, True, persona.rol)}\n\n— Mesa de ayuda MinutoDesk"
        )
        correo.enviar_correo(persona.email, f"Ticket #{ticket.id}: {asunto}", cuerpo)


def mensaje_nuevo(tareas: BackgroundTasks, session: Session, ticket: Ticket, autor: Cliente, texto: str) -> None:
    if autor.id == ticket.cliente_id:
        _al_tecnico(
            tareas, session, ticket, autor.id, "nuevo mensaje del usuario",
            f"{autor.nombre} escribió en el chat del ticket:\n\n«{_extracto(texto)}»",
        )
    else:
        _al_solicitante(
            tareas, session, ticket, autor.id, "nuevo mensaje de soporte",
            f"{autor.nombre}, del equipo de soporte, te escribió:\n\n«{_extracto(texto)}»",
        )

"""Correos que avisan de lo que pasa en un ticket.

A quien abrió el ticket: que se recibió, cada cambio de estado (en proceso, resuelto,
cancelado, reabierto), las pausas del plazo y cada mensaje del equipo de soporte. Al
técnico: que le asignaron un ticket, cada mensaje que escribe el usuario y los avisos de
plazo (por vencer y vencido).

Nunca se avisa a la persona de lo que hizo ella misma, ni a cuentas desactivadas, ni
por tickets de la carga masiva (quien los pidió no tiene cuenta). Los correos se envían
en segundo plano (BackgroundTasks) para no demorar la respuesta de la aplicación; si el
SMTP falla, quedan guardados en backend/correos_enviados/ como los demás. El aspecto
(HTML con la identidad del portal) lo pone plantilla_correo.Correo.
"""
from typing import Optional

from fastapi import BackgroundTasks
from sqlmodel import Session, select

from app.models import Cliente, PausaSla, Ticket
from app.services import correo
from app.services.catalogos import TIPOS
from app.services.plantilla_correo import Correo

MAX_EXTRACTO = 300
TITULO_TIPO = {t["nombre"]: t["titulo"] for t in TIPOS}


def _enlace(ticket: Ticket, para_personal: bool, rol: str = "tecnico") -> str:
    base = correo.base_frontend()
    if para_personal:
        seccion = "admin" if rol == "administrador" else "tecnico"
        return f"{base}/{seccion}/tickets/{ticket.id}"
    return f"{base}/usuario/tickets/{ticket.id}"


def _extracto(texto: str) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= MAX_EXTRACTO else texto[: MAX_EXTRACTO - 1] + "…"


def _primer_nombre(nombre: str) -> str:
    return (nombre or "").split()[0] if nombre else ""


def _rotulo(ticket: Ticket) -> str:
    tipo = TITULO_TIPO.get(ticket.tipo or ticket.tipo_predicho or "")
    return f"Ticket #{ticket.id}" + (f" · {tipo}" if tipo else "")


def _ficha(ticket: Ticket) -> list[tuple[str, str]]:
    return [
        ("Categoría", ticket.categoria or ticket.categoria_predicha or "Sin categoría"),
        ("Prioridad", ticket.prioridad),
        ("Creado", f"{ticket.creado_en:%d/%m/%Y %H:%M}"),
    ]


def _destinatario(session: Session, cliente_id: Optional[int], actor_id: Optional[int]) -> Optional[Cliente]:
    if cliente_id is None or cliente_id == actor_id:
        return None
    persona = session.get(Cliente, cliente_id)
    if persona is None or not persona.activo or not persona.email:
        return None
    return persona


def _al_solicitante(
    tareas: BackgroundTasks,
    session: Session,
    ticket: Ticket,
    actor_id: Optional[int],
    asunto: str,
    titulo: str,
    parrafos: list[str],
    etiqueta: str,
    tono: str,
    cita: Optional[str] = None,
    cita_rotulo: Optional[str] = None,
) -> None:
    if ticket.solicitante_externo:
        return
    persona = _destinatario(session, ticket.cliente_id, actor_id)
    if persona is None:
        return
    mensaje = Correo(
        asunto=f"Ticket #{ticket.id}: {asunto}",
        rotulo=_rotulo(ticket),
        titulo=titulo,
        etiqueta=etiqueta,
        tono=tono,
        saludo=f"Hola {_primer_nombre(persona.nombre)},",
        parrafos=parrafos,
        cita=cita or _extracto(ticket.texto),
        cita_rotulo=cita_rotulo or "Tu solicitud",
        boton="Ver mi ticket",
        enlace=_enlace(ticket, False),
        nota="Puedes responder al equipo desde el chat del ticket en el portal.",
    )
    tareas.add_task(correo.enviar, persona.email, mensaje)


def _correo_tecnico(persona: Cliente, ticket: Ticket, asunto: str, titulo: str, parrafos: list[str],
                    etiqueta: str, tono: str, cita: Optional[str] = None, cita_rotulo: Optional[str] = None) -> Correo:
    return Correo(
        asunto=f"Ticket #{ticket.id}: {asunto}",
        rotulo=_rotulo(ticket),
        titulo=titulo,
        etiqueta=etiqueta,
        tono=tono,
        saludo=f"Hola {_primer_nombre(persona.nombre)},",
        parrafos=parrafos,
        cita=cita or _extracto(ticket.texto),
        cita_rotulo=cita_rotulo or "La solicitud",
        datos=_ficha(ticket),
        boton="Abrir el ticket",
        enlace=_enlace(ticket, True, persona.rol),
    )


def _al_tecnico(
    tareas: BackgroundTasks,
    session: Session,
    ticket: Ticket,
    actor_id: Optional[int],
    asunto: str,
    titulo: str,
    parrafos: list[str],
    etiqueta: str,
    tono: str,
    cita: Optional[str] = None,
    cita_rotulo: Optional[str] = None,
) -> None:
    persona = _destinatario(session, ticket.tecnico_id, actor_id)
    if persona is None:
        return
    tareas.add_task(
        correo.enviar, persona.email, _correo_tecnico(persona, ticket, asunto, titulo, parrafos, etiqueta, tono, cita, cita_rotulo)
    )


# ---------- eventos ----------

def ticket_creado(tareas: BackgroundTasks, session: Session, ticket: Ticket) -> None:
    _al_solicitante(
        tareas, session, ticket, None,
        asunto="lo recibimos",
        titulo="Recibimos tu solicitud",
        etiqueta="Nuevo",
        tono="info",
        parrafos=[
            "Tu ticket quedó registrado. El equipo de soporte lo revisará y te avisaremos por este "
            "medio cada vez que haya novedades.",
        ],
    )
    _al_tecnico(
        tareas, session, ticket, None,
        asunto="te lo asignaron",
        titulo="Tienes un ticket nuevo",
        etiqueta="Asignado",
        tono="info",
        parrafos=["Se creó un ticket nuevo y, por su sistema, quedaste como técnico sugerido."],
    )


def tecnico_asignado(tareas: BackgroundTasks, session: Session, ticket: Ticket, actor: Cliente) -> None:
    _al_tecnico(
        tareas, session, ticket, actor.id,
        asunto="te lo asignaron",
        titulo="Te asignaron un ticket",
        etiqueta="Asignado",
        tono="info",
        parrafos=[f"{actor.nombre} te asignó este ticket."],
    )


def estado_cambiado(
    tareas: BackgroundTasks, session: Session, ticket: Ticket, anterior: str, actor: Optional[Cliente]
) -> None:
    actor_id = actor.id if actor else None
    nuevo = ticket.estado
    if nuevo == "en_proceso":
        quien = actor.nombre if actor else "Un técnico"
        datos = dict(
            asunto="estamos trabajando en él",
            titulo="Ya estamos trabajando en tu ticket",
            etiqueta="En proceso",
            tono="info",
            parrafos=[f"{quien}, del equipo de soporte, tomó tu ticket y ya está trabajando en él."],
        )
    elif nuevo == "resuelto":
        datos = dict(
            asunto="fue resuelto",
            titulo="Tu ticket quedó resuelto",
            etiqueta="Resuelto",
            tono="ok",
            parrafos=["Obra entregada: tu ticket quedó resuelto. Si el problema sigue, respóndenos en el chat del ticket o crea uno nuevo."],
        )
    elif nuevo == "cancelado":
        datos = dict(
            asunto="fue cancelado",
            titulo="Tu ticket fue cancelado",
            etiqueta="Cancelado",
            tono="pausa",
            parrafos=["El equipo de soporte canceló tu ticket."],
            cita=ticket.motivo_cancelacion or None,
            cita_rotulo="Motivo" if ticket.motivo_cancelacion else None,
        )
    elif nuevo == "abierto" and anterior in ("resuelto", "cancelado"):
        datos = dict(
            asunto="se reabrió",
            titulo="Tu ticket se reabrió",
            etiqueta="Nuevo",
            tono="info",
            parrafos=["Tu ticket se reabrió y el equipo de soporte lo volverá a revisar."],
        )
    else:
        return
    _al_solicitante(tareas, session, ticket, actor_id, **datos)


def _duracion(segundos: int) -> str:
    horas = abs(segundos) // 3600
    if horas < 24:
        return f"{horas} h"
    return f"{horas // 24} d {horas % 24} h"


def sla_pausado(tareas: BackgroundTasks, session: Session, ticket: Ticket, actor: Cliente, pausa: PausaSla) -> None:
    from app.services.sla import MOTIVOS_PAUSA  # aquí para evitar un import circular

    motivo = MOTIVOS_PAUSA.get(pausa.motivo, pausa.motivo)
    _al_solicitante(
        tareas, session, ticket, actor.id,
        asunto="en pausa",
        titulo="Pusimos en pausa el plazo de tu ticket",
        etiqueta="En pausa",
        tono="pausa",
        parrafos=[
            f"El equipo de soporte puso en pausa el plazo de atención. Motivo: {motivo}.",
            "El tiempo de atención no corre mientras dure la pausa; te avisaremos cuando se reanude.",
        ],
        cita=pausa.detalle or motivo,
        cita_rotulo="Detalle de la pausa",
    )


def sla_reanudado(tareas: BackgroundTasks, session: Session, ticket: Ticket, actor: Cliente) -> None:
    _al_solicitante(
        tareas, session, ticket, actor.id,
        asunto="se reanudó la atención",
        titulo="Se reanudó la atención de tu ticket",
        etiqueta="En tiempo",
        tono="ok",
        parrafos=["La pausa terminó y el plazo de tu ticket volvió a correr."],
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
        datos = dict(
            asunto="plazo vencido",
            titulo="Este ticket se pasó del plazo",
            etiqueta="Vencido",
            tono="alerta",
            parrafos=[f"El plazo de atención venció hace {_duracion(restante_segundos)} y el ticket sigue abierto."],
        )
    else:
        datos = dict(
            asunto="plazo por vencer",
            titulo="Este ticket está por vencer",
            etiqueta="Por vencer",
            tono="aviso",
            parrafos=[f"Al plazo de atención le quedan {_duracion(restante_segundos)}."],
        )
    for persona in destinos:
        correo.enviar(persona.email, _correo_tecnico(persona, ticket, **datos))


def mensaje_nuevo(tareas: BackgroundTasks, session: Session, ticket: Ticket, autor: Cliente, texto: str) -> None:
    if autor.id == ticket.cliente_id:
        _al_tecnico(
            tareas, session, ticket, autor.id,
            asunto="nuevo mensaje del usuario",
            titulo=f"{autor.nombre} te escribió",
            etiqueta="Mensaje",
            tono="info",
            parrafos=["El usuario escribió en el chat del ticket:"],
            cita=_extracto(texto),
            cita_rotulo="Mensaje",
        )
    else:
        _al_solicitante(
            tareas, session, ticket, autor.id,
            asunto="nuevo mensaje de soporte",
            titulo="Tienes un mensaje de soporte",
            etiqueta="Mensaje",
            tono="info",
            parrafos=[f"{autor.nombre}, del equipo de soporte, te escribió:"],
            cita=_extracto(texto),
            cita_rotulo="Mensaje",
        )

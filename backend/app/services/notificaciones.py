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
    elif nuevo == "resuelto" and ticket.resuelto_por == "tecnico" and _pide_confirmacion(ticket):
        datos = dict(
            asunto="¿quedó resuelto?",
            titulo="Marcamos tu ticket como resuelto",
            etiqueta="Resuelto",
            tono="ok",
            parrafos=[
                "Obra entregada: el equipo de soporte marcó tu ticket como resuelto. Entra a tu ticket y "
                "cuéntanos si quedó bien: si no, vuelve al mismo técnico sin que tengas que crear otro.",
                "Si no nos respondes en unos días, lo daremos por resuelto. "
                "Ahí mismo califica la atención de 1 a 5 estrellas: toma diez segundos.",
            ],
        )
    elif nuevo == "resuelto":
        datos = dict(
            asunto="fue resuelto",
            titulo="Tu ticket quedó resuelto",
            etiqueta="Resuelto",
            tono="ok",
            parrafos=[
                "Obra entregada: tu ticket quedó resuelto. Si el problema sigue, respóndenos en el chat del ticket o crea uno nuevo.",
                "¿Cómo te atendimos? Entra a tu ticket y califica la atención de 1 a 5 estrellas: "
                "toma diez segundos y nos ayuda a mejorar.",
            ],
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


def _pide_confirmacion(ticket: Ticket) -> bool:
    from app.services.confirmacion import aplica  # aquí para evitar un import circular

    return aplica(ticket)


def no_quedo_resuelto(tareas: BackgroundTasks, session: Session, ticket: Ticket, autor: Cliente, comentario: str) -> None:
    _al_tecnico(
        tareas, session, ticket, autor.id,
        asunto="no quedó resuelto",
        titulo=f"{autor.nombre} dice que no quedó resuelto",
        etiqueta="Reabierto",
        tono="alerta",
        parrafos=["El ticket que marcaste como resuelto volvió a «En proceso» y sigue a tu cargo."],
        cita=_extracto(comentario),
        cita_rotulo="Qué sigue fallando",
    )


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


# ---------- avisos agregados el 14/11/2026 ----------
# Cada uno sale por una sola acción de una persona (nunca en lote) y respeta las mismas
# reglas: no a quien hizo la acción, no a cuentas desactivadas, no por tickets de la carga
# masiva.

def _a_persona(tareas: BackgroundTasks, session: Session, ticket: Ticket, persona_id: Optional[int],
               actor_id: Optional[int], **datos) -> None:
    persona = _destinatario(session, persona_id, actor_id)
    if persona is None:
        return
    if persona.id == ticket.cliente_id and persona.rol == "usuario":
        if ticket.solicitante_externo:
            return
        _al_solicitante(tareas, session, ticket, actor_id, **datos)
        return
    tareas.add_task(correo.enviar, persona.email, _correo_tecnico(persona, ticket, **datos))


def aprobacion_solicitada(tareas: BackgroundTasks, session: Session, ticket: Ticket, actor: Cliente) -> None:
    _al_solicitante(
        tareas, session, ticket, actor.id,
        asunto="espera una aprobación",
        titulo="Tu ticket espera una aprobación",
        etiqueta="En pausa",
        tono="pausa",
        parrafos=[
            "Para continuar, el equipo de soporte pidió la aprobación de otra persona (por ejemplo, "
            "el jefe del área). Mientras llega la respuesta, el plazo de atención queda en pausa.",
            "Te avisaremos apenas la respondan.",
        ],
    )


def aprobacion_respondida(tareas: BackgroundTasks, session: Session, ticket: Ticket, aprobacion, actor: Cliente) -> None:
    aprobada = aprobacion.estado == "aprobada"
    resultado = "aprobada" if aprobada else "rechazada"
    datos = dict(
        asunto=f"aprobación {resultado}",
        etiqueta="Aprobada" if aprobada else "Rechazada",
        tono="ok" if aprobada else "alerta",
        cita=aprobacion.comentario or aprobacion.descripcion,
        cita_rotulo="Comentario" if aprobacion.comentario else "Qué se pidió aprobar",
    )
    _a_persona(
        tareas, session, ticket, aprobacion.solicitada_por_id, actor.id,
        titulo=f"{actor.nombre} respondió la aprobación",
        parrafos=[f"La aprobación que pediste fue {resultado}. El plazo del ticket vuelve a correr."],
        **datos,
    )
    _al_solicitante(
        tareas, session, ticket, actor.id,
        titulo=f"La aprobación de tu ticket fue {resultado}",
        parrafos=[
            f"La aprobación que necesitaba tu ticket fue {resultado} y el equipo de soporte continúa "
            "con la atención. El plazo volvió a correr."
        ],
        **datos,
    )


def resuelto_con_minutito(tareas: BackgroundTasks, session: Session, ticket: Ticket) -> None:
    _al_tecnico(
        tareas, session, ticket, ticket.cliente_id,
        asunto="lo resolvió Minutito",
        titulo="El usuario resolvió el ticket con Minutito",
        etiqueta="Resuelto",
        tono="ok",
        parrafos=["El usuario confirmó que la ayuda de Minutito resolvió su problema: ya no hace falta atenderlo."],
    )


# Si quien abrió el ticket sube archivos justo al crearlo, el correo de «ticket nuevo» ya
# basta: no se manda uno por archivo.
MINUTOS_GRACIA_ADJUNTOS = 5


def adjunto_subido(tareas: BackgroundTasks, session: Session, ticket: Ticket, autor: Cliente, nombre: str) -> None:
    from datetime import datetime, timedelta

    if autor.id == ticket.cliente_id:
        if datetime.now() - ticket.creado_en < timedelta(minutes=MINUTOS_GRACIA_ADJUNTOS):
            return
        _al_tecnico(
            tareas, session, ticket, autor.id,
            asunto="nuevo archivo del usuario",
            titulo=f"{autor.nombre} adjuntó un archivo",
            etiqueta="Archivo",
            tono="info",
            parrafos=["El usuario subió un archivo al ticket:"],
            cita=nombre,
            cita_rotulo="Archivo",
        )
    else:
        _al_solicitante(
            tareas, session, ticket, autor.id,
            asunto="nuevo archivo de soporte",
            titulo="Soporte adjuntó un archivo a tu ticket",
            etiqueta="Archivo",
            tono="info",
            parrafos=[f"{autor.nombre}, del equipo de soporte, subió un archivo a tu ticket:"],
            cita=nombre,
            cita_rotulo="Archivo",
        )


def prioridad_cambiada(tareas: BackgroundTasks, session: Session, ticket: Ticket, anterior: str, actor: Cliente,
                       dias: Optional[int]) -> None:
    plazo = f" Con esta prioridad, el plazo de atención es de {dias} {'día' if dias == 1 else 'días'}." if dias else ""
    _al_solicitante(
        tareas, session, ticket, actor.id,
        asunto="cambió la prioridad",
        titulo="Cambió la prioridad de tu ticket",
        etiqueta=ticket.prioridad,
        tono="info",
        parrafos=[f"El equipo de soporte cambió la prioridad de tu ticket de {anterior} a {ticket.prioridad}.{plazo}"],
    )


def encuesta_recibida(tareas: BackgroundTasks, session: Session, ticket: Ticket, estrellas: int,
                      comentario: Optional[str], autor: Cliente) -> None:
    _al_tecnico(
        tareas, session, ticket, autor.id,
        asunto=f"calificación {estrellas} de 5",
        titulo=f"{autor.nombre} calificó tu atención con {estrellas} de 5",
        etiqueta="★" * estrellas + "☆" * (5 - estrellas),
        tono="ok" if estrellas >= 4 else ("aviso" if estrellas == 3 else "alerta"),
        parrafos=["Quien abrió el ticket respondió la encuesta de satisfacción."],
        cita=comentario or None,
        cita_rotulo="Comentario" if comentario else None,
    )


def contrasena_cambiada(tareas: BackgroundTasks, persona: Cliente) -> None:
    """Aviso de seguridad: si no fue la persona, que lo sepa enseguida."""
    from app.services.plantilla_correo import Correo as _Correo

    if not persona.activo or not persona.email:
        return
    tareas.add_task(
        correo.enviar,
        persona.email,
        _Correo(
            asunto="Tu contraseña de MinutoDesk cambió",
            rotulo="Tu cuenta",
            titulo="Se cambió tu contraseña",
            etiqueta="Seguridad",
            tono="aviso",
            saludo=f"Hola {_primer_nombre(persona.nombre)},",
            parrafos=[
                "La contraseña de tu cuenta de MinutoDesk acaba de cambiar y se cerraron las demás sesiones abiertas.",
                "Si fuiste tú, no tienes que hacer nada.",
            ],
            boton="Ir a MinutoDesk",
            enlace=f"{correo.base_frontend()}/login",
            nota="Si no fuiste tú, usa «¿Olvidaste tu contraseña?» enseguida y avisa al administrador.",
        ),
    )

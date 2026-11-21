"""Plazos de seguimiento basados en el SLA (aprobados por Fátima el 20/11/2026).

Todos se cuentan como el plazo del ticket (días calendario sin los feriados de Ecuador)
y salen de los días de SLA según su tipo y prioridad:

1. **Ticket tomado sin avance.** Si el técnico a cargo no hace nada (escribir, cambiar el
   estado, pausar, pedir una aprobación...) durante el 25 % del SLA, con tope de 2 días,
   se avisa a los administradores para que lo reasignen. Un aviso por cada tramo sin avance.
2. **Usuario que no contesta.** Cuando el técnico pausa el plazo con «Esperando al
   usuario», se le recuerda al usuario a la mitad de la espera y el ticket se cancela solo
   («sin respuesta del usuario», no cuenta como resuelto) al cumplirse la espera completa:
   los días de SLA, con un mínimo de 2 y un tope de 5. El cierre nunca llega sin que el
   recordatorio haya salido antes con su margen. Si el usuario escribe, la pausa termina.
3. **Aprobaciones pendientes.** Mientras un ticket espera una aprobación nada de lo
   anterior avanza (no se avisa, no se recuerda ni se cierra). En cambio, al aprobador se
   le recuerda cada 25 % del SLA (tope 2 días), hasta 3 veces; con el último recordatorio
   también se avisa a quien la pidió, para que lo siga por otra vía.

Cualquier otra pausa con motivo (proveedor, desarrollo...) también congela el punto 1.

Solo aplica a los tickets creados desde ACTIVO_DESDE: los que ya estaban cargados no se
tocan. Lo que se hace queda en AvisoAutomatico (para no repetirlo y para la campanita).
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import (
    Adjunto,
    Aprobacion,
    AsignacionTicket,
    AvisoAutomatico,
    Cliente,
    ConfirmacionCierre,
    HistorialEstadoTicket,
    MensajeTicket,
    PausaSla,
    Ticket,
)
from app.schemas import AvisoRead
from app.services import confirmacion, correo, notificaciones, sla, toma

ACTIVO_DESDE = datetime.fromisoformat(os.getenv("SEGUIMIENTO_DESDE", "2026-11-19T00:00:00"))

DIA = sla.SEGUNDOS_DIA
DIAS_SIN_SLA = 7  # si el ticket aún no tiene tipo o prioridad válidos
FRACCION_SIN_AVANCE = 0.25
TOPE_SIN_AVANCE = 2 * DIA
ESPERA_USUARIO_MIN = 2 * DIA
ESPERA_USUARIO_TOPE = 5 * DIA
FRACCION_APROBACION = 0.25
TOPE_APROBACION = 2 * DIA
MAX_RECORDATORIOS_APROBACION = 3
ABIERTOS = ("abierto", "en_proceso")
MOTIVO_CIERRE = "Sin respuesta del usuario"


class _Inmediato:
    """Las funciones de notificaciones esperan BackgroundTasks; el revisor periódico ya
    corre en segundo plano, así que envía al momento."""

    @staticmethod
    def add_task(funcion, *args, **kwargs):
        funcion(*args, **kwargs)


# ---------- plazos ----------

def _plazo_segundos(ticket: Ticket) -> float:
    return (sla.dias_de_plazo(ticket) or DIAS_SIN_SLA) * DIA


def umbral_sin_avance(ticket: Ticket) -> float:
    return min(FRACCION_SIN_AVANCE * _plazo_segundos(ticket), TOPE_SIN_AVANCE)


def espera_usuario(ticket: Ticket) -> float:
    """Espera total antes de cerrar por falta de respuesta (el recordatorio va a la mitad)."""
    return min(max(_plazo_segundos(ticket), ESPERA_USUARIO_MIN), ESPERA_USUARIO_TOPE)


def intervalo_aprobacion(ticket: Ticket) -> float:
    return min(FRACCION_APROBACION * _plazo_segundos(ticket), TOPE_APROBACION)


def _transcurrido(desde: datetime, ahora: datetime) -> float:
    return sla.segundos_habiles(desde, ahora)


# ---------- estado del ticket ----------

def aplica(ticket: Ticket) -> bool:
    return ticket.creado_en >= ACTIVO_DESDE and ticket.estado in ABIERTOS


def aprobaciones_pendientes(session: Session, ticket_id: int) -> list[Aprobacion]:
    return list(
        session.exec(
            select(Aprobacion).where(Aprobacion.ticket_id == ticket_id, Aprobacion.estado == "pendiente")
        )
    )


def _ultima_respuesta_aprobacion(session: Session, ticket_id: int) -> Optional[datetime]:
    return session.exec(
        select(func.max(Aprobacion.respondida_en)).where(Aprobacion.ticket_id == ticket_id)
    ).first()


def ultima_actividad(session: Session, ticket: Ticket) -> Optional[datetime]:
    """Lo último que hizo el personal en el ticket (o el momento en que se tomó)."""
    tid, cliente = ticket.id, ticket.cliente_id
    fechas = [
        ticket.tomado_en,
        session.exec(
            select(func.max(MensajeTicket.creado_en)).where(MensajeTicket.ticket_id == tid, MensajeTicket.autor_id != cliente)
        ).first(),
        session.exec(
            select(func.max(HistorialEstadoTicket.fecha)).where(
                HistorialEstadoTicket.ticket_id == tid,
                HistorialEstadoTicket.cambiado_por_id.is_not(None),
                HistorialEstadoTicket.cambiado_por_id != cliente,
            )
        ).first(),
        session.exec(select(func.max(PausaSla.inicio)).where(PausaSla.ticket_id == tid)).first(),
        session.exec(select(func.max(PausaSla.fin)).where(PausaSla.ticket_id == tid)).first(),
        session.exec(select(func.max(Aprobacion.creado_en)).where(Aprobacion.ticket_id == tid)).first(),
        _ultima_respuesta_aprobacion(session, tid),
        session.exec(select(func.max(AsignacionTicket.fecha)).where(AsignacionTicket.ticket_id == tid)).first(),
        session.exec(
            select(func.max(Adjunto.creado_en)).where(Adjunto.ticket_id == tid, Adjunto.subido_por_id != cliente)
        ).first(),
    ]
    fechas = [f for f in fechas if f is not None]
    return max(fechas) if fechas else None


def _registro(session: Session, ticket_id: int, tipo: str, **filtros) -> Optional[AvisoAutomatico]:
    consulta = select(AvisoAutomatico).where(AvisoAutomatico.ticket_id == ticket_id, AvisoAutomatico.tipo == tipo)
    for campo, valor in filtros.items():
        consulta = consulta.where(getattr(AvisoAutomatico, campo) == valor)
    return session.exec(consulta.order_by(AvisoAutomatico.enviado_en.desc(), AvisoAutomatico.id.desc())).first()


def _anotar(session: Session, ticket_id: int, tipo: str, ahora: datetime, referencia_id=None, desde=None) -> None:
    session.add(
        AvisoAutomatico(ticket_id=ticket_id, tipo=tipo, referencia_id=referencia_id, desde=desde, enviado_en=ahora)
    )


def _administradores(session: Session) -> list[Cliente]:
    return list(session.exec(select(Cliente).where(Cliente.rol == "administrador", Cliente.activo == True)))  # noqa: E712


def _duracion(segundos: float) -> str:
    horas = int(segundos // 3600)
    if horas < 24:
        return f"{horas} h"
    dias, resto = divmod(horas, 24)
    return f"{dias} {'día' if dias == 1 else 'días'}" + (f" y {resto} h" if resto else "")


# ---------- 1. sin avance ----------

def _revisar_sin_avance(session: Session, ticket: Ticket, ahora: datetime) -> int:
    if not toma.esta_tomado(ticket):
        return 0
    desde = ultima_actividad(session, ticket)
    if desde is None:
        return 0
    transcurrido = _transcurrido(desde, ahora)
    if transcurrido < umbral_sin_avance(ticket) or _registro(session, ticket.id, "sin_avance", desde=desde):
        return 0
    tecnico = session.get(Cliente, ticket.tecnico_id)
    nombre = tecnico.nombre if tecnico else "El técnico a cargo"
    for admin in _administradores(session):
        if admin.id == ticket.tecnico_id:
            continue
        correo.enviar(
            admin.email,
            notificaciones._correo_tecnico(
                admin, ticket,
                asunto="sin avance",
                titulo="Este ticket no tiene avance",
                etiqueta="Sin avance",
                tono="alerta",
                parrafos=[
                    f"{nombre} tomó este ticket y no hay movimiento desde hace {_duracion(transcurrido)} "
                    f"(el límite es el 25 % de su plazo, como máximo 2 días).",
                    "Revisa si hay que reasignarlo a otro técnico.",
                ],
            ),
        )
    _anotar(session, ticket.id, "sin_avance", ahora, referencia_id=ticket.tecnico_id, desde=desde)
    return 1


# ---------- 2. usuario que no contesta ----------

def _cerrar_sin_respuesta(session: Session, ticket: Ticket, pausa: PausaSla, ahora: datetime, espera: float) -> None:
    motivo = f"{MOTIVO_CIERRE}: se cerró solo tras {_duracion(espera)} esperando su información."
    estado_anterior = ticket.estado
    sla.reanudar(session, pausa, None, ahora)  # la pausa termina con el cierre
    ticket.estado = "cancelado"
    ticket.motivo_cancelacion = motivo
    ticket.cerrado_en = ahora
    ticket.resuelto_por = None
    session.add(ticket)
    session.add(
        HistorialEstadoTicket(
            ticket_id=ticket.id, estado_anterior=estado_anterior, estado_nuevo="cancelado", motivo=motivo, fecha=ahora
        )
    )
    tareas = _Inmediato()
    notificaciones._al_solicitante(
        tareas, session, ticket, None,
        asunto="se cerró por falta de respuesta",
        titulo="Cerramos tu ticket por falta de respuesta",
        etiqueta="Cancelado",
        tono="alerta",
        parrafos=[
            f"El equipo de soporte te pidió información y no recibimos respuesta en {_duracion(espera)}, "
            "así que el ticket se cerró solo.",
            "Si el problema sigue, crea un ticket nuevo y menciona este número.",
        ],
    )
    notificaciones._al_tecnico(
        tareas, session, ticket, None,
        asunto="cerrado por falta de respuesta",
        titulo="El ticket se cerró por falta de respuesta",
        etiqueta="Cancelado",
        tono="alerta",
        parrafos=[f"El usuario no respondió en {_duracion(espera)} y el ticket se canceló solo."],
    )


def _revisar_usuario(session: Session, ticket: Ticket, pausa: PausaSla, ahora: datetime) -> int:
    if pausa.motivo != "usuario" or pausa.aprobacion_id is not None:
        return 0
    respuesta = _ultima_respuesta_aprobacion(session, ticket.id)
    desde = max(pausa.inicio, respuesta) if respuesta else pausa.inicio
    espera = espera_usuario(ticket)
    transcurrido = _transcurrido(desde, ahora)
    recordatorio = _registro(session, ticket.id, "recordatorio_usuario", referencia_id=pausa.id)
    if recordatorio is not None and recordatorio.desde == desde:
        # El cierre exige que el recordatorio haya tenido su media espera de margen.
        if transcurrido >= espera and _transcurrido(recordatorio.enviado_en, ahora) >= espera / 2:
            _cerrar_sin_respuesta(session, ticket, pausa, ahora, espera)
            _anotar(session, ticket.id, "cierre_sin_respuesta", ahora, referencia_id=pausa.id, desde=desde)
            return 1
        return 0
    if transcurrido < espera / 2:
        return 0
    notificaciones._al_solicitante(
        _Inmediato(), session, ticket, None,
        asunto="esperamos tu respuesta",
        titulo="Tu ticket espera tu respuesta",
        etiqueta="Esperando tu respuesta",
        tono="aviso",
        parrafos=[
            "Para continuar, el equipo de soporte necesita información tuya. Respóndele desde el chat del ticket.",
            f"Si no recibimos respuesta en {_duracion(espera / 2)}, el ticket se cerrará solo.",
        ],
        cita=pausa.detalle or "Información pendiente",
        cita_rotulo="Lo que te pidieron",
    )
    _anotar(session, ticket.id, "recordatorio_usuario", ahora, referencia_id=pausa.id, desde=desde)
    return 1


def reanudar_si_responde(session: Session, ticket: Ticket, autor: Cliente) -> Optional[PausaSla]:
    """Si quien abrió el ticket escribe mientras se esperaba su respuesta, el plazo vuelve a
    correr. No hace commit."""
    if autor.id != ticket.cliente_id or ticket.creado_en < ACTIVO_DESDE:
        return None
    pausa = sla.pausa_activa(session, ticket.id)
    if pausa is None or pausa.motivo != "usuario" or pausa.aprobacion_id is not None:
        return None
    sla.reanudar(session, pausa, autor.id)
    return pausa


# ---------- 3. aprobaciones pendientes ----------

def _revisar_aprobaciones(session: Session, ticket: Ticket, pendientes: list[Aprobacion], ahora: datetime) -> int:
    enviados = 0
    intervalo = intervalo_aprobacion(ticket)
    for aprobacion in pendientes:
        hechos = session.exec(
            select(func.count(AvisoAutomatico.id)).where(
                AvisoAutomatico.ticket_id == ticket.id,
                AvisoAutomatico.tipo == "recordatorio_aprobacion",
                AvisoAutomatico.referencia_id == aprobacion.id,
            )
        ).one()
        if hechos >= MAX_RECORDATORIOS_APROBACION:
            continue
        transcurrido = _transcurrido(aprobacion.creado_en, ahora)
        if transcurrido < (hechos + 1) * intervalo:
            continue
        aprobador = session.get(Cliente, aprobacion.aprobador_id)
        if aprobador is not None and aprobador.activo and aprobador.email:
            correo.enviar(
                aprobador.email,
                notificaciones.Correo(
                    asunto=f"Recordatorio: aprobación pendiente del ticket #{ticket.id}",
                    rotulo=f"Ticket #{ticket.id}",
                    titulo="Tu aprobación sigue pendiente",
                    etiqueta="Aprobación pendiente",
                    tono="aviso",
                    saludo=f"Hola {notificaciones._primer_nombre(aprobador.nombre)},",
                    parrafos=[
                        f"Hace {_duracion(transcurrido)} el equipo de soporte te pidió una aprobación y el "
                        "ticket está detenido hasta que respondas."
                    ],
                    cita=aprobacion.descripcion,
                    cita_rotulo="Qué hay que aprobar",
                    boton="Revisar y responder",
                    enlace=f"{correo.base_frontend()}/login",
                    nota="La encontrarás en la sección «Aprobaciones» del portal.",
                ),
            )
        if hechos + 1 == MAX_RECORDATORIOS_APROBACION:
            notificaciones._a_persona(
                _Inmediato(), session, ticket, aprobacion.solicitada_por_id, None,
                asunto="aprobación sin respuesta",
                titulo="La aprobación que pediste sigue sin respuesta",
                etiqueta="Aprobación pendiente",
                tono="alerta",
                parrafos=[
                    f"{aprobador.nombre if aprobador else 'El aprobador'} no ha respondido en "
                    f"{_duracion(transcurrido)} pese a {MAX_RECORDATORIOS_APROBACION} recordatorios. "
                    "Te sugerimos contactarlo por otra vía."
                ],
                cita=aprobacion.descripcion,
                cita_rotulo="Qué se pidió aprobar",
            )
        _anotar(session, ticket.id, "recordatorio_aprobacion", ahora, referencia_id=aprobacion.id)
        enviados += 1
    return enviados


# ---------- revisor ----------

def revisar(session: Session, ahora: Optional[datetime] = None) -> int:
    """Aplica los tres plazos a los tickets abiertos. Devuelve cuántas acciones hizo."""
    ahora = ahora or datetime.now()
    tickets = session.exec(
        select(Ticket).where(Ticket.estado.in_(ABIERTOS), Ticket.creado_en >= ACTIVO_DESDE)
    ).all()
    hechas = 0
    for ticket in tickets:
        pendientes = aprobaciones_pendientes(session, ticket.id)
        if pendientes:
            hechas += _revisar_aprobaciones(session, ticket, pendientes, ahora)
            continue  # esperando una aprobación: nada más avanza
        pausa = sla.pausa_activa(session, ticket.id)
        if pausa is not None:
            hechas += _revisar_usuario(session, ticket, pausa, ahora)
            continue  # en pausa con motivo: no cuenta como «sin avance»
        hechas += _revisar_sin_avance(session, ticket, ahora)
    hechas += confirmacion.vencer(session, ahora)  # «¿Quedó resuelto?» sin respuesta: se confirma solo
    session.commit()
    return hechas


# ---------- campanita ----------

def avisos_para(session: Session, usuario: Cliente) -> list[AvisoRead]:
    """Avisos vigentes para la campanita: al administrador, los tickets sin avance que
    siguen igual; al usuario, los tickets donde soporte espera su respuesta."""
    avisos: list[AvisoRead] = []
    if usuario.rol == "administrador":
        desde = datetime.now() - timedelta(days=14)
        registros = session.exec(
            select(AvisoAutomatico).where(AvisoAutomatico.tipo == "sin_avance", AvisoAutomatico.enviado_en >= desde)
        ).all()
        for r in registros:
            ticket = session.get(Ticket, r.ticket_id)
            if ticket is None or not aplica(ticket) or ticket.tecnico_id != r.referencia_id:
                continue
            if ultima_actividad(session, ticket) != r.desde:
                continue  # ya hubo movimiento
            tecnico = session.get(Cliente, ticket.tecnico_id) if ticket.tecnico_id else None
            avisos.append(
                AvisoRead(
                    tipo="sin_avance",
                    ticket_id=ticket.id,
                    texto=f"{tecnico.nombre if tecnico else 'El técnico'} no ha avanzado: {ticket.texto[:120]}",
                    fecha=r.enviado_en,
                )
            )
    elif usuario.rol == "usuario":
        por_confirmar = session.exec(
            select(ConfirmacionCierre, Ticket)
            .join(Ticket, Ticket.id == ConfirmacionCierre.ticket_id)
            .where(
                Ticket.cliente_id == usuario.id,
                Ticket.estado == "resuelto",
                ConfirmacionCierre.respuesta == "pendiente",
            )
        ).all()
        for c, ticket in por_confirmar:
            avisos.append(
                AvisoRead(tipo="confirmar_cierre", ticket_id=ticket.id, texto=ticket.texto[:160], fecha=c.resuelto_en)
            )
        pausas = session.exec(
            select(PausaSla, Ticket)
            .join(Ticket, Ticket.id == PausaSla.ticket_id)
            .where(
                Ticket.cliente_id == usuario.id,
                Ticket.estado.in_(ABIERTOS),
                Ticket.creado_en >= ACTIVO_DESDE,
                PausaSla.fin.is_(None),
                PausaSla.motivo == "usuario",
            )
        ).all()
        for pausa, ticket in pausas:
            avisos.append(
                AvisoRead(
                    tipo="esperando_respuesta",
                    ticket_id=ticket.id,
                    texto=pausa.detalle or "Soporte necesita información para continuar.",
                    fecha=pausa.inicio,
                )
            )
    return avisos

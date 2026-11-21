"""Chat entre el usuario y el equipo de soporte, y pasos de aprobación.

En el chat escriben la persona que abrió el ticket y el personal (técnico o
administrador). El personal puede pedir una aprobación a otra persona (p. ej. el jefe
del área): esa persona la ve en «Aprobaciones» y la aprueba o rechaza con un
comentario. Mientras haya una aprobación pendiente el ticket no se puede resolver.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Aprobacion, Cliente, HistorialEstadoTicket, MensajeTicket, Ticket
from app.schemas import (
    AprobacionCreate,
    AprobacionRead,
    AprobacionResponder,
    AvisoRead,
    ConversacionRead,
    MensajeCreate,
    MensajeRead,
)
from app.services import correo, notificaciones, seguimiento, sla, toma
from app.services.auth import es_personal, obtener_usuario_actual, requerir_personal

router = APIRouter()

MAX_MENSAJE = 2000
MIN_DESCRIPCION = 5
MAX_DESCRIPCION = 1000
MAX_COMENTARIO = 500
ESTADOS_CERRADOS = ("resuelto", "cancelado")


def _ticket_accesible(session: Session, ticket_id: int, usuario: Cliente) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if not es_personal(usuario) and ticket.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este ticket")
    return ticket


def _nombres(session: Session, ids: set[int]) -> dict[int, Cliente]:
    if not ids:
        return {}
    return {c.id: c for c in session.exec(select(Cliente).where(Cliente.id.in_(ids))).all()}


def _a_aprobacion_read(
    a: Aprobacion, personas: dict[int, Cliente], ticket: Optional[Ticket] = None
) -> AprobacionRead:
    def nombre(cid: int) -> str:
        return personas[cid].nombre if cid in personas else "—"

    return AprobacionRead(
        id=a.id,
        ticket_id=a.ticket_id,
        solicitada_por_id=a.solicitada_por_id,
        solicitada_por=nombre(a.solicitada_por_id),
        aprobador_id=a.aprobador_id,
        aprobador=nombre(a.aprobador_id),
        descripcion=a.descripcion,
        estado=a.estado,
        comentario=a.comentario,
        creado_en=a.creado_en,
        respondida_en=a.respondida_en,
        ticket_texto=ticket.texto if ticket else None,
        ticket_estado=ticket.estado if ticket else None,
        ticket_solicitante=nombre(ticket.cliente_id) if ticket else None,
    )


def hay_aprobacion_pendiente(session: Session, ticket_id: int) -> bool:
    return (
        session.exec(
            select(Aprobacion.id).where(
                Aprobacion.ticket_id == ticket_id, Aprobacion.estado == "pendiente"
            )
        ).first()
        is not None
    )


@router.get("/tickets/{ticket_id}/conversacion", response_model=ConversacionRead)
def ver_conversacion(
    ticket_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    _ticket_accesible(session, ticket_id, usuario)
    mensajes = session.exec(
        select(MensajeTicket)
        .where(MensajeTicket.ticket_id == ticket_id)
        .order_by(MensajeTicket.creado_en, MensajeTicket.id)
    ).all()
    aprobaciones = session.exec(
        select(Aprobacion)
        .where(Aprobacion.ticket_id == ticket_id)
        .order_by(Aprobacion.creado_en, Aprobacion.id)
    ).all()
    ids = {m.autor_id for m in mensajes}
    for a in aprobaciones:
        ids.update((a.aprobador_id, a.solicitada_por_id))
    personas = _nombres(session, ids)
    return ConversacionRead(
        mensajes=[
            MensajeRead(
                id=m.id,
                ticket_id=m.ticket_id,
                autor_id=m.autor_id,
                autor=personas[m.autor_id].nombre if m.autor_id in personas else "—",
                autor_es_personal=m.autor_id in personas and es_personal(personas[m.autor_id]),
                texto=m.texto,
                creado_en=m.creado_en,
            )
            for m in mensajes
        ],
        aprobaciones=[_a_aprobacion_read(a, personas) for a in aprobaciones],
    )


@router.post("/tickets/{ticket_id}/mensajes", response_model=MensajeRead)
def enviar_mensaje(
    ticket_id: int,
    data: MensajeCreate,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    ticket = _ticket_accesible(session, ticket_id, usuario)
    if ticket.estado in ESTADOS_CERRADOS:
        raise HTTPException(status_code=409, detail=f"Este ticket ya está {ticket.estado}.")
    texto = data.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Escribe un mensaje.")
    if len(texto) > MAX_MENSAJE:
        raise HTTPException(
            status_code=400, detail=f"El mensaje es demasiado largo (máximo {MAX_MENSAJE} caracteres)."
        )
    if es_personal(usuario) and ticket.cliente_id != usuario.id:
        # La primera respuesta del personal toma el ticket. Si ya lo atiende otro
        # técnico, solo esa persona (o un administrador) le escribe al solicitante.
        toma.exigir_que_pueda_atender(session, ticket, usuario)
        if toma.tomar_si_libre(session, ticket, usuario, via="respuesta") and ticket.estado == "abierto":
            # Ya hay alguien trabajando en él. El solicitante no recibe otro correo por el
            # cambio de estado: ya le llega el del mensaje.
            ticket.estado = "en_proceso"
            session.add(ticket)
            session.add(
                HistorialEstadoTicket(
                    ticket_id=ticket.id, estado_anterior="abierto", estado_nuevo="en_proceso", cambiado_por_id=usuario.id
                )
            )
    mensaje = MensajeTicket(ticket_id=ticket.id, autor_id=usuario.id, texto=texto)
    session.add(mensaje)
    # Si soporte esperaba la respuesta del usuario, el plazo vuelve a correr.
    seguimiento.reanudar_si_responde(session, ticket, usuario)
    session.commit()
    session.refresh(mensaje)
    notificaciones.mensaje_nuevo(tareas, session, ticket, usuario, texto)
    return MensajeRead(
        id=mensaje.id,
        ticket_id=mensaje.ticket_id,
        autor_id=usuario.id,
        autor=usuario.nombre,
        autor_es_personal=es_personal(usuario),
        texto=mensaje.texto,
        creado_en=mensaje.creado_en,
    )


@router.post("/tickets/{ticket_id}/aprobaciones", response_model=AprobacionRead)
def solicitar_aprobacion(
    ticket_id: int,
    data: AprobacionCreate,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    ticket = _ticket_accesible(session, ticket_id, usuario)
    toma.exigir_que_pueda_atender(session, ticket, usuario)
    if ticket.estado in ESTADOS_CERRADOS:
        raise HTTPException(status_code=409, detail=f"Este ticket ya está {ticket.estado}.")
    descripcion = data.descripcion.strip()
    if len(descripcion) < MIN_DESCRIPCION:
        raise HTTPException(status_code=400, detail="Describe qué hay que aprobar (mínimo 5 caracteres).")
    if len(descripcion) > MAX_DESCRIPCION:
        raise HTTPException(
            status_code=400, detail=f"La descripción es demasiado larga (máximo {MAX_DESCRIPCION} caracteres)."
        )
    aprobador = session.get(Cliente, data.aprobador_id)
    if aprobador is None or not aprobador.activo:
        raise HTTPException(status_code=400, detail="La persona elegida no existe o está desactivada.")
    if aprobador.id in (usuario.id, ticket.cliente_id):
        raise HTTPException(
            status_code=400,
            detail="La aprobación debe darla otra persona, no quien la pide ni quien abrió el ticket.",
        )

    aprobacion = Aprobacion(
        ticket_id=ticket.id,
        solicitada_por_id=usuario.id,
        aprobador_id=aprobador.id,
        descripcion=descripcion,
    )
    session.add(aprobacion)
    session.commit()
    session.refresh(aprobacion)
    # Mientras se espera la aprobación, el plazo del ticket no corre.
    if sla.pausar_por_aprobacion(session, ticket, aprobacion, usuario.id) is not None:
        session.commit()
    tareas.add_task(
        correo.enviar_aviso_aprobacion, aprobador.email, aprobador.nombre, ticket.id, descripcion
    )
    notificaciones.aprobacion_solicitada(tareas, session, ticket, usuario)
    return _a_aprobacion_read(aprobacion, {usuario.id: usuario, aprobador.id: aprobador})


@router.get("/aprobaciones", response_model=list[AprobacionRead])
def mis_aprobaciones(
    estado: Optional[str] = None,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Las aprobaciones que le pidieron a esta persona (cualquier rol)."""
    consulta = select(Aprobacion).where(Aprobacion.aprobador_id == usuario.id)
    if estado is not None:
        consulta = consulta.where(Aprobacion.estado == estado)
    aprobaciones = session.exec(consulta.order_by(Aprobacion.creado_en.desc())).all()
    tickets = {
        t.id: t
        for t in session.exec(
            select(Ticket).where(Ticket.id.in_({a.ticket_id for a in aprobaciones}))
        ).all()
    } if aprobaciones else {}
    ids = {usuario.id} | {a.solicitada_por_id for a in aprobaciones}
    ids |= {t.cliente_id for t in tickets.values()}
    personas = _nombres(session, ids)
    return [_a_aprobacion_read(a, personas, tickets.get(a.ticket_id)) for a in aprobaciones]


@router.get("/avisos", response_model=list[AvisoRead])
def mis_avisos(usuario: Cliente = Depends(obtener_usuario_actual), session: Session = Depends(get_session)):
    """Lo que espera a esta persona: aprobaciones pendientes y tickets abiertos cuyo último
    mensaje es de la otra parte. No guarda «leídos»: el aviso se va al responder."""
    avisos = [
        AvisoRead(tipo="aprobacion", ticket_id=a.ticket_id, texto=a.descripcion[:160], fecha=a.creado_en)
        for a in session.exec(
            select(Aprobacion).where(Aprobacion.aprobador_id == usuario.id, Aprobacion.estado == "pendiente")
        ).all()
    ]
    # El usuario espera respuesta en sus tickets; el personal, en los que tiene asignados.
    propios = Ticket.tecnico_id == usuario.id if es_personal(usuario) else Ticket.cliente_id == usuario.id
    tickets = session.exec(select(Ticket).where(propios, Ticket.estado.not_in(ESTADOS_CERRADOS))).all()
    for t in tickets:
        ultimo = session.exec(
            select(MensajeTicket)
            .where(MensajeTicket.ticket_id == t.id)
            .order_by(MensajeTicket.creado_en.desc(), MensajeTicket.id.desc())
        ).first()
        if ultimo is not None and ultimo.autor_id != usuario.id:
            avisos.append(AvisoRead(tipo="mensaje", ticket_id=t.id, texto=ultimo.texto[:160], fecha=ultimo.creado_en))
    avisos += seguimiento.avisos_para(session, usuario)  # sin avance / esperando tu respuesta
    return sorted(avisos, key=lambda a: a.fecha, reverse=True)


@router.post("/aprobaciones/{aprobacion_id}/responder", response_model=AprobacionRead)
def responder_aprobacion(
    aprobacion_id: int,
    data: AprobacionResponder,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    aprobacion = session.get(Aprobacion, aprobacion_id)
    # Para quien no es el aprobador, la aprobación «no existe» (no se revela nada).
    if aprobacion is None or aprobacion.aprobador_id != usuario.id:
        raise HTTPException(status_code=404, detail="Aprobación no encontrada")
    if aprobacion.estado != "pendiente":
        raise HTTPException(status_code=409, detail="Esta aprobación ya fue respondida.")
    ticket = session.get(Ticket, aprobacion.ticket_id)
    if ticket is not None and ticket.estado == "cancelado":
        raise HTTPException(status_code=409, detail="El ticket fue cancelado: ya no hace falta responder.")
    comentario = (data.comentario or "").strip() or None
    if comentario and len(comentario) > MAX_COMENTARIO:
        raise HTTPException(
            status_code=400, detail=f"El comentario es demasiado largo (máximo {MAX_COMENTARIO} caracteres)."
        )
    if not data.aprobada and not comentario:
        raise HTTPException(status_code=400, detail="Indica el motivo del rechazo.")

    aprobacion.estado = "aprobada" if data.aprobada else "rechazada"
    aprobacion.comentario = comentario
    aprobacion.respondida_en = datetime.now()
    session.add(aprobacion)
    session.commit()
    session.refresh(aprobacion)
    if ticket is not None and sla.reanudar_tras_aprobacion(session, ticket, usuario.id) is not None:
        session.commit()
    if ticket is not None:
        # Un solo correo a cada uno (quien pidió la aprobación y quien abrió el ticket) con el
        # resultado; ya incluye que el plazo vuelve a correr.
        notificaciones.aprobacion_respondida(tareas, session, ticket, aprobacion, usuario)
    personas = _nombres(session, {aprobacion.solicitada_por_id, usuario.id, ticket.cliente_id})
    return _a_aprobacion_read(aprobacion, personas, ticket)

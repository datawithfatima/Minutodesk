"""Conversaciones con Minutito, antes de que exista un ticket.

La persona conversa; si se resuelve lo confirma (cuenta como resolución autónoma y no
se crea ticket). Si no, pide un borrador del ticket armado con la conversación y lo crea
con POST /tickets indicando `conversacion_id`.
"""
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente, ConversacionMinutito, EventoGamificacion, MensajeMinutito, Ticket
from app.schemas import (
    BorradorTicket,
    ConversacionMinutitoRead,
    MensajeCreate,
    MensajeMinutitoRead,
    ResumenConversacion,
)
from app.services import minutito_chat
from app.services.auth import es_personal, obtener_usuario_actual
from app.services.classifier import sugerir

router = APIRouter()

MAX_MENSAJE = 2000
PUNTOS_AUTOSERVICIO = 10
NO_DISPONIBLE = "Minutito no está disponible en este momento. Puedes crear el ticket y lo atenderá el equipo."

# Cada respuesta ocupa el procesador varios segundos: se limita cuánto puede pedir cada
# persona para que nadie sature el equipo. Vive en memoria (se reinicia con el backend).
MAX_MENSAJES_POR_MINUTO = 20
mensajes_recientes: dict[int, list[datetime]] = {}
respondiendo: set[int] = set()  # personas con una respuesta de Minutito en curso


def _controlar_ritmo(usuario_id: int) -> None:
    if usuario_id in respondiendo:
        raise HTTPException(status_code=429, detail="Espera a que Minutito termine de responder.")
    desde = datetime.now() - timedelta(minutes=1)
    recientes = [t for t in mensajes_recientes.get(usuario_id, []) if t > desde]
    if len(recientes) >= MAX_MENSAJES_POR_MINUTO:
        raise HTTPException(status_code=429, detail="Enviaste muchos mensajes seguidos. Espera un minuto.")
    mensajes_recientes[usuario_id] = recientes + [datetime.now()]


def _conversacion(session: Session, conversacion_id: int, usuario: Cliente) -> ConversacionMinutito:
    conversacion = session.get(ConversacionMinutito, conversacion_id)
    if conversacion is None or (conversacion.cliente_id != usuario.id and not es_personal(usuario)):
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return conversacion


def _propia_y_abierta(session: Session, conversacion_id: int, usuario: Cliente) -> ConversacionMinutito:
    conversacion = _conversacion(session, conversacion_id, usuario)
    if conversacion.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="Solo quien inició la conversación puede continuarla")
    if conversacion.estado != "abierta":
        raise HTTPException(status_code=409, detail="Esta conversación ya terminó. Empieza una nueva.")
    return conversacion


def _mensajes(session: Session, conversacion_id: int) -> list[MensajeMinutito]:
    return session.exec(
        select(MensajeMinutito)
        .where(MensajeMinutito.conversacion_id == conversacion_id)
        .order_by(MensajeMinutito.creado_en, MensajeMinutito.id)
    ).all()


def _a_lectura(session: Session, c: ConversacionMinutito) -> ConversacionMinutitoRead:
    return ConversacionMinutitoRead(
        id=c.id,
        estado=c.estado,
        ticket_id=c.ticket_id,
        creado_en=c.creado_en,
        cerrado_en=c.cerrado_en,
        mensajes=[MensajeMinutitoRead.model_validate(m, from_attributes=True) for m in _mensajes(session, c.id)],
    )


@router.post("/conversaciones", response_model=ConversacionMinutitoRead)
def nueva_conversacion(
    usuario: Cliente = Depends(obtener_usuario_actual), session: Session = Depends(get_session)
):
    conversacion = ConversacionMinutito(cliente_id=usuario.id)
    session.add(conversacion)
    session.commit()
    session.refresh(conversacion)
    return _a_lectura(session, conversacion)


@router.get("/conversaciones", response_model=list[ResumenConversacion])
def mis_conversaciones(
    estado: Optional[str] = None,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Las conversaciones de la persona (p. ej. las resueltas, para «Mi histórico»)."""
    consulta = select(ConversacionMinutito).where(ConversacionMinutito.cliente_id == usuario.id)
    if estado is not None:
        consulta = consulta.where(ConversacionMinutito.estado == estado)
    resultado = []
    for c in session.exec(consulta.order_by(ConversacionMinutito.creado_en.desc())).all():
        primera = next((m.texto for m in _mensajes(session, c.id) if m.rol == "usuario"), "")
        resultado.append(
            ResumenConversacion(
                id=c.id, estado=c.estado, ticket_id=c.ticket_id, creado_en=c.creado_en,
                cerrado_en=c.cerrado_en, primera_pregunta=primera[:300],
            )
        )
    return resultado


@router.get("/conversaciones/actual", response_model=Optional[ConversacionMinutitoRead])
def conversacion_actual(
    usuario: Cliente = Depends(obtener_usuario_actual), session: Session = Depends(get_session)
):
    """La última conversación abierta de la persona, para retomarla al volver a la página."""
    conversacion = session.exec(
        select(ConversacionMinutito)
        .where(ConversacionMinutito.cliente_id == usuario.id, ConversacionMinutito.estado == "abierta")
        .order_by(ConversacionMinutito.creado_en.desc())
    ).first()
    return _a_lectura(session, conversacion) if conversacion else None


@router.get("/conversaciones/{conversacion_id}", response_model=ConversacionMinutitoRead)
def ver_conversacion(
    conversacion_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    return _a_lectura(session, _conversacion(session, conversacion_id, usuario))


@router.post("/conversaciones/{conversacion_id}/mensajes")
def enviar_mensaje(
    conversacion_id: int,
    data: MensajeCreate,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Responde en vivo: una línea JSON por fragmento ({"delta": ...}) y al final
    {"fin": true, "ofrece_ticket": ...}, o {"error": ...} si Minutito no está disponible."""
    conversacion = _propia_y_abierta(session, conversacion_id, usuario)
    texto = data.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Escribe un mensaje.")
    if len(texto) > MAX_MENSAJE:
        raise HTTPException(status_code=400, detail=f"El mensaje es demasiado largo (máximo {MAX_MENSAJE} caracteres).")
    _controlar_ritmo(usuario.id)
    usuario_id = usuario.id
    respondiendo.add(usuario_id)

    session.add(MensajeMinutito(conversacion_id=conversacion.id, rol="usuario", texto=texto))
    session.commit()
    historial = [(m.rol, m.texto) for m in _mensajes(session, conversacion.id)]
    motor = session.get_bind()  # la sesión de la petición se cierra antes de terminar de transmitir

    def transmitir():
        partes = []
        try:
            try:
                for delta in minutito_chat.responder_en_vivo(historial):
                    partes.append(delta)
                    yield json.dumps({"delta": delta}, ensure_ascii=False) + "\n"
            except minutito_chat.MinutitoNoDisponible:
                yield json.dumps({"error": NO_DISPONIBLE}, ensure_ascii=False) + "\n"
                return
            respuesta, ofrece = minutito_chat.separar_marca("".join(partes))
            with Session(motor) as s:
                guardado = MensajeMinutito(conversacion_id=conversacion_id, rol="minutito", texto=respuesta or "…")
                s.add(guardado)
                s.commit()
                s.refresh(guardado)
                yield json.dumps({"fin": True, "ofrece_ticket": ofrece, "mensaje_id": guardado.id}) + "\n"
        finally:
            respondiendo.discard(usuario_id)  # también si la persona cerró la página a mitad

    return StreamingResponse(transmitir(), media_type="application/x-ndjson")


@router.post("/conversaciones/{conversacion_id}/resolver", response_model=ConversacionMinutitoRead)
def marcar_resuelta(
    conversacion_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """La persona confirma que Minutito resolvió su problema: cuenta como resolución
    autónoma, no se crea ticket y suma puntos de autoservicio."""
    conversacion = _propia_y_abierta(session, conversacion_id, usuario)
    if not any(m.rol == "minutito" for m in _mensajes(session, conversacion.id)):
        raise HTTPException(status_code=400, detail="Primero conversa con Minutito.")
    conversacion.estado = "resuelta"
    conversacion.cerrado_en = datetime.now()
    session.add(conversacion)
    session.add(
        EventoGamificacion(cliente_id=usuario.id, puntos_otorgados=PUNTOS_AUTOSERVICIO, motivo="Resuelto con Minutito")
    )
    usuario.puntos += PUNTOS_AUTOSERVICIO
    session.add(usuario)
    session.commit()
    session.refresh(conversacion)
    return _a_lectura(session, conversacion)


@router.post("/conversaciones/{conversacion_id}/borrador", response_model=BorradorTicket)
def borrador_de_ticket(
    conversacion_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Descripción del ticket redactada con la conversación y la clasificación que propone el SVM."""
    conversacion = _propia_y_abierta(session, conversacion_id, usuario)
    historial = [(m.rol, m.texto) for m in _mensajes(session, conversacion.id)]
    if not any(r == "usuario" for r, _ in historial):
        raise HTTPException(status_code=400, detail="Cuéntale primero a Minutito qué necesitas.")
    texto = minutito_chat.resumir_para_ticket(historial)[:5000]
    return BorradorTicket(texto=texto, sugerencia=sugerir(texto))


def enlazar_ticket(session: Session, conversacion_id: int, usuario: Cliente, ticket: Ticket) -> None:
    """Lo usa la creación de tickets: la conversación queda cerrada y unida al ticket."""
    conversacion = _propia_y_abierta(session, conversacion_id, usuario)
    conversacion.estado = "ticket"
    conversacion.ticket_id = ticket.id
    conversacion.cerrado_en = datetime.now()
    session.add(conversacion)


@router.get("/tickets/{ticket_id}", response_model=Optional[ConversacionMinutitoRead])
def conversacion_de_ticket(
    ticket_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """La conversación con Minutito que dio origen al ticket, si la hubo."""
    ticket = session.get(Ticket, ticket_id)
    if ticket is None or (ticket.cliente_id != usuario.id and not es_personal(usuario)):
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    conversacion = session.exec(
        select(ConversacionMinutito).where(ConversacionMinutito.ticket_id == ticket_id)
    ).first()
    return _a_lectura(session, conversacion) if conversacion else None

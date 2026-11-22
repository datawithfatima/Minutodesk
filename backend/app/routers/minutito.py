"""Conversaciones con Minutito, antes de que exista un ticket.

La persona conversa; si se resuelve lo confirma (cuenta como resolución autónoma y no
se crea ticket). Si no, pide un borrador del ticket armado con la conversación y lo crea
con POST /tickets indicando `conversacion_id`.
"""
import json
import os
import shutil
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlmodel import Session, func, select

from app.database import get_session
from app.models import (
    Adjunto,
    Cliente,
    ConversacionMinutito,
    EventoGamificacion,
    ImagenMinutito,
    MensajeMinutito,
    Ticket,
)
from app.routers import adjuntos
from app.schemas import (
    BorradorTicket,
    ConversacionMinutitoRead,
    ImagenMinutitoRead,
    MensajeCreate,
    MensajeMinutitoRead,
    ResumenConversacion,
)
from app.services import minutito_chat, ocr
from app.services.casos_resueltos import casos_parecidos
from app.services.auth import es_personal, obtener_usuario_actual
from app.services.catalogos import MAX_ADJUNTOS, MAX_BYTES_ADJUNTO
from app.services.classifier import sugerir
from app.services.cuerpo import leer_cuerpo_limitado

router = APIRouter()

MAX_MENSAJE = 2000
PUNTOS_AUTOSERVICIO = 10
# Tope diario de conversaciones que dan puntos. Pasado el tope, «Minutito lo resolvió» sigue
# contando como resolución autónoma, pero ya no suma puntos: así los puntos no premian
# marcar como resueltas conversaciones que no lo estaban.
MAX_RESUELTAS_CON_PUNTOS_POR_DIA = 3
MOTIVO_AUTOSERVICIO = "Resuelto con Minutito"
# Las imágenes viajan al ticket como adjuntos, así que comparten su límite por ticket.
EXTENSIONES_IMAGEN = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
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


def _imagenes(session: Session, conversacion_id: int) -> list[ImagenMinutito]:
    return session.exec(
        select(ImagenMinutito)
        .where(ImagenMinutito.conversacion_id == conversacion_id)
        .order_by(ImagenMinutito.creado_en, ImagenMinutito.id)
    ).all()


def _imagenes_por_mensaje(session: Session, conversacion_id: int) -> dict[int, list[ImagenMinutito]]:
    por_mensaje: dict[int, list[ImagenMinutito]] = {}
    for imagen in _imagenes(session, conversacion_id):
        if imagen.mensaje_id is not None:
            por_mensaje.setdefault(imagen.mensaje_id, []).append(imagen)
    return por_mensaje


def _nota_de_imagen(imagen: ImagenMinutito) -> str:
    """Lo que el modelo recibe de una imagen: el texto que el OCR leyó en ella, o el aviso
    de que no se leyó ninguno. Nunca ve la imagen en sí."""
    if imagen.texto_leido:
        return (
            f"[Adjunté una captura ({imagen.nombre_original}). Este es el texto que se lee en ella:\n"
            f"{imagen.texto_leido}\n"
            "Nota para el asistente: solo tienes el texto de la imagen, no la ves; úsalo para entender el problema.]"
        )
    return (
        f"[Adjunté una captura ({imagen.nombre_original}), pero no se pudo leer texto en ella. "
        "Nota para el asistente: no puedes ver la imagen. Si necesitas lo que muestra, pide que te lo "
        "describa; el equipo de sistemas la verá si se crea el ticket.]"
    )


def _historial(session: Session, conversacion_id: int) -> list[tuple[str, str]]:
    """Pares (rol, texto) para el modelo. El modelo solo lee texto: a un mensaje con
    imágenes se le agrega el texto leído en ellas (o el aviso de que no lo tiene)."""
    imagenes = _imagenes_por_mensaje(session, conversacion_id)
    historial = []
    for m in _mensajes(session, conversacion_id):
        partes = [m.texto] + [_nota_de_imagen(i) for i in imagenes.get(m.id, [])]
        historial.append((m.rol, "\n\n".join(p for p in partes if p)))
    return historial


def _a_lectura(session: Session, c: ConversacionMinutito) -> ConversacionMinutitoRead:
    imagenes = _imagenes_por_mensaje(session, c.id)
    return ConversacionMinutitoRead(
        id=c.id,
        estado=c.estado,
        ticket_id=c.ticket_id,
        creado_en=c.creado_en,
        cerrado_en=c.cerrado_en,
        mensajes=[
            MensajeMinutitoRead(
                id=m.id,
                rol=m.rol,
                texto=m.texto,
                creado_en=m.creado_en,
                imagenes=[i.nombre_original for i in imagenes.get(m.id, [])],
            )
            for m in _mensajes(session, c.id)
        ],
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
    pendientes = [i for i in _imagenes(session, conversacion.id) if i.mensaje_id is None]
    if not texto and not pendientes:
        raise HTTPException(status_code=400, detail="Escribe un mensaje.")
    if len(texto) > MAX_MENSAJE:
        raise HTTPException(status_code=400, detail=f"El mensaje es demasiado largo (máximo {MAX_MENSAJE} caracteres).")
    _controlar_ritmo(usuario.id)
    usuario_id = usuario.id
    # Desde aquí la persona queda marcada como «con respuesta en curso» y se desmarca en el
    # `finally` del generador. Observación de la auditoría: si algo falla antes de que la
    # transmisión empiece, la marca no se quita hasta reiniciar el backend.
    respondiendo.add(usuario_id)

    nuevo = MensajeMinutito(conversacion_id=conversacion.id, rol="usuario", texto=texto)
    session.add(nuevo)
    session.flush()
    for imagen in pendientes:  # las imágenes subidas para este mensaje quedan unidas a él
        imagen.mensaje_id = nuevo.id
        session.add(imagen)
    session.commit()
    historial = _historial(session, conversacion.id)
    # Los casos parecidos se buscan con lo que escribió la persona y el texto de sus capturas,
    # sin las notas para el modelo.
    leidos = _imagenes_por_mensaje(session, conversacion.id)
    escritos = [
        " ".join([m.texto] + [i.texto_leido or "" for i in leidos.get(m.id, [])]).strip()
        for m in _mensajes(session, conversacion.id)
        if m.rol == "usuario"
    ]
    casos = casos_parecidos(session, [e for e in escritos if e][-3:])
    motor = session.get_bind()  # la sesión de la petición se cierra antes de terminar de transmitir

    def transmitir():
        partes = []
        try:
            try:
                for delta in minutito_chat.responder_en_vivo(historial, casos=casos):
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


@router.post("/conversaciones/{conversacion_id}/imagenes", response_model=ImagenMinutitoRead)
async def subir_imagen(
    conversacion_id: int,
    request: Request,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Imagen para el próximo mensaje (cuerpo crudo, nombre en X-Nombre-Archivo, igual que
    los adjuntos de tickets). Minutito recibe el texto que se lee en ella; si se crea el
    ticket, la imagen pasa a ser adjunto."""
    conversacion = _propia_y_abierta(session, conversacion_id, usuario)
    nombre = adjuntos._limpiar_nombre(request.headers.get("x-nombre-archivo"))
    if os.path.splitext(nombre)[1].lower() not in EXTENSIONES_IMAGEN:
        raise HTTPException(status_code=400, detail="Solo se pueden adjuntar imágenes (PNG, JPG, GIF, WEBP o BMP).")
    cantidad = session.exec(
        select(func.count()).select_from(ImagenMinutito).where(ImagenMinutito.conversacion_id == conversacion.id)
    ).one()
    if cantidad >= MAX_ADJUNTOS:
        raise HTTPException(status_code=409, detail=f"Una conversación admite hasta {MAX_ADJUNTOS} imágenes.")
    contenido = await leer_cuerpo_limitado(request, MAX_BYTES_ADJUNTO, "La imagen supera el límite de 10 MB.")
    if not contenido:
        raise HTTPException(status_code=400, detail="La imagen está vacía.")

    adjuntos.DIRECTORIO_ARCHIVOS.mkdir(parents=True, exist_ok=True)
    guardado = uuid.uuid4().hex
    (adjuntos.DIRECTORIO_ARCHIVOS / guardado).write_bytes(contenido)
    # Se lee el texto al subirla (menos de un segundo), así está listo al enviar el mensaje.
    texto_leido = await run_in_threadpool(ocr.leer_texto, adjuntos.DIRECTORIO_ARCHIVOS / guardado)
    imagen = ImagenMinutito(
        conversacion_id=conversacion.id,
        nombre_original=nombre,
        archivo=guardado,
        tamano=len(contenido),
        texto_leido=texto_leido or None,
    )
    session.add(imagen)
    session.commit()
    session.refresh(imagen)
    return ImagenMinutitoRead(id=imagen.id, nombre=imagen.nombre_original)


@router.delete("/conversaciones/{conversacion_id}/imagenes/{imagen_id}", status_code=204)
def quitar_imagen(
    conversacion_id: int,
    imagen_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Quita una imagen que todavía no se envió con un mensaje."""
    conversacion = _propia_y_abierta(session, conversacion_id, usuario)
    imagen = session.get(ImagenMinutito, imagen_id)
    if imagen is None or imagen.conversacion_id != conversacion.id or imagen.mensaje_id is not None:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    (adjuntos.DIRECTORIO_ARCHIVOS / imagen.archivo).unlink(missing_ok=True)
    session.delete(imagen)
    session.commit()


@router.post("/conversaciones/{conversacion_id}/resolver", response_model=ConversacionMinutitoRead)
def marcar_resuelta(
    conversacion_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """La persona confirma que Minutito resolvió su problema: cuenta como resolución
    autónoma, no se crea ticket y suma puntos de autoservicio.

    Este clic alimenta el indicador del objetivo 2 (reportes.py). Para que los puntos no
    incentiven a marcar conversaciones sin resolver, solo las primeras
    MAX_RESUELTAS_CON_PUNTOS_POR_DIA de cada día dan puntos."""
    conversacion = _propia_y_abierta(session, conversacion_id, usuario)
    if not any(m.rol == "minutito" for m in _mensajes(session, conversacion.id)):
        raise HTTPException(status_code=400, detail="Primero conversa con Minutito.")
    conversacion.estado = "resuelta"
    conversacion.cerrado_en = datetime.now()
    session.add(conversacion)
    inicio_del_dia = datetime.combine(conversacion.cerrado_en.date(), datetime.min.time())
    premiadas_hoy = session.exec(
        select(func.count())
        .select_from(EventoGamificacion)
        .where(
            EventoGamificacion.cliente_id == usuario.id,
            EventoGamificacion.motivo == MOTIVO_AUTOSERVICIO,
            EventoGamificacion.creado_en >= inicio_del_dia,
        )
    ).one()
    puntos = PUNTOS_AUTOSERVICIO if premiadas_hoy < MAX_RESUELTAS_CON_PUNTOS_POR_DIA else 0
    if puntos:
        session.add(EventoGamificacion(cliente_id=usuario.id, puntos_otorgados=puntos, motivo=MOTIVO_AUTOSERVICIO))
        usuario.puntos += puntos
        session.add(usuario)
    session.commit()
    session.refresh(conversacion)
    lectura = _a_lectura(session, conversacion)
    lectura.puntos_otorgados = puntos
    return lectura


@router.post("/conversaciones/{conversacion_id}/borrador", response_model=BorradorTicket)
def borrador_de_ticket(
    conversacion_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Descripción del ticket redactada con la conversación y la clasificación que propone el SVM."""
    conversacion = _propia_y_abierta(session, conversacion_id, usuario)
    historial = _historial(session, conversacion.id)
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
    # Las imágenes enviadas en la conversación pasan al ticket para que el técnico las vea.
    # Se copia el archivo: así quitar el adjunto del ticket no borra el de la conversación.
    enviadas = [i for i in _imagenes(session, conversacion.id) if i.mensaje_id is not None]
    for imagen in enviadas[:MAX_ADJUNTOS]:
        origen = adjuntos.DIRECTORIO_ARCHIVOS / imagen.archivo
        if not origen.is_file():
            continue
        copia = uuid.uuid4().hex
        shutil.copyfile(origen, adjuntos.DIRECTORIO_ARCHIVOS / copia)
        session.add(
            Adjunto(
                ticket_id=ticket.id,
                nombre_original=imagen.nombre_original,
                archivo=copia,
                tamano=imagen.tamano,
                subido_por_id=usuario.id,
            )
        )


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

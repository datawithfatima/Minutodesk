"""Archivos adjuntos de los tickets.

El archivo viaja como cuerpo crudo de la petición (sin multipart) con su nombre en la
cabecera X-Nombre-Archivo (codificado con %XX). En disco se guarda con un nombre
aleatorio y sin extensión, y se descarga siempre como archivo adjunto: nunca se
ejecuta ni se muestra dentro de la página.
"""
import os
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlmodel import Session, func, select

from app.database import get_session
from app.models import Adjunto, Cliente, Ticket
from app.schemas import AdjuntoRead, MensajeRespuesta
from app.services.auth import es_personal, obtener_usuario_actual
from app.services.catalogos import MAX_ADJUNTOS, MAX_BYTES_ADJUNTO, TIPOS_DE_ARCHIVO

router = APIRouter()

DIRECTORIO_ARCHIVOS = Path(__file__).resolve().parents[2] / "uploads"
LARGO_MAXIMO_NOMBRE = 150


def _ticket_accesible(session: Session, ticket_id: int, usuario: Cliente) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if not es_personal(usuario) and ticket.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este ticket")
    return ticket


def _limpiar_nombre(crudo: Optional[str]) -> str:
    nombre = unquote(crudo or "").replace("\\", "/").split("/")[-1].strip()
    nombre = "".join(c for c in nombre if c.isprintable())  # sin caracteres de control
    if not nombre or nombre.startswith("."):
        raise HTTPException(status_code=400, detail="El archivo no tiene un nombre válido.")
    if len(nombre) > LARGO_MAXIMO_NOMBRE:
        raiz, ext = os.path.splitext(nombre)
        nombre = raiz[: LARGO_MAXIMO_NOMBRE - len(ext)] + ext
    return nombre


def _a_lectura(a: Adjunto, nombres: dict[int, str]) -> AdjuntoRead:
    return AdjuntoRead(
        id=a.id,
        ticket_id=a.ticket_id,
        nombre_original=a.nombre_original,
        tamano=a.tamano,
        subido_por_id=a.subido_por_id,
        subido_por=nombres.get(a.subido_por_id, "—"),
        creado_en=a.creado_en,
    )


def _nombres(session: Session, adjuntos: list[Adjunto]) -> dict[int, str]:
    ids = {a.subido_por_id for a in adjuntos}
    if not ids:
        return {}
    return {c.id: c.nombre for c in session.exec(select(Cliente).where(Cliente.id.in_(ids))).all()}


@router.get("/tickets/{ticket_id}/adjuntos", response_model=list[AdjuntoRead])
def listar_adjuntos(
    ticket_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    _ticket_accesible(session, ticket_id, usuario)
    adjuntos = session.exec(
        select(Adjunto).where(Adjunto.ticket_id == ticket_id).order_by(Adjunto.creado_en, Adjunto.id)
    ).all()
    nombres = _nombres(session, adjuntos)
    return [_a_lectura(a, nombres) for a in adjuntos]


@router.post("/tickets/{ticket_id}/adjuntos", response_model=AdjuntoRead)
async def subir_adjunto(
    ticket_id: int,
    request: Request,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    ticket = _ticket_accesible(session, ticket_id, usuario)
    if ticket.estado in ("resuelto", "cancelado") and not es_personal(usuario):
        estado = "resuelto" if ticket.estado == "resuelto" else "cancelado"
        raise HTTPException(status_code=409, detail=f"Este ticket ya está {estado}: no admite más archivos.")

    nombre = _limpiar_nombre(request.headers.get("x-nombre-archivo"))
    extension = os.path.splitext(nombre)[1].lower()
    if extension not in TIPOS_DE_ARCHIVO:
        raise HTTPException(
            status_code=400,
            detail="Tipo de archivo no permitido. Se aceptan Word, Excel, PowerPoint, PDF, imágenes, video, audio y texto.",
        )

    declarado = request.headers.get("content-length")
    if declarado and declarado.isdigit() and int(declarado) > MAX_BYTES_ADJUNTO:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 10 MB.")

    cantidad = session.exec(
        select(func.count()).select_from(Adjunto).where(Adjunto.ticket_id == ticket_id)
    ).one()
    if cantidad >= MAX_ADJUNTOS:
        raise HTTPException(status_code=409, detail=f"Un ticket admite hasta {MAX_ADJUNTOS} archivos.")

    contenido = await request.body()
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(contenido) > MAX_BYTES_ADJUNTO:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 10 MB.")

    DIRECTORIO_ARCHIVOS.mkdir(parents=True, exist_ok=True)
    guardado = uuid.uuid4().hex
    (DIRECTORIO_ARCHIVOS / guardado).write_bytes(contenido)

    adjunto = Adjunto(
        ticket_id=ticket_id,
        nombre_original=nombre,
        archivo=guardado,
        tamano=len(contenido),
        subido_por_id=usuario.id,
    )
    session.add(adjunto)
    session.commit()
    session.refresh(adjunto)
    return _a_lectura(adjunto, {usuario.id: usuario.nombre})


@router.get("/adjuntos/{adjunto_id}")
def descargar_adjunto(
    adjunto_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    adjunto = session.get(Adjunto, adjunto_id)
    if adjunto is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    _ticket_accesible(session, adjunto.ticket_id, usuario)
    ruta = DIRECTORIO_ARCHIVOS / adjunto.archivo
    if not ruta.is_file():
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible")

    extension = os.path.splitext(adjunto.nombre_original)[1].lower()
    return FileResponse(
        ruta,
        media_type=TIPOS_DE_ARCHIVO.get(extension, "application/octet-stream"),
        filename=adjunto.nombre_original,  # Content-Disposition: attachment
        # nosniff: el navegador no adivina el tipo; no-store: un archivo privado no queda en caché.
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.delete("/adjuntos/{adjunto_id}", response_model=MensajeRespuesta)
def eliminar_adjunto(
    adjunto_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Lo puede quitar quien lo subió mientras el ticket siga abierto, o un administrador."""
    adjunto = session.get(Adjunto, adjunto_id)
    if adjunto is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    ticket = _ticket_accesible(session, adjunto.ticket_id, usuario)
    es_admin = usuario.rol == "administrador"
    if not es_admin:
        if adjunto.subido_por_id != usuario.id:
            raise HTTPException(status_code=403, detail="Solo quien subió el archivo puede quitarlo.")
        if ticket.estado in ("resuelto", "cancelado"):
            raise HTTPException(status_code=409, detail=f"El ticket ya está {ticket.estado}.")

    (DIRECTORIO_ARCHIVOS / adjunto.archivo).unlink(missing_ok=True)
    session.delete(adjunto)
    session.commit()
    return MensajeRespuesta(mensaje="Archivo eliminado.")

"""Gestión de usuarios y áreas. Solo para el rol administrador."""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_
from sqlmodel import Session, select

from app.database import get_session
from app.ml.train_classifier import quitar_tildes
from app.models import (
    Adjunto,
    Area,
    Cliente,
    EventoGamificacion,
    HistorialEstadoTicket,
    TokenAcceso,
    Ticket,
)
from app.schemas import (
    AreaCreate,
    AreaRead,
    AreaUpdate,
    ClienteRead,
    ImportacionReporte,
    MensajeRespuesta,
    PasswordTemporalRespuesta,
    UsuarioCreado,
    UsuarioCreate,
    UsuarioUpdate,
)
from app.services.auth import generar_password_temporal, hashear_password, requerir_admin
from app.services.historico import leer_csv, procesar
from app.services.usuarios import a_cliente_read, mapa_areas

router = APIRouter()

ROLES_VALIDOS = ("usuario", "tecnico", "administrador")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalizar(texto: str) -> str:
    return quitar_tildes(texto.strip().lower())


def _area_activa(session: Session, area_id: int) -> Area:
    area = session.get(Area, area_id)
    if area is None or not area.activo:
        raise HTTPException(status_code=400, detail="El área no existe o está inactiva")
    return area


def _nombre_de_area_libre(session: Session, nombre: str, excepto_id: Optional[int] = None) -> str:
    nombre = nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre del área no puede estar vacío")
    objetivo = _normalizar(nombre)
    for area in session.exec(select(Area)).all():
        if area.id != excepto_id and _normalizar(area.nombre) == objetivo:
            raise HTTPException(status_code=400, detail="Ya existe un área con ese nombre")
    return nombre


@router.get("/usuarios", response_model=list[ClienteRead])
def listar_usuarios(
    q: Optional[str] = None,
    rol: Optional[str] = None,
    activo: Optional[bool] = None,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    consulta = select(Cliente)
    if rol:
        consulta = consulta.where(Cliente.rol == rol)
    if activo is not None:
        consulta = consulta.where(Cliente.activo == activo)
    clientes = session.exec(consulta.order_by(Cliente.nombre)).all()
    if q:
        buscado = _normalizar(q)
        clientes = [c for c in clientes if buscado in _normalizar(f"{c.nombre} {c.email}")]
    areas = mapa_areas(session)
    return [a_cliente_read(c, areas) for c in clientes]


@router.post("/usuarios", response_model=UsuarioCreado)
def crear_usuario(
    data: UsuarioCreate,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    nombre = data.nombre.strip()
    email = data.email.strip().lower()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="El correo no es válido")
    if data.rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail="Rol no válido")
    area = _area_activa(session, data.area_id)
    if session.exec(select(Cliente).where(Cliente.email == email)).first():
        raise HTTPException(status_code=400, detail="Ese correo ya está registrado")

    temporal = generar_password_temporal()
    cliente = Cliente(
        nombre=nombre,
        email=email,
        area_id=area.id,
        rol=data.rol,
        password_hash=hashear_password(temporal),
        debe_cambiar_password=True,
    )
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return UsuarioCreado(
        usuario=a_cliente_read(cliente, {area.id: area}), password_temporal=temporal
    )


@router.patch("/usuarios/{usuario_id}", response_model=ClienteRead)
def actualizar_usuario(
    usuario_id: int,
    data: UsuarioUpdate,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    cliente = session.get(Cliente, usuario_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if cliente.id == admin.id and (
        (data.rol is not None and data.rol != cliente.rol) or data.activo is False
    ):
        raise HTTPException(
            status_code=400, detail="No puedes cambiar tu propio rol ni desactivar tu cuenta"
        )

    if data.nombre is not None:
        nombre = data.nombre.strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
        cliente.nombre = nombre
    if data.area_id is not None and data.area_id != cliente.area_id:
        cliente.area_id = _area_activa(session, data.area_id).id
    if data.rol is not None and data.rol != cliente.rol:
        if data.rol not in ROLES_VALIDOS:
            raise HTTPException(status_code=400, detail="Rol no válido")
        cliente.rol = data.rol
        cliente.version_token += 1  # cierra sus sesiones: el nuevo rol aplica al volver a entrar
    if data.activo is not None and data.activo != cliente.activo:
        cliente.activo = data.activo
        if not data.activo:
            cliente.version_token += 1

    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return a_cliente_read(cliente, mapa_areas(session))


@router.delete("/usuarios/{usuario_id}", response_model=MensajeRespuesta)
def eliminar_usuario(
    usuario_id: int,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    """Borra una cuenta sin actividad (p. ej. creada por error o nunca usada).

    Quien ya participó en tickets, cambios de estado o gamificación no se puede
    eliminar porque dejaría huérfano el historial; para esos casos se desactiva.
    """
    cliente = session.get(Cliente, usuario_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if cliente.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")

    tiene_actividad = (
        session.exec(
            select(Ticket.id).where(
                or_(Ticket.cliente_id == cliente.id, Ticket.tecnico_id == cliente.id)
            )
        ).first()
        is not None
        or session.exec(
            select(HistorialEstadoTicket.id).where(
                HistorialEstadoTicket.cambiado_por_id == cliente.id
            )
        ).first()
        is not None
        or session.exec(
            select(EventoGamificacion.id).where(EventoGamificacion.cliente_id == cliente.id)
        ).first()
        is not None
        or session.exec(select(Adjunto.id).where(Adjunto.subido_por_id == cliente.id)).first()
        is not None
    )
    if tiene_actividad:
        raise HTTPException(
            status_code=409,
            detail="Esta persona ya tiene actividad registrada (tickets, cambios o puntos) y "
            "no se puede eliminar sin perder el historial. Desactiva su cuenta en su lugar.",
        )

    for token in session.exec(
        select(TokenAcceso).where(TokenAcceso.cliente_id == cliente.id)
    ).all():
        session.delete(token)
    session.flush()  # los tokens deben salir antes que la cuenta a la que apuntan
    session.delete(cliente)
    session.commit()
    return MensajeRespuesta(mensaje="Usuario eliminado.")


@router.post("/usuarios/{usuario_id}/restablecer-password", response_model=PasswordTemporalRespuesta)
def restablecer_password(
    usuario_id: int,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    """Genera una contraseña temporal nueva (p. ej. si la persona no puede usar el enlace
    por correo). Se muestra una sola vez; la persona debe cambiarla al ingresar."""
    cliente = session.get(Cliente, usuario_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if cliente.id == admin.id:
        raise HTTPException(
            status_code=400, detail="Para tu propia cuenta usa «Cambiar contraseña»"
        )
    if not cliente.activo:
        raise HTTPException(status_code=400, detail="La cuenta está desactivada")

    temporal = generar_password_temporal()
    cliente.password_hash = hashear_password(temporal)
    cliente.debe_cambiar_password = True
    cliente.version_token += 1  # cierra sus sesiones abiertas
    session.add(cliente)
    session.commit()
    return PasswordTemporalRespuesta(password_temporal=temporal)


MAX_BYTES_CSV = 10 * 1024 * 1024


@router.post("/historico", response_model=ImportacionReporte)
async def importar_historico(
    request: Request,
    aplicar: bool = False,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    """Limpia el CSV recibido (cuerpo de la petición) y, con aplicar=true, lo guarda.

    Sin aplicar solo devuelve la vista previa de lo que pasaría.
    """
    contenido = await request.body()
    if len(contenido) > MAX_BYTES_CSV:
        raise HTTPException(status_code=413, detail="El archivo supera los 10 MB")
    try:
        tabla = leer_csv(contenido)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return procesar(tabla, session, aplicar)


@router.get("/areas", response_model=list[AreaRead])
def listar_areas(
    admin: Cliente = Depends(requerir_admin), session: Session = Depends(get_session)
):
    return session.exec(select(Area).order_by(Area.nombre)).all()


@router.post("/areas", response_model=AreaRead)
def crear_area(
    data: AreaCreate,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    area = Area(nombre=_nombre_de_area_libre(session, data.nombre))
    session.add(area)
    session.commit()
    session.refresh(area)
    return area


@router.patch("/areas/{area_id}", response_model=AreaRead)
def actualizar_area(
    area_id: int,
    data: AreaUpdate,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    area = session.get(Area, area_id)
    if area is None:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    if data.nombre is not None:
        area.nombre = _nombre_de_area_libre(session, data.nombre, excepto_id=area.id)
    if data.activo is not None:
        area.activo = data.activo
    session.add(area)
    session.commit()
    session.refresh(area)
    return area

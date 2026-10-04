"""Gestión de usuarios y áreas. Solo para el rol administrador."""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.ml.train_classifier import quitar_tildes
from app.models import Area, Cliente
from app.schemas import (
    AreaCreate,
    AreaRead,
    AreaUpdate,
    ClienteRead,
    InvitacionRespuesta,
    UsuarioCreado,
    UsuarioCreate,
    UsuarioUpdate,
)
from app.services import correo, tokens_acceso
from app.services.auth import requerir_admin
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

    cliente = Cliente(nombre=nombre, email=email, area_id=area.id, rol=data.rol)
    session.add(cliente)
    session.commit()
    session.refresh(cliente)

    token = tokens_acceso.generar(session, cliente, "activacion", tokens_acceso.MINUTOS_ACTIVACION)
    modo = correo.enviar_activacion(cliente.email, cliente.nombre, token)
    return UsuarioCreado(usuario=a_cliente_read(cliente, {area.id: area}), correo=modo)


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


@router.post("/usuarios/{usuario_id}/invitacion", response_model=InvitacionRespuesta)
def enviar_enlace_de_acceso(
    usuario_id: int,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    cliente = session.get(Cliente, usuario_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not cliente.activo:
        raise HTTPException(status_code=400, detail="La cuenta está desactivada")

    if cliente.password_hash is None:
        token = tokens_acceso.generar(
            session, cliente, "activacion", tokens_acceso.MINUTOS_ACTIVACION
        )
        modo = correo.enviar_activacion(cliente.email, cliente.nombre, token)
    else:
        token = tokens_acceso.generar(
            session, cliente, "recuperacion", tokens_acceso.MINUTOS_RECUPERACION
        )
        modo = correo.enviar_recuperacion(cliente.email, cliente.nombre, token)
    return InvitacionRespuesta(correo=modo)


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

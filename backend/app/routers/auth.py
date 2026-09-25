from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente
from app.schemas import ClienteRead, LoginRequest, RegistroRequest, TokenResponse
from app.services.auth import (
    crear_token,
    hashear_password,
    obtener_usuario_actual,
    validar_dominio_corporativo,
    verificar_password,
)

router = APIRouter()


@router.post("/registro", response_model=TokenResponse)
def registrar(data: RegistroRequest, session: Session = Depends(get_session)):
    validar_dominio_corporativo(data.email)

    existente = session.exec(
        select(Cliente).where(Cliente.email == data.email.lower())
    ).first()
    if existente is not None:
        raise HTTPException(status_code=400, detail="Ese correo ya está registrado")

    cliente = Cliente(
        nombre=data.nombre,
        area=data.area,
        email=data.email.lower(),
        password_hash=hashear_password(data.password),
        rol="colaborador",
    )
    session.add(cliente)
    session.commit()
    session.refresh(cliente)

    return TokenResponse(access_token=crear_token(cliente), cliente=cliente)


@router.post("/login", response_model=TokenResponse)
def iniciar_sesion(data: LoginRequest, session: Session = Depends(get_session)):
    cliente = session.exec(
        select(Cliente).where(Cliente.email == data.email.lower())
    ).first()
    if cliente is None or not verificar_password(data.password, cliente.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    return TokenResponse(access_token=crear_token(cliente), cliente=cliente)


@router.get("/yo", response_model=ClienteRead)
def yo(usuario: Cliente = Depends(obtener_usuario_actual)):
    return usuario

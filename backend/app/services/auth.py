"""Autenticación: hashing de contraseñas, JWT, y dependencias de FastAPI
para proteger endpoints por rol.
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.database import get_session
from app.models import Cliente

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "minutodesk-dev-secret-cambiar-en-produccion")
ALGORITMO = "HS256"
EXPIRACION_HORAS = 12

DOMINIO_CORPORATIVO = "@ejemplo.com"

seguridad = HTTPBearer()


def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verificar_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def validar_dominio_corporativo(email: str) -> None:
    if not email.lower().endswith(DOMINIO_CORPORATIVO):
        raise HTTPException(
            status_code=400,
            detail=f"El correo debe ser del dominio corporativo ({DOMINIO_CORPORATIVO})",
        )


def crear_token(cliente: Cliente) -> str:
    payload = {
        "sub": str(cliente.id),
        "rol": cliente.rol,
        "exp": datetime.now(timezone.utc) + timedelta(hours=EXPIRACION_HORAS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITMO)


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(seguridad),
    session: Session = Depends(get_session),
) -> Cliente:
    try:
        payload = jwt.decode(credenciales.credentials, SECRET_KEY, algorithms=[ALGORITMO])
        cliente_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    cliente = session.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return cliente


def requerir_tecnico(usuario: Cliente = Depends(obtener_usuario_actual)) -> Cliente:
    if usuario.rol != "tecnico":
        raise HTTPException(status_code=403, detail="Requiere rol de técnico")
    return usuario


def verificar_acceso_cliente(usuario: Cliente, cliente_id: int) -> None:
    """Un técnico puede acceder a cualquier cliente; un colaborador solo al suyo."""
    if usuario.rol != "tecnico" and usuario.id != cliente_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este recurso")

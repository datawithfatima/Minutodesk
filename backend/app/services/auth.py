"""Autenticación: hashing de contraseñas, JWT y dependencias de FastAPI para
proteger endpoints por rol (usuario, tecnico, administrador).
"""
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.database import get_session
from app.models import Cliente

load_dotenv()

ALGORITMO = "HS256"
EXPIRACION_HORAS = 12
ROLES_PERSONAL = ("tecnico", "administrador")


def _obtener_secret_key() -> str:
    clave = os.getenv("SECRET_KEY")
    if clave:
        return clave
    # Sin SECRET_KEY en .env se genera una clave aleatoria y se guarda en un archivo
    # local (ignorado por git), para no depender de una clave fija en el código.
    archivo = Path(__file__).resolve().parents[2] / ".secret_key"
    if archivo.exists():
        return archivo.read_text(encoding="utf-8").strip()
    clave = secrets.token_urlsafe(48)
    archivo.write_text(clave, encoding="utf-8")
    return clave


SECRET_KEY = _obtener_secret_key()

seguridad = HTTPBearer()


def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# Se usa para que iniciar sesión tarde parecido exista o no el correo.
HASH_FALSO = hashear_password("contrasena-inexistente-1")


def validar_password(password: str) -> None:
    if len(password.encode()) > 72:
        raise HTTPException(status_code=400, detail="La contraseña no puede superar 72 caracteres")
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(
            status_code=400,
            detail="La contraseña debe tener al menos 8 caracteres, con letras y números",
        )


def crear_token(cliente: Cliente) -> str:
    payload = {
        "sub": str(cliente.id),
        "rol": cliente.rol,
        "ver": cliente.version_token,
        "exp": datetime.now(timezone.utc) + timedelta(hours=EXPIRACION_HORAS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITMO)


def es_personal(usuario: Cliente) -> bool:
    """Técnico o administrador: pueden ver y gestionar todos los tickets."""
    return usuario.rol in ROLES_PERSONAL


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(seguridad),
    session: Session = Depends(get_session),
) -> Cliente:
    try:
        payload = jwt.decode(credenciales.credentials, SECRET_KEY, algorithms=[ALGORITMO])
        cliente_id = int(payload["sub"])
        version = int(payload.get("ver", 0))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    cliente = session.get(Cliente, cliente_id)
    if cliente is None or not cliente.activo or cliente.version_token != version:
        raise HTTPException(status_code=401, detail="Sesión no válida. Inicia sesión de nuevo.")
    return cliente


def requerir_personal(usuario: Cliente = Depends(obtener_usuario_actual)) -> Cliente:
    if not es_personal(usuario):
        raise HTTPException(status_code=403, detail="Requiere rol de técnico o administrador")
    return usuario


def requerir_admin(usuario: Cliente = Depends(obtener_usuario_actual)) -> Cliente:
    if usuario.rol != "administrador":
        raise HTTPException(status_code=403, detail="Requiere rol de administrador")
    return usuario


def verificar_acceso_cliente(usuario: Cliente, cliente_id: int) -> None:
    """El personal puede acceder a cualquier cliente; un usuario final solo al suyo."""
    if not es_personal(usuario) and usuario.id != cliente_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este recurso")

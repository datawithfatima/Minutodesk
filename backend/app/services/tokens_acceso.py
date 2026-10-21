"""Tokens de un solo uso para activar una cuenta nueva o recuperar la contraseña.

En la base solo se guarda el hash (SHA-256) del token: quien lea la tabla no
puede usar los enlaces. Cada token expira y se invalida al usarse.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from app.models import Cliente, TokenAcceso

MINUTOS_ACTIVACION = 72 * 60
MINUTOS_RECUPERACION = 30
# Cuando lo pide el administrador la persona quizá no esté pendiente del correo.
MINUTOS_RECUPERACION_ADMIN = 24 * 60
MAX_RECUPERACIONES_POR_HORA = 3


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generar(session: Session, cliente: Cliente, tipo: str, minutos: int) -> str:
    ahora = datetime.now()
    previos = session.exec(
        select(TokenAcceso).where(
            TokenAcceso.cliente_id == cliente.id,
            TokenAcceso.tipo == tipo,
            TokenAcceso.usado_en == None,  # noqa: E711
        )
    ).all()
    for previo in previos:
        previo.usado_en = ahora
        session.add(previo)

    token = secrets.token_urlsafe(32)
    session.add(
        TokenAcceso(
            cliente_id=cliente.id,
            tipo=tipo,
            token_hash=_hash(token),
            expira_en=ahora + timedelta(minutes=minutos),
        )
    )
    session.commit()
    return token


def buscar_valido(session: Session, token: str) -> Optional[TokenAcceso]:
    registro = session.exec(
        select(TokenAcceso).where(TokenAcceso.token_hash == _hash(token))
    ).first()
    if registro is None or registro.usado_en is not None or registro.expira_en < datetime.now():
        return None
    return registro


def marcar_usado(session: Session, registro: TokenAcceso) -> None:
    registro.usado_en = datetime.now()
    session.add(registro)


def demasiadas_recuperaciones(session: Session, cliente: Cliente) -> bool:
    desde = datetime.now() - timedelta(hours=1)
    recientes = session.exec(
        select(TokenAcceso).where(
            TokenAcceso.cliente_id == cliente.id,
            TokenAcceso.tipo == "recuperacion",
            TokenAcceso.creado_en >= desde,
        )
    ).all()
    return len(recientes) >= MAX_RECUPERACIONES_POR_HORA

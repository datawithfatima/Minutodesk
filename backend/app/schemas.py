from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class TicketCreate(SQLModel):
    texto: str


class TicketUpdate(SQLModel):
    estado: Optional[str] = None
    resuelto_por: Optional[str] = None


class ChatMensaje(SQLModel):
    mensaje: str


class ChatRespuesta(SQLModel):
    respuesta: str
    resuelto: bool
    estado_ticket: str


class ClienteRead(SQLModel):
    id: int
    nombre: str
    area: str
    email: str
    rol: str
    puntos: int


class RegistroRequest(SQLModel):
    nombre: str
    area: str
    email: str
    password: str


class LoginRequest(SQLModel):
    email: str
    password: str


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    cliente: ClienteRead


class InteraccionRead(SQLModel):
    id: int
    ticket_id: int
    mensaje_cliente: str
    respuesta_minutito: str
    marco_resuelto: bool
    creado_en: datetime


class TicketRead(SQLModel):
    id: int
    cliente_id: int
    texto: str
    tipo_predicho: Optional[str] = None
    categoria_predicha: Optional[str] = None
    confianza_clasificacion: Optional[float] = None
    estado: str
    resuelto_por: Optional[str] = None
    creado_en: datetime
    cerrado_en: Optional[datetime] = None


class EventoGamificacionRead(SQLModel):
    id: int
    ticket_id: Optional[int] = None
    puntos_otorgados: int
    motivo: str
    creado_en: datetime


class ClienteGamificacion(SQLModel):
    puntos: int
    nivel: str
    historial: list[EventoGamificacionRead]

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class TicketCreate(SQLModel):
    texto: str
    cliente_id: int


class TicketUpdate(SQLModel):
    estado: Optional[str] = None
    resuelto_por: Optional[str] = None


class ChatMensaje(SQLModel):
    mensaje: str


class ChatRespuesta(SQLModel):
    respuesta: str
    resuelto: bool
    estado_ticket: str


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

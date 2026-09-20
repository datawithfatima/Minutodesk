from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Cliente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    area: str
    puntos: int = Field(default=0)
    creado_en: datetime = Field(default_factory=datetime.now)


class Ticket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id")
    texto: str
    tipo_predicho: Optional[str] = Field(default=None)
    categoria_predicha: Optional[str] = Field(default=None)
    confianza_clasificacion: Optional[float] = Field(default=None)
    estado: str = Field(default="abierto")
    resuelto_por: Optional[str] = Field(default=None)
    creado_en: datetime = Field(default_factory=datetime.now)
    cerrado_en: Optional[datetime] = Field(default=None)


class InteraccionMinutito(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id")
    mensaje_cliente: str
    respuesta_minutito: str
    marco_resuelto: bool = Field(default=False)
    creado_en: datetime = Field(default_factory=datetime.now)


class EventoGamificacion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id")
    ticket_id: Optional[int] = Field(default=None, foreign_key="ticket.id")
    puntos_otorgados: int
    motivo: str
    creado_en: datetime = Field(default_factory=datetime.now)

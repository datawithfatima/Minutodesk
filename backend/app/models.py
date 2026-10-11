from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


class Area(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True, index=True)
    activo: bool = Field(default=True)


class Cliente(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint(
            "rol IN ('usuario','tecnico','administrador')", name="ck_cliente_rol"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    area_id: int = Field(foreign_key="area.id", index=True)
    email: str = Field(unique=True, index=True)
    # Nulo hasta que la persona activa su cuenta desde el enlace que recibe por correo.
    password_hash: Optional[str] = Field(default=None)
    rol: str = Field(default="usuario")
    activo: bool = Field(default=True)
    # Se incrementa al cambiar contraseña, rol o desactivar: invalida las sesiones abiertas.
    version_token: int = Field(default=0)
    puntos: int = Field(default=0)
    creado_en: datetime = Field(default_factory=datetime.now)


class TokenAcceso(SQLModel, table=True):
    __tablename__ = "token_acceso"
    __table_args__ = (
        CheckConstraint("tipo IN ('activacion','recuperacion')", name="ck_token_tipo"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    tipo: str
    token_hash: str = Field(unique=True, index=True)
    expira_en: datetime
    usado_en: Optional[datetime] = Field(default=None)
    creado_en: datetime = Field(default_factory=datetime.now)


class Ticket(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint(
            "estado IN ('abierto','en_proceso','resuelto')", name="ck_ticket_estado"
        ),
        CheckConstraint(
            "resuelto_por IS NULL OR resuelto_por IN ('minutito','tecnico')",
            name="ck_ticket_resuelto_por",
        ),
        CheckConstraint(
            "confianza_clasificacion IS NULL OR "
            "(confianza_clasificacion >= 0 AND confianza_clasificacion <= 1)",
            name="ck_ticket_confianza",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    tecnico_id: Optional[int] = Field(default=None, foreign_key="cliente.id", index=True)
    texto: str
    tipo_predicho: Optional[str] = Field(default=None)
    categoria_predicha: Optional[str] = Field(default=None, index=True)
    confianza_clasificacion: Optional[float] = Field(default=None)
    estado: str = Field(default="abierto", index=True)
    resuelto_por: Optional[str] = Field(default=None)
    creado_en: datetime = Field(default_factory=datetime.now)
    cerrado_en: Optional[datetime] = Field(default=None)


class HistorialEstadoTicket(SQLModel, table=True):
    __tablename__ = "historial_estado_ticket"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", index=True)
    estado_anterior: Optional[str] = Field(default=None)
    estado_nuevo: str
    # Nulo cuando el cambio lo hizo Minutito (no una persona).
    cambiado_por_id: Optional[int] = Field(default=None, foreign_key="cliente.id")
    fecha: datetime = Field(default_factory=datetime.now)


class InteraccionMinutito(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id")
    mensaje_cliente: str
    respuesta_minutito: str
    marco_resuelto: bool = Field(default=False)
    creado_en: datetime = Field(default_factory=datetime.now)


class TicketHistorico(SQLModel, table=True):
    """Ticket del export mensual de la herramienta anterior.

    Solo sirve para reportes: no guarda nombres de personas ni el texto del ticket.
    """

    __tablename__ = "ticket_historico"

    id: Optional[int] = Field(default=None, primary_key=True)
    id_externo: str = Field(unique=True, index=True)  # columna "ID" del CSV
    tipo: Optional[str] = Field(default=None)
    categoria: Optional[str] = Field(default=None, index=True)
    prioridad: Optional[str] = Field(default=None)
    estado: str
    creado_en: datetime
    resuelto_en: Optional[datetime] = Field(default=None)
    importado_en: datetime = Field(default_factory=datetime.now)


class EventoGamificacion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id")
    ticket_id: Optional[int] = Field(default=None, foreign_key="ticket.id")
    puntos_otorgados: int
    motivo: str
    creado_en: datetime = Field(default_factory=datetime.now)

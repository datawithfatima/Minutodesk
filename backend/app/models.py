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
    # Nulo solo en cuentas antiguas creadas por enlace de activación: el administrador
    # les genera una contraseña temporal.
    password_hash: Optional[str] = Field(default=None)
    # Verdadero con una contraseña temporal: debe cambiarla antes de usar el sistema.
    debe_cambiar_password: bool = Field(default=False)
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
            "estado IN ('abierto','en_proceso','resuelto','cancelado')", name="ck_ticket_estado"
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
    # Lo que la persona eligió o confirmó al crear el ticket (o un técnico corrigió después).
    # Comparado con lo predicho por el SVM mide su acierto real en uso.
    tipo: Optional[str] = Field(default=None)
    categoria: Optional[str] = Field(default=None)
    clasificacion_confirmada: bool = Field(default=False)
    prioridad: str = Field(default="Normal")  # Crítica / Alta / Normal / Baja
    # JSON con los datos del formulario de alta de colaborador (solo en esos tickets).
    datos_alta: Optional[str] = Field(default=None)
    # «abierto» se muestra como «Nuevo». «cancelado» lo fija solo el personal, con motivo.
    estado: str = Field(default="abierto", index=True)
    resuelto_por: Optional[str] = Field(default=None)
    motivo_cancelacion: Optional[str] = Field(default=None)
    creado_en: datetime = Field(default_factory=datetime.now)
    cerrado_en: Optional[datetime] = Field(default=None)


class Adjunto(SQLModel, table=True):
    """Archivo subido a un ticket. El contenido vive en backend/uploads/ con un nombre
    aleatorio (`archivo`); el nombre original solo se guarda para mostrarlo."""

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", index=True)
    nombre_original: str
    archivo: str = Field(unique=True)
    tamano: int
    subido_por_id: int = Field(foreign_key="cliente.id")
    creado_en: datetime = Field(default_factory=datetime.now)


class HistorialEstadoTicket(SQLModel, table=True):
    __tablename__ = "historial_estado_ticket"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", index=True)
    estado_anterior: Optional[str] = Field(default=None)
    estado_nuevo: str
    # Nulo cuando el cambio lo hizo Minutito (no una persona).
    cambiado_por_id: Optional[int] = Field(default=None, foreign_key="cliente.id")
    motivo: Optional[str] = Field(default=None)  # por ahora, solo al cancelar
    fecha: datetime = Field(default_factory=datetime.now)


class InteraccionMinutito(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id")
    mensaje_cliente: str
    respuesta_minutito: str
    # Verdadero solo si el usuario confirmó que esta respuesta resolvió su problema.
    marco_resuelto: bool = Field(default=False)
    creado_en: datetime = Field(default_factory=datetime.now)


class MensajeTicket(SQLModel, table=True):
    """Mensaje del chat entre el usuario que abrió el ticket y el personal de soporte."""

    __tablename__ = "mensaje_ticket"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", index=True)
    autor_id: int = Field(foreign_key="cliente.id")
    texto: str
    creado_en: datetime = Field(default_factory=datetime.now)


class Aprobacion(SQLModel, table=True):
    """Paso de aprobación que el personal pide a otra persona (p. ej. el jefe del área)
    antes de continuar con un ticket. Mientras esté pendiente el ticket no se resuelve."""

    __table_args__ = (
        CheckConstraint(
            "estado IN ('pendiente','aprobada','rechazada')", name="ck_aprobacion_estado"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", index=True)
    solicitada_por_id: int = Field(foreign_key="cliente.id")
    aprobador_id: int = Field(foreign_key="cliente.id", index=True)
    descripcion: str
    estado: str = Field(default="pendiente", index=True)
    comentario: Optional[str] = Field(default=None)  # lo escribe el aprobador al responder
    creado_en: datetime = Field(default_factory=datetime.now)
    respondida_en: Optional[datetime] = Field(default=None)


class TicketHistorico(SQLModel, table=True):
    """Ticket del export mensual de la herramienta anterior.

    Es solo de consulta (el administrador lo ve en «Datos históricos»): no tiene cuenta
    de usuario asociada, no entra en los indicadores de la plataforma, ni en el ranking
    ni en los puntos, y no se puede editar. Se identifica en pantalla con el prefijo H-.
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
    descripcion: Optional[str] = Field(default=None)  # texto plano (sin HTML)
    solicitante: Optional[str] = Field(default=None)  # nombre tal como viene en el CSV
    asignado_a: Optional[str] = Field(default=None)  # quién lo atendió, tal como viene en el CSV
    importado_en: datetime = Field(default_factory=datetime.now)


class EventoGamificacion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id")
    ticket_id: Optional[int] = Field(default=None, foreign_key="ticket.id")
    puntos_otorgados: int
    motivo: str
    creado_en: datetime = Field(default_factory=datetime.now)

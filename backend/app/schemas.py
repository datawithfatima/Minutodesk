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
    area_id: int
    area: str
    email: str
    rol: str
    activo: bool
    pendiente_activacion: bool = False
    puntos: int


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
    tecnico_id: Optional[int] = None
    texto: str
    tipo_predicho: Optional[str] = None
    categoria_predicha: Optional[str] = None
    confianza_clasificacion: Optional[float] = None
    estado: str
    resuelto_por: Optional[str] = None
    creado_en: datetime
    cerrado_en: Optional[datetime] = None


class HistorialEstadoRead(SQLModel):
    id: int
    estado_anterior: Optional[str] = None
    estado_nuevo: str
    cambiado_por_id: Optional[int] = None
    cambiado_por: str
    fecha: datetime


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


class LoginRequest(SQLModel):
    email: str
    password: str


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    cliente: ClienteRead


class OlvidePasswordRequest(SQLModel):
    email: str


class EstablecerPasswordRequest(SQLModel):
    token: str
    password: str


class MensajeRespuesta(SQLModel):
    mensaje: str


class AreaRead(SQLModel):
    id: int
    nombre: str
    activo: bool


class AreaCreate(SQLModel):
    nombre: str


class AreaUpdate(SQLModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None


class UsuarioCreate(SQLModel):
    nombre: str
    email: str
    area_id: int
    rol: str = "usuario"


class UsuarioUpdate(SQLModel):
    nombre: Optional[str] = None
    area_id: Optional[int] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None


class UsuarioCreado(SQLModel):
    usuario: ClienteRead
    correo: str  # "smtp" si se envió por correo, "archivo" si quedó guardado (modo desarrollo)


class InvitacionRespuesta(SQLModel):
    correo: str


class CategoriaConteo(SQLModel):
    categoria: str
    total: int


class ConteoEtiqueta(SQLModel):
    etiqueta: str
    total: int


class HistoricoResumen(SQLModel):
    total: int
    completados: int
    cancelados: int
    dias_medio_resolucion: Optional[float] = None
    desde: Optional[datetime] = None
    hasta: Optional[datetime] = None
    ultima_importacion: Optional[datetime] = None
    por_estado: list[ConteoEtiqueta]
    por_categoria: list[ConteoEtiqueta]
    por_prioridad: list[ConteoEtiqueta]
    por_mes: list[ConteoEtiqueta]


class ImportacionReporte(SQLModel):
    aplicado: bool
    filas: int
    validas: int
    nuevos: int
    actualizados: int
    sin_cambios: int
    omitidos: int
    duplicados_en_archivo: int
    fechas_solucion_descartadas: int
    completados_sin_fecha: int
    incidencias: list[str]
    total_en_base: int


class ReporteResumen(SQLModel):
    total: int
    abiertos: int
    en_proceso: int
    resueltos: int
    resueltos_por_minutito: int
    resueltos_por_tecnico: int
    pct_resolucion_autonoma: float
    tiempo_medio_resolucion_horas: Optional[float] = None
    confianza_media: Optional[float] = None
    por_categoria: list[CategoriaConteo]

from datetime import date, datetime
from typing import Optional

from sqlmodel import SQLModel


class TicketCreate(SQLModel):
    texto: str
    # Lo que eligió la persona en el formulario. Si vienen ambos, el ticket nace con la
    # clasificación confirmada; si no (p. ej. desde el chat con Minutito), solo queda la
    # predicción del SVM.
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    prioridad: Optional[str] = None


class TicketUpdate(SQLModel):
    estado: Optional[str] = None
    resuelto_por: Optional[str] = None
    # Correcciones del personal: quedan como clasificación confirmada.
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    prioridad: Optional[str] = None


class SugerenciaRequest(SQLModel):
    texto: str


class CategoriaAlternativa(SQLModel):
    categoria: str
    confianza: float


class SugerenciaRead(SQLModel):
    tipo: str
    confianza_tipo: float
    categoria: str
    confianza: float
    confiable: bool
    alternativas: list[CategoriaAlternativa]


class TipoCatalogo(SQLModel):
    nombre: str
    titulo: str
    ayuda: str


class LicenciaCatalogo(SQLModel):
    nombre: str
    ayuda: str


class LimitesAdjuntos(SQLModel):
    maximo: int
    megabytes: int
    extensiones: list[str]


class CatalogosRead(SQLModel):
    tipos: list[TipoCatalogo]
    prioridades: list[str]
    prioridad_por_defecto: str
    categorias: list[str]
    listas_distribucion: list[str]
    aplicaciones: list[str]
    licencias_sap: list[LicenciaCatalogo]
    adjuntos: LimitesAdjuntos


class AltaColaboradorCreate(SQLModel):
    nombres: str
    fecha_ingreso: date
    cedula: str
    cargo: str
    monitor: Optional[bool] = None
    telefono_fijo: Optional[bool] = None
    grupo: Optional[str] = None
    listas_distribucion: list[str] = []
    aplicaciones: list[str] = []
    licencia_sap: Optional[str] = None
    permisos_sap: Optional[str] = None
    observaciones: str
    prioridad: Optional[str] = None


class AdjuntoRead(SQLModel):
    id: int
    ticket_id: int
    nombre_original: str
    tamano: int
    subido_por_id: int
    subido_por: str
    creado_en: datetime


class ChatMensaje(SQLModel):
    mensaje: str


class ChatRespuesta(SQLModel):
    respuesta: str
    # Minutito derivó el caso a una persona: no hay nada que confirmar.
    escalado: bool
    # El usuario debe confirmar si la respuesta resolvió su problema.
    requiere_confirmacion: bool
    estado_ticket: str


class ConfirmarResolucion(SQLModel):
    resuelto: bool


class ConfirmacionRespuesta(SQLModel):
    estado_ticket: str
    mensaje: str


class ClienteRead(SQLModel):
    id: int
    nombre: str
    area_id: int
    area: str
    email: str
    rol: str
    activo: bool
    pendiente_activacion: bool = False  # cuenta antigua sin contraseña
    debe_cambiar_password: bool = False  # tiene una contraseña temporal
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
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    clasificacion_confirmada: bool = False
    prioridad: str = "Normal"
    estado: str
    resuelto_por: Optional[str] = None
    motivo_cancelacion: Optional[str] = None
    creado_en: datetime
    cerrado_en: Optional[datetime] = None


class CancelarTicket(SQLModel):
    motivo: str


class TicketDetalle(TicketRead):
    """Solo el detalle trae los datos del alta (llevan la cédula): las listas no."""

    datos_alta: Optional[str] = None  # JSON


class HistorialEstadoRead(SQLModel):
    id: int
    estado_anterior: Optional[str] = None
    estado_nuevo: str
    cambiado_por_id: Optional[int] = None
    cambiado_por: str
    motivo: Optional[str] = None
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


class CambiarPasswordRequest(SQLModel):
    password_actual: str
    password_nueva: str


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
    # Se muestra una sola vez al administrador para que se la entregue a la persona.
    password_temporal: str


class PasswordTemporalRespuesta(SQLModel):
    password_temporal: str


class CategoriaConteo(SQLModel):
    categoria: str
    total: int


class ConteoEtiqueta(SQLModel):
    etiqueta: str
    total: int


class PuntoValor(SQLModel):
    etiqueta: str
    valor: Optional[float] = None


class HistoricoTicketItem(SQLModel):
    id: int
    id_externo: str
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    prioridad: Optional[str] = None
    estado: str
    creado_en: datetime
    resuelto_en: Optional[datetime] = None
    solicitante: Optional[str] = None
    asignado_a: Optional[str] = None
    extracto: Optional[str] = None  # primeras palabras de la descripción


class HistoricoTicketDetalle(HistoricoTicketItem):
    descripcion: Optional[str] = None


class HistoricoFiltros(SQLModel):
    estados: list[str]
    categorias: list[str]
    prioridades: list[str]


class HistoricoTicketLista(SQLModel):
    total: int
    pagina: int
    por_pagina: int
    items: list[HistoricoTicketItem]
    filtros: HistoricoFiltros


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
    # Días medios de resolución de los tickets creados cada mes (solo completados con fecha).
    resolucion_por_mes: list[PuntoValor]


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
    cancelados: int = 0
    resueltos_por_minutito: int
    resueltos_por_tecnico: int
    # Sobre los tickets no cancelados: uno cancelado no necesitaba solución.
    pct_resolucion_autonoma: float
    tiempo_medio_resolucion_horas: Optional[float] = None
    confianza_media: Optional[float] = None
    por_categoria: list[CategoriaConteo]
    con_minutito: int = 0  # tickets en los que el usuario habló con Minutito
    ultimos_dias: list[ConteoEtiqueta] = []  # tickets creados por día, últimos 14 días

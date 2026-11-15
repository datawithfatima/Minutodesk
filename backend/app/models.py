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
    # Falso mientras el técnico es el que sugirió el sistema según la categoría; verdadero
    # cuando alguien lo eligió o tomó el ticket a mano (entonces no se reasigna solo).
    tecnico_manual: bool = Field(default=False)
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
    # Último aviso de plazo enviado al técnico: «por_vencer» o «vencido» (se limpia si
    # cambia el tipo o la prioridad, porque el plazo se recalcula).
    aviso_sla: Optional[str] = Field(default=None)
    # Solo en tickets creados por carga masiva desde el export de la herramienta anterior.
    id_externo: Optional[str] = Field(default=None, index=True)  # ID en esa herramienta
    solicitante_externo: Optional[str] = Field(default=None)  # quien lo pidió (no tiene cuenta)
    # Si el personal lo marcó como duplicado: el ticket principal, donde sigue la atención.
    duplicado_de_id: Optional[int] = Field(default=None, foreign_key="ticket.id", index=True)


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


class PausaSla(SQLModel, table=True):
    """Tramo en que el plazo de atención (SLA) del ticket no corre. La abre el personal
    con un motivo, o el sistema al pedir una aprobación (entonces lleva aprobacion_id y
    se cierra sola al responderla). Sin `fin` la pausa sigue vigente."""

    __tablename__ = "pausa_sla"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", index=True)
    motivo: str  # clave de sla.MOTIVOS_PAUSA
    detalle: Optional[str] = Field(default=None)
    aprobacion_id: Optional[int] = Field(default=None, foreign_key="aprobacion.id")
    iniciada_por_id: Optional[int] = Field(default=None, foreign_key="cliente.id")
    inicio: datetime = Field(default_factory=datetime.now)
    fin: Optional[datetime] = Field(default=None)
    reanudada_por_id: Optional[int] = Field(default=None, foreign_key="cliente.id")


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


class ConversacionMinutito(SQLModel, table=True):
    """Conversación con Minutito. Empieza sin ticket: si se resuelve, la persona lo
    confirma y no se crea ninguno; si no, se crea el ticket desde aquí y queda enlazado."""

    __tablename__ = "conversacion_minutito"
    __table_args__ = (
        CheckConstraint("estado IN ('abierta','resuelta','ticket')", name="ck_conversacion_estado"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    estado: str = Field(default="abierta", index=True)
    ticket_id: Optional[int] = Field(default=None, foreign_key="ticket.id", index=True)
    creado_en: datetime = Field(default_factory=datetime.now)
    cerrado_en: Optional[datetime] = Field(default=None)


class MensajeMinutito(SQLModel, table=True):
    __tablename__ = "mensaje_minutito"
    __table_args__ = (CheckConstraint("rol IN ('usuario','minutito')", name="ck_mensaje_minutito_rol"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    conversacion_id: int = Field(foreign_key="conversacion_minutito.id", index=True)
    rol: str
    texto: str
    creado_en: datetime = Field(default_factory=datetime.now)


class ImagenMinutito(SQLModel, table=True):
    """Imagen que la persona adjunta en la conversación con Minutito. Se sube antes de
    enviar el mensaje (`mensaje_id` vacío) y queda unida a él al enviarlo. Si se crea el
    ticket, se copia como adjunto del ticket. El contenido vive en backend/uploads/."""

    __tablename__ = "imagen_minutito"

    id: Optional[int] = Field(default=None, primary_key=True)
    conversacion_id: int = Field(foreign_key="conversacion_minutito.id", index=True)
    mensaje_id: Optional[int] = Field(default=None, foreign_key="mensaje_minutito.id", index=True)
    nombre_original: str
    archivo: str = Field(unique=True)
    tamano: int
    texto_leido: Optional[str] = None  # texto de la imagen según el OCR de Windows (ocr.py)
    creado_en: datetime = Field(default_factory=datetime.now)


class Seudonimo(SQLModel, table=True):
    """Alias estable para una persona de los datos de la empresa ("Solicitante 007").
    Solo se guarda el hash de su nombre: el nombre real no queda en la base."""

    id: Optional[int] = Field(default=None, primary_key=True)
    clave: str = Field(unique=True, index=True)  # SHA-256 del nombre normalizado
    alias: str


class EvaluacionMinutito(SQLModel, table=True):
    """Evaluación simulada de Minutito: qué le habría respondido a un ticket cargado y si,
    a juicio de una persona del equipo, esa respuesta lo habría resuelto. No cuenta como
    interacción real ni cambia el ticket."""

    __tablename__ = "evaluacion_minutito"
    __table_args__ = (
        CheckConstraint(
            "veredicto IS NULL OR veredicto IN ('resuelve','no_resuelve','no_aplica')",
            name="ck_evaluacion_veredicto",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", unique=True, index=True)
    respuesta: Optional[str] = Field(default=None)
    escalado: bool = Field(default=False)  # Minutito mismo derivó el caso a una persona
    error: Optional[str] = Field(default=None)  # p. ej. Ollama no disponible
    generada_en: datetime = Field(default_factory=datetime.now)
    veredicto: Optional[str] = Field(default=None)
    evaluado_por_id: Optional[int] = Field(default=None, foreign_key="cliente.id")
    evaluado_en: Optional[datetime] = Field(default=None)
    # Lo que el equipo considera la solución correcta: la referencia para dar el
    # veredicto. No cambia la respuesta de Minutito (eso es lo que se evalúa).
    solucion_esperada: Optional[str] = Field(default=None)


class PruebaMinutito(SQLModel, table=True):
    """Prueba controlada: un agente hace de colaborador con un problema de primer nivel
    ya definido (escenarios_prueba.py) y conversa con Minutito. Una persona del equipo
    revisa la conversación y marca si Minutito lo resolvió."""

    __tablename__ = "prueba_minutito"
    __table_args__ = (
        CheckConstraint(
            "veredicto IS NULL OR veredicto IN ('resuelve','no_resuelve','no_aplica')",
            name="ck_prueba_veredicto",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    clave: str = Field(unique=True, index=True)  # el escenario
    conversacion: Optional[str] = Field(default=None)  # JSON: [{"rol", "texto"}]
    # Cómo terminó: «resuelto» (el colaborador dijo que funcionó), «ticket» (Minutito
    # ofreció crear el ticket) o «sin_cierre» (se acabaron los turnos).
    termino: Optional[str] = Field(default=None)
    generada_en: Optional[datetime] = Field(default=None)
    veredicto: Optional[str] = Field(default=None)
    evaluado_por_id: Optional[int] = Field(default=None, foreign_key="cliente.id")
    evaluado_en: Optional[datetime] = Field(default=None)


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


class Auditoria(SQLModel, table=True):
    """Bitácora de auditoría: quién hizo qué y cuándo (inicios de sesión, cambios de
    usuarios y áreas, acciones sobre tickets, descargas, exportaciones y respaldos). La
    llena services/auditoria.py desde un middleware; solo la consulta el administrador.
    Nunca guarda contraseñas ni tokens."""

    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: datetime = Field(default_factory=datetime.now, index=True)
    actor_id: Optional[int] = Field(default=None, foreign_key="cliente.id", index=True)
    # Nombre de quien actuó, o el correo escrito en un inicio de sesión fallido.
    actor: Optional[str] = Field(default=None)
    accion: str = Field(index=True)  # clave estable, p. ej. «ticket_actualizado»
    descripcion: str  # texto legible: «Actualizó el ticket #12»
    entidad: Optional[str] = Field(default=None)  # ticket, usuario, area, adjunto...
    entidad_id: Optional[int] = Field(default=None)
    detalle: Optional[str] = Field(default=None)  # campos enviados (sin contraseñas)
    exito: bool = Field(default=True)
    ip: Optional[str] = Field(default=None)


class EncuestaSatisfaccion(SQLModel, table=True):
    """Calificación que deja quien abrió el ticket cuando se lo resuelven: de 1 a 5
    estrellas y un comentario opcional. Una por ticket (se puede cambiar). No interviene
    en el clasificador, en Minutito ni en los plazos: solo se muestra en Reportes."""

    __tablename__ = "encuesta_satisfaccion"
    __table_args__ = (CheckConstraint("estrellas BETWEEN 1 AND 5", name="ck_encuesta_estrellas"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id", unique=True, index=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    # Técnico que atendió el ticket al calificar (para el promedio por técnico).
    tecnico_id: Optional[int] = Field(default=None, foreign_key="cliente.id", index=True)
    estrellas: int
    comentario: Optional[str] = Field(default=None)
    creado_en: datetime = Field(default_factory=datetime.now)
    actualizado_en: Optional[datetime] = Field(default=None)


class RespuestaPredefinida(SQLModel, table=True):
    """Respuesta lista («macro») que el personal inserta en el chat del ticket y ajusta
    antes de enviar. Admite {nombre} (primer nombre del usuario), {ticket} y {tecnico}."""

    __tablename__ = "respuesta_predefinida"

    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str
    texto: str
    creada_por_id: Optional[int] = Field(default=None, foreign_key="cliente.id")
    usos: int = Field(default=0)
    activo: bool = Field(default=True)
    creado_en: datetime = Field(default_factory=datetime.now)


class EvaluacionHistorico(SQLModel, table=True):
    """Objetivo 3 medido en las incidencias del histórico: qué le habría respondido
    Minutito a cada una y si, a juicio de una persona del equipo, eso la habría resuelto.
    El histórico solo entrenó al clasificador; Minutito no aprende de estos casos."""

    __tablename__ = "evaluacion_historico"
    __table_args__ = (
        CheckConstraint(
            "veredicto IS NULL OR veredicto IN ('resuelve','no_resuelve','no_aplica')",
            name="ck_evaluacion_historico_veredicto",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    historico_id: int = Field(foreign_key="ticket_historico.id", unique=True, index=True)
    respuesta: str
    escalado: bool = Field(default=False)
    generada_en: datetime = Field(default_factory=datetime.now)
    veredicto: Optional[str] = Field(default=None)
    evaluado_por_id: Optional[int] = Field(default=None, foreign_key="cliente.id")
    evaluado_en: Optional[datetime] = Field(default=None)

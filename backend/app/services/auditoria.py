"""Bitácora de auditoría.

Un middleware (main.py) mira cada petición que termina y, si coincide con una de las
ACCIONES de abajo, deja una fila en la tabla `auditoria` con quién la hizo, cuándo, desde
qué IP, sobre qué (ticket, usuario...) y los campos enviados. Así se registra todo en un
solo lugar sin tocar cada endpoint. Las acciones que no están en la lista (p. ej. los
mensajes del chat con Minutito o las consultas) no se registran, para que la bitácora no
se llene de ruido. Nunca se guardan contraseñas, tokens ni el texto de los mensajes.

El historial de estados de cada ticket (historial_estado_ticket) sigue igual: esta
bitácora lo complementa con todo lo demás.
"""
import json
import logging
import re
from dataclasses import dataclass
from typing import Callable, Optional

import jwt
from sqlmodel import Session

from app.models import Auditoria, Cliente
from app.services.auth import ALGORITMO, SECRET_KEY

logger = logging.getLogger("minutodesk.auditoria")

MAX_DETALLE = 600
# Campos que nunca se copian a la bitácora.
CAMPOS_PROHIBIDOS = re.compile(r"password|contrasena|token|clave|secret", re.I)
# Campos de texto libre largos: se registra que se enviaron, no su contenido.
CAMPOS_RESUMIDOS = {"texto", "descripcion", "observaciones", "comentario", "detalle", "motivo", "solucion"}


@dataclass(frozen=True)
class Accion:
    metodo: str
    patron: re.Pattern
    clave: str
    descripcion: str  # admite {id}
    entidad: Optional[str] = None
    leer_respuesta: bool = False  # para sacar el id creado o quién inició sesión


def _a(metodo, ruta, clave, descripcion, entidad=None, leer_respuesta=False) -> Accion:
    patron = re.compile("^" + ruta.replace("{id}", r"(?P<id>\d+)").replace("{nombre}", r"(?P<nombre>[\w.-]+)") + "$")
    return Accion(metodo, patron, clave, descripcion, entidad, leer_respuesta)


ACCIONES = [
    # Acceso
    _a("POST", "/auth/login", "inicio_sesion", "Inició sesión", "usuario", leer_respuesta=True),
    _a("POST", "/auth/cambiar-password", "cambio_contrasena", "Cambió su contraseña", "usuario"),
    _a("POST", "/auth/establecer-password", "establecio_contrasena", "Estableció su contraseña con un enlace", "usuario"),
    _a("POST", "/auth/olvide-password", "pidio_recuperacion", "Pidió un enlace de recuperación de contraseña", "usuario"),
    # Usuarios y áreas
    _a("POST", "/admin/usuarios", "usuario_creado", "Creó un usuario", "usuario", leer_respuesta=True),
    _a("PATCH", "/admin/usuarios/{id}", "usuario_editado", "Editó al usuario #{id}", "usuario"),
    _a("DELETE", "/admin/usuarios/{id}", "usuario_eliminado", "Eliminó o desactivó al usuario #{id}", "usuario"),
    _a("POST", "/admin/usuarios/{id}/restablecer-password", "restablecer_contrasena",
       "Envió un enlace para restablecer la contraseña del usuario #{id}", "usuario"),
    _a("POST", "/admin/areas", "area_creada", "Creó un área", "area", leer_respuesta=True),
    _a("PATCH", "/admin/areas/{id}", "area_editada", "Editó el área #{id}", "area"),
    # Tickets
    _a("POST", "/tickets", "ticket_creado", "Creó un ticket", "ticket", leer_respuesta=True),
    _a("POST", "/tickets/alta-colaborador", "ticket_creado", "Creó un ticket de alta de colaborador", "ticket", leer_respuesta=True),
    _a("PATCH", "/tickets/{id}", "ticket_actualizado", "Actualizó el ticket #{id}", "ticket"),
    _a("POST", "/tickets/{id}/cancelar", "ticket_cancelado", "Canceló el ticket #{id}", "ticket"),
    _a("POST", "/tickets/{id}/sla/pausar", "plazo_pausado", "Pausó el plazo del ticket #{id}", "ticket"),
    _a("POST", "/tickets/{id}/sla/reanudar", "plazo_reanudado", "Reanudó el plazo del ticket #{id}", "ticket"),
    _a("POST", "/tickets/{id}/aprobaciones", "aprobacion_solicitada", "Pidió una aprobación en el ticket #{id}", "ticket"),
    _a("POST", "/aprobaciones/{id}/responder", "aprobacion_respondida", "Respondió la aprobación #{id}", "aprobacion"),
    _a("POST", "/tickets/{id}/encuesta", "encuesta_respondida", "Calificó la atención del ticket #{id}", "ticket"),
    _a("POST", "/tickets/{id}/respuesta-predefinida", "respuesta_predefinida", "Usó una respuesta predefinida en el ticket #{id}", "ticket"),
    _a("POST", "/tickets/{id}/vincular", "ticket_vinculado", "Vinculó el ticket #{id} con otro", "ticket"),
    _a("DELETE", "/tickets/{id}/vincular", "ticket_desvinculado", "Quitó el vínculo del ticket #{id}", "ticket"),
    _a("POST", "/respuestas-predefinidas", "plantilla_creada", "Creó una respuesta predefinida", "plantilla", leer_respuesta=True),
    _a("PATCH", "/respuestas-predefinidas/{id}", "plantilla_editada", "Editó la respuesta predefinida #{id}", "plantilla"),
    _a("DELETE", "/respuestas-predefinidas/{id}", "plantilla_eliminada", "Eliminó la respuesta predefinida #{id}", "plantilla"),
    # Archivos y datos
    _a("POST", "/tickets/{id}/adjuntos", "adjunto_subido", "Subió un archivo al ticket #{id}", "ticket"),
    _a("GET", "/adjuntos/{id}", "adjunto_descargado", "Descargó el archivo #{id}", "adjunto"),
    _a("DELETE", "/adjuntos/{id}", "adjunto_eliminado", "Eliminó el archivo #{id}", "adjunto"),
    _a("GET", "/reportes/exportar", "reporte_exportado", "Exportó los reportes", "reporte"),
    _a("POST", "/admin/respaldos", "respaldo_creado", "Creó un respaldo de la base de datos", "respaldo"),
    _a("GET", "/admin/respaldos/{nombre}", "respaldo_descargado", "Descargó un respaldo de la base de datos", "respaldo"),
    # Evaluación de Minutito (datos de la tesis)
    _a("POST", "/admin/evaluacion-minutito/generar", "evaluacion_generada", "Generó respuestas para la evaluación de Minutito", "evaluacion"),
    _a("POST", "/admin/evaluacion-minutito/pausar", "evaluacion_pausada", "Pausó la generación de la evaluación de Minutito", "evaluacion"),
    _a("POST", "/admin/prueba-controlada/pausar", "prueba_pausada", "Pausó la prueba controlada", "prueba"),
    _a("POST", "/admin/evaluacion-historico/pausar", "historico_pausado", "Pausó la generación de las incidencias del histórico", "evaluacion"),
    _a("POST", "/admin/evaluacion-minutito/{id}", "evaluacion_marcada", "Marcó el veredicto de la evaluación #{id}", "evaluacion"),
    _a("PATCH", "/admin/evaluacion-minutito/{id}/solucion", "evaluacion_solucion", "Guardó la solución esperada de la evaluación #{id}", "evaluacion"),
    _a("POST", "/admin/prueba-controlada/generar", "prueba_generada", "Generó conversaciones de la prueba controlada", "prueba"),
    _a("POST", "/admin/prueba-controlada/{id}", "prueba_marcada", "Marcó el veredicto de la prueba #{id}", "prueba"),
    _a("POST", "/admin/evaluacion-historico/generar", "historico_generado", "Generó respuestas de Minutito para las incidencias del histórico", "evaluacion"),
    _a("POST", "/admin/evaluacion-historico/{id}", "historico_marcado", "Marcó el veredicto de la incidencia histórica #{id}", "evaluacion"),
]

TITULOS = {a.clave: a.descripcion.replace(" #{id}", "").replace("{id}", "") for a in ACCIONES}
TITULOS["acceso_denegado"] = "Intento sin permiso"
TITULOS["inicio_sesion_fallido"] = "Inicio de sesión fallido"


def buscar(metodo: str, ruta: str) -> Optional[tuple[Accion, dict]]:
    for accion in ACCIONES:
        if accion.metodo == metodo:
            m = accion.patron.match(ruta)
            if m:
                return accion, m.groupdict()
    return None


def actor_del_token(autorizacion: Optional[str]) -> Optional[int]:
    if not autorizacion or not autorizacion.lower().startswith("bearer "):
        return None
    try:
        return int(jwt.decode(autorizacion[7:], SECRET_KEY, algorithms=[ALGORITMO])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def resumir_cuerpo(cuerpo: bytes, consulta: str = "") -> Optional[str]:
    """Campos enviados, sin contraseñas y sin el contenido de los textos largos."""
    partes = []
    if consulta:
        partes.append(consulta)
    if cuerpo:
        try:
            datos = json.loads(cuerpo)
        except (ValueError, UnicodeDecodeError):
            datos = None
        if isinstance(datos, dict):
            for clave, valor in datos.items():
                if CAMPOS_PROHIBIDOS.search(clave) or valor in (None, "", []):
                    continue
                if clave in CAMPOS_RESUMIDOS and isinstance(valor, str):
                    valor = f"({len(valor)} caracteres)"
                elif isinstance(valor, (list, dict)):
                    valor = json.dumps(valor, ensure_ascii=False)
                partes.append(f"{clave}: {valor}")
    texto = " · ".join(partes)
    return (texto[: MAX_DETALLE - 1] + "…" if len(texto) > MAX_DETALLE else texto) or None


def registrar(
    abrir_sesion: Callable[[], Session],
    *,
    metodo: str,
    ruta: str,
    consulta: str,
    estado_http: int,
    autorizacion: Optional[str],
    cuerpo: bytes,
    respuesta: Optional[bytes],
    ip: Optional[str],
) -> None:
    encontrada = buscar(metodo, ruta)
    if encontrada is None:
        return
    accion, grupos = encontrada
    # Se registran las acciones que salieron bien, los intentos sin permiso y los
    # inicios de sesión fallidos; el resto de errores (datos mal escritos) no.
    if estado_http >= 400 and estado_http not in (401, 403, 429):
        return
    if estado_http in (401, 429) and accion.clave != "inicio_sesion":
        return

    actor_id = actor_del_token(autorizacion)
    entidad_id = int(grupos["id"]) if grupos.get("id") else None
    clave, descripcion, exito = accion.clave, accion.descripcion.format(id=entidad_id or ""), True
    detalle = resumir_cuerpo(cuerpo, consulta)
    actor_texto = None
    datos_respuesta = None
    if accion.leer_respuesta and respuesta and estado_http < 400:
        try:
            datos_respuesta = json.loads(respuesta)
        except ValueError:
            datos_respuesta = None

    if accion.clave == "inicio_sesion":
        try:
            correo = str(json.loads(cuerpo or b"{}").get("email", "")).strip().lower()[:120]
        except ValueError:
            correo = ""
        detalle = None
        if estado_http >= 400:
            clave, descripcion, exito, actor_texto = "inicio_sesion_fallido", "Intentó iniciar sesión sin éxito", False, correo
            detalle = "Cuenta bloqueada 15 minutos por intentos fallidos" if estado_http == 429 else None
        elif isinstance(datos_respuesta, dict):
            actor_id = (datos_respuesta.get("cliente") or {}).get("id")
    elif estado_http == 403:
        clave, exito = "acceso_denegado", False
        descripcion = f"Intentó sin permiso: {descripcion[0].lower()}{descripcion[1:]}"
    elif isinstance(datos_respuesta, dict) and datos_respuesta.get("id") is not None:
        entidad_id = datos_respuesta["id"]
        descripcion = f"{descripcion} (#{entidad_id})"

    try:
        with abrir_sesion() as session:
            if actor_id is not None and actor_texto is None:
                persona = session.get(Cliente, actor_id)
                actor_texto = persona.nombre if persona else None
                if persona is None:
                    actor_id = None
            session.add(
                Auditoria(
                    actor_id=actor_id,
                    actor=actor_texto,
                    accion=clave,
                    descripcion=descripcion,
                    entidad=accion.entidad,
                    entidad_id=entidad_id,
                    detalle=detalle,
                    exito=exito,
                    ip=ip,
                )
            )
            session.commit()
    except Exception:  # la bitácora nunca debe romper la acción que ya se hizo
        logger.exception("No se pudo registrar la acción %s en la bitácora", clave)

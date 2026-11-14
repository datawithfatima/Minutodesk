"""Envío de correos.

Con SMTP_HOST definido en .env se envía por SMTP, en HTML con la identidad del portal y
una versión de texto plano. Sin él (modo desarrollo) el correo se guarda como archivo de
texto en backend/correos_enviados/ y se avisa en el log, para poder probar los flujos
sin un servidor de correo.
"""
import logging
import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from app.services.plantilla_correo import Correo

logger = logging.getLogger("minutodesk.correo")

DIRECTORIO_SALIDA = Path(__file__).resolve().parents[2] / "correos_enviados"


def base_frontend() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def enlace_establecer_password(token: str) -> str:
    return f"{base_frontend()}/establecer-password?token={quote(token)}"


def _enviar_smtp(destino: str, asunto: str, cuerpo: str, html: Optional[str]) -> None:
    host = os.environ["SMTP_HOST"]
    puerto = int(os.getenv("SMTP_PORT", "587"))
    usuario = os.getenv("SMTP_USER")
    clave = os.getenv("SMTP_PASSWORD")
    remitente = os.getenv("SMTP_FROM") or usuario

    mensaje = EmailMessage()
    mensaje["From"] = f"MinutoDesk <{remitente}>"
    mensaje["To"] = destino
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)
    if html:
        mensaje.add_alternative(html, subtype="html")

    if puerto == 465:
        with smtplib.SMTP_SSL(host, puerto, timeout=20) as servidor:
            if usuario:
                servidor.login(usuario, clave)
            servidor.send_message(mensaje)
        return

    with smtplib.SMTP(host, puerto, timeout=20) as servidor:
        servidor.ehlo()
        if os.getenv("SMTP_TLS", "1") != "0":
            servidor.starttls()
            servidor.ehlo()
        if usuario:
            servidor.login(usuario, clave)
        servidor.send_message(mensaje)


def _guardar_archivo(destino: str, asunto: str, cuerpo: str, html: Optional[str]) -> Path:
    DIRECTORIO_SALIDA.mkdir(parents=True, exist_ok=True)
    seguro = re.sub(r"[^A-Za-z0-9._-]", "_", destino)
    nombre = f"{datetime.now():%Y%m%d_%H%M%S_%f}_{seguro}"
    ruta = DIRECTORIO_SALIDA / f"{nombre}.txt"
    ruta.write_text(f"Para: {destino}\nAsunto: {asunto}\n\n{cuerpo}\n", encoding="utf-8")
    if html:
        (DIRECTORIO_SALIDA / f"{nombre}.html").write_text(html, encoding="utf-8")
    logger.warning("Correo guardado en %s (SMTP no disponible o no configurado)", ruta)
    return ruta


def enviar_correo(destino: str, asunto: str, cuerpo: str, html: Optional[str] = None) -> str:
    """Devuelve "smtp" si salió por correo, o "archivo" si quedó guardado en disco."""
    if os.getenv("SMTP_HOST"):
        try:
            _enviar_smtp(destino, asunto, cuerpo, html)
            return "smtp"
        except Exception:
            logger.exception("No se pudo enviar el correo por SMTP")
    _guardar_archivo(destino, asunto, cuerpo, html)
    return "archivo"


def enviar(destino: str, correo: Correo) -> str:
    """Envía un correo armado con la plantilla del portal (HTML + texto)."""
    return enviar_correo(destino, correo.asunto, correo.texto(), correo.html())


def _primer_nombre(nombre: str) -> str:
    return nombre.split()[0] if nombre and nombre.split() else nombre


def enviar_recuperacion(destino: str, nombre: str, token: str, vigencia: str = "30 minutos") -> str:
    return enviar(
        destino,
        Correo(
            asunto="Restablece tu contraseña de MinutoDesk",
            rotulo="Tu cuenta",
            titulo="Restablece tu contraseña",
            saludo=f"Hola {_primer_nombre(nombre)},",
            parrafos=[
                "Recibimos una solicitud para restablecer tu contraseña de MinutoDesk.",
                f"Entra al enlace para elegir una nueva. Vence en {vigencia} y solo funciona una vez.",
            ],
            boton="Elegir contraseña nueva",
            enlace=enlace_establecer_password(token),
            nota="Si no fuiste tú, ignora este mensaje: tu contraseña actual sigue siendo válida.",
        ),
    )


def enviar_activacion(destino: str, nombre: str, token: str) -> str:
    return enviar(
        destino,
        Correo(
            asunto="Activa tu cuenta de MinutoDesk",
            rotulo="Bienvenida al portal",
            titulo="Se creó tu cuenta en MinutoDesk",
            saludo=f"Hola {_primer_nombre(nombre)},",
            parrafos=[
                "MinutoDesk es la mesa de ayuda de TI: desde aquí pides soporte, sigues tus tickets y "
                "conversas con Minutito, el asistente virtual.",
                "Entra al enlace para elegir tu contraseña. Vence en 3 días y solo funciona una vez.",
            ],
            boton="Activar mi cuenta",
            enlace=enlace_establecer_password(token),
            nota="Nadie más conoce tu contraseña: ni el administrador ni el equipo de soporte.",
        ),
    )


def enviar_aviso_aprobacion(destino: str, nombre: str, ticket_id: int, descripcion: str) -> str:
    return enviar(
        destino,
        Correo(
            asunto=f"Aprobación pendiente del ticket #{ticket_id}",
            rotulo=f"Ticket #{ticket_id}",
            titulo="Necesitamos tu aprobación",
            etiqueta="Aprobación pendiente",
            tono="aviso",
            saludo=f"Hola {_primer_nombre(nombre)},",
            parrafos=["El equipo de soporte necesita tu aprobación para continuar con este ticket:"],
            cita=descripcion,
            cita_rotulo="Qué hay que aprobar",
            boton="Revisar y responder",
            enlace=f"{base_frontend()}/login",
            nota="La encontrarás en la sección «Aprobaciones» del portal. Mientras esté pendiente, el plazo del ticket queda en pausa.",
        ),
    )

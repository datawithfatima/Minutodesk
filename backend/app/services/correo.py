"""Envío de correos (recuperación de contraseña).

Con SMTP_HOST definido en .env se envía por SMTP. Sin él (modo desarrollo) el
correo se guarda como archivo en backend/correos_enviados/ y se avisa en el log,
para poder probar los flujos sin un servidor de correo.
"""
import logging
import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger("minutodesk.correo")

DIRECTORIO_SALIDA = Path(__file__).resolve().parents[2] / "correos_enviados"


def enlace_establecer_password(token: str) -> str:
    base = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"{base}/establecer-password?token={quote(token)}"


def _enviar_smtp(destino: str, asunto: str, cuerpo: str) -> None:
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


def _guardar_archivo(destino: str, asunto: str, cuerpo: str) -> Path:
    DIRECTORIO_SALIDA.mkdir(parents=True, exist_ok=True)
    seguro = re.sub(r"[^A-Za-z0-9._-]", "_", destino)
    ruta = DIRECTORIO_SALIDA / f"{datetime.now():%Y%m%d_%H%M%S_%f}_{seguro}.txt"
    ruta.write_text(f"Para: {destino}\nAsunto: {asunto}\n\n{cuerpo}\n", encoding="utf-8")
    logger.warning("Correo guardado en %s (SMTP no disponible o no configurado)", ruta)
    return ruta


def enviar_correo(destino: str, asunto: str, cuerpo: str) -> str:
    """Devuelve "smtp" si salió por correo, o "archivo" si quedó guardado en disco."""
    if os.getenv("SMTP_HOST"):
        try:
            _enviar_smtp(destino, asunto, cuerpo)
            return "smtp"
        except Exception:
            logger.exception("No se pudo enviar el correo por SMTP")
    _guardar_archivo(destino, asunto, cuerpo)
    return "archivo"


def enviar_recuperacion(destino: str, nombre: str, token: str, vigencia: str = "30 minutos") -> str:
    cuerpo = (
        f"Hola {nombre},\n\n"
        "Recibimos una solicitud para restablecer tu contraseña de MinutoDesk.\n"
        f"Entra a este enlace para elegir una nueva (vence en {vigencia} y solo funciona una vez):\n\n"
        f"{enlace_establecer_password(token)}\n\n"
        "Si no fuiste tú, ignora este mensaje: tu contraseña actual sigue siendo válida."
    )
    return enviar_correo(destino, "Restablece tu contraseña de MinutoDesk", cuerpo)


def enviar_activacion(destino: str, nombre: str, token: str) -> str:
    cuerpo = (
        f"Hola {nombre},\n\n"
        "Se creó tu cuenta en MinutoDesk, la mesa de ayuda.\n"
        "Entra a este enlace para elegir tu contraseña (vence en 3 días y solo funciona una vez):\n\n"
        f"{enlace_establecer_password(token)}\n\n"
        "Nadie más conoce tu contraseña: ni el administrador ni el equipo de soporte."
    )
    return enviar_correo(destino, "Activa tu cuenta de MinutoDesk", cuerpo)


def enviar_aviso_aprobacion(destino: str, nombre: str, ticket_id: int, descripcion: str) -> str:
    base = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    cuerpo = (
        f"Hola {nombre},\n\n"
        f"El equipo de soporte necesita tu aprobación para continuar con el ticket #{ticket_id}:\n\n"
        f"{descripcion}\n\n"
        f"Revísala y respóndela en MinutoDesk, sección «Aprobaciones»: {base}/login"
    )
    return enviar_correo(destino, f"Aprobación pendiente del ticket #{ticket_id}", cuerpo)

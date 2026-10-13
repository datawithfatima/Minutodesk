"""Opciones fijas del formulario de tickets y del alta de colaborador.

Se editan aquí (son listas de la operación, no del código de la aplicación) y el
frontend las pide a /tickets/catalogos, así que cambiarlas no exige tocar pantallas.
"""
import re
from typing import Optional

# Los nombres coinciden con los del CSV histórico y con las clases del clasificador de
# tipo, para poder comparar lo que sugiere el SVM con lo que elige la persona.
TIPO_INCIDENCIA = "Incidencia o problema técnico"
TIPO_SOLICITUD = "Solicitud de servicio (Nuevo requerimiento, configuraciones, etc.)"
TIPO_ACCESOS = "Gestión de usuarios y accesos (Creación, modificación, desactivación, permisos o roles)"

TIPOS = [
    {
        "nombre": TIPO_INCIDENCIA,
        "titulo": "Incidencia o problema técnico",
        "ayuda": "Algo dejó de funcionar o falla.",
    },
    {
        "nombre": TIPO_SOLICITUD,
        "titulo": "Solicitud de servicio",
        "ayuda": "Un nuevo requerimiento, configuración o mejora.",
    },
    {
        "nombre": TIPO_ACCESOS,
        "titulo": "Gestión de usuarios y accesos",
        "ayuda": "Alta de un nuevo colaborador, permisos o roles.",
    },
]
NOMBRES_TIPO = [t["nombre"] for t in TIPOS]

PRIORIDADES = ["Crítica", "Alta", "Normal", "Baja"]
PRIORIDAD_POR_DEFECTO = "Normal"

# Categoría que llevan los tickets de alta de colaborador (no la predice el SVM).
CATEGORIA_ALTA = "Creación de Usuario"
CATEGORIA_OTROS = "Otros"

LISTAS_DISTRIBUCION = [
    "Fiscalización",
    "Contabilidad",
    "Superintendentes y Residentes de Obra",
    "Tesorería",
    "Compras",
    "Finanzas",
    "Control de Costos",
]

APLICACIONES = [
    "Adobe Photoshop",
    "Facturación Electrónica",
    "Interpro",
    "Project",
    "SAP HANA 4",
    "Adobe Indesign",
    "Bluebeam",
    "Power BI",
    "Salesforce",
    "Autocad",
    "Biotime",
    "SAP BO",
    "Heinsohn Nomina",
    "Adobe Illustrator",
    "Olk",
]

LICENCIAS_SAP = [
    {"nombre": "Financiera", "ayuda": "Transacciones contables y financieras."},
    {"nombre": "Profesional", "ayuda": "Completa para todos los módulos de SAP."},
    {"nombre": "Logística", "ayuda": "Transacciones de compras, ventas e inventario."},
]
NOMBRES_LICENCIA_SAP = [lic["nombre"] for lic in LICENCIAS_SAP]

# Archivos adjuntos: lo que permitía el formulario anterior (Word, Excel, PPT, PDF, imagen,
# video y audio) más texto plano, útil para pegar registros de errores.
MAX_ADJUNTOS = 3
MAX_BYTES_ADJUNTO = 10 * 1024 * 1024
TIPOS_DE_ARCHIVO = {
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".txt": "text/plain",
    ".log": "text/plain",
}


def cedula_valida(cedula: Optional[str]) -> bool:
    """Cédula ecuatoriana de persona natural: 10 dígitos, provincia válida y dígito
    verificador (módulo 10). El formulario anterior ya exigía una cédula real."""
    if not cedula or not re.fullmatch(r"\d{10}", cedula):
        return False
    provincia = int(cedula[:2])
    if not (1 <= provincia <= 24 or provincia == 30) or int(cedula[2]) > 5:
        return False
    suma = 0
    for i in range(9):
        d = int(cedula[i]) * (2 if i % 2 == 0 else 1)
        suma += d - 9 if d > 9 else d
    return (10 - suma % 10) % 10 == int(cedula[9])

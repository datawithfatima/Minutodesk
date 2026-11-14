"""Lee el texto de las capturas que se le envían a Minutito.

El modelo de Minutito solo entiende texto. Con el OCR que ya trae Windows (en el idioma del
sistema, sin internet ni programas extra) se saca el texto de la imagen, por ejemplo el
mensaje de un error, y se le pasa a Minutito junto con el mensaje. Tarda menos de un
segundo. Fuera de Windows, o si algo falla, devuelve "" y Minutito sigue sin el texto.
"""
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).with_name("ocr_windows.ps1")
TIMEOUT_SEGUNDOS = 30
MAX_CARACTERES = 1500  # una captura con mucho texto no debe llenar el contexto del modelo


def leer_texto(ruta: Path) -> str:
    if os.name != "nt":
        return ""
    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(SCRIPT), str(ruta)],
            capture_output=True,
            timeout=TIMEOUT_SEGUNDOS,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if resultado.returncode != 0:
        return ""
    lineas = [l.strip() for l in resultado.stdout.decode("utf-8", errors="replace").splitlines()]
    texto = "\n".join(l for l in lineas if l)
    return texto[:MAX_CARACTERES].strip()

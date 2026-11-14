"""Respaldo automático de la base de datos.

Copia minutodesk.db a backend/respaldos/ con la API de respaldo de SQLite, que hace una
copia consistente aunque la aplicación esté escribiendo. Al arrancar el backend y luego
cada hora se revisa si el último respaldo tiene más de RESPALDO_HORAS (24 por defecto):
si es así, se hace uno nuevo. Se conservan los últimos RESPALDO_CONSERVAR (14). Se apaga
con RESPALDO_AUTOMATICO=0. El administrador también puede crear uno a mano y
descargarlo desde «Bitácora y respaldos». La carpeta no se sube a git (*.db).
"""
import asyncio
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.database import sqlite_file_name

logger = logging.getLogger("minutodesk.respaldo")

DIRECTORIO_BASE = Path(__file__).resolve().parents[2]  # backend/
DIRECTORIO = DIRECTORIO_BASE / "respaldos"
PATRON = re.compile(r"^minutodesk-(\d{8}-\d{6})(-manual)?\.db$")
REVISAR_CADA_SEGUNDOS = 3600


def _horas() -> float:
    return float(os.getenv("RESPALDO_HORAS", "24"))


def _conservar() -> int:
    return max(1, int(os.getenv("RESPALDO_CONSERVAR", "14")))


def listar(directorio: Optional[Path] = None) -> list[dict]:
    """Respaldos existentes, del más reciente al más antiguo."""
    carpeta = directorio or DIRECTORIO
    if not carpeta.exists():
        return []
    salida = []
    for archivo in carpeta.iterdir():
        m = PATRON.match(archivo.name)
        if not m:
            continue
        salida.append(
            {
                "nombre": archivo.name,
                "fecha": datetime.strptime(m.group(1), "%Y%m%d-%H%M%S"),
                "manual": bool(m.group(2)),
                "tamano": archivo.stat().st_size,
            }
        )
    return sorted(salida, key=lambda r: r["fecha"], reverse=True)


def ruta(nombre: str, directorio: Optional[Path] = None) -> Optional[Path]:
    """Ruta de un respaldo por su nombre, solo si es uno de los respaldos (evita rutas arbitrarias)."""
    if not PATRON.match(nombre or ""):
        return None
    archivo = (directorio or DIRECTORIO) / nombre
    return archivo if archivo.is_file() else None


def crear(manual: bool = False, origen: Optional[Path] = None, directorio: Optional[Path] = None) -> dict:
    carpeta = directorio or DIRECTORIO
    carpeta.mkdir(parents=True, exist_ok=True)
    fuente = origen or DIRECTORIO_BASE / sqlite_file_name
    ahora = datetime.now()
    while True:  # dos respaldos en el mismo segundo no se pisan
        nombre = f"minutodesk-{ahora:%Y%m%d-%H%M%S}{'-manual' if manual else ''}.db"
        destino = carpeta / nombre
        if not destino.exists():
            break
        ahora += timedelta(seconds=1)
    con_origen = sqlite3.connect(fuente)
    con_destino = sqlite3.connect(destino)
    try:
        with con_destino:
            con_origen.backup(con_destino)
        resultado = con_destino.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        con_destino.close()
        con_origen.close()
    if resultado != "ok":
        destino.unlink(missing_ok=True)
        raise RuntimeError(f"El respaldo no pasó la verificación de integridad: {resultado}")
    _podar(carpeta)
    logger.info("Respaldo creado: %s", nombre)
    return next(r for r in listar(carpeta) if r["nombre"] == nombre)


def _podar(carpeta: Path) -> None:
    """Deja solo los últimos N respaldos automáticos (los manuales no se borran solos)."""
    automaticos = [r for r in listar(carpeta) if not r["manual"]]
    for viejo in automaticos[_conservar():]:
        (carpeta / viejo["nombre"]).unlink(missing_ok=True)


def hace_falta(directorio: Optional[Path] = None) -> bool:
    respaldos = listar(directorio)
    return not respaldos or datetime.now() - respaldos[0]["fecha"] >= timedelta(hours=_horas())


def estado() -> dict:
    respaldos = listar()
    return {
        "automatico": os.getenv("RESPALDO_AUTOMATICO", "1") != "0",
        "cada_horas": _horas(),
        "conservar": _conservar(),
        "carpeta": str(DIRECTORIO),
        "ultimo": respaldos[0]["fecha"] if respaldos else None,
        "respaldos": respaldos,
    }


async def bucle() -> None:
    """Revisa al arrancar y luego cada hora si toca un respaldo automático."""
    while True:
        try:
            if hace_falta():
                await asyncio.get_running_loop().run_in_executor(None, crear)
        except Exception:  # un fallo no debe tumbar el backend
            logger.exception("No se pudo crear el respaldo automático")
        await asyncio.sleep(REVISAR_CADA_SEGUNDOS)

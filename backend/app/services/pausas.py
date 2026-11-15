"""Pausa de las corridas largas con Minutito (evaluación, prueba controlada, histórico).

Al pausar, la corrida termina el caso que está haciendo y se detiene: lo ya generado y lo
ya marcado se conservan. Se anota en un archivo (no en memoria) para que «Reanudar» siga
funcionando aunque el servidor se reinicie. Si la corrida era «volver a generar todas»,
se guarda cuándo empezó: al reanudar se rehacen solo los casos generados antes de esa hora.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

ARCHIVO = Path(__file__).resolve().parents[2] / "corridas_pausadas.json"


def _leer() -> dict:
    try:
        return json.loads(ARCHIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _escribir(datos: dict) -> None:
    ARCHIVO.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def anotar(nombre: str, todas_desde: Optional[datetime]) -> None:
    datos = _leer()
    datos[nombre] = {"pausada_en": datetime.now().isoformat(), "todas_desde": todas_desde.isoformat() if todas_desde else None}
    _escribir(datos)


def quitar(nombre: str) -> None:
    datos = _leer()
    if datos.pop(nombre, None) is not None:
        _escribir(datos)


def esta_pausada(nombre: str) -> bool:
    return nombre in _leer()


def todas_desde(nombre: str) -> Optional[datetime]:
    """Hora de inicio de una corrida «todas» pausada (None si no hay o era «las que faltan»)."""
    valor = (_leer().get(nombre) or {}).get("todas_desde")
    return datetime.fromisoformat(valor) if valor else None

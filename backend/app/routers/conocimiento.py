"""Base de conocimiento para el usuario: las mismas fichas de pasos verificados que usa
Minutito (services/conocimiento.py), para que la persona pueda resolver sola sin abrir
el chat. Solo lectura: no cambia las fichas ni lo que Minutito responde, y consultarla
no crea conversaciones ni cuenta en los indicadores de Minutito.
"""
import re
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import SQLModel

from app.models import Cliente
from app.services.auth import obtener_usuario_actual
from app.services.conocimiento import FICHAS, buscar_ficha, normalizar

router = APIRouter()


class FichaRead(SQLModel):
    clave: str
    tema: str
    pasos: list[str]
    palabras: list[str]  # para buscar en la página (sin tildes)


class ConocimientoRead(SQLModel):
    fichas: list[FichaRead]
    # Con una búsqueda: la ficha que Minutito usaría para ese problema (si reconoce el tema).
    sugerida: Optional[str] = None


def _clave(tema: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalizar(tema)).strip("-")


@router.get("", response_model=ConocimientoRead)
def base_de_conocimiento(q: Optional[str] = None, usuario: Cliente = Depends(obtener_usuario_actual)):
    fichas = [
        FichaRead(
            clave=_clave(f.tema),
            tema=f.tema[:1].upper() + f.tema[1:],
            pasos=list(f.pasos),
            palabras=list(f.fuertes) + list(f.debiles),
        )
        for f in FICHAS
    ]
    sugerida = buscar_ficha(q[:500]) if q and q.strip() else None
    return ConocimientoRead(fichas=fichas, sugerida=_clave(sugerida.tema) if sugerida else None)

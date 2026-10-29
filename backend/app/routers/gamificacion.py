from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.models import Cliente
from app.services.auth import obtener_usuario_actual
from app.services.obra import ciudad

router = APIRouter()


@router.get("/ciudad")
def ciudad_de_obras(
    periodo: str = "mes",
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Ciudad MinutoDesk: las obras del Top 5 (del mes o históricas) y la propia."""
    if periodo not in ("mes", "total"):
        raise HTTPException(status_code=400, detail="Periodo no válido")
    return ciudad(session, usuario, periodo)

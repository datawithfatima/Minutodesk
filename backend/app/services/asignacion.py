"""Técnico sugerido según el sistema (categoría) del ticket.

La tabla la definió el área de sistemas: quién suele atender cada sistema. Se compara
por nombre con las cuentas de rol «tecnico» activas (sin distinguir mayúsculas ni
tildes), así que basta con crear la cuenta del técnico para que empiece a recibir tickets.

Si un sistema tiene varios técnicos, se elige al que tiene menos tickets pendientes
(Nuevo o En proceso); si empatan, al primero de la lista. «Otros» lo puede atender
cualquier técnico. Si ninguno de los técnicos del sistema tiene cuenta todavía, el
ticket queda sin asignar para que lo tome quien corresponda.
"""
import json
import unicodedata
from pathlib import Path
from typing import Optional

from sqlmodel import Session, func, select

from app.models import Cliente, Ticket
from app.services.catalogos import CATEGORIA_OTROS

TODOS = "*"

# Los nombres reales de los técnicos no van en el código (el repositorio puede ser
# público): se leen de backend/tecnicos_por_categoria.json, que git ignora. Si no existe se
# usa el ejemplo (tecnicos_por_categoria.example.json, con nombres ficticios).
CARPETA_BACKEND = Path(__file__).resolve().parents[2]
ARCHIVO_TECNICOS = CARPETA_BACKEND / "tecnicos_por_categoria.json"
ARCHIVO_EJEMPLO = CARPETA_BACKEND / "tecnicos_por_categoria.example.json"


def cargar_tabla(archivo: Optional[Path] = None) -> dict[str, list[str]]:
    origen = archivo or (ARCHIVO_TECNICOS if ARCHIVO_TECNICOS.exists() else ARCHIVO_EJEMPLO)
    try:
        datos = json.loads(origen.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        datos = {}
    tabla = {str(k): [str(n) for n in v] for k, v in datos.items() if isinstance(v, list)}
    tabla[CATEGORIA_OTROS] = [TODOS]  # «Otros» siempre lo puede atender cualquier técnico
    return tabla


TECNICOS_POR_CATEGORIA: dict[str, list[str]] = cargar_tabla()

ESTADOS_PENDIENTES = ("abierto", "en_proceso")


def _normalizar(texto: str) -> list[str]:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower().split()


def _coincide(nombre_tabla: str, nombre_cuenta: str) -> bool:
    """«Ana Lopez» coincide con «Ana López» y con «Ana López Vera»."""
    return set(_normalizar(nombre_tabla)) <= set(_normalizar(nombre_cuenta))


def candidatos(session: Session, categoria: Optional[str]) -> list[Cliente]:
    """Técnicos con cuenta activa que atienden esta categoría, en el orden de la tabla."""
    nombres = TECNICOS_POR_CATEGORIA.get(categoria or "")
    if not nombres:
        return []
    tecnicos = session.exec(
        select(Cliente).where(Cliente.rol == "tecnico", Cliente.activo == True).order_by(Cliente.id)  # noqa: E712
    ).all()
    if nombres == [TODOS]:
        return list(tecnicos)
    elegidos: list[Cliente] = []
    for nombre in nombres:
        for t in tecnicos:
            if t not in elegidos and _coincide(nombre, t.nombre):
                elegidos.append(t)
    return elegidos


def tecnico_sugerido(
    session: Session, categoria: Optional[str], excluir: Optional[int] = None
) -> Optional[Cliente]:
    elegibles = [t for t in candidatos(session, categoria) if t.id != excluir]
    if len(elegibles) <= 1:
        return elegibles[0] if elegibles else None
    ids = [t.id for t in elegibles]
    carga = dict(
        session.exec(
            select(Ticket.tecnico_id, func.count())
            .where(Ticket.tecnico_id.in_(ids), Ticket.estado.in_(ESTADOS_PENDIENTES))
            .group_by(Ticket.tecnico_id)
        ).all()
    )
    # min() conserva el primero ante un empate, o sea el orden de la tabla.
    return min(elegibles, key=lambda t: carga.get(t.id, 0))


def asignar_automaticamente(session: Session, ticket: Ticket, excluir: Optional[int] = None) -> None:
    """Pone el técnico sugerido según la categoría vigente, salvo que alguien haya
    elegido o tomado el técnico a mano (eso no se pisa). `excluir`: el técnico que acaba
    de liberar el ticket, para no devolvérselo."""
    if ticket.tecnico_manual or ticket.tomado_en is not None or ticket.estado not in ESTADOS_PENDIENTES:
        return
    categoria = ticket.categoria or ticket.categoria_predicha
    # Si el técnico actual también atiende la nueva categoría, se queda con el ticket.
    if ticket.tecnico_id is not None and any(t.id == ticket.tecnico_id for t in candidatos(session, categoria)):
        return
    sugerido = tecnico_sugerido(session, categoria, excluir)
    ticket.tecnico_id = sugerido.id if sugerido else None

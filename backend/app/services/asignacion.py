"""Técnico sugerido según el sistema (categoría) del ticket.

La tabla la definió el área de sistemas: quién suele atender cada sistema. Se compara
por nombre con las cuentas de rol «tecnico» activas (sin distinguir mayúsculas ni
tildes), así que basta con crear la cuenta del técnico para que empiece a recibir tickets.

Si un sistema tiene varios técnicos, se elige al que tiene menos tickets pendientes
(Nuevo o En proceso); si empatan, al primero de la lista. «Otros» lo puede atender
cualquier técnico. Si ninguno de los técnicos del sistema tiene cuenta todavía, el
ticket queda sin asignar para que lo tome quien corresponda.
"""
import unicodedata
from typing import Optional

from sqlmodel import Session, func, select

from app.models import Cliente, Ticket
from app.services.catalogos import CATEGORIA_OTROS

TODOS = "*"

TECNICOS_POR_CATEGORIA: dict[str, list[str]] = {
    "Heinsohn Nomina": ["Jimmy Lopez"],
    "Internet": ["Geovanny Remache", "Fátima Reyes"],
    "Interpro": ["Geovanny Remache", "Fátima Reyes"],
    "Laptops - Impresoras": ["Geovanny Remache", "Fátima Reyes"],
    "Mantenimiento de equipos": ["Geovanny Remache", "Fátima Reyes"],
    "Office": ["Geovanny Remache", "Fátima Reyes"],
    "Portal de Planificación": ["Ricardo Neumane"],
    "Portal de Proveedores": ["Jimmy Lopez"],
    "Power BI": ["Jimmy Lopez"],
    "SAP": ["Jimmy Lopez", "Ricardo Neumane", "Luis Peñafiel", "Mercedes Lara"],
    "Salesforce": ["Carlos Sanchez"],
    "Webdox": ["Carlos Sanchez", "Ricardo Neumane"],
    CATEGORIA_OTROS: [TODOS],
}

ESTADOS_PENDIENTES = ("abierto", "en_proceso")


def _normalizar(texto: str) -> list[str]:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower().split()


def _coincide(nombre_tabla: str, nombre_cuenta: str) -> bool:
    """«Jimmy Lopez» coincide con «Jimmy López» y con «Jimmy López Vera»."""
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


def tecnico_sugerido(session: Session, categoria: Optional[str]) -> Optional[Cliente]:
    elegibles = candidatos(session, categoria)
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


def asignar_automaticamente(session: Session, ticket: Ticket) -> None:
    """Pone el técnico sugerido según la categoría vigente, salvo que alguien haya
    elegido o tomado el técnico a mano (eso no se pisa)."""
    if ticket.tecnico_manual or ticket.estado not in ESTADOS_PENDIENTES:
        return
    categoria = ticket.categoria or ticket.categoria_predicha
    # Si el técnico actual también atiende la nueva categoría, se queda con el ticket.
    if ticket.tecnico_id is not None and any(t.id == ticket.tecnico_id for t in candidatos(session, categoria)):
        return
    sugerido = tecnico_sugerido(session, categoria)
    ticket.tecnico_id = sugerido.id if sugerido else None

"""Tomar y liberar tickets.

Un ticket puede estar:
- sin asignar, o con un técnico **sugerido** por la asignación automática según su
  categoría (`tomado_en` nulo): cualquier técnico puede tomarlo;
- **tomado** (`tomado_en` con fecha): es del técnico asignado. Lo toma quien pulsa
  «Tomar», lo pasa a «En proceso», lo resuelve o le escribe la primera respuesta al
  solicitante. El administrador también puede asignárselo a alguien, y queda igual de
  tomado. Mientras esté tomado, los demás técnicos no pueden tomarlo, reasignarlo ni
  cambiarlo; el administrador sí.

El técnico a cargo lo puede liberar con un motivo obligatorio (como la pausa del plazo):
vuelve a «Nuevo» y la asignación automática lo sugiere a otro técnico del sistema (nunca
al mismo); si no hay otro, queda sin asignar para que lo tome quien corresponda.

Para que dos técnicos no se queden con el mismo ticket, la toma es una sola sentencia
UPDATE con la condición «nadie lo ha tomado o ya es mío»: la base de datos la aplica de a
una, así que el segundo encuentra el ticket tomado y recibe un 409.
"""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import or_, update
from sqlmodel import Session

from app.models import AsignacionTicket, Auditoria, Cliente, Ticket

ESTADOS_FINALES = ("resuelto", "cancelado")

MOTIVOS_LIBERACION = {
    "otra_area": "No corresponde a mi sistema o área",
    "especialista": "Necesita a otro especialista",
    "carga": "Tengo demasiados tickets pendientes",
    "ausencia": "Me ausento (vacaciones, permiso, capacitación)",
    "error": "Lo tomé por error",
    "otro": "Otro motivo",
}
MIN_DETALLE = 5
MAX_DETALLE = 500


def es_admin(usuario: Cliente) -> bool:
    return usuario.rol == "administrador"


def esta_tomado(ticket: Ticket) -> bool:
    return ticket.tomado_en is not None and ticket.tecnico_id is not None


def tomado_por_otro(ticket: Ticket, usuario: Cliente) -> bool:
    return esta_tomado(ticket) and ticket.tecnico_id != usuario.id


def _nombre(session: Session, cliente_id: Optional[int]) -> str:
    persona = session.get(Cliente, cliente_id) if cliente_id else None
    return persona.nombre if persona else "otro técnico"


def exigir_que_pueda_atender(session: Session, ticket: Ticket, usuario: Cliente) -> None:
    """403 si el ticket es de otro técnico (el administrador siempre puede)."""
    if tomado_por_otro(ticket, usuario) and not es_admin(usuario):
        raise HTTPException(
            status_code=403,
            detail=f"Este ticket lo atiende {_nombre(session, ticket.tecnico_id)}. "
            "Solo esa persona o un administrador pueden cambiarlo.",
        )


def registrar(
    session: Session,
    ticket_id: int,
    accion: str,
    tecnico_id: Optional[int],
    por: Cliente,
    *,
    via: Optional[str] = None,
    motivo: Optional[str] = None,
    detalle: Optional[str] = None,
) -> None:
    session.add(
        AsignacionTicket(
            ticket_id=ticket_id,
            accion=accion,
            tecnico_id=tecnico_id,
            por_id=por.id,
            via=via,
            motivo=motivo,
            detalle=detalle,
        )
    )


def anotar_en_bitacora(session: Session, usuario: Cliente, ticket_id: int, clave: str, descripcion: str) -> None:
    """Para las tomas que ocurren dentro de otra acción (responder, cambiar el estado):
    el middleware solo registra la acción principal, así que esta queda aparte."""
    session.add(
        Auditoria(
            actor_id=usuario.id,
            actor=usuario.nombre,
            accion=clave,
            descripcion=descripcion,
            entidad="ticket",
            entidad_id=ticket_id,
        )
    )


def tomar(session: Session, ticket: Ticket, usuario: Cliente, via: str) -> bool:
    """Deja el ticket a nombre de `usuario` si nadie lo ha tomado. Devuelve True si lo
    tomó ahora y False si ya era suyo. 409 si otro técnico lo tomó antes (también si fue
    hace un instante, en una petición simultánea). No hace commit."""
    if ticket.estado in ESTADOS_FINALES:
        raise HTTPException(status_code=409, detail=f"Este ticket ya está {ticket.estado}.")
    ya_era_mio = esta_tomado(ticket) and ticket.tecnico_id == usuario.id
    ahora = datetime.now()
    resultado = session.exec(
        update(Ticket)
        .where(
            Ticket.id == ticket.id,
            Ticket.estado.not_in(ESTADOS_FINALES),
            or_(Ticket.tomado_en.is_(None), Ticket.tecnico_id.is_(None), Ticket.tecnico_id == usuario.id),
        )
        .values(tecnico_id=usuario.id, tecnico_manual=True, tomado_en=ahora if not ya_era_mio else Ticket.tomado_en)
        .execution_options(synchronize_session=False)
    )
    session.refresh(ticket)
    if resultado.rowcount == 0:
        raise HTTPException(
            status_code=409,
            detail=f"{_nombre(session, ticket.tecnico_id)} acaba de tomar este ticket.",
        )
    if ya_era_mio:
        return False
    registrar(session, ticket.id, "tomado", usuario.id, usuario, via=via)
    if via != "boton":  # «Tomar» ya lo registra el middleware
        como = {"respuesta": "al responder", "asignacion": "al asignárselo"}.get(via, "al cambiar su estado")
        anotar_en_bitacora(session, usuario, ticket.id, "ticket_tomado", f"Tomó el ticket #{ticket.id} {como}")
    return True


def tomar_si_libre(session: Session, ticket: Ticket, usuario: Cliente, via: str) -> bool:
    """Como `tomar`, pero si otro ya lo tiene no hace nada (para el administrador, que
    puede responder o cambiar un ticket ajeno sin quitárselo a quien lo atiende)."""
    if tomado_por_otro(ticket, usuario):
        return False
    return tomar(session, ticket, usuario, via)


def reasignar(session: Session, ticket: Ticket, tecnico: Cliente, por: Cliente) -> None:
    """El administrador pasa el ticket a otro técnico: queda tomado a su nombre."""
    ticket.tecnico_id = tecnico.id
    ticket.tecnico_manual = True
    ticket.tomado_en = datetime.now()
    registrar(session, ticket.id, "reasignado", tecnico.id, por)


def liberar(session: Session, ticket: Ticket, por: Cliente, motivo: str, detalle: str) -> int:
    """Suelta el ticket. Devuelve el id del técnico que lo tenía. No hace commit."""
    anterior = ticket.tecnico_id
    ticket.tomado_en = None
    ticket.tecnico_manual = False
    ticket.tecnico_id = None
    registrar(session, ticket.id, "liberado", anterior, por, motivo=motivo, detalle=detalle)
    return anterior

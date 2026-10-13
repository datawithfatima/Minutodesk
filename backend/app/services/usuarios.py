from sqlmodel import Session, select

from app.models import Area, Cliente
from app.schemas import ClienteRead


def mapa_areas(session: Session) -> dict[int, Area]:
    return {a.id: a for a in session.exec(select(Area)).all()}


def a_cliente_read(cliente: Cliente, areas_por_id: dict[int, Area]) -> ClienteRead:
    area = areas_por_id.get(cliente.area_id)
    return ClienteRead(
        id=cliente.id,
        nombre=cliente.nombre,
        area_id=cliente.area_id,
        area=area.nombre if area else "—",
        email=cliente.email,
        rol=cliente.rol,
        activo=cliente.activo,
        pendiente_activacion=cliente.password_hash is None,
        debe_cambiar_password=cliente.debe_cambiar_password,
        puntos=cliente.puntos,
    )

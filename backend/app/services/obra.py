"""Gamificación «Mi obra»: cada persona construye su edificio con puntos de autoservicio.

Ambientada en el rubro de la empresa (constructora y promotora inmobiliaria): los niveles
son etapas de obra, cada 25 puntos sube un piso y las insignias llevan nombres del sector.
Los puntos se siguen otorgando en gamification_rules.py y en la conversación con Minutito;
aquí solo se interpretan para mostrarlos.
"""
from datetime import date, datetime, timedelta
from typing import Optional

from sqlmodel import Session, func, select

from app.models import Adjunto, Cliente, ConversacionMinutito, EventoGamificacion, Ticket

PUNTOS_POR_PISO = 25
TOP = 5

# (puntos mínimos, nombre). La etapa depende de los puntos acumulados en total.
ETAPAS = [
    (0, "Cimientos"),
    (50, "Estructura"),
    (150, "Acabados"),
    (300, "Entrega de llaves"),
]

INSIGNIAS = [
    ("primera_piedra", "Primera piedra", "Resolviste tu primera consulta con Minutito."),
    ("planos_al_dia", "Planos al día", "Resolviste 5 consultas con Minutito sin crear ticket."),
    ("obra_sin_retrasos", "Obra sin retrasos", "Usaste el autoservicio 4 semanas seguidas."),
    ("inspector", "Inspector", "Creaste un ticket desde Minutito con una captura adjunta."),
]


def etapa(puntos: int) -> dict:
    actual = ETAPAS[0]
    for e in ETAPAS:
        if puntos >= e[0]:
            actual = e
    i = ETAPAS.index(actual)
    siguiente = ETAPAS[i + 1] if i + 1 < len(ETAPAS) else None
    return {
        "etapa": actual[1],
        "numero_etapa": i + 1,
        "pisos": puntos // PUNTOS_POR_PISO,
        "siguiente_etapa": siguiente[1] if siguiente else None,
        "puntos_para_siguiente": siguiente[0] - puntos if siguiente else None,
    }


def _semanas_seguidas(fechas: list[datetime], hoy: Optional[date] = None) -> int:
    """Semanas consecutivas con actividad, contando hacia atrás desde esta semana (o la anterior)."""
    hoy = hoy or date.today()
    semanas = {(f.date() - timedelta(days=f.weekday())) for f in fechas}
    inicio = hoy - timedelta(days=hoy.weekday())
    if inicio not in semanas:
        inicio -= timedelta(weeks=1)  # la semana en curso todavía puede sumarse
    racha = 0
    while inicio in semanas:
        racha += 1
        inicio -= timedelta(weeks=1)
    return racha


def insignias(session: Session, cliente_id: int) -> list[dict]:
    resueltas = session.exec(
        select(func.count()).select_from(ConversacionMinutito).where(
            ConversacionMinutito.cliente_id == cliente_id, ConversacionMinutito.estado == "resuelta"
        )
    ).one()
    # Tickets del flujo anterior que Minutito resolvió con confirmación también cuentan.
    resueltas += session.exec(
        select(func.count()).select_from(Ticket).where(
            Ticket.cliente_id == cliente_id, Ticket.resuelto_por == "minutito"
        )
    ).one()
    fechas = session.exec(
        select(EventoGamificacion.creado_en).where(EventoGamificacion.cliente_id == cliente_id)
    ).all()
    con_captura = session.exec(
        select(ConversacionMinutito.id)
        .join(Adjunto, Adjunto.ticket_id == ConversacionMinutito.ticket_id)
        .where(ConversacionMinutito.cliente_id == cliente_id, Adjunto.subido_por_id == cliente_id)
    ).first()
    logradas = {
        "primera_piedra": resueltas >= 1,
        "planos_al_dia": resueltas >= 5,
        "obra_sin_retrasos": _semanas_seguidas(list(fechas)) >= 4,
        "inspector": con_captura is not None,
    }
    return [
        {"clave": c, "nombre": n, "descripcion": d, "obtenida": logradas[c]} for c, n, d in INSIGNIAS
    ]


def nombre_corto(nombre: str) -> str:
    """«Ana López» → «Ana L.»: en la ciudad se reconoce a la persona sin exponer su nombre completo."""
    partes = nombre.split()
    return partes[0] if len(partes) == 1 else f"{partes[0]} {partes[1][0]}."


def ciudad(session: Session, yo: Cliente, periodo: str) -> dict:
    """Las obras del Top 5 (por puntos del mes o totales) y la posición de quien consulta."""
    usuarios = session.exec(
        select(Cliente).where(Cliente.rol == "usuario", Cliente.activo == True)  # noqa: E712
    ).all()
    if periodo == "mes":
        inicio = date.today().replace(day=1)
        filas = session.exec(
            select(EventoGamificacion.cliente_id, func.sum(EventoGamificacion.puntos_otorgados))
            .where(EventoGamificacion.creado_en >= datetime.combine(inicio, datetime.min.time()))
            .group_by(EventoGamificacion.cliente_id)
        ).all()
        puntos_periodo = dict(filas)
    else:
        puntos_periodo = {u.id: u.puntos for u in usuarios}

    orden = sorted(usuarios, key=lambda u: (-puntos_periodo.get(u.id, 0), -u.puntos, u.nombre))
    posicion = {u.id: i + 1 for i, u in enumerate(orden)}

    def fila(u: Cliente) -> dict:
        return {
            "posicion": posicion[u.id],
            "nombre": "Tú" if u.id == yo.id else nombre_corto(u.nombre),
            "es_yo": u.id == yo.id,
            "puntos_periodo": puntos_periodo.get(u.id, 0),
            "puntos": u.puntos,
            **etapa(u.puntos),
            "insignias": [i["clave"] for i in insignias(session, u.id) if i["obtenida"]],
        }

    top = [fila(u) for u in orden[:TOP] if puntos_periodo.get(u.id, 0) > 0 or periodo == "total"]
    mia = fila(yo) if yo.rol == "usuario" and yo.activo else None
    return {"periodo": periodo, "top": top, "yo": mia}

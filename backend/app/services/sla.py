"""Plazo de atención (SLA) de cada ticket y su temporizador.

El plazo lo fija la tabla del área de sistemas, en días, según el tipo y la prioridad del
ticket. Por decisión de la mesa (14/11/2026) se cuentan días calendario; con
SOLO_DIAS_HABILES = True pasarían a contarse solo lunes a viernes (y fuera de FERIADOS). Corre desde
que se crea el ticket y se detiene mientras está en pausa (con motivo) o cerrado
(resuelto o cancelado). Si el ticket se reabre, continúa con el tiempo que le quedaba.
Si cambian el tipo o la prioridad, el plazo se recalcula con la tabla, pero el tiempo ya
consumido se mantiene. Todo se calcula al momento: no se guarda ningún «restante».
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable, Optional

from sqlmodel import Session, select

from app.models import Aprobacion, Cliente, HistorialEstadoTicket, PausaSla, Ticket
from app.schemas import PausaSlaRead, SlaRead
from app.services.catalogos import TIPO_ACCESOS, TIPO_INCIDENCIA, TIPO_SOLICITUD

# Días por tipo y prioridad (tabla de SLA del área).
DIAS_SLA: dict[str, dict[str, int]] = {
    TIPO_INCIDENCIA: {"Baja": 15, "Normal": 7, "Alta": 3, "Crítica": 1},
    TIPO_SOLICITUD: {"Baja": 30, "Normal": 15, "Alta": 7, "Crítica": 3},
    TIPO_ACCESOS: {"Baja": 7, "Normal": 5, "Alta": 3, "Crítica": 1},
}
SOLO_DIAS_HABILES = False
# Con SOLO_DIAS_HABILES, fechas que tampoco cuentan (además de sábados y domingos).
FERIADOS: set[date] = set()

MOTIVOS_PAUSA: dict[str, str] = {
    "aprobacion": "Aprobación pendiente",
    "usuario": "Esperando al usuario",
    "desarrollo": "Desarrollo o imprevisto",
    "proveedor": "Proveedor externo",
    "otro": "Otro motivo",
}
MIN_DETALLE = 5
MAX_DETALLE = 500

UMBRAL_POR_VENCER = 0.8  # con el 80 % consumido se avisa al técnico
SEGUNDOS_DIA = 24 * 3600
ESTADOS_CERRADOS = ("resuelto", "cancelado")

Intervalo = tuple[datetime, datetime]


# ---------- tiempo hábil ----------

def es_habil(dia: date) -> bool:
    if not SOLO_DIAS_HABILES:
        return True
    return dia.weekday() < 5 and dia not in FERIADOS


def segundos_habiles(inicio: datetime, fin: datetime) -> float:
    """Segundos que cuentan para el plazo entre dos instantes (un día cuenta entero)."""
    if fin <= inicio:
        return 0.0
    if not SOLO_DIAS_HABILES:
        return (fin - inicio).total_seconds()
    total = 0.0
    cursor = inicio
    while cursor < fin:
        siguiente = datetime.combine(cursor.date() + timedelta(days=1), time.min)
        if es_habil(cursor.date()):
            total += (min(siguiente, fin) - cursor).total_seconds()
        cursor = siguiente
    return total


def sumar_segundos_habiles(desde: datetime, segundos: float) -> datetime:
    """Instante en que, desde `desde`, se habrán consumido `segundos` de tiempo hábil."""
    cursor, restante = desde, max(0.0, segundos)
    if not SOLO_DIAS_HABILES:
        return desde + timedelta(seconds=restante)
    while True:
        siguiente = datetime.combine(cursor.date() + timedelta(days=1), time.min)
        if es_habil(cursor.date()):
            disponible = (siguiente - cursor).total_seconds()
            if restante <= disponible:
                return cursor + timedelta(seconds=restante)
            restante -= disponible
        cursor = siguiente


def _unir(intervalos: Iterable[Intervalo], desde: datetime, hasta: datetime) -> list[Intervalo]:
    """Recorta los intervalos a [desde, hasta] y une los que se solapan."""
    recortados = sorted((max(a, desde), min(b, hasta)) for a, b in intervalos if b > desde and a < hasta)
    unidos: list[Intervalo] = []
    for a, b in recortados:
        if unidos and a <= unidos[-1][1]:
            unidos[-1] = (unidos[-1][0], max(unidos[-1][1], b))
        else:
            unidos.append((a, b))
    return unidos


# ---------- plazo ----------

def dias_de_plazo(ticket: Ticket) -> Optional[int]:
    tipo = ticket.tipo or ticket.tipo_predicho
    return DIAS_SLA.get(tipo or "", {}).get(ticket.prioridad)


def _tramos_cerrado(ticket: Ticket, historial: list[HistorialEstadoTicket], ahora: datetime) -> list[Intervalo]:
    """Tramos en que el ticket estuvo resuelto o cancelado, según su historial de estados."""
    tramos: list[Intervalo] = []
    inicio: Optional[datetime] = None
    for h in sorted(historial, key=lambda x: (x.fecha, x.id or 0)):
        if h.estado_nuevo in ESTADOS_CERRADOS:
            inicio = inicio or h.fecha
        elif inicio is not None:
            tramos.append((inicio, h.fecha))
            inicio = None
    if inicio is not None:
        tramos.append((inicio, ahora))
    elif ticket.estado in ESTADOS_CERRADOS:  # sin historial (datos antiguos): desde cerrado_en
        tramos.append((ticket.cerrado_en or ahora, ahora))
    return tramos


@dataclass
class _Contexto:
    pausas: dict[int, list[PausaSla]]
    historial: dict[int, list[HistorialEstadoTicket]]
    nombres: dict[int, str]


def _contexto(session: Session, ids: list[int]) -> _Contexto:
    if not ids:
        return _Contexto({}, {}, {})
    pausas: dict[int, list[PausaSla]] = {}
    for p in session.exec(select(PausaSla).where(PausaSla.ticket_id.in_(ids)).order_by(PausaSla.inicio, PausaSla.id)):
        pausas.setdefault(p.ticket_id, []).append(p)
    historial: dict[int, list[HistorialEstadoTicket]] = {}
    for h in session.exec(select(HistorialEstadoTicket).where(HistorialEstadoTicket.ticket_id.in_(ids))):
        historial.setdefault(h.ticket_id, []).append(h)
    personas = {p.iniciada_por_id for ps in pausas.values() for p in ps} | {
        p.reanudada_por_id for ps in pausas.values() for p in ps
    }
    personas.discard(None)
    nombres = (
        {c.id: c.nombre for c in session.exec(select(Cliente).where(Cliente.id.in_(personas)))} if personas else {}
    )
    return _Contexto(pausas, historial, nombres)


def _a_pausa_read(p: PausaSla, nombres: dict[int, str]) -> PausaSlaRead:
    return PausaSlaRead(
        id=p.id,
        motivo=p.motivo,
        motivo_titulo=MOTIVOS_PAUSA.get(p.motivo, p.motivo),
        detalle=p.detalle,
        automatica=p.aprobacion_id is not None,
        inicio=p.inicio,
        fin=p.fin,
        iniciada_por=nombres.get(p.iniciada_por_id, "MinutoDesk") if p.iniciada_por_id else "MinutoDesk",
        reanudada_por=nombres.get(p.reanudada_por_id) if p.reanudada_por_id else None,
    )


def _calcular(ticket: Ticket, ctx: _Contexto, ahora: datetime) -> Optional[SlaRead]:
    dias = dias_de_plazo(ticket)
    if dias is None:
        return None
    pausas = ctx.pausas.get(ticket.id, [])
    plazo = dias * SEGUNDOS_DIA
    no_cuenta = [(p.inicio, p.fin or ahora) for p in pausas] + _tramos_cerrado(
        ticket, ctx.historial.get(ticket.id, []), ahora
    )
    consumido = segundos_habiles(ticket.creado_en, ahora) - sum(
        segundos_habiles(a, b) for a, b in _unir(no_cuenta, ticket.creado_en, ahora)
    )
    consumido = max(0.0, consumido)
    restante = plazo - consumido
    vencido = restante <= 0
    activa = next((p for p in pausas if p.fin is None), None)
    cerrado = ticket.estado in ESTADOS_CERRADOS

    if cerrado:
        estado = "incumplido" if vencido else "cumplido"
    elif activa is not None:
        estado = "pausado"
    elif vencido:
        estado = "vencido"
    elif consumido >= plazo * UMBRAL_POR_VENCER:
        estado = "por_vencer"
    else:
        estado = "en_tiempo"

    return SlaRead(
        dias=dias,
        plazo_segundos=plazo,
        consumido_segundos=int(consumido),
        restante_segundos=int(restante),
        porcentaje=int(round(100 * consumido / plazo)),
        estado=estado,
        vencido=vencido,
        vence_en=sumar_segundos_habiles(ahora, restante) if estado in ("en_tiempo", "por_vencer") else None,
        pausa_actual=_a_pausa_read(activa, ctx.nombres) if activa else None,
        pausas=[_a_pausa_read(p, ctx.nombres) for p in pausas],
    )


def calcular(session: Session, ticket: Ticket, ahora: Optional[datetime] = None) -> Optional[SlaRead]:
    return _calcular(ticket, _contexto(session, [ticket.id]), ahora or datetime.now())


def calcular_varios(
    session: Session, tickets: list[Ticket], ahora: Optional[datetime] = None
) -> dict[int, Optional[SlaRead]]:
    ctx = _contexto(session, [t.id for t in tickets])
    momento = ahora or datetime.now()
    return {t.id: _calcular(t, ctx, momento) for t in tickets}


# ---------- pausas ----------

def pausa_activa(session: Session, ticket_id: int) -> Optional[PausaSla]:
    return session.exec(
        select(PausaSla).where(PausaSla.ticket_id == ticket_id, PausaSla.fin == None)  # noqa: E711
    ).first()


def pausar(
    session: Session,
    ticket: Ticket,
    motivo: str,
    detalle: Optional[str],
    por_id: Optional[int],
    aprobacion_id: Optional[int] = None,
) -> PausaSla:
    pausa = PausaSla(
        ticket_id=ticket.id, motivo=motivo, detalle=detalle, iniciada_por_id=por_id, aprobacion_id=aprobacion_id
    )
    session.add(pausa)
    return pausa


def reanudar(session: Session, pausa: PausaSla, por_id: Optional[int], ahora: Optional[datetime] = None) -> None:
    pausa.fin = ahora or datetime.now()
    pausa.reanudada_por_id = por_id
    session.add(pausa)


def cerrar_pausa_activa(session: Session, ticket_id: int, por_id: Optional[int]) -> Optional[PausaSla]:
    """Al resolver o cancelar: la pausa termina (el tramo cerrado ya no cuenta de por sí)."""
    activa = pausa_activa(session, ticket_id)
    if activa is not None:
        reanudar(session, activa, por_id)
    return activa


def pausar_por_aprobacion(session: Session, ticket: Ticket, aprobacion: Aprobacion, por_id: int) -> Optional[PausaSla]:
    """Al pedir una aprobación el reloj se detiene solo (si no estaba ya en pausa)."""
    if pausa_activa(session, ticket.id) is not None:
        return None
    return pausar(session, ticket, "aprobacion", aprobacion.descripcion, por_id, aprobacion_id=aprobacion.id)


def reanudar_tras_aprobacion(session: Session, ticket: Ticket, por_id: int) -> Optional[PausaSla]:
    """Al responder una aprobación: si la pausa vigente la abrió el sistema y ya no queda
    ninguna aprobación pendiente, el reloj vuelve a correr. Una pausa puesta a mano se respeta."""
    activa = pausa_activa(session, ticket.id)
    if activa is None or activa.aprobacion_id is None:
        return None
    pendientes = session.exec(
        select(Aprobacion).where(Aprobacion.ticket_id == ticket.id, Aprobacion.estado == "pendiente")
    ).first()
    if pendientes is not None:
        return None
    reanudar(session, activa, por_id)
    return activa

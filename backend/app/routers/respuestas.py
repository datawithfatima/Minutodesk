"""Herramientas del personal: respuestas predefinidas para el chat del ticket y vincular
tickets duplicados.

- Respuestas predefinidas: textos listos que el técnico inserta en el chat y ajusta antes
  de enviar (no se envían solos). Cualquier técnico o administrador las usa y crea; cada
  quien edita las suyas y el administrador, todas.
- Duplicados: un ticket se vincula a su ticket principal. Si se pide, el duplicado se
  cancela con el motivo «Duplicado del ticket #X» (el mismo flujo de «Cancelar ticket»:
  no cuenta como resuelto ni da puntos). Para encontrarlos se sugieren tickets abiertos
  parecidos, comparando palabras (no usa el clasificador).
"""
import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from app.database import get_session
from app.models import Cliente, RespuestaPredefinida, Ticket
from app.routers.tickets import ESTADOS_FINALES, _con_sla, cancelar_ticket
from app.schemas import CancelarTicket, TicketRead
from app.services.auth import requerir_personal
from app.services.conocimiento import normalizar

router = APIRouter()

MAX_TITULO = 80
MAX_TEXTO = 2000
DIAS_DUPLICADOS = 30

PREDEFINIDAS_INICIALES = [
    (
        "Tomo tu caso",
        "Hola {nombre}, soy {tecnico} del equipo de sistemas. Ya tomé tu ticket #{ticket} y te escribo por aquí en cuanto tenga novedades.",
    ),
    (
        "Pedir más detalles",
        "Hola {nombre}, para avanzar con tu ticket necesito un poco más de información: ¿desde cuándo pasa, en qué equipo y qué mensaje aparece exactamente?",
    ),
    (
        "Pedir captura del error",
        "{nombre}, ¿me puedes adjuntar una captura de pantalla del error? Puedes subirla en «Archivos adjuntos» del ticket.",
    ),
    (
        "Reiniciar y probar",
        "{nombre}, por favor reinicia el equipo (Inicio → Reiniciar, no solo apagar la pantalla) y vuelve a intentarlo. Me cuentas si el problema sigue.",
    ),
    (
        "Confirmar solución",
        "{nombre}, ya aplicamos la solución. ¿Puedes confirmarme si todo funciona bien? Si no tengo respuesta, cerraré el ticket #{ticket} como resuelto.",
    ),
]


def sembrar_predefinidas(session: Session) -> None:
    """Deja unas respuestas de ejemplo la primera vez (solo si la tabla está vacía)."""
    if session.exec(select(RespuestaPredefinida.id).limit(1)).first() is None:
        for titulo, texto in PREDEFINIDAS_INICIALES:
            session.add(RespuestaPredefinida(titulo=titulo, texto=texto))
        session.commit()


# ---------- respuestas predefinidas ----------

class PredefinidaCreate(SQLModel):
    titulo: str
    texto: str


class PredefinidaUpdate(SQLModel):
    titulo: Optional[str] = None
    texto: Optional[str] = None


class PredefinidaRead(SQLModel):
    id: int
    titulo: str
    texto: str
    usos: int
    creada_por_id: Optional[int] = None
    autor: Optional[str] = None
    editable: bool = False


class UsarPredefinida(SQLModel):
    predefinida_id: int


def _validar(titulo: Optional[str], texto: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if titulo is not None:
        titulo = " ".join(titulo.split())
        if not 3 <= len(titulo) <= MAX_TITULO:
            raise HTTPException(status_code=400, detail=f"El título debe tener entre 3 y {MAX_TITULO} caracteres.")
    if texto is not None:
        texto = texto.strip()
        if not 5 <= len(texto) <= MAX_TEXTO:
            raise HTTPException(status_code=400, detail=f"El texto debe tener entre 5 y {MAX_TEXTO} caracteres.")
    return titulo, texto


def _puede_editar(p: RespuestaPredefinida, usuario: Cliente) -> bool:
    return usuario.rol == "administrador" or p.creada_por_id == usuario.id or p.creada_por_id is None


def _lectura(p: RespuestaPredefinida, usuario: Cliente, nombres: dict[int, str]) -> PredefinidaRead:
    return PredefinidaRead(
        id=p.id,
        titulo=p.titulo,
        texto=p.texto,
        usos=p.usos,
        creada_por_id=p.creada_por_id,
        autor=nombres.get(p.creada_por_id) if p.creada_por_id else None,
        editable=_puede_editar(p, usuario),
    )


def _obtener(session: Session, predefinida_id: int) -> RespuestaPredefinida:
    p = session.get(RespuestaPredefinida, predefinida_id)
    if p is None or not p.activo:
        raise HTTPException(status_code=404, detail="Respuesta predefinida no encontrada")
    return p


@router.get("/respuestas-predefinidas", response_model=list[PredefinidaRead])
def listar_predefinidas(usuario: Cliente = Depends(requerir_personal), session: Session = Depends(get_session)):
    sembrar_predefinidas(session)
    filas = session.exec(
        select(RespuestaPredefinida)
        .where(RespuestaPredefinida.activo == True)  # noqa: E712
        .order_by(RespuestaPredefinida.usos.desc(), RespuestaPredefinida.titulo)
    ).all()
    ids = {p.creada_por_id for p in filas if p.creada_por_id}
    nombres = {c.id: c.nombre for c in session.exec(select(Cliente).where(Cliente.id.in_(ids))).all()} if ids else {}
    return [_lectura(p, usuario, nombres) for p in filas]


@router.post("/respuestas-predefinidas", response_model=PredefinidaRead)
def crear_predefinida(
    data: PredefinidaCreate, usuario: Cliente = Depends(requerir_personal), session: Session = Depends(get_session)
):
    titulo, texto = _validar(data.titulo, data.texto)
    p = RespuestaPredefinida(titulo=titulo, texto=texto, creada_por_id=usuario.id)
    session.add(p)
    session.commit()
    session.refresh(p)
    return _lectura(p, usuario, {usuario.id: usuario.nombre})


@router.patch("/respuestas-predefinidas/{predefinida_id}", response_model=PredefinidaRead)
def editar_predefinida(
    predefinida_id: int,
    data: PredefinidaUpdate,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    p = _obtener(session, predefinida_id)
    if not _puede_editar(p, usuario):
        raise HTTPException(status_code=403, detail="Solo quien la creó o un administrador puede editarla.")
    titulo, texto = _validar(data.titulo, data.texto)
    if titulo is not None:
        p.titulo = titulo
    if texto is not None:
        p.texto = texto
    session.add(p)
    session.commit()
    session.refresh(p)
    autor = session.get(Cliente, p.creada_por_id) if p.creada_por_id else None
    return _lectura(p, usuario, {autor.id: autor.nombre} if autor else {})


@router.delete("/respuestas-predefinidas/{predefinida_id}")
def eliminar_predefinida(
    predefinida_id: int, usuario: Cliente = Depends(requerir_personal), session: Session = Depends(get_session)
):
    p = _obtener(session, predefinida_id)
    if not _puede_editar(p, usuario):
        raise HTTPException(status_code=403, detail="Solo quien la creó o un administrador puede eliminarla.")
    p.activo = False  # se oculta; no se borra para no perder el conteo de usos
    session.add(p)
    session.commit()
    return {"mensaje": "Respuesta predefinida eliminada"}


@router.post("/tickets/{ticket_id}/respuesta-predefinida")
def usar_predefinida(
    ticket_id: int,
    data: UsarPredefinida,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    """Devuelve el texto con los datos del ticket ya puestos, para pegarlo en el chat. No envía nada."""
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    p = _obtener(session, data.predefinida_id)
    solicitante = session.get(Cliente, ticket.cliente_id)
    nombre = (ticket.solicitante_externo or (solicitante.nombre if solicitante else "") or "").split()
    valores = {
        "nombre": nombre[0] if nombre else "",
        "ticket": str(ticket.id),
        "tecnico": usuario.nombre,
    }
    texto = re.sub(r"\{(nombre|ticket|tecnico)\}", lambda m: valores[m.group(1)], p.texto)
    texto = re.sub(r"^Hola ,", "Hola,", texto).replace(" ,", ",")
    p.usos += 1
    session.add(p)
    session.commit()
    return {"texto": texto}


# ---------- tickets duplicados ----------

class VincularTicket(SQLModel):
    principal_id: int
    cancelar: bool = True


class PosibleDuplicado(SQLModel):
    id: int
    texto: str
    estado: str
    categoria: Optional[str] = None
    creado_en: datetime
    similitud: float


_PALABRAS_VACIAS = set(
    "a al algo con de del el en es esta este hay la las lo los me mi mis no o para pero por que se si sin su "
    "sus te tengo un una y ya favor ayuda buenos buenas dias tardes hola gracias puede pueden necesito".split()
)


def _palabras(texto: str) -> set[str]:
    return {p for p in re.findall(r"[a-z0-9]{3,}", normalizar(texto)) if p not in _PALABRAS_VACIAS}


@router.get("/tickets/{ticket_id}/posibles-duplicados", response_model=list[PosibleDuplicado])
def posibles_duplicados(
    ticket_id: int, usuario: Cliente = Depends(requerir_personal), session: Session = Depends(get_session)
):
    """Tickets de los últimos 30 días, no cerrados, que se parecen a este (palabras en común)."""
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    base = _palabras(ticket.texto)
    if not base:
        return []
    candidatos = session.exec(
        select(Ticket).where(
            Ticket.id != ticket.id,
            Ticket.estado.not_in(ESTADOS_FINALES),
            Ticket.duplicado_de_id.is_(None),
            Ticket.creado_en >= ticket.creado_en - timedelta(days=DIAS_DUPLICADOS),
            Ticket.creado_en <= ticket.creado_en + timedelta(days=DIAS_DUPLICADOS),
        )
    ).all()
    salida = []
    categoria = ticket.categoria or ticket.categoria_predicha
    for t in candidatos:
        otras = _palabras(t.texto)
        if not otras:
            continue
        similitud = len(base & otras) / len(base | otras)
        if (t.categoria or t.categoria_predicha) == categoria:
            similitud += 0.1
        if t.cliente_id == ticket.cliente_id and not ticket.solicitante_externo:
            similitud += 0.1
        if similitud >= 0.25:
            salida.append(
                PosibleDuplicado(
                    id=t.id,
                    texto=t.texto[:200],
                    estado=t.estado,
                    categoria=t.categoria or t.categoria_predicha,
                    creado_en=t.creado_en,
                    similitud=round(min(similitud, 1.0), 2),
                )
            )
    return sorted(salida, key=lambda x: -x.similitud)[:5]


@router.post("/tickets/{ticket_id}/vincular", response_model=TicketRead)
def vincular_duplicado(
    ticket_id: int,
    data: VincularTicket,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    principal = session.get(Ticket, data.principal_id)
    if ticket is None or principal is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if principal.id == ticket.id:
        raise HTTPException(status_code=400, detail="Un ticket no puede ser duplicado de sí mismo.")
    if principal.duplicado_de_id is not None:
        raise HTTPException(
            status_code=400,
            detail=f"El ticket #{principal.id} ya es duplicado del #{principal.duplicado_de_id}: vincúlalo a ese.",
        )
    if session.exec(select(Ticket.id).where(Ticket.duplicado_de_id == ticket.id)).first() is not None:
        raise HTTPException(status_code=400, detail="Este ticket ya tiene duplicados vinculados: es un ticket principal.")
    if data.cancelar and ticket.estado == "resuelto":
        raise HTTPException(status_code=409, detail="Este ticket ya está resuelto: vincúlalo sin cancelarlo.")

    ticket.duplicado_de_id = principal.id
    session.add(ticket)
    session.commit()
    if data.cancelar and ticket.estado not in ESTADOS_FINALES:
        return cancelar_ticket(
            ticket.id, CancelarTicket(motivo=f"Duplicado del ticket #{principal.id}"), tareas, usuario, session
        )
    session.refresh(ticket)
    return _con_sla(session, [ticket])[0]


@router.delete("/tickets/{ticket_id}/vincular", response_model=TicketRead)
def quitar_vinculo(ticket_id: int, usuario: Cliente = Depends(requerir_personal), session: Session = Depends(get_session)):
    """Quita el vínculo. Si se había cancelado por duplicado, se reabre desde «Reabrir»."""
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    ticket.duplicado_de_id = None
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return _con_sla(session, [ticket])[0]

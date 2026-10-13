import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente, HistorialEstadoTicket, Ticket
from app.schemas import (
    AltaColaboradorCreate,
    CancelarTicket,
    CatalogosRead,
    HistorialEstadoRead,
    LimitesAdjuntos,
    SugerenciaRead,
    SugerenciaRequest,
    TicketCreate,
    TicketDetalle,
    TicketRead,
    TicketUpdate,
)
from app.services.auth import (
    es_personal,
    obtener_usuario_actual,
    requerir_personal,
)
from app.services.catalogos import (
    APLICACIONES,
    CATEGORIA_ALTA,
    LICENCIAS_SAP,
    LISTAS_DISTRIBUCION,
    MAX_ADJUNTOS,
    MAX_BYTES_ADJUNTO,
    NOMBRES_LICENCIA_SAP,
    NOMBRES_TIPO,
    PRIORIDAD_POR_DEFECTO,
    PRIORIDADES,
    TIPO_ACCESOS,
    TIPOS,
    TIPOS_DE_ARCHIVO,
    cedula_valida,
)
from app.services.classifier import categorias_clasificables, clasificar_ticket, sugerir
from app.services.gamification_rules import evaluar_evento

router = APIRouter()

MIN_TEXTO = 5
MAX_TEXTO = 5000

# Estados que se fijan con PATCH. «cancelado» tiene su propia acción porque exige motivo.
ESTADOS_VALIDOS = ("abierto", "en_proceso", "resuelto")
ESTADOS_FINALES = ("resuelto", "cancelado")
RESUELTO_POR_VALIDOS = ("minutito", "tecnico")
MIN_MOTIVO = 5
MAX_MOTIVO = 500


def _validar_texto(texto: str) -> str:
    texto = texto.strip()
    if len(texto) < MIN_TEXTO:
        raise HTTPException(
            status_code=400,
            detail=f"Describe tu solicitud con un poco más de detalle (mínimo {MIN_TEXTO} caracteres).",
        )
    if len(texto) > MAX_TEXTO:
        raise HTTPException(
            status_code=400, detail=f"El texto es demasiado largo (máximo {MAX_TEXTO} caracteres)."
        )
    return texto


def _validar_prioridad(prioridad: Optional[str]) -> str:
    if prioridad is None:
        return PRIORIDAD_POR_DEFECTO
    if prioridad not in PRIORIDADES:
        raise HTTPException(status_code=400, detail="Prioridad no válida")
    return prioridad


def _validar_tipo(tipo: str) -> None:
    if tipo not in NOMBRES_TIPO:
        raise HTTPException(status_code=400, detail="Tipo de ticket no válido")


def _categorias_seleccionables() -> list[str]:
    return categorias_clasificables()


def _validar_categoria(categoria: str) -> None:
    if categoria not in _categorias_seleccionables() and categoria != CATEGORIA_ALTA:
        raise HTTPException(status_code=400, detail="Categoría no válida")


def registrar_estado(
    session: Session,
    ticket_id: int,
    anterior: Optional[str],
    nuevo: str,
    por_id: Optional[int],
    motivo: Optional[str] = None,
) -> None:
    session.add(
        HistorialEstadoTicket(
            ticket_id=ticket_id,
            estado_anterior=anterior,
            estado_nuevo=nuevo,
            cambiado_por_id=por_id,
            motivo=motivo,
        )
    )


def _verificar_acceso(ticket: Ticket, usuario: Cliente) -> None:
    if not es_personal(usuario) and ticket.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este ticket")


@router.post("", response_model=TicketRead)
def crear_ticket(
    data: TicketCreate,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    texto = _validar_texto(data.texto)
    prioridad = _validar_prioridad(data.prioridad)
    if data.tipo is not None:
        _validar_tipo(data.tipo)
        if data.tipo == TIPO_ACCESOS:
            raise HTTPException(
                status_code=400,
                detail="Para gestionar usuarios y accesos usa el formulario de alta de colaborador.",
            )
    if data.categoria is not None:
        _validar_categoria(data.categoria)
    prediccion = clasificar_ticket(texto)

    ticket = Ticket(
        cliente_id=usuario.id,
        texto=texto,
        tipo_predicho=prediccion["tipo"],
        categoria_predicha=prediccion["categoria"],
        confianza_clasificacion=prediccion["confianza"],
        tipo=data.tipo,
        categoria=data.categoria,
        # Solo cuenta como confirmada si la persona eligió las dos cosas.
        clasificacion_confirmada=data.tipo is not None and data.categoria is not None,
        prioridad=prioridad,
    )
    session.add(ticket)
    session.flush()
    registrar_estado(session, ticket.id, None, "abierto", usuario.id)
    session.commit()
    session.refresh(ticket)
    return ticket


@router.get("/catalogos", response_model=CatalogosRead)
def catalogos(usuario: Cliente = Depends(obtener_usuario_actual)):
    """Opciones del formulario: tipos, prioridades, categorías, listas del alta y límites de archivos."""
    return CatalogosRead(
        tipos=TIPOS,
        prioridades=PRIORIDADES,
        prioridad_por_defecto=PRIORIDAD_POR_DEFECTO,
        categorias=_categorias_seleccionables(),
        listas_distribucion=LISTAS_DISTRIBUCION,
        aplicaciones=APLICACIONES,
        licencias_sap=LICENCIAS_SAP,
        adjuntos=LimitesAdjuntos(
            maximo=MAX_ADJUNTOS,
            megabytes=MAX_BYTES_ADJUNTO // (1024 * 1024),
            extensiones=sorted(TIPOS_DE_ARCHIVO),
        ),
    )


@router.post("/sugerir", response_model=SugerenciaRead)
def sugerir_clasificacion(
    data: SugerenciaRequest,
    usuario: Cliente = Depends(obtener_usuario_actual),
):
    """Qué tipo y categoría propone el SVM para este texto (no crea nada). El formulario
    lo muestra mientras la persona escribe; ella confirma o cambia."""
    texto = data.texto.strip()
    if len(texto) < MIN_TEXTO:
        raise HTTPException(status_code=400, detail="Escribe un poco más para poder sugerir.")
    return sugerir(texto[:MAX_TEXTO])


@router.post("/alta-colaborador", response_model=TicketRead)
def crear_alta_de_colaborador(
    data: AltaColaboradorCreate,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    """Ticket de «Gestión de usuarios y accesos» para dar de alta a un colaborador.
    Son datos estructurados: no pasan por el SVM y la categoría es fija."""
    nombres = " ".join(data.nombres.split())
    cargo = " ".join(data.cargo.split())
    observaciones = data.observaciones.strip()
    if not nombres or not cargo or not observaciones:
        raise HTTPException(status_code=400, detail="Nombres, cargo y observaciones son obligatorios.")
    if len(observaciones) > MAX_TEXTO:
        raise HTTPException(status_code=400, detail=f"Las observaciones son demasiado largas (máximo {MAX_TEXTO}).")
    cedula = data.cedula.strip()
    if not cedula_valida(cedula):
        raise HTTPException(
            status_code=400,
            detail="La cédula no es válida. Escribe la cédula real del colaborador (10 dígitos).",
        )
    for elegidas, permitidas, nombre in (
        (data.listas_distribucion, LISTAS_DISTRIBUCION, "lista de distribución"),
        (data.aplicaciones, APLICACIONES, "aplicación"),
    ):
        desconocidas = [e for e in elegidas if e not in permitidas]
        if desconocidas:
            raise HTTPException(status_code=400, detail=f"{nombre.capitalize()} no válida: {desconocidas[0]}")
    if data.licencia_sap is not None and data.licencia_sap not in NOMBRES_LICENCIA_SAP:
        raise HTTPException(status_code=400, detail="Licencia SAP no válida")
    prioridad = _validar_prioridad(data.prioridad)

    datos = {
        "nombres": nombres,
        "fecha_ingreso": data.fecha_ingreso.isoformat(),
        "cedula": cedula,
        "cargo": cargo,
        "monitor": data.monitor,
        "telefono_fijo": data.telefono_fijo,
        "grupo": (data.grupo or "").strip() or None,
        "listas_distribucion": data.listas_distribucion,
        "aplicaciones": data.aplicaciones,
        "licencia_sap": data.licencia_sap,
        "permisos_sap": (data.permisos_sap or "").strip() or None,
        "observaciones": observaciones,
    }
    ticket = Ticket(
        cliente_id=usuario.id,
        # Resumen legible para listas y búsquedas (sin la cédula).
        texto=f"Alta de colaborador: {nombres} · Cargo: {cargo} · Ingreso: {data.fecha_ingreso:%d/%m/%Y}",
        tipo=TIPO_ACCESOS,
        categoria=CATEGORIA_ALTA,
        clasificacion_confirmada=True,
        prioridad=prioridad,
        datos_alta=json.dumps(datos, ensure_ascii=False),
    )
    session.add(ticket)
    session.flush()
    registrar_estado(session, ticket.id, None, "abierto", usuario.id)
    session.commit()
    session.refresh(ticket)
    return ticket


@router.get("", response_model=list[TicketRead])
def listar_tickets(
    estado: Optional[str] = None,
    categoria_predicha: Optional[str] = None,
    cliente_id: Optional[int] = None,
    tecnico_id: Optional[int] = None,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    query = select(Ticket)
    if estado is not None:
        query = query.where(Ticket.estado == estado)
    if categoria_predicha is not None:
        query = query.where(Ticket.categoria_predicha == categoria_predicha)

    if es_personal(usuario):
        if cliente_id is not None:
            query = query.where(Ticket.cliente_id == cliente_id)
        if tecnico_id is not None:
            query = query.where(Ticket.tecnico_id == tecnico_id)
    else:
        # Un usuario final solo ve sus propios tickets, sin importar el filtro pedido.
        query = query.where(Ticket.cliente_id == usuario.id)

    return session.exec(query.order_by(Ticket.creado_en.desc())).all()


@router.get("/{ticket_id}", response_model=TicketDetalle)
def obtener_ticket(
    ticket_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    _verificar_acceso(ticket, usuario)
    return ticket


@router.get("/{ticket_id}/historial", response_model=list[HistorialEstadoRead])
def historial_del_ticket(
    ticket_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    _verificar_acceso(ticket, usuario)

    filas = session.exec(
        select(HistorialEstadoTicket)
        .where(HistorialEstadoTicket.ticket_id == ticket_id)
        .order_by(HistorialEstadoTicket.fecha, HistorialEstadoTicket.id)
    ).all()
    ids = {f.cambiado_por_id for f in filas if f.cambiado_por_id is not None}
    nombres = (
        {c.id: c.nombre for c in session.exec(select(Cliente).where(Cliente.id.in_(ids))).all()}
        if ids
        else {}
    )
    return [
        HistorialEstadoRead(
            id=f.id,
            estado_anterior=f.estado_anterior,
            estado_nuevo=f.estado_nuevo,
            cambiado_por_id=f.cambiado_por_id,
            cambiado_por=nombres.get(f.cambiado_por_id, "Minutito")
            if f.cambiado_por_id is not None
            else "Minutito",
            motivo=f.motivo,
            fecha=f.fecha,
        )
        for f in filas
    ]


@router.patch("/{ticket_id}", response_model=TicketRead)
def actualizar_ticket(
    ticket_id: int,
    data: TicketUpdate,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    if data.estado == "cancelado":
        raise HTTPException(status_code=400, detail="Para cancelar un ticket usa «Cancelar ticket» e indica el motivo.")
    if data.estado is not None and data.estado not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Estado no válido")
    if data.resuelto_por is not None and data.resuelto_por not in RESUELTO_POR_VALIDOS:
        raise HTTPException(status_code=400, detail="Valor de resuelto_por no válido")
    if data.prioridad is not None and data.prioridad not in PRIORIDADES:
        raise HTTPException(status_code=400, detail="Prioridad no válida")
    if data.tipo is not None:
        _validar_tipo(data.tipo)
    if data.categoria is not None:
        _validar_categoria(data.categoria)
    if ticket.datos_alta is not None and (data.tipo is not None or data.categoria is not None):
        raise HTTPException(
            status_code=400, detail="El tipo y la categoría de un alta de colaborador no se cambian."
        )
    if data.tipo == TIPO_ACCESOS and ticket.datos_alta is None:
        raise HTTPException(
            status_code=400, detail="Un ticket de accesos se crea con el formulario de alta de colaborador."
        )

    if data.prioridad is not None:
        ticket.prioridad = data.prioridad
    # Si el personal fija o corrige el tipo o la categoría, queda como clasificación confirmada.
    if data.tipo is not None:
        ticket.tipo = data.tipo
        ticket.clasificacion_confirmada = True
    if data.categoria is not None:
        ticket.categoria = data.categoria
        ticket.clasificacion_confirmada = True

    estado_anterior = ticket.estado
    ya_estaba_resuelto = estado_anterior == "resuelto"

    if data.estado is not None and data.estado != estado_anterior:
        ticket.estado = data.estado
        if data.estado == "resuelto":
            ticket.cerrado_en = datetime.now()
            ticket.resuelto_por = data.resuelto_por or "tecnico"
            if ticket.tecnico_id is None:
                ticket.tecnico_id = usuario.id
        else:
            ticket.cerrado_en = None
            ticket.resuelto_por = None
            ticket.motivo_cancelacion = None  # reabrir un cancelado borra el motivo vigente
            if data.estado == "en_proceso":
                ticket.tecnico_id = usuario.id
        registrar_estado(session, ticket.id, estado_anterior, data.estado, usuario.id)
    elif data.resuelto_por is not None and ticket.estado == "resuelto":
        ticket.resuelto_por = data.resuelto_por

    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    if not ya_estaba_resuelto and ticket.estado == "resuelto":
        evaluar_evento(ticket, ticket.cliente_id, session)

    return ticket


@router.post("/{ticket_id}/cancelar", response_model=TicketRead)
def cancelar_ticket(
    ticket_id: int,
    data: CancelarTicket,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    """Solo técnico o administrador, con motivo. Un ticket cancelado no cuenta como resuelto,
    no entra en el tiempo medio de resolución ni da puntos. Se puede reabrir si fue un error."""
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if ticket.estado in ESTADOS_FINALES:
        raise HTTPException(
            status_code=409,
            detail="Este ticket ya está resuelto." if ticket.estado == "resuelto" else "Este ticket ya está cancelado.",
        )
    motivo = " ".join(data.motivo.split())
    if len(motivo) < MIN_MOTIVO:
        raise HTTPException(status_code=400, detail="Escribe el motivo de la cancelación (mínimo 5 caracteres).")
    if len(motivo) > MAX_MOTIVO:
        raise HTTPException(status_code=400, detail=f"El motivo es demasiado largo (máximo {MAX_MOTIVO} caracteres).")

    estado_anterior = ticket.estado
    ticket.estado = "cancelado"
    ticket.motivo_cancelacion = motivo
    ticket.cerrado_en = datetime.now()
    ticket.resuelto_por = None
    registrar_estado(session, ticket.id, estado_anterior, "cancelado", usuario.id, motivo)
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket

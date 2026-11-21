import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import AsignacionTicket, Cliente, HistorialEstadoTicket, Ticket
from app.schemas import (
    AltaColaboradorCreate,
    AsignacionRead,
    LiberarTicket,
    MotivoLiberacion,
    CancelarTicket,
    CatalogosRead,
    HistorialEstadoRead,
    LimitesAdjuntos,
    MotivoPausa,
    PausarSla,
    SlaRead,
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
from app.routers.conversacion import hay_aprobacion_pendiente
from app.routers.minutito import enlazar_ticket
from app.services.asignacion import asignar_automaticamente, tecnico_sugerido
from app.services.classifier import categorias_clasificables, clasificar_ticket, sugerir
from app.services import confirmacion, incidentes, notificaciones, sla, toma
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
    tareas: BackgroundTasks,
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
    asignar_automaticamente(session, ticket)
    session.add(ticket)
    session.flush()
    registrar_estado(session, ticket.id, None, "abierto", usuario.id)
    if data.conversacion_id is not None:
        enlazar_ticket(session, data.conversacion_id, usuario, ticket)
    session.commit()
    session.refresh(ticket)
    notificaciones.ticket_creado(tareas, session, ticket)
    return _con_sla(session, [ticket])[0]


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
    tareas: BackgroundTasks,
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
    notificaciones.ticket_creado(tareas, session, ticket)
    return _con_sla(session, [ticket])[0]


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

    tickets = session.exec(query.order_by(Ticket.creado_en.desc())).all()
    return _con_sla(session, tickets)


def _con_sla(session: Session, tickets: list[Ticket]) -> list[TicketRead]:
    plazos = sla.calcular_varios(session, tickets)
    salida = []
    for t in tickets:
        lectura = TicketRead.model_validate(t, from_attributes=True)
        lectura.sla = plazos.get(t.id)
        salida.append(lectura)
    return salida


@router.get("/motivos-pausa", response_model=list[MotivoPausa])
def motivos_de_pausa(usuario: Cliente = Depends(requerir_personal)):
    return [MotivoPausa(clave=k, titulo=v) for k, v in sla.MOTIVOS_PAUSA.items()]


@router.get("/motivos-liberacion", response_model=list[MotivoLiberacion])
def motivos_de_liberacion(usuario: Cliente = Depends(requerir_personal)):
    return [MotivoLiberacion(clave=k, titulo=v) for k, v in toma.MOTIVOS_LIBERACION.items()]


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
    detalle = TicketDetalle.model_validate(ticket, from_attributes=True)
    detalle.sla = sla.calcular(session, ticket)
    detalle.duplicados = list(
        session.exec(select(Ticket.id).where(Ticket.duplicado_de_id == ticket.id).order_by(Ticket.id)).all()
    )
    if es_personal(usuario):
        sugerido = tecnico_sugerido(session, ticket.categoria or ticket.categoria_predicha)
        detalle.tecnico_sugerido_id = sugerido.id if sugerido else None
    return detalle


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
    tareas: BackgroundTasks,
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
    if data.tecnico_id is not None:
        tecnico = session.get(Cliente, data.tecnico_id)
        if tecnico is None or tecnico.rol not in ("tecnico", "administrador") or not tecnico.activo:
            raise HTTPException(status_code=400, detail="Técnico no válido")
    if data.tipo == TIPO_ACCESOS and ticket.datos_alta is None:
        raise HTTPException(
            status_code=400, detail="Un ticket de accesos se crea con el formulario de alta de colaborador."
        )
    # Un ticket tomado solo lo cambian quien lo atiende y el administrador.
    toma.exigir_que_pueda_atender(session, ticket, usuario)
    admin = toma.es_admin(usuario)
    if not admin and toma.esta_tomado(ticket):
        if data.tecnico_id is not None and data.tecnico_id != usuario.id:
            raise HTTPException(
                status_code=409, detail="Para pasar el ticket a otro técnico, libéralo indicando el motivo."
            )
        if data.tecnico_auto:
            raise HTTPException(
                status_code=409,
                detail="Para devolver el ticket a la asignación automática, libéralo indicando el motivo.",
            )
    if data.estado == "resuelto" and ticket.estado != "resuelto" and hay_aprobacion_pendiente(session, ticket.id):
        raise HTTPException(
            status_code=409, detail="Hay una aprobación pendiente: espera la respuesta antes de resolver."
        )

    prioridad_anterior = ticket.prioridad
    if data.prioridad is not None and data.prioridad != ticket.prioridad:
        ticket.prioridad = data.prioridad
        ticket.aviso_sla = None  # el plazo cambia: los avisos se vuelven a evaluar
    if data.tipo is not None and data.tipo != ticket.tipo:
        ticket.aviso_sla = None
    # Si el personal fija o corrige el tipo o la categoría, queda como clasificación confirmada.
    if data.tipo is not None:
        ticket.tipo = data.tipo
        ticket.clasificacion_confirmada = True
    if data.categoria is not None:
        ticket.categoria = data.categoria
        ticket.clasificacion_confirmada = True

    tecnico_anterior = ticket.tecnico_id
    # Técnico: elegido a mano, devuelto al sugerido, o (si cambió la categoría y nadie lo
    # eligió a mano) el que corresponde a la nueva categoría. Elegirse a sí mismo es
    # tomarlo; el administrador, al elegir a alguien, se lo deja tomado; un técnico que
    # elige a otro en un ticket libre solo cambia la sugerencia.
    if data.tecnico_id is not None:
        if data.tecnico_id == usuario.id and not toma.tomado_por_otro(ticket, usuario):
            toma.tomar(session, ticket, usuario, via="asignacion")
        elif admin:
            if not (toma.esta_tomado(ticket) and ticket.tecnico_id == data.tecnico_id):
                toma.reasignar(session, ticket, session.get(Cliente, data.tecnico_id), usuario)
        else:
            ticket.tecnico_id = data.tecnico_id
            ticket.tecnico_manual = True
    elif data.tecnico_auto:
        if toma.esta_tomado(ticket):  # solo llega aquí el administrador
            toma.liberar(session, ticket, usuario, None, "Devuelto a la asignación automática")
        ticket.tecnico_manual = False
        ticket.tomado_en = None
        ticket.tecnico_id = None
        asignar_automaticamente(session, ticket)
    elif data.categoria is not None:
        asignar_automaticamente(session, ticket)

    estado_anterior = ticket.estado
    ya_estaba_resuelto = estado_anterior == "resuelto"

    if data.estado is not None and data.estado != estado_anterior:
        if data.estado == "resuelto" and estado_anterior not in ESTADOS_FINALES:
            # Quien lo resuelve queda a cargo, salvo que ya lo atendiera otro (el
            # administrador puede cerrar un ticket ajeno sin quitárselo).
            toma.tomar_si_libre(session, ticket, usuario, via="estado")
        ticket.estado = data.estado
        if data.estado == "resuelto":
            ticket.cerrado_en = datetime.now()
            ticket.resuelto_por = data.resuelto_por or "tecnico"
            sla.cerrar_pausa_activa(session, ticket.id, usuario.id)
            if ticket.tecnico_id is None:
                ticket.tecnico_id = usuario.id
                ticket.tecnico_manual = True
        else:
            ticket.cerrado_en = None
            ticket.resuelto_por = None
            ticket.motivo_cancelacion = None  # reabrir un cancelado borra el motivo vigente
            if data.estado == "en_proceso":
                # Quien pasa el ticket a «En proceso» lo toma (aunque el sugerido fuera otro).
                toma.tomar_si_libre(session, ticket, usuario, via="estado")
        registrar_estado(session, ticket.id, estado_anterior, data.estado, usuario.id)
    elif data.resuelto_por is not None and ticket.estado == "resuelto":
        ticket.resuelto_por = data.resuelto_por

    if ticket.estado != estado_anterior:
        # «¿Quedó resuelto?»: se abre al resolver y se anula si el personal lo reabre.
        confirmacion.al_cambiar_estado(session, ticket, estado_anterior)
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    if not ya_estaba_resuelto and ticket.estado == "resuelto":
        evaluar_evento(ticket, ticket.cliente_id, session)
        # Si era el principal de un problema general, sus afectados se resuelven con él.
        incidentes.resolver_afectados(session, tareas, ticket, usuario)

    if ticket.estado != estado_anterior:
        notificaciones.estado_cambiado(tareas, session, ticket, estado_anterior, usuario)
    if ticket.tecnico_id is not None and ticket.tecnico_id != tecnico_anterior:
        notificaciones.tecnico_asignado(tareas, session, ticket, usuario)
    if ticket.prioridad != prioridad_anterior and ticket.estado not in ESTADOS_FINALES:
        notificaciones.prioridad_cambiada(tareas, session, ticket, prioridad_anterior, usuario, sla.dias_de_plazo(ticket))

    return _con_sla(session, [ticket])[0]


@router.post("/{ticket_id}/cancelar", response_model=TicketRead)
def cancelar_ticket(
    ticket_id: int,
    data: CancelarTicket,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    """Solo técnico o administrador, con motivo. Un ticket cancelado no cuenta como resuelto,
    no entra en el tiempo medio de resolución ni da puntos. Se puede reabrir si fue un error."""
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    toma.exigir_que_pueda_atender(session, ticket, usuario)
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
    sla.cerrar_pausa_activa(session, ticket.id, usuario.id)
    ticket.cerrado_en = datetime.now()
    ticket.resuelto_por = None
    registrar_estado(session, ticket.id, estado_anterior, "cancelado", usuario.id, motivo)
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    notificaciones.estado_cambiado(tareas, session, ticket, estado_anterior, usuario)
    return _con_sla(session, [ticket])[0]


# ---------- temporizador del plazo (SLA) ----------

@router.get("/{ticket_id}/sla", response_model=Optional[SlaRead])
def plazo_del_ticket(
    ticket_id: int,
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    _verificar_acceso(ticket, usuario)
    return sla.calcular(session, ticket)


@router.post("/{ticket_id}/sla/pausar", response_model=SlaRead)
def pausar_plazo(
    ticket_id: int,
    data: PausarSla,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    """Detiene el reloj del plazo con un motivo obligatorio. Solo técnico o administrador."""
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    toma.exigir_que_pueda_atender(session, ticket, usuario)
    if ticket.estado in ESTADOS_FINALES:
        raise HTTPException(status_code=409, detail="El plazo de un ticket cerrado ya no corre.")
    if data.motivo not in sla.MOTIVOS_PAUSA:
        raise HTTPException(status_code=400, detail="Motivo de pausa no válido")
    detalle = " ".join(data.detalle.split())
    if len(detalle) < sla.MIN_DETALLE:
        raise HTTPException(status_code=400, detail="Explica por qué se pausa (mínimo 5 caracteres).")
    if len(detalle) > sla.MAX_DETALLE:
        raise HTTPException(status_code=400, detail=f"El detalle es demasiado largo (máximo {sla.MAX_DETALLE}).")
    if sla.dias_de_plazo(ticket) is None:
        raise HTTPException(status_code=409, detail="Este ticket no tiene plazo definido: fija primero su tipo.")
    if sla.pausa_activa(session, ticket.id) is not None:
        raise HTTPException(status_code=409, detail="El plazo ya está en pausa.")
    pausa = sla.pausar(session, ticket, data.motivo, detalle, usuario.id)
    session.commit()
    session.refresh(pausa)
    notificaciones.sla_pausado(tareas, session, ticket, usuario, pausa)
    return sla.calcular(session, ticket)


@router.post("/{ticket_id}/sla/reanudar", response_model=SlaRead)
def reanudar_plazo(
    ticket_id: int,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    toma.exigir_que_pueda_atender(session, ticket, usuario)
    pausa = sla.pausa_activa(session, ticket.id)
    if pausa is None:
        raise HTTPException(status_code=409, detail="El plazo no está en pausa.")
    if pausa.aprobacion_id is not None and hay_aprobacion_pendiente(session, ticket.id):
        raise HTTPException(
            status_code=409,
            detail="Hay una aprobación pendiente: el plazo se reanuda solo cuando la respondan.",
        )
    sla.reanudar(session, pausa, usuario.id)
    session.commit()
    notificaciones.sla_reanudado(tareas, session, ticket, usuario)
    return sla.calcular(session, ticket)


# ---------- tomar y liberar ----------

def _obtener(session: Session, ticket_id: int) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


@router.post("/{ticket_id}/tomar", response_model=TicketRead)
def tomar_ticket(
    ticket_id: int,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    """El ticket queda a nombre de quien lo toma y pasa a «En proceso». Si otro técnico
    lo tomó antes (aunque sea en el mismo instante), 409 con su nombre."""
    ticket = _obtener(session, ticket_id)
    tecnico_anterior = ticket.tecnico_id
    toma.tomar(session, ticket, usuario, via="boton")
    estado_anterior = ticket.estado
    if ticket.estado == "abierto":
        ticket.estado = "en_proceso"
        registrar_estado(session, ticket.id, estado_anterior, "en_proceso", usuario.id)
        session.add(ticket)
    session.commit()
    session.refresh(ticket)
    if ticket.estado != estado_anterior:
        notificaciones.estado_cambiado(tareas, session, ticket, estado_anterior, usuario)
    return _con_sla(session, [ticket])[0]


@router.post("/{ticket_id}/liberar", response_model=TicketRead)
def liberar_ticket(
    ticket_id: int,
    data: LiberarTicket,
    tareas: BackgroundTasks,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    """Quien atiende el ticket (o un administrador) lo suelta con un motivo. Vuelve a
    «Nuevo» y la asignación automática lo sugiere a otro técnico del sistema."""
    ticket = _obtener(session, ticket_id)
    if ticket.estado in ESTADOS_FINALES:
        raise HTTPException(status_code=409, detail=f"Este ticket ya está {ticket.estado}.")
    if not toma.esta_tomado(ticket):
        raise HTTPException(status_code=409, detail="Nadie ha tomado este ticket todavía.")
    toma.exigir_que_pueda_atender(session, ticket, usuario)
    if data.motivo not in toma.MOTIVOS_LIBERACION:
        raise HTTPException(status_code=400, detail="Motivo no válido")
    detalle = " ".join(data.detalle.split())
    if len(detalle) < toma.MIN_DETALLE:
        raise HTTPException(status_code=400, detail="Explica por qué liberas el ticket (mínimo 5 caracteres).")
    if len(detalle) > toma.MAX_DETALLE:
        raise HTTPException(status_code=400, detail=f"El detalle es demasiado largo (máximo {toma.MAX_DETALLE}).")

    anterior = toma.liberar(session, ticket, usuario, data.motivo, detalle)
    estado_anterior = ticket.estado
    if ticket.estado == "en_proceso":
        ticket.estado = "abierto"
        registrar_estado(
            session, ticket.id, estado_anterior, "abierto", usuario.id,
            f"Liberado: {toma.MOTIVOS_LIBERACION[data.motivo]}. {detalle}",
        )
    asignar_automaticamente(session, ticket, excluir=anterior)
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    if ticket.tecnico_id is not None:
        notificaciones.tecnico_asignado(tareas, session, ticket, usuario)
    return _con_sla(session, [ticket])[0]


@router.get("/{ticket_id}/asignaciones", response_model=list[AsignacionRead])
def historial_de_asignacion(
    ticket_id: int,
    usuario: Cliente = Depends(requerir_personal),
    session: Session = Depends(get_session),
):
    """Quién tomó, liberó o reasignó el ticket (solo lo ve el personal)."""
    _obtener(session, ticket_id)
    filas = session.exec(
        select(AsignacionTicket)
        .where(AsignacionTicket.ticket_id == ticket_id)
        .order_by(AsignacionTicket.fecha, AsignacionTicket.id)
    ).all()
    ids = {f.por_id for f in filas} | {f.tecnico_id for f in filas if f.tecnico_id}
    nombres = (
        {c.id: c.nombre for c in session.exec(select(Cliente).where(Cliente.id.in_(ids))).all()} if ids else {}
    )
    return [
        AsignacionRead(
            id=f.id,
            accion=f.accion,
            tecnico_id=f.tecnico_id,
            tecnico=nombres.get(f.tecnico_id),
            por_id=f.por_id,
            por=nombres.get(f.por_id, "—"),
            motivo=f.motivo,
            motivo_titulo=toma.MOTIVOS_LIBERACION.get(f.motivo) if f.motivo else None,
            detalle=f.detalle,
            via=f.via,
            fecha=f.fecha,
        )
        for f in filas
    ]

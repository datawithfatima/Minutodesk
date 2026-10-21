"""Carga masiva de tickets nuevos desde el export de la herramienta anterior.

El histórico (TicketHistorico) es el conjunto de entrenamiento y se cargó una sola
vez. Los tickets posteriores se crean aquí como tickets normales de MinutoDesk,
con su fecha y estado reales: el SVM los clasifica igual que en el formulario y
su tipo y categoría reales quedan como la elección de la persona. Así la comparación
entre lo predicho y lo real aparece en «Calidad del clasificador» (acierto en uso).

Reglas:
- Se omiten los ID que ya están en el histórico (son datos de entrenamiento) y los
  que ya se cargaron antes: repetir la carga no duplica nada.
- Se omiten los que no traen tipo, categoría o descripción (sin texto no hay nada
  que clasificar; sin la clasificación real no hay contra qué comparar).
- Los solicitantes no tienen cuenta: el ticket queda a nombre de una cuenta interna
  sin acceso y el nombre de quien lo pidió se guarda como texto.
- El estado es el de la herramienta anterior (Completado → Resuelto, En Curso → En
  proceso, Cancelado → Cancelado, Nuevo → Nuevo). «Asignado a» se enlaza con la
  cuenta del técnico si su nombre coincide.
"""
from collections import Counter
from datetime import datetime

from sqlmodel import Session, select

from app.models import Area, Cliente, HistorialEstadoTicket, Ticket, TicketHistorico
from app.services.catalogos import NOMBRES_TIPO, PRIORIDAD_POR_DEFECTO, PRIORIDADES
from app.services.classifier import clasificar_ticket
from app.services.historico import (
    COL_CATEGORIA,
    COL_ASIGNADO,
    COL_CREADO,
    COL_DESCRIPCION,
    COL_ESTADO,
    COL_ID,
    COL_PRIORIDAD,
    COL_SOLICITANTE,
    COL_SOLUCION,
    COL_TIPO,
    _clave,
    _descripcion,
    _fecha,
    _texto,
)

EMAIL_CUENTA = "carga-masiva@minutodesk.local"
NOMBRE_CUENTA = "Carga masiva (sin cuenta)"
MAX_TEXTO_TICKET = 5000

MOTIVO_CANCELADO = "Cancelado en la herramienta anterior (carga masiva)."
# Estado de la herramienta anterior -> estado en MinutoDesk.
ESTADOS = {"completado": "resuelto", "cancelado": "cancelado", "en curso": "en_proceso", "nuevo": "abierto"}
PRIORIDADES_POR_CLAVE = {_clave(p): p for p in PRIORIDADES}
TIPOS_POR_CLAVE = {_clave(t): t for t in NOMBRES_TIPO}


def cuenta_interna(session: Session) -> Cliente:
    """Dueña de los tickets cargados: sin contraseña y desactivada, así nadie puede
    iniciar sesión con ella ni elegirla como aprobador."""
    cuenta = session.exec(select(Cliente).where(Cliente.email == EMAIL_CUENTA)).first()
    if cuenta is None:
        area = session.exec(select(Area).order_by(Area.id)).first()
        if area is None:
            area = Area(nombre="Sistemas")
            session.add(area)
            session.flush()
        cuenta = Cliente(nombre=NOMBRE_CUENTA, email=EMAIL_CUENTA, area_id=area.id, activo=False)
        session.add(cuenta)
        session.flush()
    return cuenta


def cargar(tabla, session: Session, aplicar: bool, quien: Cliente) -> dict:
    """Crea los tickets del CSV. Sin `aplicar` solo cuenta lo que pasaría."""
    for columna in (COL_TIPO, COL_CATEGORIA, COL_DESCRIPCION):
        if columna not in tabla.columns:
            raise ValueError(f"Al CSV le falta la columna «{columna}».")

    de_entrenamiento = set(session.exec(select(TicketHistorico.id_externo)).all())
    ya_cargados = set(
        session.exec(select(Ticket.id_externo).where(Ticket.id_externo != None)).all()  # noqa: E711
    )
    fin_entrenamiento = max(session.exec(select(TicketHistorico.creado_en)).all(), default=None)
    personal = session.exec(
        select(Cliente).where(Cliente.rol.in_(("tecnico", "administrador")), Cliente.activo == True)  # noqa: E712
    ).all()
    # Si alguien tiene cuenta de técnico y de administrador, el ticket va a la de técnico.
    tecnicos = {}
    for c in sorted(personal, key=lambda c: c.rol != "tecnico", reverse=True):
        tecnicos[_clave(c.nombre)] = c

    resumen = Counter()
    nuevos: list[Ticket] = []
    vistos: set[str] = set()
    for _, fila in tabla.iterrows():
        resumen["filas"] += 1
        id_externo = _texto(fila.get(COL_ID))
        if id_externo is None or id_externo in vistos:
            resumen["sin_id_o_repetidos"] += 1
            continue
        vistos.add(id_externo)
        if id_externo in de_entrenamiento:
            resumen["de_entrenamiento"] += 1
            continue
        if id_externo in ya_cargados:
            resumen["ya_cargados"] += 1
            continue
        creado = _fecha(fila.get(COL_CREADO))
        if creado is not None and fin_entrenamiento is not None and creado <= fin_entrenamiento:
            resumen["de_entrenamiento"] += 1  # dentro del periodo de entrenamiento
            continue

        tipo = TIPOS_POR_CLAVE.get(_clave(_texto(fila.get(COL_TIPO)) or ""))
        categoria = _texto(fila.get(COL_CATEGORIA))
        texto = _descripcion(fila.get(COL_DESCRIPCION))
        if tipo is None or categoria is None or texto is None:
            resumen["incompletos"] += 1
            continue

        resumen["validos"] += 1
        if not aplicar:
            continue
        texto = texto[:MAX_TEXTO_TICKET]
        prediccion = clasificar_ticket(texto)
        estado = ESTADOS.get(_clave(_texto(fila.get(COL_ESTADO)) or ""), "abierto")
        tecnico = tecnicos.get(_clave(_texto(fila.get(COL_ASIGNADO)) or ""))
        cerrado = None
        if estado in ("resuelto", "cancelado"):
            cerrado = _fecha(fila.get(COL_SOLUCION))
            if cerrado is None or (creado and cerrado < creado):
                cerrado = creado
        nuevos.append(
            Ticket(
                texto=texto,
                tipo_predicho=prediccion["tipo"],
                categoria_predicha=prediccion["categoria"],
                confianza_clasificacion=prediccion["confianza"],
                # Como en el formulario: la persona eligió tipo y categoría.
                tipo=tipo,
                categoria=categoria,
                clasificacion_confirmada=True,
                prioridad=PRIORIDADES_POR_CLAVE.get(
                    _clave(_texto(fila.get(COL_PRIORIDAD)) or ""), PRIORIDAD_POR_DEFECTO
                ),
                estado=estado,
                tecnico_id=tecnico.id if tecnico and estado != "abierto" else None,
                resuelto_por="tecnico" if estado == "resuelto" else None,
                motivo_cancelacion=MOTIVO_CANCELADO if estado == "cancelado" else None,
                creado_en=creado or datetime.now(),
                cerrado_en=cerrado,
                id_externo=id_externo,
                solicitante_externo=_texto(fila.get(COL_SOLICITANTE)),
            )
        )

    if aplicar and nuevos:
        cuenta = cuenta_interna(session)
        for ticket in nuevos:
            ticket.cliente_id = cuenta.id
        session.add_all(nuevos)
        session.flush()
        for t in nuevos:
            session.add(
                HistorialEstadoTicket(
                    ticket_id=t.id, estado_anterior=None, estado_nuevo="abierto",
                    cambiado_por_id=quien.id, fecha=t.creado_en,
                )
            )
            if t.estado != "abierto":
                session.add(
                    HistorialEstadoTicket(
                        ticket_id=t.id,
                        estado_anterior="abierto",
                        estado_nuevo=t.estado,
                        cambiado_por_id=t.tecnico_id or quien.id,
                        motivo=t.motivo_cancelacion,
                        fecha=t.cerrado_en or t.creado_en,
                    )
                )
        session.commit()
    return {
        "aplicado": aplicar,
        "filas": resumen["filas"],
        "de_entrenamiento": resumen["de_entrenamiento"],
        "ya_cargados": resumen["ya_cargados"],
        "incompletos": resumen["incompletos"],
        "sin_id_o_repetidos": resumen["sin_id_o_repetidos"],
        "validos": resumen["validos"],
        "creados": len(nuevos),
    }

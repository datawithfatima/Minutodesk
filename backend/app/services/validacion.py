"""Validación del clasificador con tickets que no vio al entrenar.

El histórico (TicketHistorico) es el conjunto de entrenamiento y se cargó una sola
vez. Los tickets posteriores llegan en un CSV con el mismo formato: cada uno se crea
como ticket de validación, el SVM lo clasifica y se guarda junto a su clasificación
real (`tipo`/`categoria`). Así se mide si el modelo generaliza.

Reglas al cargar:
- Se omiten los ID que ya están en el histórico (son datos de entrenamiento) y los
  que ya se cargaron como validación: repetir la carga no duplica nada.
- Se omiten los que no traen tipo, categoría o descripción: sin la clasificación
  real no hay contra qué comparar.
- Estos tickets quedan a nombre de una cuenta interna sin acceso; el solicitante
  original se guarda solo como texto.

Para comparar la categoría se usa la misma regla del entrenamiento: las categorías
del histórico con muy pocos ejemplos se aprendieron como «Otros». Una categoría
que no estaba en el histórico no se puede acertar y se reporta aparte.
"""
from collections import Counter
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.models import Area, Cliente, Ticket, TicketHistorico
from app.services.catalogos import NOMBRES_TIPO, PRIORIDAD_POR_DEFECTO, PRIORIDADES
from app.services.classifier import cargar_metricas, categorias_clasificables, clasificar_ticket
from app.services.historico import (
    COL_CATEGORIA,
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

EMAIL_CUENTA = "validacion@minutodesk.local"
NOMBRE_CUENTA = "Validación del clasificador"
CATEGORIA_OTROS = "Otros"
MAX_TEXTO_TICKET = 5000

# Estado de la herramienta anterior -> estado en MinutoDesk.
ESTADOS = {"completado": "resuelto", "cancelado": "cancelado", "en curso": "en_proceso", "nuevo": "abierto"}
PRIORIDADES_POR_CLAVE = {_clave(p): p for p in PRIORIDADES}
TIPOS_POR_CLAVE = {_clave(t): t for t in NOMBRES_TIPO}


def cuenta_de_validacion(session: Session) -> Cliente:
    """Cuenta interna dueña de los tickets de validación: sin contraseña y desactivada,
    así nadie puede iniciar sesión con ella ni elegirla como aprobador."""
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


def cargar(tabla, session: Session, aplicar: bool) -> dict:
    """Crea los tickets de validación del CSV. Sin `aplicar` solo cuenta lo que pasaría."""
    for columna in (COL_TIPO, COL_CATEGORIA, COL_DESCRIPCION):
        if columna not in tabla.columns:
            raise ValueError(f"Al CSV le falta la columna «{columna}».")

    de_entrenamiento = set(session.exec(select(TicketHistorico.id_externo)).all())
    ya_cargados = set(
        session.exec(select(Ticket.id_externo).where(Ticket.es_validacion == True)).all()  # noqa: E712
    )
    fin_entrenamiento = max(session.exec(select(TicketHistorico.creado_en)).all(), default=None)

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
            resumen["sin_clasificacion_real"] += 1
            continue

        resumen["validables"] += 1
        if not aplicar:
            continue
        texto = texto[:MAX_TEXTO_TICKET]
        prediccion = clasificar_ticket(texto)
        estado = ESTADOS.get(_clave(_texto(fila.get(COL_ESTADO)) or ""), "abierto")
        cerrado = _fecha(fila.get(COL_SOLUCION)) if estado in ("resuelto", "cancelado") else None
        nuevos.append(
            Ticket(
                texto=texto,
                tipo_predicho=prediccion["tipo"],
                categoria_predicha=prediccion["categoria"],
                confianza_clasificacion=prediccion["confianza"],
                tipo=tipo,
                categoria=categoria,
                clasificacion_confirmada=True,
                prioridad=PRIORIDADES_POR_CLAVE.get(
                    _clave(_texto(fila.get(COL_PRIORIDAD)) or ""), PRIORIDAD_POR_DEFECTO
                ),
                estado=estado,
                resuelto_por="tecnico" if estado == "resuelto" else None,
                creado_en=creado or datetime.now(),
                cerrado_en=cerrado if cerrado and creado and cerrado >= creado else None,
                es_validacion=True,
                id_externo=id_externo,
                solicitante_externo=_texto(fila.get(COL_SOLICITANTE)),
            )
        )

    if aplicar and nuevos:
        cuenta = cuenta_de_validacion(session)
        for ticket in nuevos:
            ticket.cliente_id = cuenta.id
        session.add_all(nuevos)
        session.commit()
    return {
        "aplicado": aplicar,
        "filas": resumen["filas"],
        "de_entrenamiento": resumen["de_entrenamiento"],
        "ya_cargados": resumen["ya_cargados"],
        "sin_clasificacion_real": resumen["sin_clasificacion_real"],
        "sin_id_o_repetidos": resumen["sin_id_o_repetidos"],
        "validables": resumen["validables"],
        "creados": len(nuevos),
    }


def _categoria_esperada(real: str, aprendidas: set[str], en_historico: set[str]) -> Optional[str]:
    """La etiqueta con la que el modelo aprendió esa categoría; None si nunca la vio."""
    por_clave = {_clave(c): c for c in aprendidas}
    if _clave(real) in por_clave:
        return por_clave[_clave(real)]
    # Estaba en el histórico con pocos ejemplos: se entrenó dentro de «Otros».
    return CATEGORIA_OTROS if _clave(real) in en_historico else None


def _proporcion(aciertos: int, total: int) -> Optional[float]:
    return round(aciertos / total, 4) if total else None


def resultados(session: Session) -> dict:
    tickets = session.exec(
        select(Ticket).where(Ticket.es_validacion == True).order_by(Ticket.creado_en)  # noqa: E712
    ).all()
    aprendidas = set(categorias_clasificables())
    en_historico = {_clave(c) for c in session.exec(select(TicketHistorico.categoria)).all() if c}
    umbral = cargar_metricas().get("categoria", {}).get("umbral")

    detalle = []
    por_categoria: dict[str, Counter] = {}
    errores = Counter()
    for t in tickets:
        esperada = _categoria_esperada(t.categoria, aprendidas, en_historico)
        acierto_categoria = esperada is not None and esperada == t.categoria_predicha
        if esperada is not None:
            fila = por_categoria.setdefault(esperada, Counter())
            fila["total"] += 1
            fila["aciertos"] += acierto_categoria
            if not acierto_categoria:
                errores[(esperada, t.categoria_predicha)] += 1
        detalle.append(
            {
                "id": t.id,
                "id_externo": t.id_externo,
                "creado_en": t.creado_en,
                "solicitante": t.solicitante_externo,
                "texto": t.texto,
                "tipo_real": t.tipo,
                "tipo_predicho": t.tipo_predicho,
                "acierto_tipo": t.tipo == t.tipo_predicho,
                "categoria_real": t.categoria,
                "categoria_esperada": esperada,
                "categoria_predicha": t.categoria_predicha,
                "confianza": t.confianza_clasificacion,
                "acierto_categoria": acierto_categoria if esperada is not None else None,
            }
        )

    evaluables = [d for d in detalle if d["categoria_esperada"] is not None]
    seguros = [d for d in evaluables if umbral is not None and (d["confianza"] or 0) >= umbral]
    return {
        "total": len(detalle),
        "desde": tickets[0].creado_en if tickets else None,
        "hasta": tickets[-1].creado_en if tickets else None,
        "objetivo": cargar_metricas().get("objetivo_precision", 0.8),
        "acierto_tipo": _proporcion(sum(d["acierto_tipo"] for d in detalle), len(detalle)),
        "categoria_evaluables": len(evaluables),
        "acierto_categoria": _proporcion(sum(d["acierto_categoria"] for d in evaluables), len(evaluables)),
        "umbral": umbral,
        "categoria_en_umbral": _proporcion(sum(d["acierto_categoria"] for d in seguros), len(seguros)),
        "cobertura_en_umbral": _proporcion(len(seguros), len(evaluables)),
        "categorias_no_vistas": sorted({d["categoria_real"] for d in detalle if d["categoria_esperada"] is None}),
        "tickets_no_vistos": len(detalle) - len(evaluables),
        "por_categoria": [
            {"categoria": c, "total": f["total"], "aciertos": f["aciertos"]}
            for c, f in sorted(por_categoria.items(), key=lambda x: -x[1]["total"])
        ],
        "errores_frecuentes": [
            {"real": r, "predicha": p, "veces": n} for (r, p), n in errores.most_common(8)
        ],
        "tickets": detalle,
    }

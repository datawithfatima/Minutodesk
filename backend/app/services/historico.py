"""Importación del CSV mensual de tickets históricos (consulta y reportes del administrador).

El archivo pasa por una limpieza antes de guardarse y se puede repetir cada
mes con el export completo o parcial: los tickets se identifican por la
columna "ID", así que los que ya existen se actualizan (p. ej. cuando pasan a
"Completado") y los nuevos se agregan. Se guarda también la descripción (sin
HTML), el solicitante y quién atendió, para poder consultarlos; esos tickets no
forman parte de la plataforma (ver TicketHistorico).

Reglas de limpieza:
- Se descartan filas sin ID, sin estado o con fecha de creación ilegible.
- Si un ID aparece varias veces en el archivo, gana la última fila.
- Se quitan espacios sobrantes y se unifican mayúsculas/tildes en estado,
  prioridad y categoría ("critica" -> "Crítica", "internet" -> "Internet").
- La fecha de solución se ignora si es ilegible o anterior a la creación.
"""
import html
import io
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Optional

import pandas as pd
from sqlmodel import Session, select

from app.ml.train_classifier import quitar_tildes
from app.models import TicketHistorico

COL_ID = "ID"
COL_TIPO = "Seleccione una opción para la respectiva atención."
COL_CATEGORIA = "Categoría"
COL_PRIORIDAD = "Prioridad"
COL_CREADO = "Creado"
COL_SOLUCION = "Fecha Solución"
COL_ESTADO = "Estado"
COL_DESCRIPCION = "Descripción"
COL_SOLICITANTE = "Solicitante"
COL_ASIGNADO = "Asignado a"
MAX_DESCRIPCION = 8000

COLUMNAS_OBLIGATORIAS = [COL_ID, COL_CREADO, COL_ESTADO]
FORMATOS_FECHA = ("%d/%m/%Y %H:%M", "%d/%m/%Y")
MAX_INCIDENCIAS = 10

ESTADOS = {"nuevo": "Nuevo", "en curso": "En Curso", "completado": "Completado", "cancelado": "Cancelado"}
PRIORIDADES = {"baja": "Baja", "normal": "Normal", "alta": "Alta", "critica": "Crítica"}


def _texto(valor) -> Optional[str]:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    limpio = " ".join(str(valor).split())
    return limpio or None


_SALTOS_HTML = re.compile(r"<\s*(?:br|/p|/div|/li|/tr|/h\d)\s*/?\s*>", re.IGNORECASE)
_ETIQUETAS_HTML = re.compile(r"<[^>]+>")


def _descripcion(valor) -> Optional[str]:
    """Texto plano de la descripción: quita el HTML, conserva los saltos de línea."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = _SALTOS_HTML.sub("\n", str(valor))
    texto = html.unescape(_ETIQUETAS_HTML.sub(" ", texto))
    lineas = (" ".join(linea.split()) for linea in texto.splitlines())
    limpio = "\n".join(linea for linea in lineas if linea)
    return limpio[:MAX_DESCRIPCION] or None


def _clave(texto: str) -> str:
    return quitar_tildes(texto.lower())


def _fecha(valor) -> Optional[datetime]:
    texto = _texto(valor)
    if texto is None:
        return None
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def leer_csv(contenido: bytes) -> pd.DataFrame:
    """Convierte los bytes del archivo en tabla. Lanza ValueError si no sirve."""
    if not contenido.strip():
        raise ValueError("El archivo está vacío.")
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = contenido.decode("cp1252", errors="replace")  # export de Excel en español
    try:
        df = pd.read_csv(io.StringIO(texto), dtype=str, keep_default_na=False)
        if len(df.columns) == 1 and ";" in df.columns[0]:
            df = pd.read_csv(io.StringIO(texto), dtype=str, keep_default_na=False, sep=";")
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as e:
        raise ValueError(f"No se pudo leer el archivo como CSV: {e}") from e

    df.columns = [c.strip() for c in df.columns]
    faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Al CSV le faltan columnas obligatorias: {', '.join(faltantes)}")
    return df


def procesar(df: pd.DataFrame, session: Session, aplicar: bool) -> dict:
    """Limpia la tabla y la compara con lo ya guardado; solo escribe si `aplicar`."""
    existentes = {t.id_externo: t for t in session.exec(select(TicketHistorico)).all()}

    # Escritura oficial de cada categoría: la más frecuente (contando lo ya guardado)
    # y, en empate, la que empieza con mayúscula.
    escrituras: dict[str, Counter] = {}
    nombres = [t.categoria for t in existentes.values()] + [
        _texto(f.get(COL_CATEGORIA)) for f in df.to_dict("records")
    ]
    for nombre in nombres:
        if nombre:
            escrituras.setdefault(_clave(nombre), Counter())[nombre] += 1
    categorias = {
        clave: max(cuentas, key=lambda n: (cuentas[n], n[:1].isupper()))
        for clave, cuentas in escrituras.items()
    }

    incidencias: list[str] = []
    omitidos = duplicados = fechas_descartadas = 0
    limpios: dict[str, dict] = {}

    def anotar(mensaje: str) -> None:
        if len(incidencias) < MAX_INCIDENCIAS:
            incidencias.append(mensaje)

    for numero, fila in enumerate(df.to_dict("records"), start=2):  # 1 = encabezado
        id_externo = _texto(fila.get(COL_ID))
        estado_crudo = _texto(fila.get(COL_ESTADO))
        creado = _fecha(fila.get(COL_CREADO))
        if id_externo is None:
            omitidos += 1
            anotar(f"Fila {numero}: sin ID.")
            continue
        if estado_crudo is None:
            omitidos += 1
            anotar(f"Fila {numero} (ID {id_externo}): sin estado.")
            continue
        if creado is None:
            omitidos += 1
            anotar(f"Fila {numero} (ID {id_externo}): fecha de creación ausente o ilegible.")
            continue

        resuelto = _fecha(fila.get(COL_SOLUCION))
        if _texto(fila.get(COL_SOLUCION)) and (resuelto is None or resuelto.date() < creado.date()):
            fechas_descartadas += 1
            anotar(f"Fila {numero} (ID {id_externo}): fecha de solución inválida, se ignoró.")
            resuelto = None

        categoria = _texto(fila.get(COL_CATEGORIA))
        if categoria:
            categoria = categorias[_clave(categoria)]
        prioridad = _texto(fila.get(COL_PRIORIDAD))
        if prioridad:
            prioridad = PRIORIDADES.get(_clave(prioridad), prioridad)

        if id_externo in limpios:
            duplicados += 1
        limpios[id_externo] = {
            "tipo": _texto(fila.get(COL_TIPO)),
            "categoria": categoria,
            "prioridad": prioridad,
            "estado": ESTADOS.get(_clave(estado_crudo), estado_crudo),
            "creado_en": creado,
            "resuelto_en": resuelto,
            "descripcion": _descripcion(fila.get(COL_DESCRIPCION)),
            "solicitante": _texto(fila.get(COL_SOLICITANTE)),
            "asignado_a": _texto(fila.get(COL_ASIGNADO)),
        }

    nuevos = actualizados = sin_cambios = 0
    for id_externo, datos in limpios.items():
        ticket = existentes.get(id_externo)
        if ticket is None:
            nuevos += 1
            if aplicar:
                nuevo = TicketHistorico(id_externo=id_externo, **datos)
                session.add(nuevo)
                existentes[id_externo] = nuevo
        elif any(getattr(ticket, campo) != valor for campo, valor in datos.items()):
            actualizados += 1
            if aplicar:
                for campo, valor in datos.items():
                    setattr(ticket, campo, valor)
                session.add(ticket)
        else:
            sin_cambios += 1

    if aplicar:
        ahora = datetime.now()
        for id_externo in limpios:
            existentes[id_externo].importado_en = ahora
            session.add(existentes[id_externo])
        session.commit()

    completados_sin_fecha = sum(
        1 for d in limpios.values() if d["estado"] == "Completado" and d["resuelto_en"] is None
    )
    return {
        "aplicado": aplicar,
        "filas": len(df),
        "validas": len(limpios),
        "nuevos": nuevos,
        "actualizados": actualizados,
        "sin_cambios": sin_cambios,
        "omitidos": omitidos,
        "duplicados_en_archivo": duplicados,
        "fechas_solucion_descartadas": fechas_descartadas,
        "completados_sin_fecha": completados_sin_fecha,
        "incidencias": incidencias,
        "total_en_base": len(existentes) if aplicar else len(existentes) + nuevos,
    }


def importar_csv(ruta: Path, session: Session) -> dict:
    """Limpia y guarda un archivo CSV del disco (usado por el script mensual)."""
    return procesar(leer_csv(Path(ruta).read_bytes()), session, aplicar=True)


def resumen_historico(session: Session) -> dict:
    tickets = session.exec(select(TicketHistorico)).all()
    por_estado = Counter(t.estado for t in tickets)
    completados = [t for t in tickets if t.estado == "Completado" and t.resuelto_en]
    dias = [max((t.resuelto_en.date() - t.creado_en.date()).days, 0) for t in completados]
    por_mes = Counter(t.creado_en.strftime("%Y-%m") for t in tickets)
    meses = sorted(por_mes)[-12:]
    importados = [t.importado_en for t in tickets]

    dias_por_mes: dict[str, list[int]] = {}
    for t, d in zip(completados, dias):
        dias_por_mes.setdefault(t.creado_en.strftime("%Y-%m"), []).append(d)

    return {
        "total": len(tickets),
        "completados": por_estado.get("Completado", 0),
        "cancelados": por_estado.get("Cancelado", 0),
        "dias_medio_resolucion": round(mean(dias), 1) if dias else None,
        "desde": min((t.creado_en for t in tickets), default=None),
        "hasta": max((t.creado_en for t in tickets), default=None),
        "ultima_importacion": max(importados, default=None),
        "por_estado": [{"etiqueta": e, "total": n} for e, n in por_estado.most_common()],
        "por_categoria": [
            {"etiqueta": c, "total": n}
            for c, n in Counter(t.categoria or "Sin categoría" for t in tickets).most_common(8)
        ],
        "por_prioridad": [
            {"etiqueta": p, "total": n}
            for p, n in Counter(t.prioridad or "Sin prioridad" for t in tickets).most_common()
        ],
        "por_mes": [{"etiqueta": m, "total": por_mes[m]} for m in meses],
        "resolucion_por_mes": [
            {"etiqueta": m, "valor": round(mean(dias_por_mes[m]), 1) if dias_por_mes.get(m) else None}
            for m in meses
        ],
    }

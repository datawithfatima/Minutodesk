"""Exportación de Reportes a Excel (.xlsx) y PDF, p. ej. para los anexos de la tesis.

Solo reúne y da formato a las mismas cifras que ya muestra la pantalla de Reportes (el
resumen de la plataforma, el plazo de atención, la satisfacción y, para el administrador,
la calidad del clasificador): no calcula nada nuevo ni cambia datos.
"""
from datetime import datetime
from io import BytesIO
from typing import Optional

from sqlmodel import Session, select

from app.models import Cliente, EncuestaSatisfaccion, Ticket
from app.services import sla
from app.services.catalogos import TIPOS

GRAFITO = "1B1E22"
CASCO = "F5B800"
ACENTO = "C2410C"
HORMIGON = "F3F1EC"
LINEA = "E1E0D9"

TITULO_TIPO = {t["nombre"]: t["titulo"] for t in TIPOS}
ETIQUETA_ESTADO = {"abierto": "Nuevo", "en_proceso": "En proceso", "resuelto": "Resuelto", "cancelado": "Cancelado"}


def _pct(valor: Optional[float]) -> str:
    return "—" if valor is None else f"{valor:.1f} %".replace(".", ",")


def _num(valor) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, float):
        return f"{valor:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return str(valor)


def _horas(h: Optional[float]) -> str:
    if h is None:
        return "—"
    return f"{h / 24:.1f} días ({h:.1f} h)".replace(".", ",") if h >= 48 else f"{h:.1f} h".replace(".", ",")


def reunir(resumen, categorias: list[tuple[str, int]], satisfaccion: dict, clasificador: Optional[dict]) -> list[dict]:
    """Secciones del reporte como tablas: [{"titulo", "nota", "columnas", "filas"}]."""
    r = resumen
    secciones = [
        {
            "titulo": "1. Indicadores de la plataforma",
            "nota": "Tickets creados en MinutoDesk (incluye los de la carga masiva).",
            "columnas": ["Indicador", "Valor"],
            "filas": [
                ["Tickets totales", r.total],
                ["Nuevos", r.abiertos],
                ["En proceso", r.en_proceso],
                ["Resueltos", r.resueltos],
                ["Cancelados", r.cancelados],
                ["Tiempo medio de resolución", _horas(r.tiempo_medio_resolucion_horas)],
                ["Conversaciones con Minutito terminadas", r.conversaciones_minutito],
                ["Conversaciones resueltas por Minutito (sin ticket)", r.conversaciones_resueltas],
                ["Resolución autónoma de Minutito (todas las consultas)", _pct(r.pct_resolucion_autonoma)],
                ["Resolución autónoma de Minutito (primer nivel)", _pct(r.pct_primer_nivel)],
                ["Casos resueltos por Minutito", r.resueltos_por_minutito],
                ["Tickets resueltos por el equipo de soporte", r.resueltos_por_tecnico],
            ],
        },
        {
            "titulo": "2. Tickets por categoría",
            "nota": "Categoría confirmada por la persona o el técnico; si no hay, la que predijo el clasificador.",
            "columnas": ["Categoría", "Tickets"],
            "filas": [[c, n] for c, n in categorias],
        },
    ]
    s = r.sla
    if s is not None:
        secciones.append(
            {
                "titulo": "3. Cumplimiento del plazo de atención (SLA)",
                "nota": "Tickets resueltos dentro del plazo según su tipo y prioridad; abiertos según cómo va su plazo hoy.",
                "columnas": ["Grupo", "Resueltos con plazo", "A tiempo", "Cumplimiento"],
                "filas": [["Global", s.resueltos_con_plazo, s.cumplidos, _pct(s.pct_cumplimiento)]]
                + [[f"Tipo: {g.etiqueta}", g.total, g.cumplidos, _pct(g.pct)] for g in s.por_tipo]
                + [[f"Prioridad: {g.etiqueta}", g.total, g.cumplidos, _pct(g.pct)] for g in s.por_prioridad]
                + [
                    ["Abiertos en tiempo", s.abiertos_en_tiempo, "", ""],
                    ["Abiertos por vencer", s.abiertos_por_vencer, "", ""],
                    ["Abiertos vencidos", s.abiertos_vencidos, "", ""],
                    ["Abiertos en pausa", s.abiertos_pausados, "", ""],
                ],
            }
        )
    secciones.append(
        {
            "titulo": "4. Satisfacción del usuario",
            "nota": "Encuesta de 1 a 5 estrellas al resolverse un ticket.",
            "columnas": ["Indicador", "Valor"],
            "filas": [
                ["Respuestas", satisfaccion["respuestas"]],
                ["Calificación promedio (de 5)", _num(satisfaccion["promedio"])],
                ["Satisfechos (4 o 5 estrellas)", _pct(satisfaccion["satisfechos_pct"])],
                ["Tasa de respuesta", _pct(satisfaccion["tasa_respuesta_pct"])],
            ]
            + [[f"{x['estrellas']} " + ("estrella" if x["estrellas"] == 1 else "estrellas"), x["total"]] for x in satisfaccion["reparto"]]
            + [[f"Promedio · {t['tecnico']}", f"{_num(t['promedio'])} ({t['respuestas']} resp.)"] for t in satisfaccion["por_tecnico"]],
        }
    )
    if clasificador and clasificador.get("disponible"):
        cat, tipo, en_uso = clasificador["categoria"], clasificador["tipo"], clasificador.get("en_uso") or {}
        filas = [
            ["Método de evaluación", clasificador.get("metodo", "")],
            ["Tickets de entrenamiento", cat.get("tickets")],
            ["Meta de precisión", _pct(100 * clasificador["objetivo_precision"])],
            ["Categoría · precisión global", _pct(100 * cat["accuracy"])],
            ["Tipo · precisión global", _pct(100 * tipo["accuracy"])],
        ]
        if cat.get("umbral") is not None:
            filas.append(["Categoría · umbral de confianza", _pct(100 * cat["umbral"])])
            if cat.get("precision_en_umbral") is not None:
                filas += [
                    ["Categoría · precisión sobre el umbral", _pct(100 * cat["precision_en_umbral"])],
                    ["Categoría · cobertura sobre el umbral", _pct(100 * cat["cobertura_en_umbral"])],
                ]
        if en_uso.get("acierto_categoria") is not None:
            filas.append([f"Acierto en uso · categoría ({en_uso['tickets_categoria']} tickets)", _pct(100 * en_uso["acierto_categoria"])])
        if en_uso.get("acierto_tipo") is not None:
            filas.append([f"Acierto en uso · tipo ({en_uso['tickets_tipo']} tickets)", _pct(100 * en_uso["acierto_tipo"])])
        secciones.append(
            {
                "titulo": "5. Calidad del clasificador",
                "nota": f"Entrenado el {clasificador.get('entrenado_en', '')[:10]}.",
                "columnas": ["Indicador", "Valor"],
                "filas": filas,
            }
        )
    return secciones


def listado_tickets(session: Session) -> tuple[list[str], list[list]]:
    """Una fila por ticket, sin la descripción (puede traer datos personales)."""
    tickets = session.exec(select(Ticket).order_by(Ticket.id)).all()
    plazos = sla.calcular_varios(session, tickets)
    tecnicos = {c.id: c.nombre for c in session.exec(select(Cliente).where(Cliente.rol != "usuario")).all()}
    estrellas = {e.ticket_id: e.estrellas for e in session.exec(select(EncuestaSatisfaccion)).all()}
    columnas = [
        "Ticket", "Creado", "Estado", "Tipo", "Categoría", "Categoría predicha (SVM)", "Prioridad",
        "Técnico", "Cerrado", "Horas hasta el cierre", "Plazo (días)", "Plazo cumplido", "Resuelto por", "Calificación",
    ]
    filas = []
    for t in tickets:
        p = plazos.get(t.id)
        horas = round((t.cerrado_en - t.creado_en).total_seconds() / 3600, 1) if t.cerrado_en and t.estado == "resuelto" else None
        cumplido = None
        if p is not None and t.estado == "resuelto":
            cumplido = "No" if p.vencido else "Sí"
        filas.append([
            t.id,
            t.creado_en,
            ETIQUETA_ESTADO.get(t.estado, t.estado),
            TITULO_TIPO.get(t.tipo or t.tipo_predicho or "", t.tipo or t.tipo_predicho or ""),
            t.categoria or "",
            t.categoria_predicha or "",
            t.prioridad,
            tecnicos.get(t.tecnico_id, "") if t.tecnico_id else "",
            t.cerrado_en,
            horas,
            p.dias if p is not None else None,
            cumplido or "",
            {"minutito": "Minutito", "tecnico": "Equipo de soporte"}.get(t.resuelto_por or "", ""),
            estrellas.get(t.id),
        ])
    return columnas, filas


# ---------- Excel ----------

def a_excel(secciones: list[dict], listado: tuple[list[str], list[list]], generado_por: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Resumen"
    banda = PatternFill("solid", fgColor=GRAFITO)
    cabecera = PatternFill("solid", fgColor=HORMIGON)
    borde = Border(bottom=Side(style="thin", color=LINEA))

    hoja.merge_cells("A1:D1")
    hoja["A1"] = "MinutoDesk · Reporte de indicadores"
    hoja["A1"].font = Font(bold=True, size=16, color="FFFFFF")
    hoja["A1"].fill = banda
    hoja.row_dimensions[1].height = 30
    hoja.merge_cells("A2:D2")
    hoja["A2"] = f"Corte al {datetime.now():%d/%m/%Y %H:%M} · generado por {generado_por}"
    hoja["A2"].font = Font(italic=True, color="52514E")
    for col in "ABCD":
        hoja[f"{col}3"].fill = PatternFill("solid", fgColor=CASCO)
    hoja.row_dimensions[3].height = 4

    fila = 5
    for sec in secciones:
        hoja.cell(fila, 1, sec["titulo"]).font = Font(bold=True, size=12, color=ACENTO)
        fila += 1
        if sec.get("nota"):
            hoja.cell(fila, 1, sec["nota"]).font = Font(italic=True, size=9, color="6F6B63")
            fila += 1
        for j, c in enumerate(sec["columnas"], start=1):
            celda = hoja.cell(fila, j, c)
            celda.font = Font(bold=True)
            celda.fill = cabecera
            celda.border = borde
        fila += 1
        for valores in sec["filas"]:
            for j, v in enumerate(valores, start=1):
                celda = hoja.cell(fila, j, v)
                celda.border = borde
                if j > 1:
                    celda.alignment = Alignment(horizontal="right")
            fila += 1
        fila += 1
    hoja.column_dimensions["A"].width = 52
    for col in "BCD":
        hoja.column_dimensions[col].width = 20

    columnas, filas = listado
    tabla = libro.create_sheet("Tickets")
    tabla.append(columnas)
    for c in tabla[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = banda
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for f in filas:
        tabla.append(f)
    for fila_celdas in tabla.iter_rows(min_row=2):
        for indice in (1, 8):  # Creado y Cerrado
            if fila_celdas[indice].value is not None:
                fila_celdas[indice].number_format = "dd/mm/yyyy hh:mm"
    anchos = [9, 17, 12, 24, 26, 26, 11, 22, 17, 12, 10, 10, 18, 11]
    for i, ancho in enumerate(anchos, start=1):
        tabla.column_dimensions[get_column_letter(i)].width = ancho
    tabla.freeze_panes = "A2"
    tabla.auto_filter.ref = tabla.dimensions

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


# ---------- PDF ----------

def a_pdf(secciones: list[dict], generado_por: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    grafito, casco, acento = colors.HexColor(f"#{GRAFITO}"), colors.HexColor(f"#{CASCO}"), colors.HexColor(f"#{ACENTO}")
    hormigon, linea = colors.HexColor(f"#{HORMIGON}"), colors.HexColor(f"#{LINEA}")
    generado = datetime.now()

    def encabezado(lienzo, doc):
        ancho, alto = A4
        lienzo.saveState()
        lienzo.setFillColor(grafito)
        lienzo.rect(0, alto - 26 * mm, ancho, 26 * mm, stroke=0, fill=1)
        # Franja de obra bajo la banda.
        lienzo.setFillColor(casco)
        lienzo.rect(0, alto - 27.5 * mm, ancho, 1.5 * mm, stroke=0, fill=1)
        lienzo.setFillColor(grafito)
        x = 0
        while x < ancho:
            lienzo.saveState()
            camino = lienzo.beginPath()
            camino.moveTo(x, alto - 27.5 * mm)
            camino.lineTo(x + 3 * mm, alto - 27.5 * mm)
            camino.lineTo(x + 4.5 * mm, alto - 26 * mm)
            camino.lineTo(x + 1.5 * mm, alto - 26 * mm)
            camino.close()
            lienzo.drawPath(camino, stroke=0, fill=1)
            lienzo.restoreState()
            x += 6 * mm
        # Logo: bloque amarillo y «M».
        lienzo.setFillColor(casco)
        lienzo.rect(15 * mm, alto - 19 * mm, 9 * mm, 9 * mm, stroke=0, fill=1)
        lienzo.setFillColor(grafito)
        lienzo.setFont("Helvetica-Bold", 13)
        lienzo.drawCentredString(19.5 * mm, alto - 16.6 * mm, "M")
        lienzo.setFillColor(colors.white)
        lienzo.setFont("Helvetica-Bold", 15)
        lienzo.drawString(28 * mm, alto - 14 * mm, "MinutoDesk")
        lienzo.setFont("Helvetica", 8)
        lienzo.setFillColor(casco)
        lienzo.drawString(28 * mm, alto - 18.5 * mm, "MESA DE AYUDA DE TI · REPORTE DE INDICADORES")
        lienzo.setFillColor(colors.HexColor("#B3B6BC"))
        lienzo.drawRightString(ancho - 15 * mm, alto - 14 * mm, f"Corte al {generado:%d/%m/%Y %H:%M}")
        lienzo.drawRightString(ancho - 15 * mm, alto - 18.5 * mm, f"Generado por {generado_por}")
        # Pie.
        lienzo.setStrokeColor(linea)
        lienzo.line(15 * mm, 14 * mm, ancho - 15 * mm, 14 * mm)
        lienzo.setFillColor(colors.HexColor("#6F6B63"))
        lienzo.setFont("Helvetica", 7.5)
        lienzo.drawString(15 * mm, 10 * mm, "MinutoDesk · Prototipo de mesa de ayuda con inteligencia artificial")
        lienzo.drawRightString(ancho - 15 * mm, 10 * mm, f"Página {doc.page}")
        lienzo.restoreState()

    titulo = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=12.5, textColor=acento, spaceAfter=2, alignment=TA_LEFT)
    nota = ParagraphStyle("nota", fontName="Helvetica-Oblique", fontSize=8, textColor=colors.HexColor("#6F6B63"), spaceAfter=5)
    celda = ParagraphStyle("celda", fontName="Helvetica", fontSize=8.8, leading=11)
    celda_cab = ParagraphStyle("celda_cab", parent=celda, fontName="Helvetica-Bold")

    salida = BytesIO()
    doc = SimpleDocTemplate(
        salida, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=34 * mm, bottomMargin=20 * mm,
        title="MinutoDesk · Reporte de indicadores", author="MinutoDesk",
    )
    ancho_util = A4[0] - 30 * mm
    historia = []
    for sec in secciones:
        n = len(sec["columnas"])
        anchos = [ancho_util * 0.58] + [ancho_util * 0.42 / (n - 1)] * (n - 1) if n > 1 else [ancho_util]
        datos = [[Paragraph(str(c), celda_cab) for c in sec["columnas"]]]
        datos += [[Paragraph("" if v is None else str(v), celda) for v in fila] for fila in sec["filas"]]
        tabla = Table(datos, colWidths=anchos, repeatRows=1)
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), hormigon),
                    ("LINEBELOW", (0, 0), (-1, 0), 1, grafito),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.4, linea),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                    ("LINEBEFORE", (0, 0), (0, -1), 2.2, casco),
                ]
            )
        )
        bloque = [Paragraph(sec["titulo"], titulo)]
        if sec.get("nota"):
            bloque.append(Paragraph(sec["nota"], nota))
        if len(sec["filas"]) <= 18:
            historia.append(KeepTogether(bloque + [tabla]))
        else:
            historia += bloque + [tabla]
        historia.append(Spacer(1, 8 * mm))
    doc.build(historia, onFirstPage=encabezado, onLaterPages=encabezado)
    return salida.getvalue()

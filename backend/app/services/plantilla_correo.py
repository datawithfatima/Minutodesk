"""Plantilla HTML de los correos, con la identidad del portal: cabecera grafito con el
logo «M», franja de obra amarilla y negra, fondo hormigón, tarjeta blanca, botón naranja
de señalización y rótulos en monoespaciada. Todo con tablas y estilos en línea para que
se vea bien en Gmail y Outlook. Cada correo lleva también una versión de texto plano.
"""
from dataclasses import dataclass, field
from html import escape
from typing import Optional

GRAFITO = "#1b1e22"
HORMIGON = "#f3f1ec"
LINEA = "#e1ddd3"
ACENTO = "#c2410c"
CASCO = "#f5b800"
TEXTO = "#1b1e22"
TEXTO_SUAVE = "#6f6b63"
SANS = "Archivo, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
MONO = "'IBM Plex Mono', Consolas, 'Courier New', monospace"

# Color del rótulo de estado según el tipo de novedad.
COLORES_ETIQUETA = {
    "ok": "#0ca30c",
    "aviso": "#fab219",
    "alerta": "#d64545",
    "pausa": "#9b968c",
    "info": ACENTO,
}


@dataclass
class Correo:
    """Contenido de un correo; de aquí salen la versión HTML y la de texto."""

    asunto: str
    titulo: str  # titular grande dentro de la tarjeta
    saludo: str  # «Hola Ana,»
    parrafos: list[str] = field(default_factory=list)
    # Rótulo pequeño sobre el titular, p. ej. «Ticket #97 · Solicitud»
    rotulo: Optional[str] = None
    etiqueta: Optional[str] = None  # pastilla de estado: «En pausa», «Resuelto»…
    tono: str = "info"  # clave de COLORES_ETIQUETA
    cita: Optional[str] = None  # texto citado (la solicitud, el mensaje, el motivo)
    cita_rotulo: Optional[str] = None
    datos: list[tuple[str, str]] = field(default_factory=list)  # filas de ficha: (rótulo, valor)
    boton: Optional[str] = None
    enlace: Optional[str] = None
    nota: Optional[str] = None  # texto pequeño al pie de la tarjeta

    # ---------- texto plano ----------
    def texto(self) -> str:
        partes = [f"{self.saludo}", ""]
        partes += [p for p in self.parrafos]
        if self.cita:
            partes += ["", f"{self.cita_rotulo or 'Detalle'}: «{self.cita}»"]
        if self.datos:
            partes += [""] + [f"{k}: {v}" for k, v in self.datos]
        if self.enlace:
            partes += ["", f"{self.boton or 'Ábrelo aquí'}: {self.enlace}"]
        if self.nota:
            partes += ["", self.nota]
        partes += ["", "— Mesa de ayuda MinutoDesk"]
        return "\n".join(partes)

    # ---------- HTML ----------
    def html(self) -> str:
        color_etq = COLORES_ETIQUETA.get(self.tono, ACENTO)
        rotulo = (
            f'<p style="margin:0 0 6px;font:500 11px/1.4 {MONO};letter-spacing:.14em;text-transform:uppercase;'
            f'color:{TEXTO_SUAVE}">{escape(self.rotulo)}</p>'
            if self.rotulo
            else ""
        )
        etiqueta = (
            f'<span style="display:inline-block;margin:0 0 14px;padding:3px 9px;border-radius:4px;'
            f'background:{color_etq}22;border:1px solid {color_etq};font:600 12px/1.4 {SANS};color:{TEXTO}">'
            f'<span style="display:inline-block;width:7px;height:7px;margin:0 7px 1px 0;background:{color_etq};'
            f'border-radius:1px"></span>{escape(self.etiqueta)}</span>'
            if self.etiqueta
            else ""
        )
        parrafos = "".join(
            f'<p style="margin:0 0 12px;font:15px/1.6 {SANS};color:{TEXTO}">{_lineas(p)}</p>' for p in self.parrafos
        )
        cita = (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:6px 0 16px">'
            f'<tr><td style="padding:12px 14px;background:{HORMIGON};border-left:3px solid {CASCO};border-radius:0 6px 6px 0">'
            + (
                f'<p style="margin:0 0 4px;font:500 10px/1.4 {MONO};letter-spacing:.14em;text-transform:uppercase;'
                f'color:{TEXTO_SUAVE}">{escape(self.cita_rotulo)}</p>'
                if self.cita_rotulo
                else ""
            )
            + f'<p style="margin:0;font:14px/1.55 {SANS};color:{TEXTO}">{_lineas(self.cita)}</p></td></tr></table>'
            if self.cita
            else ""
        )
        datos = (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 16px;'
            f'border-top:1px dashed {LINEA}">'
            + "".join(
                f'<tr><td style="padding:8px 0;border-bottom:1px dashed {LINEA};font:12px/1.4 {SANS};color:{TEXTO_SUAVE};width:40%">{escape(k)}</td>'
                f'<td style="padding:8px 0;border-bottom:1px dashed {LINEA};font:600 13px/1.4 {SANS};color:{TEXTO};text-align:right">{escape(v)}</td></tr>'
                for k, v in self.datos
            )
            + "</table>"
            if self.datos
            else ""
        )
        boton = (
            f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:4px 0 18px"><tr>'
            f'<td style="background:{ACENTO};border-radius:6px">'
            f'<a href="{escape(self.enlace, quote=True)}" style="display:inline-block;padding:11px 20px;font:600 14px/1.2 {SANS};'
            f'color:#ffffff;text-decoration:none;border-radius:6px">{escape(self.boton or "Abrir en MinutoDesk")} &rarr;</a>'
            f"</td></tr></table>"
            f'<p style="margin:0 0 16px;font:12px/1.5 {SANS};color:{TEXTO_SUAVE}">Si el botón no funciona, copia este enlace: '
            f'<a href="{escape(self.enlace, quote=True)}" style="color:{ACENTO};word-break:break-all">{escape(self.enlace)}</a></p>'
            if self.enlace
            else ""
        )
        nota = (
            f'<p style="margin:0;padding-top:14px;border-top:1px dashed {LINEA};font:12px/1.55 {SANS};color:{TEXTO_SUAVE}">{_lineas(self.nota)}</p>'
            if self.nota
            else ""
        )
        return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{escape(self.asunto)}</title></head>
<body style="margin:0;padding:0;background:{HORMIGON}">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{escape(self.parrafos[0] if self.parrafos else self.titulo)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{HORMIGON}">
<tr><td align="center" style="padding:28px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;border-radius:10px;overflow:hidden;border:1px solid {LINEA};background:#ffffff">
  <tr><td style="background:{GRAFITO};padding:18px 24px">
    <table role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td style="width:34px;height:34px;background:{GRAFITO};border:2px solid {CASCO};border-radius:6px;text-align:center;vertical-align:middle;font:800 18px/30px {SANS};color:#ffffff">M</td>
      <td style="padding-left:12px">
        <div style="font:800 17px/1.1 {SANS};color:#ffffff;letter-spacing:-.01em">Minuto<span style="color:{CASCO}">Desk</span></div>
        <div style="font:500 10px/1.4 {MONO};color:{CASCO};letter-spacing:.16em;text-transform:uppercase">Mesa de ayuda de TI</div>
      </td></tr></table>
  </td></tr>
  <tr><td style="height:5px;background:{CASCO};background-image:repeating-linear-gradient(135deg,{GRAFITO} 0 10px,{CASCO} 10px 20px);font-size:0;line-height:0">&nbsp;</td></tr>
  <tr><td style="padding:26px 24px 22px">
    {rotulo}
    <h1 style="margin:0 0 10px;font:800 23px/1.2 {SANS};color:{TEXTO};letter-spacing:-.01em">{escape(self.titulo)}</h1>
    {etiqueta}
    <p style="margin:0 0 12px;font:15px/1.6 {SANS};color:{TEXTO}">{escape(self.saludo)}</p>
    {parrafos}
    {cita}
    {datos}
    {boton}
    {nota}
  </td></tr>
  <tr><td style="padding:14px 24px;background:{HORMIGON};border-top:1px solid {LINEA}">
    <p style="margin:0;font:500 10.5px/1.6 {MONO};color:{TEXTO_SUAVE};letter-spacing:.12em;text-transform:uppercase">Mesa de ayuda MinutoDesk</p>
    <p style="margin:2px 0 0;font:12px/1.5 {SANS};color:{TEXTO_SUAVE}">Este correo se envió automáticamente; no respondas a este mensaje. Usa el chat del ticket en el portal.</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def _lineas(texto: str) -> str:
    return escape(texto).replace("\n", "<br>")

"""Anonimización de los datos reales de la empresa.

Los nombres de solicitantes y técnicos se reemplazan por alias estables
("Solicitante 007", "Técnico 03"): la misma persona recibe siempre el mismo alias,
así los análisis por persona siguen funcionando. En la base solo queda el hash del
nombre, nunca el nombre.

En las descripciones se reemplazan correos, cédulas y teléfonos, los nombres
completos de las personas conocidas, las menciones (@Nombre) y el nombre que va
justo antes de una cédula. Un nombre suelto ("Carlos, por favor…") no se
puede distinguir con seguridad de una palabra común y se deja.
"""
import hashlib
import re
from typing import Iterable, Optional

from sqlmodel import Session, select

from app.ml.train_classifier import quitar_tildes
from app.models import Seudonimo

PREFIJOS = {"solicitante": ("Solicitante", 3), "tecnico": ("Técnico", 2)}
ALIAS_RE = re.compile(r"^(Solicitante \d{3}|Técnico \d{2})$")

CORREO_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Cédula o celular de Ecuador (10 dígitos), con o sin +593; teléfonos fijos con prefijo.
NUMERO_RE = re.compile(r"(?<!\d)(?:\+?593[\s-]?)?\d{2,3}[\s-]?\d{3}[\s-]?\d{4}(?!\d)")


_PALABRA = r"[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñü]+"
# Menciones (@Nombre Apellido) y nombres de terceros justo antes de su cédula
# ("Danny Briones C.I. #…", "DAVID MALLA CEDULA …"): suelen ser colaboradores nuevos.
MENCION_RE = re.compile(rf"@{_PALABRA}(?:\s+{_PALABRA}){{0,3}}")
ANTES_DE_CEDULA_RE = re.compile(
    rf"\b{_PALABRA}(?:\s+{_PALABRA}){{1,3}}(?=\s*-?\s*(?i:con\s+)?(?i:C\.?\s?I\b|c[eé]dula))"
)


def _normalizar(nombre: str) -> str:
    return " ".join(quitar_tildes(nombre).lower().split())


def es_alias(texto: Optional[str]) -> bool:
    return bool(texto) and bool(ALIAS_RE.match(texto))


def alias(session: Session, nombre: Optional[str], tipo: str) -> Optional[str]:
    """Alias de la persona; lo crea la primera vez que aparece."""
    if not nombre or es_alias(nombre):
        return nombre
    clave = hashlib.sha256(f"{tipo}:{_normalizar(nombre)}".encode()).hexdigest()
    existente = session.exec(select(Seudonimo).where(Seudonimo.clave == clave)).first()
    if existente:
        return existente.alias
    prefijo, digitos = PREFIJOS[tipo]
    cuantos = len(session.exec(select(Seudonimo.id).where(Seudonimo.alias.startswith(prefijo))).all())
    nuevo = Seudonimo(clave=clave, alias=f"{prefijo} {cuantos + 1:0{digitos}d}")
    session.add(nuevo)
    session.flush()
    return nuevo.alias


_VOCALES = {"a": "[aáà]", "e": "[eéè]", "i": "[iíì]", "o": "[oóò]", "u": "[uúüù]", "n": "[nñ]"}


def _patron_de_nombre(nombre: str) -> Optional[re.Pattern]:
    partes = _normalizar(nombre).split()
    if len(partes) < 2:  # un nombre suelto es demasiado ambiguo
        return None
    piezas = ["".join(_VOCALES.get(c, re.escape(c)) for c in p) for p in partes]
    return re.compile(r"\b" + r"\s+".join(piezas) + r"\b", re.IGNORECASE)


def preparar_nombres(nombres: Iterable[Optional[str]]) -> list[re.Pattern]:
    patrones = {_normalizar(n): _patron_de_nombre(n) for n in nombres if n and not es_alias(n)}
    # Los nombres más largos primero, para no dejar restos de un nombre compuesto.
    return [p for _, p in sorted(patrones.items(), key=lambda x: -len(x[0])) if p is not None]


def limpiar_texto(texto: Optional[str], nombres: list[re.Pattern]) -> Optional[str]:
    if not texto:
        return texto
    texto = CORREO_RE.sub("[correo]", texto)
    texto = MENCION_RE.sub("@[persona]", texto)
    texto = ANTES_DE_CEDULA_RE.sub("[persona]", texto)
    texto = NUMERO_RE.sub("[número]", texto)
    for patron in nombres:
        texto = patron.sub("[persona]", texto)
    return texto


def anonimizar_base(session: Session) -> dict:
    """Aplica la anonimización a lo que ya está en la base: el histórico y los tickets de
    la carga masiva. Se puede repetir: lo que ya es alias no cambia."""
    from app.models import Ticket, TicketHistorico

    historicos = session.exec(select(TicketHistorico)).all()
    cargados = session.exec(select(Ticket).where(Ticket.id_externo != None)).all()  # noqa: E711
    nombres = preparar_nombres(
        [h.solicitante for h in historicos]
        + [h.asignado_a for h in historicos]
        + [t.solicitante_externo for t in cargados]
    )
    cambios = {"historico": 0, "tickets": 0}
    for h in historicos:
        nuevo = (
            alias(session, h.solicitante, "solicitante"),
            alias(session, h.asignado_a, "tecnico"),
            limpiar_texto(h.descripcion, nombres),
        )
        if nuevo != (h.solicitante, h.asignado_a, h.descripcion):
            h.solicitante, h.asignado_a, h.descripcion = nuevo
            session.add(h)
            cambios["historico"] += 1
    for t in cargados:
        nuevo = (alias(session, t.solicitante_externo, "solicitante"), limpiar_texto(t.texto, nombres))
        if nuevo != (t.solicitante_externo, t.texto):
            t.solicitante_externo, t.texto = nuevo
            session.add(t)
            cambios["tickets"] += 1
    session.commit()
    return cambios

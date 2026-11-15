"""Genera en lote las respuestas de Minutito para las incidencias del histórico.

Minutito responde el texto de cada incidencia, como si la persona se lo escribiera, y se
guarda en data/evaluacion_historico/respuestas.json (se puede cortar y retomar; no
escribe en la base). La plataforma las carga en Datos históricos → Incidencias del
histórico, donde se marcan y se calcula la reducción (services/evaluacion_historico.py).

Uso (desde backend/):  venv/Scripts/python.exe scripts/minutito_historico.py
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlmodel import Session, create_engine, select  # noqa: E402

from app.models import TicketHistorico  # noqa: E402
from app.services.catalogos import TIPO_INCIDENCIA  # noqa: E402

DB = BACKEND / "minutodesk.db"
SALIDA = BACKEND.parent / "data" / "evaluacion_historico"
RESPUESTAS = SALIDA / "respuestas.json"


def _engine():
    return create_engine(f"sqlite:///file:{DB}?mode=ro&uri=true")


def incidencias(session: Session) -> list[TicketHistorico]:
    """Las mismas que usa la línea base de incidencias en simulacion_tiempos.simular."""
    filas = session.exec(
        select(TicketHistorico).where(
            TicketHistorico.resuelto_en != None,  # noqa: E711
            TicketHistorico.estado == "Completado",
            TicketHistorico.tipo == TIPO_INCIDENCIA,
        ).order_by(TicketHistorico.creado_en)
    ).all()
    return [h for h in filas if h.resuelto_en >= h.creado_en or h.resuelto_en.date() == h.creado_en.date()]


def generar() -> None:
    from app.services.casos_resueltos import casos_parecidos
    from app.services.minutito_chat import MinutitoNoDisponible, responder

    SALIDA.mkdir(parents=True, exist_ok=True)
    hechas = json.loads(RESPUESTAS.read_text(encoding="utf-8")) if RESPUESTAS.exists() else {}
    with Session(_engine()) as s:
        lista = incidencias(s)
        for i, h in enumerate(lista, 1):
            if h.id_externo in hechas or not (h.descripcion or "").strip():
                continue
            try:
                casos = casos_parecidos(s, [h.descripcion])
                texto, escala = responder([("usuario", h.descripcion)], casos=casos)
            except MinutitoNoDisponible as e:
                print(f"Minutito no disponible, se retoma luego: {e}")
                break
            hechas[h.id_externo] = {"respuesta": texto, "escalado": escala}
            RESPUESTAS.write_text(json.dumps(hechas, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{i}/{len(lista)} H-{h.id_externo}", flush=True)
    print(f"Listas {len(hechas)} de {len(lista)}")


if __name__ == "__main__":
    generar()

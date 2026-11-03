"""Prueba controlada de Minutito con un colaborador simulado.

Para cada escenario de primer nivel (escenarios_prueba.py) un agente, con el mismo
modelo local, hace de colaborador: cuenta el problema con sus palabras y responde a lo
que Minutito le pide. Solo dice que se arregló si Minutito le indica lo que de verdad lo
arregla. Minutito responde igual que en el chat real (con los casos que aprendió).

El agente no califica: una persona del equipo lee cada conversación y marca si Minutito
lo resolvió, igual que en la evaluación con los tickets de la empresa.
"""
import json
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.models import Cliente, PruebaMinutito
from app.services import minutito_chat
from app.services.casos_resueltos import casos_parecidos
from app.services.escenarios_prueba import ESCENARIOS, Escenario
from app.services.minutito_chat import MinutitoNoDisponible

logger = logging.getLogger("minutodesk.prueba")

VEREDICTOS = ("resuelve", "no_resuelve", "no_aplica")
META = 0.30
MAX_RESPUESTAS = 3  # respuestas de Minutito por conversación
MARCA_RESUELTO = "[RESUELTO]"
MARCA_TICKET = "[TICKET]"
INICIO = "(Escribe ahora tu primer mensaje al asistente de soporte.)"

PROMPT_COLABORADOR = """Eres un colaborador de una constructora e inmobiliaria que le escribe por chat al asistente de soporte de sistemas. No sabes mucho de computadoras.

Tu situación: {situacion}
Lo que de verdad pasa (tú NO lo sabes, nunca lo digas): {causa}
Lo único que lo arregla: {arreglo}

Reglas:
- Escribe como una persona real por chat: de 1 a 3 frases, informal, en español, sin listas ni formato.
- En tu primer mensaje cuenta el problema con tus palabras, sin decir la causa ni la solución, y sin decir que ya probaste cosas.
- Si el asistente te pregunta algo, respóndele de forma coherente con tu situación.
- Cuando el asistente te dé pasos, haz como que los hiciste en ese momento y cuenta el resultado; no digas «voy a probar».
- Si alguno de esos pasos equivale a lo que lo arregla, di cuál hiciste y que con eso funcionó, y termina tu mensaje con {marca}
- Si ninguno equivale a lo que lo arregla, di que los probaste y que sigue igual (puedes contar qué ves).
- Si el asistente solo te ofrece crear un ticket, sin nada nuevo que probar, acepta y termina tu mensaje con {marca_ticket}
- Nunca digas que funcionó si no te indicó lo que lo arregla."""


def _por_clave() -> dict[str, Escenario]:
    return {e.clave: e for e in ESCENARIOS}


def _colaborador(escenario: Escenario, historial: list[tuple[str, str]]) -> str:
    """Siguiente mensaje del colaborador. Para el agente, Minutito es el «usuario»."""
    mensajes = [
        {
            "role": "system",
            "content": PROMPT_COLABORADOR.format(
                situacion=escenario.situacion,
                causa=escenario.causa,
                arreglo=escenario.arreglo,
                marca=MARCA_RESUELTO,
                marca_ticket=MARCA_TICKET,
            ),
        },
        {"role": "user", "content": INICIO},
    ]
    mensajes += [{"role": "assistant" if r == "usuario" else "user", "content": t} for r, t in historial]
    respuesta = minutito_chat._llamar(mensajes, stream=False)
    texto = (respuesta.message.content or "").strip()
    if not texto:
        raise MinutitoNoDisponible("Ollama devolvió una respuesta vacía")
    return texto


def _sin_marcas(texto: str) -> str:
    return texto.replace(MARCA_RESUELTO, "").replace(MARCA_TICKET, "").strip()


def simular(session: Session, escenario: Escenario) -> tuple[list[tuple[str, str]], str]:
    """Conversación completa entre el colaborador simulado y Minutito, y cómo terminó.
    Aunque Minutito ofrezca el ticket, el colaborador contesta: si junto con la oferta
    le dio lo que lo arregla, lo prueba y se resuelve."""
    historial = [("usuario", _sin_marcas(_colaborador(escenario, [])))]
    ofrece_ticket = False
    for turno in range(MAX_RESPUESTAS):
        casos = casos_parecidos(session, [t for r, t in historial if r == "usuario"][-3:])
        respuesta, ofrece_ticket = minutito_chat.responder(historial, casos=casos)
        historial.append(("minutito", respuesta))
        if turno == MAX_RESPUESTAS - 1:
            break
        mensaje = _colaborador(escenario, historial)
        historial.append(("usuario", _sin_marcas(mensaje)))
        if MARCA_RESUELTO in mensaje:
            return historial, "resuelto"
        if MARCA_TICKET in mensaje:
            return historial, "ticket"
    return historial, "ticket" if ofrece_ticket else "sin_cierre"


# Avance de la corrida en segundo plano, para que la pantalla lo muestre y no se lancen
# dos a la vez (las dos competirían por el mismo procesador).
progreso = {"en_curso": False, "hechas": 0, "total": 0}


def generar_pendientes(session: Session, *args, **kwargs) -> dict:
    progreso.update(en_curso=True, hechas=0, total=0)
    try:
        return _generar(session, *args, **kwargs)
    finally:
        progreso["en_curso"] = False


def _generar(session: Session, todas: bool = False) -> dict:
    """Corre las conversaciones que faltan (o todas otra vez). Si Ollama no responde se
    detiene: lo que falte se completa en otra corrida."""
    hechos = 0
    existentes = {p.clave: p for p in session.exec(select(PruebaMinutito)).all()}
    pendientes = [
        e for e in ESCENARIOS if todas or e.clave not in existentes or existentes[e.clave].conversacion is None
    ]
    progreso["total"] = len(pendientes)
    for escenario in pendientes:
        registro = existentes.get(escenario.clave) or PruebaMinutito(clave=escenario.clave)
        try:
            historial, termino = simular(session, escenario)
        except MinutitoNoDisponible as e:
            logger.warning("Minutito no disponible en la prueba controlada: %s", e)
            return {"generadas": hechos, "pendientes": len(pendientes) - hechos, "error": str(e)}
        registro.conversacion = json.dumps([{"rol": r, "texto": t} for r, t in historial], ensure_ascii=False)
        registro.termino = termino
        registro.generada_en = datetime.now()
        registro.veredicto = None  # una conversación nueva se vuelve a evaluar
        registro.evaluado_por_id = None
        registro.evaluado_en = None
        session.add(registro)
        session.commit()
        hechos += 1
        progreso["hechas"] = hechos
    return {"generadas": hechos, "pendientes": len(pendientes) - hechos, "error": None}


def marcar(session: Session, prueba_id: int, veredicto: Optional[str], quien: Cliente) -> PruebaMinutito:
    if veredicto is not None and veredicto not in VEREDICTOS:
        raise ValueError("Veredicto no válido")
    registro = session.get(PruebaMinutito, prueba_id)
    if registro is None or registro.conversacion is None:
        raise LookupError("Prueba no encontrada")
    registro.veredicto = veredicto
    registro.evaluado_por_id = quien.id if veredicto else None
    registro.evaluado_en = datetime.now() if veredicto else None
    session.add(registro)
    session.commit()
    session.refresh(registro)
    return registro


def resumen(session: Session) -> dict:
    escenarios = _por_clave()
    hechas = [
        p
        for p in session.exec(select(PruebaMinutito).order_by(PruebaMinutito.id)).all()
        if p.conversacion and p.clave in escenarios
    ]
    cuenta = {v: sum(p.veredicto == v for p in hechas) for v in VEREDICTOS}
    primer_nivel = cuenta["resuelve"] + cuenta["no_resuelve"]
    return {
        "meta": META,
        "escenarios": len(ESCENARIOS),
        "generadas": len(hechas),
        "sin_evaluar": sum(p.veredicto is None for p in hechas),
        **cuenta,
        "pct_resolveria": round(cuenta["resuelve"] / primer_nivel, 4) if primer_nivel else None,
        "progreso": dict(progreso),
        "items": [
            {
                "id": p.id,
                "clave": p.clave,
                "tema": escenarios[p.clave].tema,
                "situacion": escenarios[p.clave].situacion,
                "arreglo": escenarios[p.clave].arreglo,
                "conversacion": json.loads(p.conversacion),
                "termino": p.termino,
                "veredicto": p.veredicto,
            }
            for p in hechas
        ],
    }

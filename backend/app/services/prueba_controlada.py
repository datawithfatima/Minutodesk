"""Prueba controlada de Minutito con un colaborador simulado.

Para cada escenario de primer nivel (escenarios_prueba.py) un agente, con el mismo
modelo local, hace de colaborador: cuenta el problema con sus palabras y responde a lo
que Minutito le pide. Si una respuesta de Minutito incluye lo que de verdad lo arregla
(se pregunta aparte, con una pregunta cerrada), el colaborador dice que funcionó; si no,
que sigue igual, hasta 3 respuestas. Minutito responde igual que en el chat real (con
los casos que aprendió).

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

# El colaborador no conoce la solución: así no la «adivina» ni la sugiere. Qué le pasa
# al seguir los pasos se decide aparte (_le_dio_el_arreglo) y se le dice en cada turno.
PROMPT_COLABORADOR = """Eres un colaborador de una constructora e inmobiliaria que le escribe por chat al asistente de soporte de sistemas. No sabes mucho de computadoras.

Tu situación: {situacion}

Escribe como una persona real por chat: de 1 a 3 frases, informal, en español, sin listas ni formato. No inventes que ya probaste cosas que nadie te indicó."""

PRIMER_MENSAJE = "(Escribe tu primer mensaje al asistente: cuenta el problema con tus palabras.)"
FUNCIONO = "(Hiciste lo que te indicó y con el paso «{arreglo}» se arregló. Respóndele en 1 o 2 frases que ya funcionó y agradécele.)"
NO_FUNCIONO = "(Hiciste lo que te indicó, pero el problema sigue igual. Respóndele en 1 o 2 frases qué hiciste y que sigue igual; si te hizo preguntas, respóndelas de forma coherente con tu situación.)"

PROMPT_COINCIDE = """Decide si la respuesta de un asistente de soporte le indica a la persona hacer un paso concreto.

Paso que arregla el problema: {arreglo}

Respuesta del asistente:
{respuesta}

¿La respuesta le indica hacer ese paso o uno equivalente (aunque lo diga con otras palabras, entre otros pasos)? Contesta solo SI o NO."""


def _por_clave() -> dict[str, Escenario]:
    return {e.clave: e for e in ESCENARIOS}


def _texto(mensajes: list[dict]) -> str:
    respuesta = minutito_chat._llamar(mensajes, stream=False)
    texto = (respuesta.message.content or "").strip()
    if not texto:
        raise MinutitoNoDisponible("Ollama devolvió una respuesta vacía")
    return texto


def _le_dio_el_arreglo(escenario: Escenario, respuesta: str) -> bool:
    """¿La respuesta de Minutito incluye lo que arregla el problema? Es una pregunta
    cerrada y aparte: el modelo la acierta mucho mejor que actuando a la vez de persona."""
    veredicto = _texto([{"role": "user", "content": PROMPT_COINCIDE.format(arreglo=escenario.arreglo, respuesta=respuesta)}])
    return veredicto.upper().lstrip("¡¿ *").startswith(("SI", "SÍ"))


def _colaborador(escenario: Escenario, historial: list[tuple[str, str]], indicacion: str) -> str:
    """Siguiente mensaje del colaborador. Para el agente, Minutito es el «usuario»."""
    mensajes = [{"role": "system", "content": PROMPT_COLABORADOR.format(situacion=escenario.situacion)}]
    mensajes.append({"role": "user", "content": PRIMER_MENSAJE})
    turnos = [{"role": "assistant" if r == "usuario" else "user", "content": t} for r, t in historial]
    mensajes += turnos
    if turnos:  # la indicación acompaña la última respuesta de Minutito
        mensajes[-1] = {"role": "user", "content": f"{turnos[-1]['content']}\n\n{indicacion}"}
    return _texto(mensajes)


def simular(session: Session, escenario: Escenario) -> tuple[list[tuple[str, str]], str]:
    """Conversación completa entre el colaborador simulado y Minutito, y cómo terminó:
    «resuelto» si Minutito le dio lo que lo arregla, si no «ticket» (si lo ofreció al
    final) o «sin_cierre»."""
    historial = [("usuario", _colaborador(escenario, [], PRIMER_MENSAJE))]
    ofrece_ticket = False
    for turno in range(MAX_RESPUESTAS):
        casos = casos_parecidos(session, [t for r, t in historial if r == "usuario"][-3:])
        respuesta, ofrece_ticket = minutito_chat.responder(historial, casos=casos)
        historial.append(("minutito", respuesta))
        if not escenario.arreglo:  # una solicitud que solo atiende sistemas: no hay arreglo por chat
            if ofrece_ticket:
                return historial, "ticket"
        elif _le_dio_el_arreglo(escenario, respuesta):
            historial.append(("usuario", _colaborador(escenario, historial, FUNCIONO.format(arreglo=escenario.arreglo))))
            return historial, "resuelto"
        if turno == MAX_RESPUESTAS - 1:
            break
        historial.append(("usuario", _colaborador(escenario, historial, NO_FUNCIONO)))
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

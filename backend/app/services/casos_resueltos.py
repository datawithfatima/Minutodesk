"""Casos resueltos que Minutito usa como ejemplo.

En «Evaluación de Minutito» el equipo anota qué se debía hacer en cada ticket. Cuando
alguien le pregunta algo a Minutito, se buscan los casos con el texto más parecido
(con el mismo TF-IDF del clasificador) y sus soluciones se le pasan como referencia.

Para que la evaluación siga siendo justa, al generar la respuesta de un ticket evaluado
se excluye su propia solución (validación «dejando uno fuera»): Minutito aprende de los
demás casos, nunca del que se está midiendo.
"""
from typing import Optional

from sklearn.metrics.pairwise import cosine_similarity
from sqlmodel import Session, select

from app.ml.train_classifier import preprocesar_texto
from app.models import EvaluacionMinutito, Ticket
from app.services.classifier import _vectorizer

MAXIMO_CASOS = 2
SIMILITUD_MINIMA = 0.25  # por debajo, el caso no se parece lo suficiente


def casos_parecidos(
    session: Session, textos: list[str], excluir_ticket_id: Optional[int] = None
) -> list[tuple[str, str]]:
    """Pares (consulta, solución) de los casos anotados más parecidos a `textos`."""
    consulta = " ".join(t for t in textos if t).strip()
    if not consulta:
        return []
    filas = session.exec(
        select(Ticket.id, Ticket.texto, EvaluacionMinutito.solucion_esperada)
        .where(EvaluacionMinutito.ticket_id == Ticket.id, EvaluacionMinutito.solucion_esperada != None)  # noqa: E711
    ).all()
    filas = [f for f in filas if f[0] != excluir_ticket_id]
    if not filas:
        return []
    matriz = _vectorizer.transform([preprocesar_texto(f[1]) for f in filas])
    similitudes = cosine_similarity(_vectorizer.transform([preprocesar_texto(consulta)]), matriz)[0]
    orden = similitudes.argsort()[::-1][:MAXIMO_CASOS]
    return [(filas[i][1], filas[i][2]) for i in orden if similitudes[i] >= SIMILITUD_MINIMA]

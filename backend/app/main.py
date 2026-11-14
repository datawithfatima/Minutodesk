import asyncio
import os
from contextlib import contextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app import models  # noqa: F401 (registra las tablas en SQLModel.metadata)
from app.database import get_session, init_db
from app.services import auditoria, avisos_sla, minutito_chat, respaldo
from app.routers import (
    adjuntos,
    admin,
    auth,
    bitacora,
    chat,
    clientes,
    conocimiento,
    conversacion,
    encuestas,
    gamificacion,
    historico,
    minutito,
    reportes,
    respuestas,
    tickets,
)

# La documentación interactiva (/docs) solo si se pide en .env: no hace falta exponerla.
docs_activas = os.getenv("API_DOCS", "0") == "1"
app = FastAPI(
    title="MinutoDesk",
    docs_url="/docs" if docs_activas else None,
    redoc_url=None,
    openapi_url="/openapi.json" if docs_activas else None,
)

origenes = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origenes.split(",") if o.strip()],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Nombre-Archivo"],
)


@app.middleware("http")
async def cabeceras_de_seguridad(request: Request, call_next):
    respuesta = await call_next(request)
    respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
    respuesta.headers.setdefault("X-Frame-Options", "DENY")
    respuesta.headers.setdefault("Referrer-Policy", "no-referrer")
    # Las respuestas de la API traen datos personales: que no queden en la caché del navegador.
    respuesta.headers.setdefault("Cache-Control", "no-store")
    return respuesta


@contextmanager
def _sesion_bitacora():
    # La misma fábrica de sesiones que usan los endpoints (las pruebas la reemplazan).
    generador = app.dependency_overrides.get(get_session, get_session)()
    try:
        yield next(generador)
    finally:
        generador.close()


@app.middleware("http")
async def bitacora_de_auditoria(request: Request, call_next):
    """Registra en la bitácora las acciones de auditoria.ACCIONES (ver ese módulo). Solo
    lee el cuerpo de esas peticiones, y solo si es JSON: el resto pasa sin tocarse."""
    if request.method == "OPTIONS" or auditoria.buscar(request.method, request.url.path) is None:
        return await call_next(request)
    accion, _ = auditoria.buscar(request.method, request.url.path)
    es_json = request.headers.get("content-type", "").startswith("application/json")
    cuerpo = await request.body() if es_json else b""
    respuesta = await call_next(request)
    contenido = None
    if accion.leer_respuesta and respuesta.status_code < 400:
        contenido = b"".join([trozo async for trozo in respuesta.body_iterator])
        respuesta = Response(
            content=contenido,
            status_code=respuesta.status_code,
            headers={k: v for k, v in respuesta.headers.items() if k.lower() != "content-length"},
            media_type=respuesta.media_type,
        )
    await run_in_threadpool(
        auditoria.registrar,
        _sesion_bitacora,
        metodo=request.method,
        ruta=request.url.path,
        consulta=request.url.query,
        estado_http=respuesta.status_code,
        autorizacion=request.headers.get("authorization"),
        cuerpo=cuerpo,
        respuesta=contenido,
        ip=request.client.host if request.client else None,
    )
    return respuesta


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(bitacora.router, prefix="/admin", tags=["bitacora"])  # bitácora y respaldos
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(adjuntos.router, tags=["adjuntos"])  # /tickets/{id}/adjuntos y /adjuntos/{id}
app.include_router(chat.router, prefix="/tickets", tags=["chat"])
app.include_router(conversacion.router, tags=["conversacion"])  # chat con soporte y aprobaciones
app.include_router(minutito.router, prefix="/minutito", tags=["minutito"])  # conversación antes del ticket
app.include_router(conocimiento.router, prefix="/conocimiento", tags=["conocimiento"])  # autoservicio
app.include_router(respuestas.router, tags=["respuestas"])  # macros del personal y duplicados
app.include_router(encuestas.router, tags=["encuestas"])  # satisfacción al resolver
app.include_router(clientes.router, prefix="/clientes", tags=["clientes"])
app.include_router(gamificacion.router, prefix="/gamificacion", tags=["gamificacion"])
app.include_router(reportes.router, prefix="/reportes", tags=["reportes"])
app.include_router(historico.router, prefix="/historico", tags=["historico"])


@app.on_event("startup")
def on_startup():
    init_db()


@app.on_event("startup")
async def iniciar_avisos_de_plazo():
    # Revisa cada tanto los tickets abiertos y avisa al técnico cuando su plazo está por
    # vencer o venció. Se apaga con SLA_AVISOS=0 (p. ej. en pruebas).
    if os.getenv("SLA_AVISOS", "1") != "0":
        asyncio.create_task(avisos_sla.bucle())


@app.on_event("startup")
async def iniciar_respaldos():
    # Respaldo automático de la base (al arrancar si el último tiene más de 24 h, y luego
    # se revisa cada hora). Se apaga con RESPALDO_AUTOMATICO=0.
    if os.getenv("RESPALDO_AUTOMATICO", "1") != "0":
        asyncio.create_task(respaldo.bucle())


@app.on_event("startup")
async def precalentar_minutito():
    # Carga el modelo de Minutito en segundo plano al arrancar, para que la primera pregunta
    # no espere ~40 s. Se apaga con MINUTITO_PRECALENTAR=0 (p. ej. en pruebas).
    if os.getenv("MINUTITO_PRECALENTAR", "1") != "0":
        asyncio.get_running_loop().run_in_executor(None, minutito_chat.precalentar)


@app.get("/health")
def health():
    return {"status": "ok"}

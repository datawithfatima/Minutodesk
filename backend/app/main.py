import asyncio
import os
from contextlib import contextmanager

from fastapi import FastAPI, Request
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


class BitacoraDeAuditoria:
    """Middleware ASGI que registra en la bitácora las acciones de auditoria.ACCIONES.

    No retiene ni modifica nada: copia el cuerpo JSON de la petición mientras el endpoint
    lo lee y, si hace falta, el de la respuesta mientras se envía. La fila se escribe
    cuando la petición terminó del todo (incluido el cierre de su sesión de base de
    datos), así no compite con ella y no demora la respuesta."""

    def __init__(self, aplicacion):
        self.aplicacion = aplicacion

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] == "OPTIONS":
            return await self.aplicacion(scope, receive, send)
        encontrada = auditoria.buscar(scope["method"], scope["path"])
        if encontrada is None:
            return await self.aplicacion(scope, receive, send)
        accion, _ = encontrada
        cabeceras = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        es_json = cabeceras.get("content-type", "").startswith("application/json")
        cuerpo, contenido, estado = bytearray(), bytearray(), {"codigo": 500}

        async def recibir():
            mensaje = await receive()
            if es_json and mensaje["type"] == "http.request" and len(cuerpo) < 65536:
                cuerpo.extend(mensaje.get("body", b""))
            return mensaje

        async def enviar(mensaje):
            if mensaje["type"] == "http.response.start":
                estado["codigo"] = mensaje["status"]
            elif mensaje["type"] == "http.response.body" and accion.leer_respuesta and len(contenido) < 65536:
                contenido.extend(mensaje.get("body", b""))
            await send(mensaje)

        try:
            await self.aplicacion(scope, recibir, enviar)
        finally:
            cliente = scope.get("client")
            await run_in_threadpool(
                auditoria.registrar,
                _sesion_bitacora,
                metodo=scope["method"],
                ruta=scope["path"],
                consulta=scope.get("query_string", b"").decode("latin-1"),
                estado_http=estado["codigo"],
                autorizacion=cabeceras.get("authorization"),
                cuerpo=bytes(cuerpo),
                respuesta=bytes(contenido) if contenido else None,
                ip=cliente[0] if cliente else None,
            )


app.add_middleware(BitacoraDeAuditoria)


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

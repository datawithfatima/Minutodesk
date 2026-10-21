import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 (registra las tablas en SQLModel.metadata)
from app.database import init_db
from app.routers import (
    adjuntos,
    admin,
    auth,
    chat,
    clientes,
    conversacion,
    historico,
    reportes,
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


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(adjuntos.router, tags=["adjuntos"])  # /tickets/{id}/adjuntos y /adjuntos/{id}
app.include_router(chat.router, prefix="/tickets", tags=["chat"])
app.include_router(conversacion.router, tags=["conversacion"])  # chat con soporte y aprobaciones
app.include_router(clientes.router, prefix="/clientes", tags=["clientes"])
app.include_router(reportes.router, prefix="/reportes", tags=["reportes"])
app.include_router(historico.router, prefix="/historico", tags=["historico"])


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}

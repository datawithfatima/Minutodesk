from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 (registra las tablas en SQLModel.metadata)
from app.database import init_db
from app.routers import auth, chat, clientes, tickets

app = FastAPI(title="MinutoDesk")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(chat.router, prefix="/tickets", tags=["chat"])
app.include_router(clientes.router, prefix="/clientes", tags=["clientes"])


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}

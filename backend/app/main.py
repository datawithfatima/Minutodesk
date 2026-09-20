from fastapi import FastAPI

from app import models  # noqa: F401 (registra las tablas en SQLModel.metadata)
from app.database import init_db
from app.routers import chat, tickets

app = FastAPI(title="MinutoDesk")
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(chat.router, prefix="/tickets", tags=["chat"])


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}

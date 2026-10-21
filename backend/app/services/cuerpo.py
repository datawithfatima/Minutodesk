"""Lectura del cuerpo de una petición con tope de tamaño.

`await request.body()` carga todo en memoria antes de poder medirlo; aquí se corta
en cuanto se supera el límite, aunque el cliente no declare Content-Length.
"""
from fastapi import HTTPException, Request


async def leer_cuerpo_limitado(request: Request, maximo: int, mensaje: str) -> bytes:
    declarado = request.headers.get("content-length")
    if declarado and declarado.isdigit() and int(declarado) > maximo:
        raise HTTPException(status_code=413, detail=mensaje)
    contenido = bytearray()
    async for trozo in request.stream():
        contenido.extend(trozo)
        if len(contenido) > maximo:
            raise HTTPException(status_code=413, detail=mensaje)
    return bytes(contenido)

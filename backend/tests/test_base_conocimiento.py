"""Base de conocimiento: muestra las fichas de Minutito y sugiere la que corresponde."""
from app.services.conocimiento import FICHAS


def test_cualquier_cuenta_ve_las_fichas_y_la_sugerida(client, crear_cuenta, entrar):
    crear_cuenta("u@ejemplo.com", "usuario")
    usuario = entrar("u@ejemplo.com")

    assert client.get("/conocimiento").status_code == 401
    datos = client.get("/conocimiento", headers=usuario).json()
    assert len(datos["fichas"]) == len(FICHAS) and datos["sugerida"] is None
    assert all(f["pasos"] for f in datos["fichas"])

    datos = client.get("/conocimiento", params={"q": "La impresora no imprime nada"}, headers=usuario).json()
    assert datos["sugerida"] == "impresora"
    assert client.get("/conocimiento", params={"q": "zzzz"}, headers=usuario).json()["sugerida"] is None

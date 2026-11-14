"""Exportar Reportes: Excel con hoja de tickets y PDF; solo personal, y la calidad
del clasificador solo para el administrador."""
from io import BytesIO

from openpyxl import load_workbook

from .test_acceso_y_roles import _crear_ticket


def test_el_personal_exporta_excel_y_pdf(client, crear_cuenta, entrar):
    crear_cuenta("u@ejemplo.com", "usuario")
    crear_cuenta("t@ejemplo.com", "tecnico")
    usuario, tecnico = entrar("u@ejemplo.com"), entrar("t@ejemplo.com")
    ticket = _crear_ticket(client, usuario)
    client.patch(f"/tickets/{ticket['id']}", json={"estado": "resuelto"}, headers=tecnico)

    assert client.get("/reportes/exportar", headers=usuario).status_code == 403
    assert client.get("/reportes/exportar?formato=doc", headers=tecnico).status_code == 400

    r = client.get("/reportes/exportar?formato=xlsx", headers=tecnico)
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    libro = load_workbook(BytesIO(r.content))
    assert libro.sheetnames == ["Resumen", "Tickets"]
    textos = [c.value for fila in libro["Resumen"].iter_rows() for c in fila if c.value]
    assert "4. Satisfacción del usuario" in textos
    assert not any(str(t).startswith("5. Calidad del clasificador") for t in textos)  # solo administrador
    tickets = list(libro["Tickets"].iter_rows(values_only=True))
    assert tickets[0][0] == "Ticket" and tickets[1][0] == ticket["id"] and tickets[1][2] == "Resuelto"

    r = client.get("/reportes/exportar?formato=pdf", headers=tecnico)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")

"""Correos de aviso por cada movimiento del ticket."""


def _correos(carpeta):
    """[(para, asunto)] de los correos guardados, en orden."""
    salida = []
    for archivo in sorted(carpeta.glob("*.txt")):
        lineas = archivo.read_text(encoding="utf-8").splitlines()
        salida.append((lineas[0].removeprefix("Para: "), lineas[1].removeprefix("Asunto: ")))
    return salida


def _limpiar(carpeta):
    for archivo in carpeta.glob("*.txt"):
        archivo.unlink()


def _crear(client, h, categoria="Power BI"):
    r = client.post(
        "/tickets",
        json={"texto": "No me abre el reporte de ventas", "tipo": "Incidencia o problema técnico", "categoria": categoria},
        headers=h,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_ciclo_completo_de_avisos(client, crear_cuenta, entrar, correos):
    crear_cuenta("usr@ejemplo.com", nombre="Ana Torres")
    crear_cuenta("ana@ejemplo.com", "tecnico", nombre="Ana Mora")
    hu, ht = entrar("usr@ejemplo.com"), entrar("ana@ejemplo.com")

    tid = _crear(client, hu)
    assert _correos(correos) == [
        ("usr@ejemplo.com", f"Ticket #{tid}: lo recibimos"),
        ("ana@ejemplo.com", f"Ticket #{tid}: te lo asignaron"),
    ]
    _limpiar(correos)

    client.patch(f"/tickets/{tid}", json={"estado": "en_proceso"}, headers=ht)
    client.post(f"/tickets/{tid}/mensajes", json={"texto": "¿Qué error te sale?"}, headers=ht)
    client.post(f"/tickets/{tid}/mensajes", json={"texto": "Dice acceso denegado"}, headers=hu)
    client.patch(f"/tickets/{tid}", json={"estado": "resuelto"}, headers=ht)
    client.patch(f"/tickets/{tid}", json={"estado": "abierto"}, headers=ht)
    assert _correos(correos) == [
        ("usr@ejemplo.com", f"Ticket #{tid}: estamos trabajando en él"),
        ("usr@ejemplo.com", f"Ticket #{tid}: nuevo mensaje de soporte"),
        ("ana@ejemplo.com", f"Ticket #{tid}: nuevo mensaje del usuario"),
        ("usr@ejemplo.com", f"Ticket #{tid}: ¿quedó resuelto?"),
        ("usr@ejemplo.com", f"Ticket #{tid}: se reabrió"),
    ]


def test_cancelar_avisa_con_el_motivo(client, crear_cuenta, entrar, correos):
    crear_cuenta("usr@ejemplo.com")
    crear_cuenta("adm@ejemplo.com", "administrador")
    tid = _crear(client, entrar("usr@ejemplo.com"), "Salesforce")  # sin técnico: solo el acuse
    _limpiar(correos)
    client.post(f"/tickets/{tid}/cancelar", json={"motivo": "Duplicado del ticket 3"}, headers=entrar("adm@ejemplo.com"))
    (archivo,) = correos.glob("*.txt")
    texto = archivo.read_text(encoding="utf-8")
    assert "fue cancelado" in texto and "Motivo: «Duplicado del ticket 3»" in texto
    assert f"/usuario/tickets/{tid}" in texto


def test_no_se_avisa_a_quien_hizo_el_cambio_ni_por_cambios_menores(client, crear_cuenta, entrar, correos):
    crear_cuenta("usr@ejemplo.com")
    tec = crear_cuenta("tec@ejemplo.com", "tecnico", nombre="Luis Paredes")
    otro = crear_cuenta("otro@ejemplo.com", "tecnico", nombre="Daniela Cevallos")
    tid = _crear(client, entrar("usr@ejemplo.com"), "Salesforce")
    _limpiar(correos)
    ht = entrar("tec@ejemplo.com")
    client.patch(f"/tickets/{tid}", json={"tecnico_id": tec.id}, headers=ht)  # se lo asigna a sí mismo
    assert _correos(correos) == []
    # Ya es suyo: para pasárselo a otro técnico tiene que liberarlo; el administrador sí
    # lo reasigna directo, y el nuevo técnico recibe el aviso.
    crear_cuenta("adm@ejemplo.com", "administrador")
    client.patch(f"/tickets/{tid}", json={"tecnico_id": otro.id}, headers=entrar("adm@ejemplo.com"))
    assert _correos(correos) == [("otro@ejemplo.com", f"Ticket #{tid}: te lo asignaron")]


def test_avisos_nuevos_aprobacion_archivo_prioridad_encuesta_y_contrasena(
    client, crear_cuenta, entrar, correos, session, tmp_path, monkeypatch
):
    from datetime import datetime, timedelta

    from app.models import Ticket
    from app.routers import adjuntos

    monkeypatch.setattr(adjuntos, "DIRECTORIO_ARCHIVOS", tmp_path / "uploads")  # nunca la carpeta real

    crear_cuenta("usr@ejemplo.com", nombre="Ana Torres")
    crear_cuenta("ana@ejemplo.com", "tecnico", nombre="Ana Mora")
    crear_cuenta("jefe@ejemplo.com", "usuario", nombre="Jefe Area")
    hu, ht, hj = entrar("usr@ejemplo.com"), entrar("ana@ejemplo.com"), entrar("jefe@ejemplo.com")
    tid = _crear(client, hu)
    jefe_id = client.get("/auth/yo", headers=hj).json()["id"]

    # Archivo subido al crear el ticket: ya basta el aviso de «ticket nuevo».
    _limpiar(correos)
    subir = lambda h: client.post(f"/tickets/{tid}/adjuntos", content=b"datos", headers={**h, "X-Nombre-Archivo": "captura.png", "Content-Type": "application/octet-stream"})
    assert subir(hu).status_code == 200
    assert _correos(correos) == []
    ticket = session.get(Ticket, tid)
    ticket.creado_en = datetime.now() - timedelta(hours=1)
    session.add(ticket)
    session.commit()
    subir(hu)
    subir(ht)
    assert _correos(correos) == [
        ("ana@ejemplo.com", f"Ticket #{tid}: nuevo archivo del usuario"),
        ("usr@ejemplo.com", f"Ticket #{tid}: nuevo archivo de soporte"),
    ]

    _limpiar(correos)
    client.patch(f"/tickets/{tid}", json={"prioridad": "Alta"}, headers=ht)
    assert _correos(correos) == [("usr@ejemplo.com", f"Ticket #{tid}: cambió la prioridad")]

    _limpiar(correos)
    r = client.post(f"/tickets/{tid}/aprobaciones", json={"aprobador_id": jefe_id, "descripcion": "Aprobar compra de licencia"}, headers=ht)
    assert r.status_code == 200, r.text
    assert _correos(correos) == [
        ("jefe@ejemplo.com", f"Aprobación pendiente del ticket #{tid}"),
        ("usr@ejemplo.com", f"Ticket #{tid}: espera una aprobación"),
    ]
    _limpiar(correos)
    client.post(f"/aprobaciones/{r.json()['id']}/responder", json={"aprobada": True}, headers=hj)
    assert _correos(correos) == [
        ("ana@ejemplo.com", f"Ticket #{tid}: aprobación aprobada"),
        ("usr@ejemplo.com", f"Ticket #{tid}: aprobación aprobada"),
    ]

    client.patch(f"/tickets/{tid}", json={"estado": "resuelto"}, headers=ht)
    _limpiar(correos)
    client.post(f"/tickets/{tid}/encuesta", json={"estrellas": 5, "comentario": "Excelente"}, headers=hu)
    client.post(f"/tickets/{tid}/encuesta", json={"estrellas": 4}, headers=hu)  # cambiarla no vuelve a avisar
    assert _correos(correos) == [("ana@ejemplo.com", f"Ticket #{tid}: calificación 5 de 5")]

    _limpiar(correos)
    client.post("/auth/cambiar-password", json={"password_actual": "Clave12345", "password_nueva": "OtraClave99"}, headers=hu)
    assert _correos(correos) == [("usr@ejemplo.com", "Tu contraseña de MinutoDesk cambió")]

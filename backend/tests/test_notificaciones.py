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
    crear_cuenta("jimmy@ejemplo.com", "tecnico", nombre="Jimmy Lopez")
    hu, ht = entrar("usr@ejemplo.com"), entrar("jimmy@ejemplo.com")

    tid = _crear(client, hu)
    assert _correos(correos) == [
        ("usr@ejemplo.com", f"Ticket #{tid}: lo recibimos"),
        ("jimmy@ejemplo.com", f"Ticket #{tid}: te lo asignaron"),
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
        ("jimmy@ejemplo.com", f"Ticket #{tid}: nuevo mensaje del usuario"),
        ("usr@ejemplo.com", f"Ticket #{tid}: fue resuelto"),
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
    client.patch(f"/tickets/{tid}", json={"prioridad": "Alta"}, headers=ht)
    client.patch(f"/tickets/{tid}", json={"tecnico_id": tec.id}, headers=ht)  # se lo asigna a sí mismo
    assert _correos(correos) == []
    client.patch(f"/tickets/{tid}", json={"tecnico_id": otro.id}, headers=ht)
    assert _correos(correos) == [("otro@ejemplo.com", f"Ticket #{tid}: te lo asignaron")]

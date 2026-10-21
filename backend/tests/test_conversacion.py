"""Chat entre el usuario y soporte, y pasos de aprobación con otras personas."""


def _ticket(client, h):
    r = client.post("/tickets", json={"texto": "Necesito instalar un programa nuevo"}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_usuario_y_tecnico_conversan_y_nadie_mas_ve_el_chat(client, crear_cuenta, entrar):
    crear_cuenta("ana@ejemplo.com", nombre="Ana")
    crear_cuenta("beto@ejemplo.com")
    crear_cuenta("tec@ejemplo.com", "tecnico", nombre="Tito")
    h_ana, h_beto, h_tec = entrar("ana@ejemplo.com"), entrar("beto@ejemplo.com"), entrar("tec@ejemplo.com")
    tid = _ticket(client, h_ana)

    assert client.post(f"/tickets/{tid}/mensajes", json={"texto": "¿Qué programa?"}, headers=h_tec).status_code == 200
    assert client.post(f"/tickets/{tid}/mensajes", json={"texto": "  Power BI  "}, headers=h_ana).status_code == 200
    conversacion = client.get(f"/tickets/{tid}/conversacion", headers=h_ana).json()
    assert [(m["autor"], m["texto"], m["autor_es_personal"]) for m in conversacion["mensajes"]] == [
        ("Tito", "¿Qué programa?", True),
        ("Ana", "Power BI", False),
    ]

    assert client.get(f"/tickets/{tid}/conversacion", headers=h_beto).status_code == 403
    assert client.post(f"/tickets/{tid}/mensajes", json={"texto": "hola"}, headers=h_beto).status_code == 403
    assert client.post(f"/tickets/{tid}/mensajes", json={"texto": "   "}, headers=h_ana).status_code == 400
    assert client.post(f"/tickets/{tid}/mensajes", json={"texto": "x" * 2001}, headers=h_ana).status_code == 400


def test_no_se_escribe_en_un_ticket_cerrado(client, crear_cuenta, entrar):
    crear_cuenta("ana@ejemplo.com")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h_ana, h_tec = entrar("ana@ejemplo.com"), entrar("tec@ejemplo.com")
    tid = _ticket(client, h_ana)
    client.patch(f"/tickets/{tid}", json={"estado": "resuelto"}, headers=h_tec)
    assert client.post(f"/tickets/{tid}/mensajes", json={"texto": "gracias"}, headers=h_ana).status_code == 409


def test_aprobacion_del_jefe_bloquea_resolver_hasta_que_responda(client, crear_cuenta, entrar, correos):
    crear_cuenta("ana@ejemplo.com", nombre="Ana")
    jefe = crear_cuenta("jefe@ejemplo.com", nombre="Jefa Carla")
    crear_cuenta("tec@ejemplo.com", "tecnico", nombre="Tito")
    h_ana, h_jefe, h_tec = entrar("ana@ejemplo.com"), entrar("jefe@ejemplo.com"), entrar("tec@ejemplo.com")
    tid = _ticket(client, h_ana)

    r = client.post(
        f"/tickets/{tid}/aprobaciones",
        json={"aprobador_id": jefe.id, "descripcion": "Aprobar la licencia de Power BI para Ana"},
        headers=h_tec,
    )
    assert r.status_code == 200, r.text
    aprobacion = r.json()
    assert aprobacion["estado"] == "pendiente" and aprobacion["aprobador"] == "Jefa Carla"
    aviso = list(correos.glob("*jefe_ejemplo.com.txt"))
    assert aviso and f"ticket #{tid}" in aviso[0].read_text(encoding="utf-8")

    # la dueña del ticket ve el paso en su chat
    assert client.get(f"/tickets/{tid}/conversacion", headers=h_ana).json()["aprobaciones"][0]["estado"] == "pendiente"

    bloqueo = client.patch(f"/tickets/{tid}", json={"estado": "resuelto"}, headers=h_tec)
    assert bloqueo.status_code == 409 and "aprobación pendiente" in bloqueo.json()["detail"]

    # solo la jefa la ve y la responde
    pendientes = client.get("/aprobaciones", params={"estado": "pendiente"}, headers=h_jefe).json()
    assert len(pendientes) == 1 and pendientes[0]["ticket_solicitante"] == "Ana"
    assert pendientes[0]["ticket_texto"] == "Necesito instalar un programa nuevo"
    assert client.get("/aprobaciones", headers=h_ana).json() == []
    url = f"/aprobaciones/{aprobacion['id']}/responder"
    assert client.post(url, json={"aprobada": True}, headers=h_tec).status_code == 404
    assert client.post(url, json={"aprobada": False}, headers=h_jefe).status_code == 400  # rechazo sin motivo
    ok = client.post(url, json={"aprobada": True, "comentario": "Adelante"}, headers=h_jefe)
    assert ok.status_code == 200 and ok.json()["estado"] == "aprobada"
    assert client.post(url, json={"aprobada": False, "comentario": "no"}, headers=h_jefe).status_code == 409

    assert client.patch(f"/tickets/{tid}", json={"estado": "resuelto"}, headers=h_tec).status_code == 200


def test_reglas_para_pedir_una_aprobacion(client, crear_cuenta, entrar):
    ana = crear_cuenta("ana@ejemplo.com")
    baja = crear_cuenta("baja@ejemplo.com", activo=False)
    tec = crear_cuenta("tec@ejemplo.com", "tecnico")
    jefe = crear_cuenta("jefe@ejemplo.com")
    h_ana, h_tec = entrar("ana@ejemplo.com"), entrar("tec@ejemplo.com")
    tid = _ticket(client, h_ana)
    url = f"/tickets/{tid}/aprobaciones"

    def pedir(aprobador_id, h=h_tec, descripcion="Aprobar el acceso"):
        return client.post(url, json={"aprobador_id": aprobador_id, "descripcion": descripcion}, headers=h)

    assert pedir(jefe.id, h=h_ana).status_code == 403  # el usuario final no pide aprobaciones
    assert pedir(ana.id).status_code == 400  # ni la dueña del ticket
    assert pedir(tec.id).status_code == 400  # ni quien la pide
    assert pedir(baja.id).status_code == 400  # ni una cuenta desactivada
    assert pedir(9999).status_code == 400
    assert pedir(jefe.id, descripcion="ok").status_code == 400


def test_quien_participo_en_el_chat_no_se_puede_eliminar(client, crear_cuenta, entrar):
    crear_cuenta("adm@ejemplo.com", "administrador")
    jefe = crear_cuenta("jefe@ejemplo.com")
    crear_cuenta("ana@ejemplo.com")
    h_ana = entrar("ana@ejemplo.com")
    tid = _ticket(client, h_ana)
    client.post(
        f"/tickets/{tid}/aprobaciones",
        json={"aprobador_id": jefe.id, "descripcion": "Aprobar la compra"},
        headers=entrar("adm@ejemplo.com"),
    )
    assert client.delete(f"/admin/usuarios/{jefe.id}", headers=entrar("adm@ejemplo.com")).status_code == 409

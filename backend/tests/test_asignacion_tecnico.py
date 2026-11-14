"""Técnico sugerido según el sistema (categoría) del ticket, y su corrección a mano."""
from app.models import Ticket


def _crear(client, h, categoria, texto="La impresora del piso 3 no imprime nada"):
    r = client.post(
        "/tickets",
        json={"texto": texto, "tipo": "Incidencia o problema técnico", "categoria": categoria},
        headers=h,
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_se_asigna_el_tecnico_del_sistema(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    jimmy = crear_cuenta("jimmy@ejemplo.com", "tecnico", nombre="Jimmy López")
    crear_cuenta("carlos@ejemplo.com", "tecnico", nombre="Carlos Sanchez")
    h = entrar("usr@ejemplo.com")
    t = _crear(client, h, "Power BI")
    assert t["tecnico_id"] == jimmy.id and t["tecnico_manual"] is False
    assert t["estado"] == "abierto"  # sugerido, no tomado


def test_varios_tecnicos_se_elige_al_de_menos_pendientes(client, crear_cuenta, entrar, session):
    crear_cuenta("usr@ejemplo.com")
    geo = crear_cuenta("geo@ejemplo.com", "tecnico", nombre="Geovanny Remache")
    fati = crear_cuenta("fati@ejemplo.com", "tecnico", nombre="Fatima Reyes")
    h = entrar("usr@ejemplo.com")
    assert _crear(client, h, "Office")["tecnico_id"] == geo.id  # empate: el primero de la lista
    assert _crear(client, h, "Internet")["tecnico_id"] == fati.id
    assert _crear(client, h, "Interpro")["tecnico_id"] == geo.id


def test_sin_cuenta_del_tecnico_queda_sin_asignar_y_otros_va_a_cualquiera(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    luis = crear_cuenta("luis@ejemplo.com", "tecnico", nombre="Luis Paredes")
    h = entrar("usr@ejemplo.com")
    assert _crear(client, h, "Salesforce")["tecnico_id"] is None
    assert _crear(client, h, "Otros")["tecnico_id"] == luis.id


def test_cambiar_la_categoria_cambia_el_tecnico_salvo_si_se_eligio_a_mano(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    jimmy = crear_cuenta("jimmy@ejemplo.com", "tecnico", nombre="Jimmy Lopez")
    carlos = crear_cuenta("carlos@ejemplo.com", "tecnico", nombre="Carlos Sánchez")
    crear_cuenta("adm@ejemplo.com", "administrador")
    t = _crear(client, entrar("usr@ejemplo.com"), "Power BI")
    ha = entrar("adm@ejemplo.com")

    r = client.patch(f"/tickets/{t['id']}", json={"categoria": "Salesforce"}, headers=ha).json()
    assert r["tecnico_id"] == carlos.id

    r = client.patch(f"/tickets/{t['id']}", json={"tecnico_id": jimmy.id}, headers=ha).json()
    assert r["tecnico_id"] == jimmy.id and r["tecnico_manual"] is True
    r = client.patch(f"/tickets/{t['id']}", json={"categoria": "Webdox"}, headers=ha).json()
    assert r["tecnico_id"] == jimmy.id  # elegido a mano: no se pisa

    r = client.patch(f"/tickets/{t['id']}", json={"tecnico_auto": True}, headers=ha).json()
    assert r["tecnico_id"] == carlos.id and r["tecnico_manual"] is False


def test_tomar_el_ticket_lo_asigna_a_quien_lo_toma(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    crear_cuenta("jimmy@ejemplo.com", "tecnico", nombre="Jimmy Lopez")
    otro = crear_cuenta("otro@ejemplo.com", "tecnico", nombre="Daniela Cevallos")
    t = _crear(client, entrar("usr@ejemplo.com"), "Power BI")
    r = client.patch(f"/tickets/{t['id']}", json={"estado": "en_proceso"}, headers=entrar("otro@ejemplo.com")).json()
    assert r["tecnico_id"] == otro.id and r["tecnico_manual"] is True


def test_no_se_asigna_a_un_usuario_final(client, crear_cuenta, entrar):
    usr = crear_cuenta("usr@ejemplo.com")
    crear_cuenta("adm@ejemplo.com", "administrador")
    t = _crear(client, entrar("usr@ejemplo.com"), "Otros")
    r = client.patch(f"/tickets/{t['id']}", json={"tecnico_id": usr.id}, headers=entrar("adm@ejemplo.com"))
    assert r.status_code == 400


def test_el_detalle_dice_quien_es_el_sugerido(client, crear_cuenta, entrar, session):
    usr = crear_cuenta("usr@ejemplo.com")
    jimmy = crear_cuenta("jimmy@ejemplo.com", "tecnico", nombre="Jimmy Lopez")
    crear_cuenta("adm@ejemplo.com", "administrador")
    # Un ticket anterior a la asignación automática: sin técnico.
    viejo = Ticket(cliente_id=usr.id, texto="No abre Power BI", categoria="Power BI")
    session.add(viejo)
    session.commit()
    ha = entrar("adm@ejemplo.com")
    d = client.get(f"/tickets/{viejo.id}", headers=ha).json()
    assert d["tecnico_id"] is None and d["tecnico_sugerido_id"] == jimmy.id
    r = client.patch(f"/tickets/{viejo.id}", json={"tecnico_auto": True}, headers=ha).json()
    assert r["tecnico_id"] == jimmy.id
    # El usuario final no ve la sugerencia interna.
    assert client.get(f"/tickets/{viejo.id}", headers=entrar("usr@ejemplo.com")).json()["tecnico_sugerido_id"] is None

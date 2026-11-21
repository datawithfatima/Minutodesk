"""Técnico sugerido según el sistema (categoría) del ticket, y su corrección a mano."""
from app.models import Ticket

# La tabla de técnicos de prueba (nombres ficticios) la fija conftest.py.


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
    ana = crear_cuenta("ana@ejemplo.com", "tecnico", nombre="Ana Móra")
    crear_cuenta("pedro@ejemplo.com", "tecnico", nombre="Pedro Vera")
    h = entrar("usr@ejemplo.com")
    t = _crear(client, h, "Power BI")
    assert t["tecnico_id"] == ana.id and t["tecnico_manual"] is False
    assert t["estado"] == "abierto"  # sugerido, no tomado


def test_varios_tecnicos_se_elige_al_de_menos_pendientes(client, crear_cuenta, entrar, session):
    crear_cuenta("usr@ejemplo.com")
    gabi = crear_cuenta("gabi@ejemplo.com", "tecnico", nombre="Gabriel Ruiz")
    sofi = crear_cuenta("sofi@ejemplo.com", "tecnico", nombre="Sofia Luna")
    h = entrar("usr@ejemplo.com")
    assert _crear(client, h, "Office")["tecnico_id"] == gabi.id  # empate: el primero de la lista
    assert _crear(client, h, "Internet")["tecnico_id"] == sofi.id
    assert _crear(client, h, "Interpro")["tecnico_id"] == gabi.id


def test_sin_cuenta_del_tecnico_queda_sin_asignar_y_otros_va_a_cualquiera(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    luis = crear_cuenta("luis@ejemplo.com", "tecnico", nombre="Luis Paredes")
    h = entrar("usr@ejemplo.com")
    assert _crear(client, h, "Salesforce")["tecnico_id"] is None
    assert _crear(client, h, "Otros")["tecnico_id"] == luis.id


def test_cambiar_la_categoria_cambia_el_tecnico_salvo_si_se_eligio_a_mano(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    ana = crear_cuenta("ana@ejemplo.com", "tecnico", nombre="Ana Mora")
    pedro = crear_cuenta("pedro@ejemplo.com", "tecnico", nombre="Pedro Véra")
    crear_cuenta("adm@ejemplo.com", "administrador")
    t = _crear(client, entrar("usr@ejemplo.com"), "Power BI")
    ha = entrar("adm@ejemplo.com")

    r = client.patch(f"/tickets/{t['id']}", json={"categoria": "Salesforce"}, headers=ha).json()
    assert r["tecnico_id"] == pedro.id

    r = client.patch(f"/tickets/{t['id']}", json={"tecnico_id": ana.id}, headers=ha).json()
    assert r["tecnico_id"] == ana.id and r["tecnico_manual"] is True
    r = client.patch(f"/tickets/{t['id']}", json={"categoria": "Webdox"}, headers=ha).json()
    assert r["tecnico_id"] == ana.id  # elegido a mano: no se pisa

    r = client.patch(f"/tickets/{t['id']}", json={"tecnico_auto": True}, headers=ha).json()
    assert r["tecnico_id"] == pedro.id and r["tecnico_manual"] is False


def test_tomar_el_ticket_lo_asigna_a_quien_lo_toma(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    crear_cuenta("ana@ejemplo.com", "tecnico", nombre="Ana Mora")
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
    ana = crear_cuenta("ana@ejemplo.com", "tecnico", nombre="Ana Mora")
    crear_cuenta("adm@ejemplo.com", "administrador")
    # Un ticket anterior a la asignación automática: sin técnico.
    viejo = Ticket(cliente_id=usr.id, texto="No abre Power BI", categoria="Power BI")
    session.add(viejo)
    session.commit()
    ha = entrar("adm@ejemplo.com")
    d = client.get(f"/tickets/{viejo.id}", headers=ha).json()
    assert d["tecnico_id"] is None and d["tecnico_sugerido_id"] == ana.id
    r = client.patch(f"/tickets/{viejo.id}", json={"tecnico_auto": True}, headers=ha).json()
    assert r["tecnico_id"] == ana.id
    # El usuario final no ve la sugerencia interna.
    assert client.get(f"/tickets/{viejo.id}", headers=entrar("usr@ejemplo.com")).json()["tecnico_sugerido_id"] is None

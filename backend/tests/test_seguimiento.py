"""Plazos de seguimiento basados en el SLA: sin avance, usuario que no contesta,
recordatorios de aprobaciones y aviso de ticket parecido antes de crearlo."""
from datetime import datetime, timedelta

from sqlmodel import select

from app.models import AvisoAutomatico, Ticket
from app.services import seguimiento
from app.services.catalogos import TIPO_INCIDENCIA

from .test_notificaciones import _correos, _limpiar


def _crear(client, h, prioridad="Normal", texto="No me abre el reporte de ventas en Power BI"):
    r = client.post(
        "/tickets",
        json={"texto": texto, "tipo": TIPO_INCIDENCIA, "categoria": "Power BI", "prioridad": prioridad},
        headers=h,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _escenario(client, crear_cuenta, entrar, prioridad="Normal"):
    crear_cuenta("usr@ejemplo.com", nombre="Usuaria Uno")
    crear_cuenta("tec@ejemplo.com", "tecnico", nombre="Técnico Uno")
    crear_cuenta("adm@ejemplo.com", "administrador", nombre="Admin Uno")
    hu, ht = entrar("usr@ejemplo.com"), entrar("tec@ejemplo.com")
    tid = _crear(client, hu, prioridad)
    assert client.post(f"/tickets/{tid}/tomar", headers=ht).status_code == 200
    return tid, hu, ht


def _dias(d):
    return datetime.now() + timedelta(days=d)


# ---------- plazos ----------

def test_los_plazos_salen_del_sla_con_sus_topes():
    def t(prioridad):
        return Ticket(cliente_id=1, texto="x", tipo=TIPO_INCIDENCIA, prioridad=prioridad)

    dia = 86400
    assert seguimiento.umbral_sin_avance(t("Crítica")) == 0.25 * dia  # 6 h
    assert seguimiento.umbral_sin_avance(t("Normal")) == 1.75 * dia
    assert seguimiento.umbral_sin_avance(t("Baja")) == 2 * dia  # tope
    assert seguimiento.espera_usuario(t("Crítica")) == 2 * dia  # mínimo
    assert seguimiento.espera_usuario(t("Alta")) == 3 * dia
    assert seguimiento.espera_usuario(t("Normal")) == 5 * dia  # tope


# ---------- 1. sin avance ----------

def test_ticket_tomado_sin_avance_avisa_al_administrador_una_vez(client, crear_cuenta, entrar, session, correos):
    tid, _, ht = _escenario(client, crear_cuenta, entrar)
    _limpiar(correos)
    assert seguimiento.revisar(session, _dias(1)) == 0
    assert seguimiento.revisar(session, _dias(1.8)) == 1
    assert _correos(correos) == [("adm@ejemplo.com", f"Ticket #{tid}: sin avance")]
    assert seguimiento.revisar(session, _dias(3)) == 0  # ya avisado

    ha = entrar("adm@ejemplo.com")
    avisos = client.get("/avisos", headers=ha).json()
    assert [a["tipo"] for a in avisos] == ["sin_avance"] and "Técnico Uno" in avisos[0]["texto"]

    # En cuanto el técnico se mueve, el aviso se va y el contador vuelve a empezar.
    client.post(f"/tickets/{tid}/mensajes", json={"texto": "Ya lo estoy revisando"}, headers=ht)
    assert client.get("/avisos", headers=ha).json() == []
    assert seguimiento.revisar(session, _dias(1)) == 0


def test_sin_avance_no_corre_mientras_espera_una_aprobacion(client, crear_cuenta, entrar, session, correos):
    tid, _, ht = _escenario(client, crear_cuenta, entrar)
    jefe = crear_cuenta("jefe@ejemplo.com", nombre="Jefa de Área")
    client.post(f"/tickets/{tid}/aprobaciones", json={"aprobador_id": jefe.id, "descripcion": "Licencia Pro"}, headers=ht)
    _limpiar(correos)
    seguimiento.revisar(session, _dias(1.8))
    assert ("adm@ejemplo.com", f"Ticket #{tid}: sin avance") not in _correos(correos)


def test_sin_avance_no_corre_en_pausa_con_motivo(client, crear_cuenta, entrar, session, correos):
    tid, _, ht = _escenario(client, crear_cuenta, entrar)
    r = client.post(f"/tickets/{tid}/sla/pausar", json={"motivo": "proveedor", "detalle": "Esperando a Microsoft"}, headers=ht)
    assert r.status_code == 200, r.text
    _limpiar(correos)
    assert seguimiento.revisar(session, _dias(4)) == 0
    assert _correos(correos) == []


def test_los_tickets_anteriores_no_se_tocan(client, crear_cuenta, entrar, session, monkeypatch):
    tid, _, _ = _escenario(client, crear_cuenta, entrar)
    monkeypatch.setattr(seguimiento, "ACTIVO_DESDE", datetime.now() + timedelta(hours=1))
    assert seguimiento.revisar(session, _dias(10)) == 0
    assert session.get(Ticket, tid).estado == "en_proceso"


# ---------- 2. usuario que no contesta ----------

def _pausar_por_usuario(client, tid, ht):
    r = client.post(
        f"/tickets/{tid}/sla/pausar", json={"motivo": "usuario", "detalle": "Envíame una captura del error"}, headers=ht
    )
    assert r.status_code == 200, r.text


def test_usuario_que_no_contesta_recordatorio_y_cierre(client, crear_cuenta, entrar, session, correos):
    tid, hu, ht = _escenario(client, crear_cuenta, entrar)  # Normal: espera de 5 días
    _pausar_por_usuario(client, tid, ht)
    assert [a["tipo"] for a in client.get("/avisos", headers=hu).json()] == ["esperando_respuesta"]
    _limpiar(correos)
    assert seguimiento.revisar(session, _dias(2)) == 0
    assert seguimiento.revisar(session, _dias(2.6)) == 1
    assert _correos(correos) == [("usr@ejemplo.com", f"Ticket #{tid}: esperamos tu respuesta")]
    assert seguimiento.revisar(session, _dias(4)) == 0
    _limpiar(correos)
    assert seguimiento.revisar(session, _dias(5.1)) == 1

    session.expire_all()
    ticket = session.get(Ticket, tid)
    assert ticket.estado == "cancelado" and ticket.motivo_cancelacion.startswith("Sin respuesta del usuario")
    assert sorted(_correos(correos)) == [
        ("tec@ejemplo.com", f"Ticket #{tid}: cerrado por falta de respuesta"),
        ("usr@ejemplo.com", f"Ticket #{tid}: se cerró por falta de respuesta"),
    ]
    s = client.get(f"/tickets/{tid}/sla", headers=ht).json()
    assert s["pausa_actual"] is None


def test_el_cierre_siempre_deja_margen_tras_el_recordatorio(client, crear_cuenta, entrar, session):
    tid, _, ht = _escenario(client, crear_cuenta, entrar)
    _pausar_por_usuario(client, tid, ht)
    # El revisor no corrió a tiempo (servidor apagado): primero recuerda, no cierra.
    assert seguimiento.revisar(session, _dias(6)) == 1
    assert seguimiento.revisar(session, _dias(7)) == 0
    assert session.get(Ticket, tid).estado == "en_proceso"
    assert seguimiento.revisar(session, _dias(8.6)) == 1
    session.expire_all()
    assert session.get(Ticket, tid).estado == "cancelado"


def test_si_el_usuario_escribe_la_espera_termina(client, crear_cuenta, entrar, session):
    tid, hu, ht = _escenario(client, crear_cuenta, entrar)
    _pausar_por_usuario(client, tid, ht)
    client.post(f"/tickets/{tid}/mensajes", json={"texto": "Adjunto la captura"}, headers=hu)
    s = client.get(f"/tickets/{tid}/sla", headers=ht).json()
    assert s["pausa_actual"] is None and s["pausas"][0]["reanudada_por"] == "Usuaria Uno"
    assert "esperando_respuesta" not in [a["tipo"] for a in client.get("/avisos", headers=hu).json()]
    seguimiento.revisar(session, _dias(6))
    session.expire_all()
    assert session.get(Ticket, tid).estado == "en_proceso"


def test_no_se_cierra_mientras_hay_una_aprobacion_pendiente(client, crear_cuenta, entrar, session):
    tid, _, ht = _escenario(client, crear_cuenta, entrar)
    _pausar_por_usuario(client, tid, ht)
    jefe = crear_cuenta("jefe@ejemplo.com", nombre="Jefa de Área")
    client.post(f"/tickets/{tid}/aprobaciones", json={"aprobador_id": jefe.id, "descripcion": "Licencia Pro"}, headers=ht)
    for d in (3, 6, 9, 12):
        seguimiento.revisar(session, _dias(d))
    session.expire_all()
    assert session.get(Ticket, tid).estado == "en_proceso"
    tipos = {a.tipo for a in session.exec(select(AvisoAutomatico)).all()}
    assert tipos == {"recordatorio_aprobacion"}


# ---------- 3. recordatorios de aprobaciones ----------

def test_recordatorios_de_aprobacion_al_aprobador_y_al_final_a_quien_la_pidio(
    client, crear_cuenta, entrar, session, correos
):
    tid, _, ht = _escenario(client, crear_cuenta, entrar)  # Normal: cada 1,75 días
    jefe = crear_cuenta("jefe@ejemplo.com", nombre="Jefa de Área")
    client.post(f"/tickets/{tid}/aprobaciones", json={"aprobador_id": jefe.id, "descripcion": "Licencia Pro"}, headers=ht)
    _limpiar(correos)
    recordatorio = ("jefe@ejemplo.com", f"Recordatorio: aprobación pendiente del ticket #{tid}")
    assert seguimiento.revisar(session, _dias(1)) == 0
    assert seguimiento.revisar(session, _dias(1.8)) == 1
    assert seguimiento.revisar(session, _dias(2)) == 0
    assert seguimiento.revisar(session, _dias(3.6)) == 1
    assert _correos(correos) == [recordatorio, recordatorio]
    _limpiar(correos)
    assert seguimiento.revisar(session, _dias(5.3)) == 1
    assert sorted(_correos(correos)) == sorted(
        [recordatorio, ("tec@ejemplo.com", f"Ticket #{tid}: aprobación sin respuesta")]
    )
    assert seguimiento.revisar(session, _dias(20)) == 0  # máximo 3


# ---------- 4. ticket parecido antes de crear ----------

def test_avisa_si_la_persona_ya_tiene_un_ticket_parecido_abierto(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    crear_cuenta("otra@ejemplo.com")
    hu = entrar("usr@ejemplo.com")
    tid = _crear(client, hu, texto="No me abre el reporte de ventas en Power BI desde esta mañana")
    r = client.post("/tickets/parecidos-mios", json={"texto": "El reporte de ventas de Power BI no me abre"}, headers=hu)
    assert r.status_code == 200 and [p["id"] for p in r.json()] == [tid]
    # Otro problema, u otra persona con el mismo problema: no se le avisa.
    otro = client.post("/tickets/parecidos-mios", json={"texto": "Necesito acceso a la impresora del piso tres"}, headers=hu)
    assert otro.json() == []
    ajena = client.post(
        "/tickets/parecidos-mios",
        json={"texto": "El reporte de ventas de Power BI no me abre"},
        headers=entrar("otra@ejemplo.com"),
    )
    assert ajena.json() == []


# ---------- 3 y 5. «¿Quedó resuelto?» ----------

def _resolver(client, tid, ht):
    r = client.patch(f"/tickets/{tid}", json={"estado": "resuelto"}, headers=ht)
    assert r.status_code == 200, r.text


def test_confirmar_que_quedo_resuelto(client, crear_cuenta, entrar, correos):
    tid, hu, ht = _escenario(client, crear_cuenta, entrar)
    _limpiar(correos)
    _resolver(client, tid, ht)
    assert _correos(correos) == [("usr@ejemplo.com", f"Ticket #{tid}: ¿quedó resuelto?")]
    c = client.get(f"/tickets/{tid}/confirmacion-cierre", headers=hu).json()
    assert c["respuesta"] == "pendiente" and c["puede_responder"] is True
    assert client.get(f"/tickets/{tid}/confirmacion-cierre", headers=ht).json()["puede_responder"] is False
    assert [a["tipo"] for a in client.get("/avisos", headers=hu).json()] == ["confirmar_cierre"]
    # Solo quien abrió el ticket responde.
    r = client.post(f"/tickets/{tid}/confirmacion-cierre", json={"quedo_resuelto": True}, headers=ht)
    assert r.status_code == 403
    r = client.post(f"/tickets/{tid}/confirmacion-cierre", json={"quedo_resuelto": True}, headers=hu)
    assert r.status_code == 200 and r.json()["respuesta"] == "confirmado"
    assert client.get("/avisos", headers=hu).json() == []
    assert client.post(f"/tickets/{tid}/confirmacion-cierre", json={"quedo_resuelto": True}, headers=hu).status_code == 409


def test_si_no_quedo_resuelto_vuelve_al_mismo_tecnico(client, crear_cuenta, entrar, session, correos):
    tid, hu, ht = _escenario(client, crear_cuenta, entrar)
    _resolver(client, tid, ht)
    sin_motivo = client.post(f"/tickets/{tid}/confirmacion-cierre", json={"quedo_resuelto": False}, headers=hu)
    assert sin_motivo.status_code == 400
    _limpiar(correos)
    r = client.post(
        f"/tickets/{tid}/confirmacion-cierre",
        json={"quedo_resuelto": False, "comentario": "Sigue sin abrir el reporte"},
        headers=hu,
    )
    assert r.status_code == 200 and r.json()["respuesta"] == "rechazado"
    t = client.get(f"/tickets/{tid}", headers=ht).json()
    tecnico = session.exec(select(Ticket)).first().tecnico_id
    assert t["estado"] == "en_proceso" and t["tecnico_id"] == tecnico and t["resuelto_por"] is None
    assert _correos(correos) == [("tec@ejemplo.com", f"Ticket #{tid}: no quedó resuelto")]
    chat = client.get(f"/tickets/{tid}/conversacion", headers=ht).json()["mensajes"]
    assert chat[-1]["texto"] == "No quedó resuelto: Sigue sin abrir el reporte"
    # Al resolverlo otra vez se vuelve a preguntar.
    _resolver(client, tid, ht)
    assert client.get(f"/tickets/{tid}/confirmacion-cierre", headers=hu).json()["respuesta"] == "pendiente"


def test_sin_respuesta_se_confirma_solo_al_pasar_la_ventana(client, crear_cuenta, entrar, session):
    tid, hu, ht = _escenario(client, crear_cuenta, entrar)  # Normal: 3,5 días
    _resolver(client, tid, ht)
    seguimiento.revisar(session, _dias(3))
    assert client.get(f"/tickets/{tid}/confirmacion-cierre", headers=hu).json()["respuesta"] == "pendiente"
    seguimiento.revisar(session, _dias(3.6))
    c = client.get(f"/tickets/{tid}/confirmacion-cierre", headers=hu).json()
    assert c["respuesta"] == "automatico" and c["puede_responder"] is False
    assert client.get(f"/tickets/{tid}", headers=ht).json()["estado"] == "resuelto"


def test_si_el_personal_lo_reabre_la_confirmacion_se_anula(client, crear_cuenta, entrar):
    tid, hu, ht = _escenario(client, crear_cuenta, entrar)
    _resolver(client, tid, ht)
    client.patch(f"/tickets/{tid}", json={"estado": "en_proceso"}, headers=ht)
    assert client.get(f"/tickets/{tid}/confirmacion-cierre", headers=hu).json()["respuesta"] == "anulado"


# ---------- ticket principal y afectados ----------

def test_principal_con_afectados_se_resuelven_juntos(client, crear_cuenta, entrar, session, correos):
    crear_cuenta("tec@ejemplo.com", "tecnico", nombre="Técnico Uno")
    ht = entrar("tec@ejemplo.com")
    ids = []
    for n in range(3):
        crear_cuenta(f"u{n}@ejemplo.com", nombre=f"Usuario {n}")
        ids.append(_crear(client, entrar(f"u{n}@ejemplo.com"), texto="No hay internet en el piso dos desde la mañana"))
    principal, otros = ids[0], ids[1:]
    client.post(f"/tickets/{principal}/tomar", headers=ht)

    sugeridos = client.get(f"/tickets/{principal}/incidente-sugerido", headers=ht).json()
    assert sorted(s["id"] for s in sugeridos) == otros

    _limpiar(correos)
    r = client.post(f"/tickets/{principal}/afectados", json={"ids": otros}, headers=ht)
    assert r.status_code == 200, r.text
    assert sorted(_correos(correos)) == [
        ("u1@ejemplo.com", f"Ticket #{otros[0]}: se atiende junto con otros"),
        ("u2@ejemplo.com", f"Ticket #{otros[1]}: se atiende junto con otros"),
    ]
    s = client.get(f"/tickets/{otros[0]}/sla", headers=ht).json()
    assert s["estado"] == "pausado" and s["pausa_actual"]["motivo_titulo"] == "Se atiende en el ticket principal"
    assert client.get(f"/tickets/{principal}/incidente-sugerido", headers=ht).json() == []
    assert seguimiento.revisar(session, _dias(4)) == 1  # solo el principal puede quedar «sin avance»

    _limpiar(correos)
    _resolver(client, principal, ht)
    for i in otros:
        t = client.get(f"/tickets/{i}", headers=ht).json()
        assert t["estado"] == "resuelto" and t["resuelto_por"] == "tecnico"
    hu1 = entrar("u1@ejemplo.com")
    assert client.get(f"/tickets/{otros[0]}/confirmacion-cierre", headers=hu1).json()["respuesta"] == "pendiente"
    assert ("u2@ejemplo.com", f"Ticket #{otros[1]}: ¿quedó resuelto?") in _correos(correos)


def test_no_se_sugiere_con_menos_de_tres_personas(client, crear_cuenta, entrar):
    crear_cuenta("tec@ejemplo.com", "tecnico")
    crear_cuenta("a@ejemplo.com")
    crear_cuenta("b@ejemplo.com")
    ha, hb = entrar("a@ejemplo.com"), entrar("b@ejemplo.com")
    texto = "No hay internet en el piso dos desde la mañana"
    t1 = _crear(client, ha, texto=texto)
    _crear(client, ha, texto=texto)  # la misma persona dos veces no suma
    _crear(client, hb, texto=texto)
    assert client.get(f"/tickets/{t1}/incidente-sugerido", headers=entrar("tec@ejemplo.com")).json() == []


def test_separar_un_afectado_reanuda_su_plazo(client, crear_cuenta, entrar):
    crear_cuenta("tec@ejemplo.com", "tecnico")
    crear_cuenta("a@ejemplo.com")
    crear_cuenta("b@ejemplo.com")
    ht = entrar("tec@ejemplo.com")
    p = _crear(client, entrar("a@ejemplo.com"))
    o = _crear(client, entrar("b@ejemplo.com"))
    client.post(f"/tickets/{p}/afectados", json={"ids": [o]}, headers=ht)
    assert client.delete(f"/tickets/{o}/afectado", headers=ht).status_code == 200
    s = client.get(f"/tickets/{o}/sla", headers=ht).json()
    assert s["pausa_actual"] is None
    assert client.get(f"/tickets/{p}/afectados", headers=ht).json() == []

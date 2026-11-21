"""Plazo de atención (SLA): cálculo, pausas con motivo, aprobaciones y avisos."""
from datetime import datetime, timedelta

from sqlmodel import select

from app.models import PausaSla, Ticket
from app.services import avisos_sla, sla
from app.services.catalogos import TIPO_INCIDENCIA, TIPO_SOLICITUD

from .test_notificaciones import _correos, _limpiar

DIA = 86400


def _crear(client, h, tipo=TIPO_INCIDENCIA, prioridad="Normal", categoria="Power BI"):
    r = client.post(
        "/tickets",
        json={"texto": "No me abre el reporte de ventas", "tipo": tipo, "categoria": categoria, "prioridad": prioridad},
        headers=h,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _retroceder(session, ticket_id, dias):
    """Simula que el ticket se creó hace `dias` días (también su historial)."""
    t = session.get(Ticket, ticket_id)
    t.creado_en = t.creado_en - timedelta(days=dias)
    session.add(t)
    session.commit()


def test_el_plazo_sale_de_la_tabla_por_tipo_y_prioridad():
    assert sla.DIAS_SLA[TIPO_INCIDENCIA] == {"Baja": 15, "Normal": 7, "Alta": 3, "Crítica": 1}
    assert sla.DIAS_SLA[TIPO_SOLICITUD]["Baja"] == 30
    assert sla.segundos_habiles(datetime(2026, 11, 13, 12), datetime(2026, 11, 16, 12)) == 3 * DIA  # calendario


def test_ticket_nuevo_trae_su_temporizador(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    t = _crear(client, entrar("usr@ejemplo.com"), prioridad="Alta")
    s = t["sla"]
    assert s["dias"] == 3 and s["plazo_segundos"] == 3 * DIA
    assert s["estado"] == "en_tiempo" and s["porcentaje"] == 0 and s["vence_en"] is not None
    assert DIA * 3 - 60 < s["restante_segundos"] <= DIA * 3


def test_cambiar_prioridad_recalcula_el_plazo_y_conserva_lo_consumido(client, crear_cuenta, entrar, session):
    crear_cuenta("usr@ejemplo.com")
    crear_cuenta("adm@ejemplo.com", "administrador")
    t = _crear(client, entrar("usr@ejemplo.com"), prioridad="Normal")  # 7 días
    _retroceder(session, t["id"], 2)
    ha = entrar("adm@ejemplo.com")
    s = client.get(f"/tickets/{t['id']}", headers=ha).json()["sla"]
    assert s["porcentaje"] == 29 and s["estado"] == "en_tiempo"
    s = client.patch(f"/tickets/{t['id']}", json={"prioridad": "Crítica"}, headers=ha).json()["sla"]
    assert s["dias"] == 1 and s["vencido"] is True and s["estado"] == "vencido"
    assert s["restante_segundos"] <= -DIA


def test_pausa_manual_detiene_el_reloj_y_exige_motivo(client, crear_cuenta, entrar, session, correos):
    crear_cuenta("usr@ejemplo.com")
    crear_cuenta("tec@ejemplo.com", "tecnico", nombre="Luis Paredes")
    t = _crear(client, entrar("usr@ejemplo.com"), prioridad="Alta")
    ht = entrar("tec@ejemplo.com")
    _limpiar(correos)

    r = client.post(f"/tickets/{t['id']}/sla/pausar", json={"motivo": "desarrollo", "detalle": ""}, headers=ht)
    assert r.status_code == 400
    r = client.post(f"/tickets/{t['id']}/sla/pausar", json={"motivo": "vacaciones", "detalle": "lo que sea"}, headers=ht)
    assert r.status_code == 400
    r = client.post(
        f"/tickets/{t['id']}/sla/pausar",
        json={"motivo": "desarrollo", "detalle": "Falló el servidor de reportes, esperamos al proveedor"},
        headers=ht,
    )
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["estado"] == "pausado" and s["pausa_actual"]["motivo_titulo"] == "Desarrollo o imprevisto"
    assert s["pausa_actual"]["iniciada_por"] == "Luis Paredes" and s["pausa_actual"]["automatica"] is False
    assert _correos(correos) == [("usr@ejemplo.com", f"Ticket #{t['id']}: en pausa")]
    assert client.post(f"/tickets/{t['id']}/sla/pausar", json={"motivo": "otro", "detalle": "de nuevo"}, headers=ht).status_code == 409

    # Dos días de pausa: no cuentan.
    pausa = session.exec(select(PausaSla)).one()
    pausa.inicio -= timedelta(days=2)
    session.add(pausa)
    _retroceder(session, t["id"], 2)
    s = client.get(f"/tickets/{t['id']}", headers=ht).json()["sla"]
    assert s["porcentaje"] == 0 and s["estado"] == "pausado"

    _limpiar(correos)
    s = client.post(f"/tickets/{t['id']}/sla/reanudar", headers=ht).json()
    assert s["estado"] == "en_tiempo" and s["pausa_actual"] is None
    assert s["pausas"][0]["reanudada_por"] == "Luis Paredes" and s["pausas"][0]["fin"] is not None
    assert _correos(correos) == [("usr@ejemplo.com", f"Ticket #{t['id']}: se reanudó la atención")]


def test_el_usuario_final_ve_el_plazo_pero_no_lo_pausa(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    hu = entrar("usr@ejemplo.com")
    t = _crear(client, hu)
    assert client.get(f"/tickets/{t['id']}/sla", headers=hu).json()["dias"] == 7
    r = client.post(f"/tickets/{t['id']}/sla/pausar", json={"motivo": "otro", "detalle": "quiero pausar"}, headers=hu)
    assert r.status_code == 403


def test_una_aprobacion_pausa_sola_y_se_reanuda_al_responder(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    jefe = crear_cuenta("jefe@ejemplo.com", nombre="Jefa de Área")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    t = _crear(client, entrar("usr@ejemplo.com"))
    ht = entrar("tec@ejemplo.com")
    r = client.post(
        f"/tickets/{t['id']}/aprobaciones",
        json={"aprobador_id": jefe.id, "descripcion": "Comprar licencia de Power BI Pro"},
        headers=ht,
    )
    assert r.status_code == 200, r.text
    s = client.get(f"/tickets/{t['id']}/sla", headers=ht).json()
    assert s["estado"] == "pausado" and s["pausa_actual"]["automatica"] is True
    assert s["pausa_actual"]["motivo"] == "aprobacion" and "Power BI Pro" in s["pausa_actual"]["detalle"]
    # A mano no se reanuda mientras la aprobación siga pendiente.
    assert client.post(f"/tickets/{t['id']}/sla/reanudar", headers=ht).status_code == 409

    client.post(f"/aprobaciones/{r.json()['id']}/responder", json={"aprobada": True}, headers=entrar("jefe@ejemplo.com"))
    s = client.get(f"/tickets/{t['id']}/sla", headers=ht).json()
    assert s["estado"] == "en_tiempo" and s["pausas"][0]["fin"] is not None


def test_resolver_cierra_la_pausa_y_el_tiempo_cerrado_no_cuenta_al_reabrir(client, crear_cuenta, entrar, session):
    crear_cuenta("usr@ejemplo.com")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    t = _crear(client, entrar("usr@ejemplo.com"), prioridad="Alta")  # 3 días
    ht = entrar("tec@ejemplo.com")
    client.post(f"/tickets/{t['id']}/sla/pausar", json={"motivo": "usuario", "detalle": "No responde el usuario"}, headers=ht)
    s = client.patch(f"/tickets/{t['id']}", json={"estado": "resuelto"}, headers=ht).json()["sla"]
    assert s["estado"] == "cumplido" and s["pausa_actual"] is None

    # Pasan 10 días resuelto; al reabrir, el reloj sigue donde estaba.
    for h in session.exec(select(__import__("app.models", fromlist=["HistorialEstadoTicket"]).HistorialEstadoTicket)):
        h.fecha -= timedelta(days=10)
        session.add(h)
    for p in session.exec(select(PausaSla)):
        p.inicio -= timedelta(days=10)
        p.fin -= timedelta(days=10)
        session.add(p)
    _retroceder(session, t["id"], 10)
    s = client.patch(f"/tickets/{t['id']}", json={"estado": "abierto"}, headers=ht).json()["sla"]
    assert s["estado"] == "en_tiempo" and s["porcentaje"] == 0


def test_avisos_al_80_por_ciento_y_al_vencer_una_sola_vez(client, crear_cuenta, entrar, session, correos):
    crear_cuenta("usr@ejemplo.com")
    tec = crear_cuenta("ana@ejemplo.com", "tecnico", nombre="Ana Mora")
    t = _crear(client, entrar("usr@ejemplo.com"), prioridad="Alta")  # 3 días → Ana (Power BI)
    assert t["tecnico_id"] == tec.id
    _limpiar(correos)

    ahora = datetime.now()
    assert avisos_sla.revisar(session, ahora + timedelta(days=1)) == 0
    assert avisos_sla.revisar(session, ahora + timedelta(days=2, hours=12)) == 1  # 83 %
    assert avisos_sla.revisar(session, ahora + timedelta(days=2, hours=13)) == 0  # ya avisado
    assert avisos_sla.revisar(session, ahora + timedelta(days=3, hours=1)) == 1  # vencido
    assert avisos_sla.revisar(session, ahora + timedelta(days=4)) == 0
    assert _correos(correos) == [
        ("ana@ejemplo.com", f"Ticket #{t['id']}: plazo por vencer"),
        ("ana@ejemplo.com", f"Ticket #{t['id']}: plazo vencido"),
    ]


def test_el_resumen_trae_cumplimiento_del_sla(client, crear_cuenta, entrar, session):
    crear_cuenta("usr@ejemplo.com")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    hu, ht = entrar("usr@ejemplo.com"), entrar("tec@ejemplo.com")
    a = _crear(client, hu, prioridad="Crítica")  # 1 día
    b = _crear(client, hu, prioridad="Baja")
    _retroceder(session, a["id"], 3)
    client.patch(f"/tickets/{a['id']}", json={"estado": "resuelto"}, headers=ht)  # fuera de plazo
    client.patch(f"/tickets/{b['id']}", json={"estado": "resuelto"}, headers=ht)  # a tiempo
    _crear(client, hu)
    r = client.get("/reportes/resumen", headers=ht).json()["sla"]
    assert r["resueltos_con_plazo"] == 2 and r["cumplidos"] == 1 and r["pct_cumplimiento"] == 50.0
    assert r["abiertos_en_tiempo"] == 1
    assert next(g for g in r["por_prioridad"] if g["etiqueta"] == "Crítica")["pct"] == 0.0


def test_los_feriados_de_ecuador_no_cuentan_pero_los_fines_de_semana_si():
    from datetime import datetime

    from app.services import sla

    # Carnaval 2026: lunes 16 y martes 17 de febrero. El domingo 15 sí cuenta.
    assert sla.segundos_habiles(datetime(2026, 2, 15), datetime(2026, 2, 18)) == sla.SEGUNDOS_DIA
    # Un plazo de 1 día que empieza el viernes santo (3/4/2026) vence el domingo.
    assert sla.sumar_segundos_habiles(datetime(2026, 4, 3, 9), sla.SEGUNDOS_DIA) == datetime(2026, 4, 5)
    assert sla._pascua(2027).isoformat() == "2027-03-28"

"""Simulación del tiempo de resolución (objetivo 3)."""
from datetime import datetime

from app.models import EvaluacionMinutito, Ticket, TicketHistorico
from app.services.catalogos import TIPO_INCIDENCIA, TIPO_SOLICITUD


def _cargado(session, cliente_id, id_externo, creado, cerrado):
    t = Ticket(cliente_id=cliente_id, texto="x", id_externo=id_externo, estado="resuelto",
               resuelto_por="tecnico", creado_en=creado, cerrado_en=cerrado)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def test_simulacion_reemplaza_el_tiempo_de_lo_que_minutito_resolveria(client, crear_cuenta, entrar, session):
    usuario = crear_cuenta("x@ejemplo.com")
    crear_cuenta("adm@ejemplo.com", "administrador")
    # histórico: 2 y 4 días; el que se resolvió el mismo día (fecha sin hora) cuenta como 0
    for i, (creado, resuelto) in enumerate([
        (datetime(2026, 3, 2, 9), datetime(2026, 3, 4, 9)),
        (datetime(2026, 3, 2, 9), datetime(2026, 3, 6, 9)),
        (datetime(2026, 3, 2, 15), datetime(2026, 3, 2, 0)),
    ]):
        session.add(TicketHistorico(id_externo=str(i), estado="Completado", creado_en=creado, resuelto_en=resuelto))
    session.commit()
    a = _cargado(session, usuario.id, "100", datetime(2026, 9, 1, 9), datetime(2026, 9, 5, 9))  # 4 días
    _cargado(session, usuario.id, "101", datetime(2026, 9, 1, 9), datetime(2026, 9, 3, 9))  # 2 días
    session.add(EvaluacionMinutito(ticket_id=a.id, respuesta="pasos", veredicto="resuelve"))
    session.commit()

    r = client.get("/reportes/simulacion-tiempos", params={"minutos_minutito": 1440}, headers=entrar("adm@ejemplo.com")).json()
    assert r["linea_base_historico"]["tickets"] == 3 and r["linea_base_historico"]["media_dias"] == 2.0
    m = r["muestra"]
    assert (m["tickets"], m["resueltos_por_minutito"], m["sin_evaluar"]) == (2, 1, 1)
    assert (m["media_real_dias"], m["media_simulada_dias"]) == (3.0, 1.5)  # 4 días pasan a 1 día
    assert m["reduccion"] == 0.5


def test_simulacion_solo_para_el_administrador(client, crear_cuenta, entrar):
    crear_cuenta("tec@ejemplo.com", "tecnico")
    assert client.get("/reportes/simulacion-tiempos", headers=entrar("tec@ejemplo.com")).status_code == 403


def test_objetivo_3_se_mide_en_las_incidencias(client, crear_cuenta, entrar, session):
    usuario = crear_cuenta("x@ejemplo.com")
    crear_cuenta("adm@ejemplo.com", "administrador")
    # histórico: una incidencia de 2 días y una solicitud de 6 -> las incidencias son el 25 % del tiempo
    session.add(TicketHistorico(id_externo="1", estado="Completado", tipo=TIPO_INCIDENCIA,
                                creado_en=datetime(2026, 3, 2, 9), resuelto_en=datetime(2026, 3, 4, 9)))
    session.add(TicketHistorico(id_externo="2", estado="Completado", tipo=TIPO_SOLICITUD,
                                creado_en=datetime(2026, 3, 2, 9), resuelto_en=datetime(2026, 3, 8, 9)))
    session.commit()
    inc = _cargado(session, usuario.id, "100", datetime(2026, 9, 1, 9), datetime(2026, 9, 3, 9))  # 2 días
    inc.tipo = TIPO_INCIDENCIA
    sol = _cargado(session, usuario.id, "101", datetime(2026, 9, 1, 9), datetime(2026, 9, 9, 9))  # 8 días
    sol.tipo = TIPO_SOLICITUD
    session.add_all([inc, sol, EvaluacionMinutito(ticket_id=inc.id, respuesta="pasos", veredicto="resuelve")])
    session.commit()

    r = client.get("/reportes/simulacion-tiempos", params={"minutos_minutito": 1440}, headers=entrar("adm@ejemplo.com")).json()
    i = r["incidencias"]
    assert (i["linea_base_historico"]["tickets"], i["parte_del_tiempo_total"]) == (1, 0.25)
    assert (i["muestra"]["tickets"], i["muestra"]["reduccion"]) == (1, 0.5)  # 2 días pasan a 1
    assert r["muestra"]["reduccion"] == 0.1  # sobre todos: 5 -> 4,5 días

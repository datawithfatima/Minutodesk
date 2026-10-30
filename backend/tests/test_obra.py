"""Gamificación «Mi obra»: etapas de obra, insignias y la ciudad del Top 5."""
from datetime import date, datetime, timedelta

from app.models import EventoGamificacion
from app.services.obra import _semanas_seguidas, etapa, nombre_corto


def test_etapas_y_pisos_segun_los_puntos():
    assert etapa(0)["etapa"] == "Cimientos" and etapa(0)["puntos_para_siguiente"] == 50
    assert etapa(60) | {} == {
        "etapa": "Estructura", "numero_etapa": 2, "pisos": 2,
        "siguiente_etapa": "Acabados", "puntos_para_siguiente": 90,
    }
    assert etapa(300)["etapa"] == "Entrega de llaves" and etapa(300)["siguiente_etapa"] is None


def test_racha_de_semanas_seguidas():
    hoy = date(2026, 10, 29)  # jueves
    dias = [datetime(2026, 10, 27), datetime(2026, 10, 20), datetime(2026, 10, 13), datetime(2026, 10, 6)]
    assert _semanas_seguidas(dias, hoy) == 4
    assert _semanas_seguidas(dias[1:], hoy) == 3  # esta semana aún no hay actividad: cuenta desde la anterior
    assert _semanas_seguidas([datetime(2026, 10, 27), datetime(2026, 10, 6)], hoy) == 1


def test_nombre_corto():
    assert nombre_corto("Ana López Pérez") == "Ana L." and nombre_corto("Ana") == "Ana"


def _puntos(session, cliente, puntos, cuando=None):
    session.add(EventoGamificacion(cliente_id=cliente.id, puntos_otorgados=puntos, motivo="x",
                                   creado_en=cuando or datetime.now()))
    cliente.puntos += puntos
    session.add(cliente)
    session.commit()


def test_mis_logros_trae_etapa_pisos_e_insignias(client, crear_cuenta, entrar, session):
    ana = crear_cuenta("ana@ejemplo.com", nombre="Ana López")
    _puntos(session, ana, 60)
    r = client.get(f"/clientes/{ana.id}/gamificacion", headers=entrar("ana@ejemplo.com")).json()
    assert (r["nivel"], r["pisos"], r["siguiente_etapa"]) == ("Estructura", 2, "Acabados")
    assert [i["clave"] for i in r["insignias"]] == ["primera_piedra", "planos_al_dia", "obra_sin_retrasos", "inspector"]
    assert not any(i["obtenida"] for i in r["insignias"])  # puntos sin consultas resueltas no dan insignias


def test_ciudad_muestra_el_top_5_del_mes_y_la_obra_propia(client, crear_cuenta, entrar, session):
    personas = [crear_cuenta(f"u{i}@ejemplo.com", nombre=f"Persona{i} Apellido") for i in range(7)]
    for i, p in enumerate(personas):
        _puntos(session, p, 10 * (i + 1))
    # puntos de hace meses: cuentan en el histórico, no en el mes
    _puntos(session, personas[0], 500, datetime.now() - timedelta(days=90))
    crear_cuenta("tec@ejemplo.com", "tecnico")

    mes = client.get("/gamificacion/ciudad", params={"periodo": "mes"}, headers=entrar("u1@ejemplo.com")).json()
    assert [f["nombre"] for f in mes["top"]] == ["Persona6 A.", "Persona5 A.", "Persona4 A.", "Persona3 A.", "Persona2 A."]
    assert mes["yo"]["es_yo"] and mes["yo"]["posicion"] == 6 and mes["yo"]["nombre"] == "Tú"
    # el resto llena la ciudad sin nombre
    assert len(mes["vecinos"]) == 1 and mes["vecinos"][0]["anonimo"] and "nombre" not in mes["vecinos"][0]

    total = client.get("/gamificacion/ciudad", params={"periodo": "total"}, headers=entrar("u0@ejemplo.com")).json()
    assert total["top"][0]["nombre"] == "Tú" and total["top"][0]["etapa"] == "Entrega de llaves"
    assert client.get("/gamificacion/ciudad", params={"periodo": "anual"}, headers=entrar("u0@ejemplo.com")).status_code == 400
    # el personal también la ve, pero no tiene obra propia
    assert client.get("/gamificacion/ciudad", headers=entrar("tec@ejemplo.com")).json()["yo"] is None

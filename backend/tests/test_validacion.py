"""Validación del clasificador con tickets posteriores al entrenamiento."""
from datetime import datetime

from app.models import TicketHistorico

SOLICITUD = "Solicitud de servicio (Nuevo requerimiento, configuraciones, etc.)"
INCIDENCIA = "Incidencia o problema técnico"

CABECERA = '"ID","Seleccione una opción para la respectiva atención.","Categoría","Prioridad","Creado","Solicitante","Estado","Descripción"\n'
CSV = CABECERA + (
    f'"1","{INCIDENCIA}","Internet","Normal","01/01/2026 09:00","Ana","Completado","<p>No hay internet</p>"\n'  # entrenamiento
    f'"100","{INCIDENCIA}","Internet","Alta","10/09/2026 09:00","Beto Ruiz","Completado","<p>No tengo internet en mi laptop, el wifi no conecta</p>"\n'
    f'"101","{SOLICITUD}","Salesforce","Normal","11/09/2026 10:00","Carla","En Curso","Necesito acceso a Salesforce para ver oportunidades"\n'
    f'"102","{SOLICITUD}","CollectXpert","Normal","12/09/2026 10:00","Dani","Nuevo","Revisar el reporte de cobranzas en CollectXpert"\n'  # se aprendió como Otros
    f'"103","{SOLICITUD}","SAP BO","Normal","13/09/2026 10:00","Eva","Nuevo","Error al abrir el informe de SAP BO"\n'  # nunca vista
    f'"104","{SOLICITUD}","","Normal","14/09/2026 10:00","Fede","Nuevo","Sin categoría"\n'  # sin clasificación real
    f'"105","","Internet","Normal","14/09/2026 10:00","Gabi","Nuevo","Sin tipo"\n'
)


def _historico(session):
    for i, categoria in [("1", "Internet"), ("2", "CollectXpert")]:
        session.add(
            TicketHistorico(id_externo=i, categoria=categoria, estado="Completado", creado_en=datetime(2026, 1, 1, 9))
        )
    session.commit()


def _subir(client, h, aplicar):
    return client.post(
        f"/admin/validacion?aplicar={'true' if aplicar else 'false'}",
        content=CSV.encode("utf-8"),
        headers={**h, "Content-Type": "text/csv"},
    )


def test_carga_de_validacion_filtra_clasifica_y_no_duplica(client, crear_cuenta, entrar, session):
    _historico(session)
    crear_cuenta("adm@ejemplo.com", "administrador")
    h = entrar("adm@ejemplo.com")

    previa = _subir(client, h, aplicar=False).json()
    assert (previa["filas"], previa["de_entrenamiento"], previa["sin_clasificacion_real"]) == (7, 1, 2)
    assert previa["validables"] == 4 and previa["creados"] == 0
    assert client.get("/reportes/validacion", headers=h).json()["total"] == 0  # la vista previa no guarda

    real = _subir(client, h, aplicar=True).json()
    assert real["creados"] == 4
    otra_vez = _subir(client, h, aplicar=True).json()
    assert otra_vez["ya_cargados"] == 4 and otra_vez["creados"] == 0

    r = client.get("/reportes/validacion", headers=h).json()
    assert r["total"] == 4 and r["categoria_evaluables"] == 3
    assert r["categorias_no_vistas"] == ["SAP BO"] and r["tickets_no_vistos"] == 1
    por_id = {t["id_externo"]: t for t in r["tickets"]}
    assert por_id["102"]["categoria_esperada"] == "Otros"
    assert por_id["103"]["acierto_categoria"] is None
    assert por_id["100"]["solicitante"] == "Beto Ruiz"
    assert por_id["100"]["texto"] == "No tengo internet en mi laptop, el wifi no conecta"  # sin HTML


def test_los_tickets_de_validacion_no_se_mezclan_con_soporte(client, crear_cuenta, entrar, session):
    _historico(session)
    crear_cuenta("adm@ejemplo.com", "administrador")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h = entrar("adm@ejemplo.com")
    _subir(client, h, aplicar=True)

    h_tec = entrar("tec@ejemplo.com")
    assert client.get("/tickets", headers=h_tec).json() == []
    assert client.get("/reportes/resumen", headers=h_tec).json()["total"] == 0
    assert client.get("/reportes/clasificador", headers=h).json()["en_uso"]["tickets_categoria"] == 0
    # la cuenta dueña de esos tickets no puede iniciar sesión
    assert client.post("/auth/login", json={"email": "validacion@minutodesk.local", "password": "x"}).status_code == 401


def test_validacion_solo_para_el_administrador(client, crear_cuenta, entrar):
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h = entrar("tec@ejemplo.com")
    assert _subir(client, h, aplicar=False).status_code == 403
    assert client.get("/reportes/validacion", headers=h).status_code == 403

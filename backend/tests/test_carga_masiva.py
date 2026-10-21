"""Carga masiva de tickets nuevos como tickets normales de MinutoDesk."""
from datetime import datetime

from app.models import TicketHistorico

SOLICITUD = "Solicitud de servicio (Nuevo requerimiento, configuraciones, etc.)"
INCIDENCIA = "Incidencia o problema técnico"

CABECERA = (
    '"ID","Seleccione una opción para la respectiva atención.","Categoría","Prioridad","Creado",'
    '"Solicitante","Asignado a","Estado","Descripción","Fecha Solución"\n'
)
CSV = CABECERA + (
    # entrenamiento: se ignora
    f'"1","{INCIDENCIA}","Internet","Normal","01/01/2026 09:00","Ana","","Completado","<p>No hay internet</p>",""\n'
    f'"100","{INCIDENCIA}","Internet","Alta","10/09/2026 09:00","Beto Ruiz","Tito Pérez","Completado",'
    '"<p>No tengo internet en mi laptop, el wifi no conecta</p>","12/09/2026"\n'
    f'"101","{SOLICITUD}","Salesforce","Normal","11/09/2026 10:00","Carla","Nadie Conocido","En Curso",'
    '"Necesito acceso a Salesforce para ver oportunidades",""\n'
    f'"102","{SOLICITUD}","Salesforce","Normal","12/09/2026 10:00","Dani","","Nuevo","<p></p>",""\n'  # sin texto
    f'"103","{SOLICITUD}","","Normal","14/09/2026 10:00","Fede","","Nuevo","Sin categoría",""\n'
)


def _historico(session):
    session.add(TicketHistorico(id_externo="1", categoria="Internet", estado="Completado", creado_en=datetime(2026, 1, 1, 9)))
    session.commit()


def _subir(client, h, aplicar):
    return client.post(
        f"/admin/carga-masiva?aplicar={'true' if aplicar else 'false'}",
        content=CSV.encode("utf-8"),
        headers={**h, "Content-Type": "text/csv"},
    )


def test_carga_masiva_crea_tickets_normales_clasificados_y_no_duplica(client, crear_cuenta, entrar, session):
    _historico(session)
    crear_cuenta("adm@ejemplo.com", "administrador")
    tito = crear_cuenta("tec@ejemplo.com", "tecnico", nombre="Tito Perez")
    h, h_tec = entrar("adm@ejemplo.com"), entrar("tec@ejemplo.com")

    previa = _subir(client, h, aplicar=False).json()
    assert (previa["filas"], previa["de_entrenamiento"], previa["incompletos"], previa["validos"]) == (5, 1, 2, 2)
    assert client.get("/tickets", headers=h_tec).json() == []  # la vista previa no guarda

    assert _subir(client, h, aplicar=True).json()["creados"] == 2
    assert _subir(client, h, aplicar=True).json()["ya_cargados"] == 2

    # tickets normales, con su estado y fecha reales, la predicción del SVM y lo elegido
    tickets = {t["solicitante_externo"]: t for t in client.get("/tickets", headers=h_tec).json()}
    assert set(tickets) == {"Solicitante 001", "Solicitante 002"}  # sin nombres reales
    beto, carla = tickets["Solicitante 001"], tickets["Solicitante 002"]
    assert beto["estado"] == "resuelto" and beto["resuelto_por"] == "tecnico" and beto["prioridad"] == "Alta"
    assert beto["tecnico_id"] == tito.id  # «Asignado a» coincide con su cuenta (sin importar tildes)
    assert beto["creado_en"].startswith("2026-09-10") and beto["cerrado_en"].startswith("2026-09-12")
    assert beto["texto"] == "No tengo internet en mi laptop, el wifi no conecta"  # sin HTML
    assert beto["categoria"] == "Internet" and beto["categoria_predicha"] and beto["clasificacion_confirmada"]
    assert carla["estado"] == "en_proceso" and carla["tecnico_id"] is None

    historial = client.get(f"/tickets/{beto['id']}/historial", headers=h_tec).json()
    assert [(c["estado_nuevo"], c["cambiado_por"]) for c in historial] == [("abierto", "adm"), ("resuelto", "Tito Perez")]

    resumen = client.get("/reportes/resumen", headers=h_tec).json()
    assert (resumen["resueltos"], resumen["en_proceso"]) == (1, 1)
    assert client.get("/reportes/clasificador", headers=h).json()["en_uso"]["tickets_categoria"] == 2
    # la cuenta dueña de esos tickets no puede iniciar sesión
    assert client.post("/auth/login", json={"email": "carga-masiva@minutodesk.local", "password": "x"}).status_code == 401


def test_carga_masiva_solo_para_el_administrador(client, crear_cuenta, entrar):
    crear_cuenta("tec@ejemplo.com", "tecnico")
    assert _subir(client, entrar("tec@ejemplo.com"), aplicar=False).status_code == 403

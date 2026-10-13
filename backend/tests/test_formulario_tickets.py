"""Formulario de tickets: catálogo, sugerencia del SVM, alta de colaborador, correcciones
del personal, medición del acierto real y archivos adjuntos."""
import json
from datetime import date
from urllib.parse import quote

import pytest
from sqlmodel import select

from app.models import Ticket
from app.services.catalogos import CATEGORIA_ALTA, TIPO_ACCESOS, TIPO_INCIDENCIA, TIPO_SOLICITUD

from .test_acceso_y_roles import _crear_ticket

CEDULA_VALIDA = "1710034065"


def _alta(**cambios):
    datos = {
        "nombres": "  Juan   Pérez ",
        "fecha_ingreso": "2026-11-02",
        "cedula": CEDULA_VALIDA,
        "cargo": "Analista contable",
        "monitor": True,
        "telefono_fijo": False,
        "grupo": "Compras",
        "listas_distribucion": ["Contabilidad", "Finanzas"],
        "aplicaciones": ["Power BI", "SAP BO"],
        "licencia_sap": "Financiera",
        "permisos_sap": "Módulo FI, usuario referencia Ana",
        "observaciones": "Ingresa el 2 de noviembre",
    }
    datos.update(cambios)
    return datos


# ---------- catálogo y sugerencia ----------

def test_catalogos_del_formulario(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    c = client.get("/tickets/catalogos", headers=entrar("usr@ejemplo.com")).json()
    assert [t["nombre"] for t in c["tipos"]] == [TIPO_INCIDENCIA, TIPO_SOLICITUD, TIPO_ACCESOS]
    assert c["prioridades"] == ["Crítica", "Alta", "Normal", "Baja"]
    assert c["prioridad_por_defecto"] == "Normal"
    assert c["categorias"][-1] == "Otros" and "Salesforce" in c["categorias"]
    assert CATEGORIA_ALTA not in c["categorias"]  # esa categoría solo la lleva el alta
    assert c["adjuntos"]["maximo"] == 3 and c["adjuntos"]["megabytes"] == 10
    assert ".pdf" in c["adjuntos"]["extensiones"]
    assert "Power BI" in c["aplicaciones"]
    assert {x["nombre"] for x in c["licencias_sap"]} == {"Financiera", "Profesional", "Logística"}


def test_sugerencia_de_clasificacion_devuelve_tipo_categoria_y_alternativas(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    h = entrar("usr@ejemplo.com")
    r = client.post("/tickets/sugerir", json={"texto": "Mi laptop no enciende y la impresora no imprime"}, headers=h)
    assert r.status_code == 200
    s = r.json()
    assert s["categoria"] in client.get("/tickets/catalogos", headers=h).json()["categorias"]
    assert len(s["alternativas"]) == 3 and 0 < s["confianza"] <= 1
    assert isinstance(s["confiable"], bool)
    assert s["tipo"] in (TIPO_INCIDENCIA, TIPO_SOLICITUD, TIPO_ACCESOS)
    assert client.post("/tickets/sugerir", json={"texto": "hola"}, headers=h).status_code == 400


# ---------- crear con lo que eligió la persona ----------

def test_ticket_con_tipo_y_categoria_elegidos_nace_confirmado_y_con_prioridad(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    h = entrar("usr@ejemplo.com")
    r = client.post(
        "/tickets",
        json={"texto": "No puedo entrar a Salesforce", "tipo": TIPO_INCIDENCIA, "categoria": "Salesforce", "prioridad": "Alta"},
        headers=h,
    ).json()
    assert r["tipo"] == TIPO_INCIDENCIA and r["categoria"] == "Salesforce" and r["prioridad"] == "Alta"
    assert r["clasificacion_confirmada"] is True
    assert r["categoria_predicha"]  # sigue guardada la predicción del SVM

    solo_texto = _crear_ticket(client, h)  # como el chat con Minutito: sin elegir nada
    assert solo_texto["clasificacion_confirmada"] is False and solo_texto["prioridad"] == "Normal"
    assert solo_texto["tipo"] is None and solo_texto["categoria"] is None
    solo_tipo = client.post("/tickets", json={"texto": "Necesito una configuración", "tipo": TIPO_SOLICITUD}, headers=h).json()
    assert solo_tipo["clasificacion_confirmada"] is False  # se confirma solo con tipo y categoría


def test_ticket_rechaza_prioridad_categoria_o_tipo_invalidos(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    h = entrar("usr@ejemplo.com")
    base = {"texto": "No puedo imprimir desde mi laptop"}
    assert client.post("/tickets", json={**base, "prioridad": "Urgentísima"}, headers=h).status_code == 400
    assert client.post("/tickets", json={**base, "categoria": "Inventada"}, headers=h).status_code == 400
    assert client.post("/tickets", json={**base, "tipo": "Otra cosa"}, headers=h).status_code == 400
    # los accesos solo se piden con el formulario de alta
    assert client.post("/tickets", json={**base, "tipo": TIPO_ACCESOS}, headers=h).status_code == 400
    assert client.get("/tickets", headers=h).json() == []


# ---------- alta de colaborador ----------

def test_alta_de_colaborador_crea_ticket_estructurado_sin_pasar_por_el_svm(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    r = client.post("/tickets/alta-colaborador", json=_alta(prioridad="Alta"), headers=entrar("usr@ejemplo.com"))
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["tipo"] == TIPO_ACCESOS and t["categoria"] == CATEGORIA_ALTA
    assert t["clasificacion_confirmada"] is True and t["prioridad"] == "Alta"
    assert t["tipo_predicho"] is None and t["categoria_predicha"] is None
    assert "Juan Pérez" in t["texto"] and CEDULA_VALIDA not in t["texto"]  # el resumen no lleva la cédula

    # los datos completos (con la cédula) solo en el detalle, no en las listas
    ht = entrar("tec@ejemplo.com")
    datos = json.loads(client.get(f"/tickets/{t['id']}", headers=ht).json()["datos_alta"])
    assert datos["cedula"] == CEDULA_VALIDA and datos["nombres"] == "Juan Pérez"
    assert datos["aplicaciones"] == ["Power BI", "SAP BO"]
    assert all("datos_alta" not in x for x in client.get("/tickets", headers=ht).json())


def test_alta_de_colaborador_valida_cedula_y_opciones(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    h = entrar("usr@ejemplo.com")
    for cambios in (
        {"cedula": "1710034066"},  # dígito verificador incorrecto
        {"cedula": "12345"},
        {"cargo": "  "},
        {"observaciones": ""},
        {"aplicaciones": ["Programa Inventado"]},
        {"listas_distribucion": ["Lista Inventada"]},
        {"licencia_sap": "Platino"},
        {"prioridad": "Mañana"},
    ):
        assert client.post("/tickets/alta-colaborador", json=_alta(**cambios), headers=h).status_code == 400, cambios
    assert client.get("/tickets", headers=h).json() == []


def test_la_cedula_se_valida_con_su_digito_verificador():
    from app.services.catalogos import cedula_valida

    assert cedula_valida(CEDULA_VALIDA)
    assert not cedula_valida("1710034066") and not cedula_valida("9910034065") and not cedula_valida("")


# ---------- correcciones del personal ----------

def test_el_personal_corrige_categoria_y_prioridad_y_queda_confirmado(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h, ht = entrar("usr@ejemplo.com"), entrar("tec@ejemplo.com")
    t = _crear_ticket(client, h)
    assert t["clasificacion_confirmada"] is False

    r = client.patch(f"/tickets/{t['id']}", json={"categoria": "Salesforce", "prioridad": "Crítica"}, headers=ht).json()
    assert r["categoria"] == "Salesforce" and r["prioridad"] == "Crítica" and r["clasificacion_confirmada"] is True
    assert client.patch(f"/tickets/{t['id']}", json={"categoria": "Inventada"}, headers=ht).status_code == 400
    assert client.patch(f"/tickets/{t['id']}", json={"prioridad": "Mañana"}, headers=ht).status_code == 400
    assert client.patch(f"/tickets/{t['id']}", json={"tipo": TIPO_ACCESOS}, headers=ht).status_code == 400
    assert client.patch(f"/tickets/{t['id']}", json={"categoria": "SAP"}, headers=h).status_code == 403  # el usuario no


def test_en_un_alta_solo_se_puede_cambiar_la_prioridad(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    t = client.post("/tickets/alta-colaborador", json=_alta(), headers=entrar("usr@ejemplo.com")).json()
    ht = entrar("tec@ejemplo.com")
    assert client.patch(f"/tickets/{t['id']}", json={"categoria": "SAP"}, headers=ht).status_code == 400
    assert client.patch(f"/tickets/{t['id']}", json={"prioridad": "Baja"}, headers=ht).json()["prioridad"] == "Baja"


# ---------- medición del acierto real ----------

def test_acierto_real_del_clasificador_con_lo_que_confirman_las_personas(client, crear_cuenta, entrar, session):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("adm@ejemplo.com", "administrador")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h = entrar("usr@ejemplo.com")
    a = client.post("/tickets", json={"texto": "Problema con la laptop", "tipo": TIPO_INCIDENCIA, "categoria": "Internet"}, headers=h).json()
    b = client.post("/tickets", json={"texto": "Problema con la impresora", "tipo": TIPO_INCIDENCIA, "categoria": "Internet"}, headers=h).json()
    _crear_ticket(client, h)  # sin confirmar: no entra en la medición
    # se fuerzan las predicciones para no depender del modelo: una acierta y otra no
    for tid, predicha in ((a["id"], "Internet"), (b["id"], "SAP")):
        t = session.get(Ticket, tid)
        t.categoria_predicha = predicha
        t.tipo_predicho = TIPO_INCIDENCIA
        session.add(t)
    session.commit()

    r = client.get("/reportes/clasificador", headers=entrar("adm@ejemplo.com")).json()["en_uso"]
    assert r["tickets_categoria"] == 2 and r["acierto_categoria"] == 0.5
    assert r["tickets_tipo"] == 2 and r["acierto_tipo"] == 1.0
    assert client.get("/reportes/clasificador", headers=entrar("tec@ejemplo.com")).status_code == 403


def test_los_reportes_cuentan_la_categoria_final_si_existe(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h = entrar("usr@ejemplo.com")
    client.post("/tickets", json={"texto": "Algo con SAP", "tipo": TIPO_INCIDENCIA, "categoria": "Power BI"}, headers=h)
    por_categoria = client.get("/reportes/resumen", headers=entrar("tec@ejemplo.com")).json()["por_categoria"]
    assert por_categoria == [{"categoria": "Power BI", "total": 1}]


def test_la_base_antigua_de_tickets_recibe_las_columnas_nuevas():
    from sqlalchemy import create_engine as crear_motor

    from app.database import _agregar_columnas_nuevas

    motor = crear_motor("sqlite://")
    with motor.begin() as c:
        c.exec_driver_sql("CREATE TABLE ticket (id INTEGER PRIMARY KEY, texto TEXT)")
        c.exec_driver_sql("INSERT INTO ticket (id, texto) VALUES (1, 'viejo')")
    _agregar_columnas_nuevas(motor)
    with motor.begin() as c:
        fila = c.exec_driver_sql(
            "SELECT texto, tipo, categoria, clasificacion_confirmada, prioridad, datos_alta FROM ticket"
        ).one()
    assert tuple(fila) == ("viejo", None, None, 0, "Normal", None)


# ---------- archivos adjuntos ----------

@pytest.fixture()
def carpeta_de_archivos(tmp_path, monkeypatch):
    from app.routers import adjuntos

    destino = tmp_path / "uploads"
    monkeypatch.setattr(adjuntos, "DIRECTORIO_ARCHIVOS", destino)
    return destino


def _subir(client, headers, ticket_id, nombre="captura.png", contenido=b"contenido de prueba"):
    return client.post(
        f"/tickets/{ticket_id}/adjuntos",
        content=contenido,
        headers={**headers, "X-Nombre-Archivo": quote(nombre), "Content-Type": "application/octet-stream"},
    )


def test_subir_listar_y_descargar_un_adjunto(client, crear_cuenta, entrar, carpeta_de_archivos):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    crear_cuenta("otro@ejemplo.com", "usuario")
    h, ht = entrar("usr@ejemplo.com"), entrar("tec@ejemplo.com")
    t = _crear_ticket(client, h)

    r = _subir(client, h, t["id"], nombre="Informe de error ñ.pdf", contenido=b"%PDF-1.4 prueba")
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["nombre_original"] == "Informe de error ñ.pdf" and a["tamano"] == 15 and a["subido_por"] == "usr"

    # en disco queda con nombre aleatorio y sin extensión
    guardados = list(carpeta_de_archivos.iterdir())
    assert len(guardados) == 1 and "." not in guardados[0].name and "Informe" not in guardados[0].name

    assert [x["id"] for x in client.get(f"/tickets/{t['id']}/adjuntos", headers=ht).json()] == [a["id"]]
    d = client.get(f"/adjuntos/{a['id']}", headers=ht)
    assert d.status_code == 200 and d.content == b"%PDF-1.4 prueba"
    assert d.headers["content-type"] == "application/pdf" and d.headers["x-content-type-options"] == "nosniff"
    assert d.headers["content-disposition"].startswith("attachment")
    assert "no-store" in d.headers["cache-control"]  # no queda en la caché del navegador

    # otra persona no ve ni descarga archivos de un ticket ajeno
    ho = entrar("otro@ejemplo.com")
    assert client.get(f"/tickets/{t['id']}/adjuntos", headers=ho).status_code == 403
    assert client.get(f"/adjuntos/{a['id']}", headers=ho).status_code == 403
    assert client.get("/adjuntos/9999", headers=ht).status_code == 404


def test_adjuntos_validan_tipo_tamano_y_cantidad(client, crear_cuenta, entrar, carpeta_de_archivos, monkeypatch):
    from app.routers import adjuntos

    crear_cuenta("usr@ejemplo.com", "usuario")
    h = entrar("usr@ejemplo.com")
    t = _crear_ticket(client, h)

    assert _subir(client, h, t["id"], nombre="virus.exe").status_code == 400
    assert _subir(client, h, t["id"], nombre="pagina.html").status_code == 400
    assert _subir(client, h, t["id"], nombre="sin_extension").status_code == 400
    assert _subir(client, h, t["id"], nombre="vacio.txt", contenido=b"").status_code == 400
    assert _subir(client, h, 9999, nombre="a.txt").status_code == 404

    monkeypatch.setattr(adjuntos, "MAX_BYTES_ADJUNTO", 10)
    assert _subir(client, h, t["id"], nombre="grande.txt", contenido=b"x" * 11).status_code == 413
    monkeypatch.setattr(adjuntos, "MAX_BYTES_ADJUNTO", 10 * 1024 * 1024)

    for i in range(3):
        assert _subir(client, h, t["id"], nombre=f"ok{i}.txt").status_code == 200
    r = _subir(client, h, t["id"], nombre="cuarto.txt")
    assert r.status_code == 409 and "hasta 3" in r.json()["detail"]
    assert len(list(carpeta_de_archivos.iterdir())) == 3  # el rechazado no dejó nada en disco


def test_el_nombre_del_adjunto_se_limpia_de_rutas(client, crear_cuenta, entrar, carpeta_de_archivos):
    crear_cuenta("usr@ejemplo.com", "usuario")
    h = entrar("usr@ejemplo.com")
    t = _crear_ticket(client, h)
    assert _subir(client, h, t["id"], nombre="../../etc/passwd.txt").json()["nombre_original"] == "passwd.txt"
    assert _subir(client, h, t["id"], nombre=".oculto.txt").status_code == 400


def test_quitar_adjuntos_y_ticket_resuelto(client, crear_cuenta, entrar, carpeta_de_archivos):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("otro@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    crear_cuenta("adm@ejemplo.com", "administrador")
    h, ho = entrar("usr@ejemplo.com"), entrar("otro@ejemplo.com")
    ht, ha = entrar("tec@ejemplo.com"), entrar("adm@ejemplo.com")
    t = _crear_ticket(client, h)
    a = _subir(client, h, t["id"], nombre="a.txt").json()
    b = _subir(client, h, t["id"], nombre="b.txt").json()

    assert client.delete(f"/adjuntos/{a['id']}", headers=ho).status_code == 403
    assert client.delete(f"/adjuntos/{a['id']}", headers=ht).status_code == 403  # el técnico no borra lo del usuario
    assert client.delete(f"/adjuntos/{a['id']}", headers=h).status_code == 200
    assert len(list(carpeta_de_archivos.iterdir())) == 1  # también se borró el archivo del disco

    client.patch(f"/tickets/{t['id']}", json={"estado": "resuelto"}, headers=ht)
    assert _subir(client, h, t["id"], nombre="c.txt").status_code == 409  # el usuario ya no sube
    assert client.delete(f"/adjuntos/{b['id']}", headers=h).status_code == 409
    assert _subir(client, ht, t["id"], nombre="solucion.txt").status_code == 200  # el técnico sí
    assert client.delete(f"/adjuntos/{b['id']}", headers=ha).status_code == 200  # el administrador siempre


def test_no_se_elimina_a_quien_subio_archivos(client, crear_cuenta, entrar, carpeta_de_archivos):
    crear_cuenta("adm@ejemplo.com", "administrador")
    crear_cuenta("usr@ejemplo.com", "usuario")
    tec = crear_cuenta("tec@ejemplo.com", "tecnico")
    t = _crear_ticket(client, entrar("usr@ejemplo.com"))
    _subir(client, entrar("tec@ejemplo.com"), t["id"], nombre="evidencia.txt")
    r = client.delete(f"/admin/usuarios/{tec.id}", headers=entrar("adm@ejemplo.com"))
    assert r.status_code == 409  # tiene actividad registrada

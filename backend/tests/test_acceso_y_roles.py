from sqlmodel import select

from app.models import HistorialEstadoTicket, Ticket

from .conftest import PASSWORD, token_del_ultimo_correo


# ---------- inicio de sesión ----------

def test_login_correcto_devuelve_cliente_con_area_y_rol(client, crear_cuenta):
    crear_cuenta("ana@ejemplo.com", nombre="Ana", area="Contabilidad")
    r = client.post("/auth/login", json={"email": "ANA@ejemplo.com", "password": PASSWORD})
    assert r.status_code == 200
    cliente = r.json()["cliente"]
    assert cliente["rol"] == "usuario" and cliente["area"] == "Contabilidad"


def test_login_con_password_incorrecta_o_correo_inexistente_da_el_mismo_error(client, crear_cuenta):
    crear_cuenta("ana@ejemplo.com")
    a = client.post("/auth/login", json={"email": "ana@ejemplo.com", "password": "otra-clave-1"})
    b = client.post("/auth/login", json={"email": "nadie@ejemplo.com", "password": PASSWORD})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_cuenta_sin_password_no_puede_iniciar_sesion(client, crear_cuenta):
    crear_cuenta("nueva@ejemplo.com", password=None)
    r = client.post("/auth/login", json={"email": "nueva@ejemplo.com", "password": PASSWORD})
    assert r.status_code == 401


def test_cuenta_desactivada_no_puede_iniciar_sesion(client, crear_cuenta):
    crear_cuenta("baja@ejemplo.com", activo=False)
    r = client.post("/auth/login", json={"email": "baja@ejemplo.com", "password": PASSWORD})
    assert r.status_code == 403


def test_no_existe_registro_publico(client):
    r = client.post("/auth/registro", json={"nombre": "X", "email": "x@ejemplo.com", "password": PASSWORD})
    assert r.status_code == 404


# ---------- permisos por rol ----------

def test_solo_el_administrador_entra_a_las_rutas_de_admin(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    crear_cuenta("adm@ejemplo.com", "administrador")
    assert client.get("/admin/usuarios", headers=entrar("usr@ejemplo.com")).status_code == 403
    assert client.get("/admin/usuarios", headers=entrar("tec@ejemplo.com")).status_code == 403
    assert client.get("/admin/usuarios", headers=entrar("adm@ejemplo.com")).status_code == 200
    assert client.get("/admin/usuarios").status_code in (401, 403)


def test_usuario_final_no_puede_listar_clientes_ni_cambiar_tickets(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    h = entrar("usr@ejemplo.com")
    assert client.get("/clientes", headers=h).status_code == 403
    assert client.patch("/tickets/1", json={"estado": "resuelto"}, headers=h).status_code == 403


# ---------- altas y restablecimiento: siempre por enlace al correo de la persona ----------

def _bearer(login):
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_admin_crea_usuario_y_la_persona_recibe_enlace_sin_que_el_admin_vea_la_clave(
    client, crear_cuenta, entrar, correos
):
    admin = crear_cuenta("adm@ejemplo.com", "administrador")
    r = client.post(
        "/admin/usuarios",
        json={"nombre": "Nuevo Usuario", "email": "Nuevo@Ejemplo.com", "area_id": admin.area_id, "rol": "tecnico"},
        headers=entrar("adm@ejemplo.com"),
    )
    assert r.status_code == 200, r.text
    assert "password_temporal" not in r.json() and r.json()["envio"] == "archivo"
    assert r.json()["usuario"]["email"] == "nuevo@ejemplo.com"
    assert r.json()["usuario"]["pendiente_activacion"] is True

    archivos = list(correos.glob("*nuevo_ejemplo.com.txt"))
    assert len(archivos) == 1 and "Activa tu cuenta" in archivos[0].read_text(encoding="utf-8")
    token = token_del_ultimo_correo(correos)
    assert client.post("/auth/establecer-password", json={"token": token, "password": "ClaveElegida7"}).status_code == 200
    login = client.post("/auth/login", json={"email": "nuevo@ejemplo.com", "password": "ClaveElegida7"})
    assert login.status_code == 200
    assert login.json()["cliente"]["debe_cambiar_password"] is False and login.json()["cliente"]["rol"] == "tecnico"


def test_con_contrasena_temporal_solo_se_puede_cambiarla(client, crear_cuenta, session):
    # Solo la primera cuenta de administrador (seed_data.py) nace con contraseña temporal.
    temporal = "Temporal123"
    ana = crear_cuenta("ana@ejemplo.com", password=temporal)
    ana.debe_cambiar_password = True
    session.add(ana)
    session.commit()
    login = client.post("/auth/login", json={"email": "ana@ejemplo.com", "password": temporal})
    h = _bearer(login)

    # el resto del sistema queda bloqueado en el servidor, no solo en la pantalla
    bloqueado = client.get("/tickets", headers=h)
    assert bloqueado.status_code == 403 and "cambiar tu contraseña" in bloqueado.json()["detail"]
    assert client.get("/auth/yo", headers=h).status_code == 200

    cambio = "/auth/cambiar-password"
    assert client.post(cambio, json={"password_actual": "otra", "password_nueva": "ClaveNueva9"}, headers=h).status_code == 400
    assert client.post(cambio, json={"password_actual": temporal, "password_nueva": "corta"}, headers=h).status_code == 400
    assert client.post(cambio, json={"password_actual": temporal, "password_nueva": temporal}, headers=h).status_code == 400

    ok = client.post(cambio, json={"password_actual": temporal, "password_nueva": "ClaveNueva9"}, headers=h)
    assert ok.status_code == 200 and ok.json()["cliente"]["debe_cambiar_password"] is False
    assert client.get("/tickets", headers=_bearer(ok)).status_code == 200  # el token nuevo ya sirve
    assert client.get("/auth/yo", headers=h).status_code == 401  # el anterior se cerró
    assert client.post("/auth/login", json={"email": "ana@ejemplo.com", "password": temporal}).status_code == 401
    assert client.post("/auth/login", json={"email": "ana@ejemplo.com", "password": "ClaveNueva9"}).status_code == 200


def test_cualquier_usuario_puede_cambiar_su_contrasena_voluntariamente(client, crear_cuenta, entrar):
    crear_cuenta("ana@ejemplo.com")
    h = entrar("ana@ejemplo.com")
    r = client.post("/auth/cambiar-password", json={"password_actual": PASSWORD, "password_nueva": "OtraClave99"}, headers=h)
    assert r.status_code == 200
    assert client.post("/auth/login", json={"email": "ana@ejemplo.com", "password": "OtraClave99"}).status_code == 200


def test_admin_restablece_contrasena_enviando_enlace_solo_a_la_persona(client, crear_cuenta, entrar, correos):
    admin = crear_cuenta("adm@ejemplo.com", "administrador")
    usuario = crear_cuenta("ana@ejemplo.com")
    ha, h_ana = entrar("adm@ejemplo.com"), entrar("ana@ejemplo.com")

    r = client.post(f"/admin/usuarios/{usuario.id}/restablecer-password", headers=ha)
    assert r.status_code == 200
    assert "password_temporal" not in r.json() and r.json()["envio"] == "archivo"
    assert "correos_enviados" in r.json()["mensaje"]  # avisa que el correo no salió por SMTP
    texto = list(correos.glob("*ana_ejemplo.com.txt"))[0].read_text(encoding="utf-8")
    assert texto.startswith("Para: ana@ejemplo.com") and "24 horas" in texto

    token = token_del_ultimo_correo(correos)
    assert client.post("/auth/establecer-password", json={"token": token, "password": "ClaveElegida7"}).status_code == 200
    assert client.get("/tickets", headers=h_ana).status_code == 401  # al cambiarla se cierran sus sesiones
    assert client.post("/auth/login", json={"email": "ana@ejemplo.com", "password": "ClaveElegida7"}).status_code == 200

    assert client.post(f"/admin/usuarios/{admin.id}/restablecer-password", headers=ha).status_code == 400
    assert client.post(f"/admin/usuarios/{usuario.id}/restablecer-password", headers=entrar("ana@ejemplo.com", "ClaveElegida7")).status_code == 403


def test_restablecer_a_cuenta_sin_activar_reenvia_la_activacion(client, crear_cuenta, entrar, correos):
    crear_cuenta("adm@ejemplo.com", "administrador")
    nueva = crear_cuenta("nueva@ejemplo.com", password=None)
    r = client.post(f"/admin/usuarios/{nueva.id}/restablecer-password", headers=entrar("adm@ejemplo.com"))
    assert r.status_code == 200
    assert "Activa tu cuenta" in list(correos.glob("*nueva_ejemplo.com.txt"))[0].read_text(encoding="utf-8")


def test_demasiados_intentos_fallidos_bloquean_el_correo(client, crear_cuenta):
    crear_cuenta("ana@ejemplo.com")
    for _ in range(5):
        assert client.post("/auth/login", json={"email": "ana@ejemplo.com", "password": "mala-clave-1"}).status_code == 401
    # ni con la clave correcta: hay que esperar
    bloqueado = client.post("/auth/login", json={"email": "ANA@ejemplo.com", "password": PASSWORD})
    assert bloqueado.status_code == 429
    # otro correo no se ve afectado
    crear_cuenta("beto@ejemplo.com")
    assert client.post("/auth/login", json={"email": "beto@ejemplo.com", "password": PASSWORD}).status_code == 200


def test_la_api_manda_cabeceras_de_seguridad_y_no_expone_docs(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_la_base_antigua_recibe_la_columna_nueva_sin_perder_datos():
    from sqlalchemy import create_engine as crear_motor

    from app.database import _agregar_columnas_nuevas

    motor = crear_motor("sqlite://")
    with motor.begin() as c:
        c.exec_driver_sql("CREATE TABLE cliente (id INTEGER PRIMARY KEY, nombre TEXT)")
        c.exec_driver_sql("INSERT INTO cliente (id, nombre) VALUES (1, 'Ana')")
    _agregar_columnas_nuevas(motor)
    _agregar_columnas_nuevas(motor)  # repetirlo no debe fallar
    with motor.begin() as c:
        fila = c.exec_driver_sql("SELECT nombre, debe_cambiar_password FROM cliente").one()
    assert tuple(fila) == ("Ana", 0)


def test_admin_no_puede_crear_correo_duplicado_ni_area_inactiva(client, crear_cuenta, entrar, session):
    admin = crear_cuenta("adm@ejemplo.com", "administrador")
    h = entrar("adm@ejemplo.com")
    base = {"nombre": "Otro", "area_id": admin.area_id, "rol": "usuario"}
    assert client.post("/admin/usuarios", json={**base, "email": "adm@ejemplo.com"}, headers=h).status_code == 400
    assert client.post("/admin/usuarios", json={**base, "email": "no-es-correo"}, headers=h).status_code == 400
    assert client.post("/admin/usuarios", json={**base, "email": "x@ejemplo.com", "area_id": 999}, headers=h).status_code == 400
    assert client.post("/admin/usuarios", json={**base, "email": "x@ejemplo.com", "rol": "root"}, headers=h).status_code == 400


# ---------- olvidé mi contraseña ----------

def test_olvide_password_responde_igual_exista_o_no_el_correo(client, crear_cuenta, correos):
    crear_cuenta("ana@ejemplo.com")
    existe = client.post("/auth/olvide-password", json={"email": "ana@ejemplo.com"})
    no_existe = client.post("/auth/olvide-password", json={"email": "fantasma@ejemplo.com"})
    assert existe.status_code == no_existe.status_code == 200
    assert existe.json() == no_existe.json()
    assert len(list(correos.glob("*.txt"))) == 1  # solo se envió correo a la cuenta real


def test_recuperar_password_cambia_la_clave_y_cierra_sesiones_anteriores(
    client, crear_cuenta, entrar, correos
):
    crear_cuenta("ana@ejemplo.com")
    h_viejo = entrar("ana@ejemplo.com")
    client.post("/auth/olvide-password", json={"email": "ana@ejemplo.com"})
    token = token_del_ultimo_correo(correos)

    assert client.post("/auth/establecer-password", json={"token": token, "password": "Nueva12345"}).status_code == 200
    assert client.post("/auth/login", json={"email": "ana@ejemplo.com", "password": PASSWORD}).status_code == 401
    assert client.post("/auth/login", json={"email": "ana@ejemplo.com", "password": "Nueva12345"}).status_code == 200
    assert client.get("/auth/yo", headers=h_viejo).status_code == 401  # la sesión anterior ya no sirve


def test_password_debil_se_rechaza_sin_consumir_el_enlace(client, crear_cuenta, correos):
    crear_cuenta("ana@ejemplo.com")
    client.post("/auth/olvide-password", json={"email": "ana@ejemplo.com"})
    token = token_del_ultimo_correo(correos)
    assert client.post("/auth/establecer-password", json={"token": token, "password": "corta1"}).status_code == 400
    assert client.post("/auth/establecer-password", json={"token": token, "password": "sololetrasaqui"}).status_code == 400
    assert client.post("/auth/establecer-password", json={"token": token, "password": "Valida12345"}).status_code == 200


def test_limite_de_solicitudes_de_recuperacion_por_hora(client, crear_cuenta, correos):
    crear_cuenta("ana@ejemplo.com")
    for _ in range(6):
        assert client.post("/auth/olvide-password", json={"email": "ana@ejemplo.com"}).status_code == 200
    assert len(list(correos.glob("*.txt"))) == 3


def test_enlace_inventado_no_sirve(client):
    r = client.post("/auth/establecer-password", json={"token": "inventado", "password": PASSWORD})
    assert r.status_code == 400


# ---------- gestión de usuarios: salvaguardas ----------

def test_admin_no_puede_quitarse_el_rol_ni_desactivarse(client, crear_cuenta, entrar):
    admin = crear_cuenta("adm@ejemplo.com", "administrador")
    h = entrar("adm@ejemplo.com")
    assert client.patch(f"/admin/usuarios/{admin.id}", json={"rol": "usuario"}, headers=h).status_code == 400
    assert client.patch(f"/admin/usuarios/{admin.id}", json={"activo": False}, headers=h).status_code == 400
    assert client.patch(f"/admin/usuarios/{admin.id}", json={"nombre": "Nuevo Nombre"}, headers=h).status_code == 200


def test_desactivar_o_cambiar_rol_cierra_la_sesion_de_ese_usuario(client, crear_cuenta, entrar):
    crear_cuenta("adm@ejemplo.com", "administrador")
    usuario = crear_cuenta("usr@ejemplo.com", "usuario")
    ha = entrar("adm@ejemplo.com")

    h_usr = entrar("usr@ejemplo.com")
    assert client.patch(f"/admin/usuarios/{usuario.id}", json={"rol": "tecnico"}, headers=ha).status_code == 200
    assert client.get("/auth/yo", headers=h_usr).status_code == 401
    h_usr = entrar("usr@ejemplo.com")
    assert client.get("/clientes", headers=h_usr).status_code == 200  # ya con permisos de técnico

    assert client.patch(f"/admin/usuarios/{usuario.id}", json={"activo": False}, headers=ha).status_code == 200
    assert client.get("/auth/yo", headers=h_usr).status_code == 401
    assert client.post("/auth/login", json={"email": "usr@ejemplo.com", "password": PASSWORD}).status_code == 403


def test_areas_no_se_duplican_ignorando_tildes_y_mayusculas(client, crear_cuenta, entrar):
    crear_cuenta("adm@ejemplo.com", "administrador")
    h = entrar("adm@ejemplo.com")
    assert client.post("/admin/areas", json={"nombre": "Administración"}, headers=h).status_code == 200
    assert client.post("/admin/areas", json={"nombre": "  ADMINISTRACION "}, headers=h).status_code == 400


# ---------- tickets: visibilidad, asignación e historial ----------

def _crear_ticket(client, headers, texto="no puedo imprimir desde mi laptop"):
    r = client.post("/tickets", json={"texto": texto}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_usuario_ve_solo_sus_tickets_y_el_personal_ve_todos(client, crear_cuenta, entrar):
    crear_cuenta("a@ejemplo.com", "usuario")
    crear_cuenta("b@ejemplo.com", "usuario")
    crear_cuenta("t@ejemplo.com", "tecnico")
    crear_cuenta("adm@ejemplo.com", "administrador")
    ticket_a = _crear_ticket(client, entrar("a@ejemplo.com"))
    _crear_ticket(client, entrar("b@ejemplo.com"))

    assert len(client.get("/tickets", headers=entrar("a@ejemplo.com")).json()) == 1
    assert len(client.get("/tickets", headers=entrar("t@ejemplo.com")).json()) == 2
    assert len(client.get("/tickets", headers=entrar("adm@ejemplo.com")).json()) == 2
    assert client.get(f"/tickets/{ticket_a['id']}", headers=entrar("b@ejemplo.com")).status_code == 403


def test_tomar_y_resolver_asigna_tecnico_y_deja_historial(client, crear_cuenta, entrar, session):
    crear_cuenta("a@ejemplo.com", "usuario")
    tecnico = crear_cuenta("t@ejemplo.com", "tecnico", nombre="Tec")
    ticket = _crear_ticket(client, entrar("a@ejemplo.com"))
    ht = entrar("t@ejemplo.com")

    tomado = client.patch(f"/tickets/{ticket['id']}", json={"estado": "en_proceso"}, headers=ht).json()
    assert tomado["estado"] == "en_proceso" and tomado["tecnico_id"] == tecnico.id

    resuelto = client.patch(
        f"/tickets/{ticket['id']}", json={"estado": "resuelto", "resuelto_por": "tecnico"}, headers=ht
    ).json()
    assert resuelto["estado"] == "resuelto" and resuelto["cerrado_en"] is not None

    mios = client.get("/tickets", params={"tecnico_id": tecnico.id}, headers=ht).json()
    assert [t["id"] for t in mios] == [ticket["id"]]

    historial = client.get(f"/tickets/{ticket['id']}/historial", headers=entrar("a@ejemplo.com")).json()
    pasos = [(h["estado_anterior"], h["estado_nuevo"]) for h in historial]
    assert pasos == [(None, "abierto"), ("abierto", "en_proceso"), ("en_proceso", "resuelto")]
    assert historial[1]["cambiado_por"] == "Tec"
    assert len(session.exec(select(HistorialEstadoTicket)).all()) == 3


def test_el_administrador_tambien_puede_tomar_y_resolver(client, crear_cuenta, entrar):
    crear_cuenta("a@ejemplo.com", "usuario")
    admin = crear_cuenta("adm@ejemplo.com", "administrador")
    ticket = _crear_ticket(client, entrar("a@ejemplo.com"))
    r = client.patch(
        f"/tickets/{ticket['id']}", json={"estado": "resuelto", "resuelto_por": "tecnico"},
        headers=entrar("adm@ejemplo.com"),
    )
    assert r.status_code == 200 and r.json()["tecnico_id"] == admin.id


def test_estado_invalido_se_rechaza(client, crear_cuenta, entrar):
    crear_cuenta("a@ejemplo.com", "usuario")
    crear_cuenta("t@ejemplo.com", "tecnico")
    ticket = _crear_ticket(client, entrar("a@ejemplo.com"))
    r = client.patch(f"/tickets/{ticket['id']}", json={"estado": "cerrado"}, headers=entrar("t@ejemplo.com"))
    assert r.status_code == 400


# ---------- reportes ----------

def test_reporte_del_usuario_solo_cuenta_sus_tickets(client, crear_cuenta, entrar):
    crear_cuenta("a@ejemplo.com", "usuario")
    crear_cuenta("b@ejemplo.com", "usuario")
    crear_cuenta("t@ejemplo.com", "tecnico")
    ticket = _crear_ticket(client, entrar("a@ejemplo.com"))
    _crear_ticket(client, entrar("b@ejemplo.com"))
    client.patch(f"/tickets/{ticket['id']}", json={"estado": "resuelto", "resuelto_por": "tecnico"},
                 headers=entrar("t@ejemplo.com"))

    propio = client.get("/reportes/resumen", headers=entrar("a@ejemplo.com")).json()
    global_ = client.get("/reportes/resumen", headers=entrar("t@ejemplo.com")).json()
    assert propio["total"] == 1 and propio["resueltos"] == 1
    assert global_["total"] == 2 and global_["abiertos"] == 1
    assert global_["pct_resolucion_autonoma"] == 0.0 and global_["tiempo_medio_resolucion_horas"] is not None


def test_admin_elimina_cuenta_sin_actividad_y_sus_enlaces(client, crear_cuenta, entrar, session):
    from app.models import Cliente, TokenAcceso
    from app.services import tokens_acceso

    admin = crear_cuenta("adm@ejemplo.com", "administrador")
    h = entrar("adm@ejemplo.com")
    creado = client.post(
        "/admin/usuarios",
        json={"nombre": "Nueva", "email": "nueva@ejemplo.com", "area_id": admin.area_id, "rol": "usuario"},
        headers=h,
    ).json()["usuario"]
    # la persona pidió un enlace de recuperación antes de que la eliminaran
    tokens_acceso.generar(session, session.get(Cliente, creado["id"]), "recuperacion", 30)
    assert session.exec(select(TokenAcceso).where(TokenAcceso.cliente_id == creado["id"])).first()

    r = client.delete(f"/admin/usuarios/{creado['id']}", headers=h)
    assert r.status_code == 200
    assert session.get(Cliente, creado["id"]) is None
    assert session.exec(select(TokenAcceso).where(TokenAcceso.cliente_id == creado["id"])).first() is None
    assert client.delete(f"/admin/usuarios/{creado['id']}", headers=h).status_code == 404


def test_no_se_elimina_a_si_mismo_ni_a_quien_tiene_actividad(client, crear_cuenta, entrar):
    admin = crear_cuenta("adm@ejemplo.com", "administrador")
    usuario = crear_cuenta("usr@ejemplo.com", "usuario")
    tecnico = crear_cuenta("tec@ejemplo.com", "tecnico")
    ha = entrar("adm@ejemplo.com")
    ticket = _crear_ticket(client, entrar("usr@ejemplo.com"))
    client.patch(f"/tickets/{ticket['id']}", json={"estado": "en_proceso"}, headers=entrar("tec@ejemplo.com"))

    assert client.delete(f"/admin/usuarios/{admin.id}", headers=ha).status_code == 400
    # el usuario tiene un ticket; el técnico lo tomó y cambió su estado
    assert client.delete(f"/admin/usuarios/{usuario.id}", headers=ha).status_code == 409
    assert client.delete(f"/admin/usuarios/{tecnico.id}", headers=ha).status_code == 409
    assert client.get("/admin/usuarios", headers=ha).status_code == 200


def test_solo_el_administrador_puede_eliminar_usuarios(client, crear_cuenta, entrar):
    crear_cuenta("tec@ejemplo.com", "tecnico")
    victima = crear_cuenta("usr@ejemplo.com", "usuario")
    assert client.delete(f"/admin/usuarios/{victima.id}", headers=entrar("tec@ejemplo.com")).status_code == 403
    assert client.delete(f"/admin/usuarios/{victima.id}", headers=entrar("usr@ejemplo.com")).status_code == 403


CSV_HISTORICO = (
    '"ID","Seleccione una opción para la respectiva atención.","Categoría","Prioridad",'
    '"Creado","Solicitante","Estado","Fecha Solución"\n'
    '"1","Incidencia o problema técnico","Internet","Alta","03/09/2026 14:29","Alguien Real","Completado","05/09/2026"\n'
    '"2","Solicitud de servicio","","","04/09/2026 09:22","Otra Persona","En Curso",""\n'
    '"3","Incidencia o problema técnico","SAP","Normal","fecha-rota","Alguien","Nuevo",""\n'
)


def test_importar_historico_es_repetible_y_no_duplica(session, tmp_path):
    from app.models import TicketHistorico
    from app.services.historico import importar_csv

    csv = tmp_path / "export.csv"
    csv.write_text(CSV_HISTORICO, encoding="utf-8-sig")

    primero = importar_csv(csv, session)
    assert (primero["nuevos"], primero["actualizados"], primero["omitidos"]) == (2, 0, 1)

    # el mes siguiente: el ticket 2 ya se completó y llega el 4 nuevo
    csv.write_text(
        CSV_HISTORICO.replace('"En Curso",""', '"Completado","06/09/2026"')
        + '"4","Solicitud de servicio","Office","Baja","10/09/2026 08:00","X","Nuevo",""\n',
        encoding="utf-8-sig",
    )
    segundo = importar_csv(csv, session)
    assert (segundo["nuevos"], segundo["actualizados"], segundo["omitidos"]) == (1, 1, 1)
    assert segundo["total_en_base"] == 3

    filas = session.exec(select(TicketHistorico)).all()
    assert {f.estado for f in filas} == {"Completado", "Nuevo"}


def test_importar_historico_rechaza_csv_sin_columnas(session, tmp_path):
    import pytest as _pytest

    from app.services.historico import importar_csv

    csv = tmp_path / "malo.csv"
    csv.write_text('"A","B"\n"1","2"\n', encoding="utf-8")
    with _pytest.raises(ValueError):
        importar_csv(csv, session)


def test_reporte_historico_solo_para_el_administrador_y_calcula_indicadores(
    client, crear_cuenta, entrar, session, tmp_path
):
    from app.services.historico import importar_csv

    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    crear_cuenta("adm@ejemplo.com", "administrador")
    csv = tmp_path / "export.csv"
    csv.write_text(CSV_HISTORICO, encoding="utf-8-sig")
    importar_csv(csv, session)

    assert client.get("/reportes/historico", headers=entrar("usr@ejemplo.com")).status_code == 403
    assert client.get("/reportes/historico", headers=entrar("tec@ejemplo.com")).status_code == 403
    datos = client.get("/reportes/historico", headers=entrar("adm@ejemplo.com")).json()
    assert datos["total"] == 2 and datos["completados"] == 1
    assert datos["dias_medio_resolucion"] == 2.0  # del 03/09 al 05/09
    assert datos["por_mes"] == [{"etiqueta": "2026-09", "total": 2}]
    assert {c["etiqueta"] for c in datos["por_categoria"]} == {"Internet", "Sin categoría"}


CSV_SUCIO = (
    '"ID","Seleccione una opción para la respectiva atención.","Categoría","Prioridad",'
    '"Creado","Solicitante","Estado","Fecha Solución"\n'
    '" 10 ","Incidencia","internet","critica","03/09/2026 14:29","A","completado","05/09/2026"\n'
    '"11","Incidencia","  Internet ","  Alta  ","04/09/2026 09:22","B","En  Curso","01/09/2026"\n'
    '"12","Incidencia","SAP","Normal","04/09/2026 09:22","C","Nuevo",""\n'
    '"12","Incidencia","SAP","Baja","04/09/2026 09:22","C","Nuevo",""\n'
    '"","Incidencia","SAP","Normal","04/09/2026 09:22","D","Nuevo",""\n'
    '"13","Incidencia","SAP","Normal","","E","Nuevo",""\n'
)


def _subir(client, headers, csv, aplicar):
    return client.post(
        f"/admin/historico?aplicar={'true' if aplicar else 'false'}",
        content=csv.encode("utf-8"),
        headers={**headers, "Content-Type": "text/csv"},
    )


def test_limpieza_unifica_valores_descarta_filas_malas_y_no_escribe_en_vista_previa(
    client, crear_cuenta, entrar, session
):
    from app.models import TicketHistorico

    crear_cuenta("adm@ejemplo.com", "administrador")
    h = entrar("adm@ejemplo.com")

    previa = _subir(client, h, CSV_SUCIO, aplicar=False).json()
    assert previa["aplicado"] is False
    assert (previa["nuevos"], previa["omitidos"], previa["duplicados_en_archivo"]) == (3, 2, 1)
    assert previa["fechas_solucion_descartadas"] == 1  # el 11 se "resolvió" antes de crearse
    assert session.exec(select(TicketHistorico)).all() == []  # la vista previa no guarda nada

    real = _subir(client, h, CSV_SUCIO, aplicar=True).json()
    assert real["aplicado"] is True and real["total_en_base"] == 3
    filas = {t.id_externo: t for t in session.exec(select(TicketHistorico)).all()}
    assert filas["10"].estado == "Completado" and filas["10"].prioridad == "Crítica"
    assert filas["11"].estado == "En Curso" and filas["11"].resuelto_en is None
    assert filas["10"].categoria == filas["11"].categoria == "Internet"  # misma categoría, una escritura
    assert filas["12"].prioridad == "Baja"  # gana la última fila repetida

    otra_vez = _subir(client, h, CSV_SUCIO, aplicar=True).json()
    assert (otra_vez["nuevos"], otra_vez["actualizados"], otra_vez["sin_cambios"]) == (0, 0, 3)


def test_subida_de_csv_solo_admin_y_rechaza_archivos_invalidos(client, crear_cuenta, entrar):
    crear_cuenta("tec@ejemplo.com", "tecnico")
    crear_cuenta("adm@ejemplo.com", "administrador")
    assert _subir(client, entrar("tec@ejemplo.com"), CSV_SUCIO, aplicar=False).status_code == 403
    h = entrar("adm@ejemplo.com")
    assert _subir(client, h, "", aplicar=False).status_code == 400
    assert _subir(client, h, '"A","B"\n"1","2"\n', aplicar=False).status_code == 400


# Un mensaje que Minutito no resuelve con respuesta directa ni con una ficha de pasos: llega al
# modelo (lo que estas pruebas simulan). Con «no tengo internet» respondería la ficha de internet.
MENSAJE_PARA_EL_MODELO = "no me carga el sistema de facturación"


class _RespuestaFalsa:
    def __init__(self, contenido):
        self.message = type("M", (), {"content": contenido})()


def _chat_con(monkeypatch, resultado):
    from app.services import assistant

    def falso(*args, **kwargs):
        if isinstance(resultado, Exception):
            raise resultado
        return _RespuestaFalsa(resultado)

    monkeypatch.setattr(assistant._cliente, "chat", falso)


def test_chat_con_ollama_caido_responde_503_y_deja_el_ticket_intacto(
    client, crear_cuenta, entrar, session, monkeypatch
):
    import httpx
    import ollama
    from app.models import InteraccionMinutito

    crear_cuenta("usr@ejemplo.com", "usuario")
    h = entrar("usr@ejemplo.com")
    ticket = _crear_ticket(client, h)

    for falla in (
        ConnectionError("Failed to connect to Ollama"),  # apagado
        httpx.ReadTimeout("sin respuesta"),  # colgado
        ollama.ResponseError("model not found", 404),  # modelo no instalado
    ):
        _chat_con(monkeypatch, falla)
        r = client.post(f"/tickets/{ticket['id']}/chat", json={"mensaje": MENSAJE_PARA_EL_MODELO}, headers=h)
        assert r.status_code == 503, falla
        assert "un técnico lo atenderá" in r.json()["detail"]

    assert client.get(f"/tickets/{ticket['id']}", headers=h).json()["estado"] == "abierto"
    assert session.exec(select(InteraccionMinutito)).all() == []  # no se guardó nada a medias


def test_chat_con_respuesta_vacia_se_trata_como_no_disponible(client, crear_cuenta, entrar, monkeypatch):
    crear_cuenta("usr@ejemplo.com", "usuario")
    h = entrar("usr@ejemplo.com")
    ticket = _crear_ticket(client, h)
    _chat_con(monkeypatch, "   ")
    r = client.post(f"/tickets/{ticket['id']}/chat", json={"mensaje": MENSAJE_PARA_EL_MODELO}, headers=h)
    assert r.status_code == 503


def test_chat_normal_sigue_funcionando(client, crear_cuenta, entrar, monkeypatch):
    crear_cuenta("usr@ejemplo.com", "usuario")
    h = entrar("usr@ejemplo.com")
    ticket = _crear_ticket(client, h)
    _chat_con(monkeypatch, "Prueba reiniciar el equipo y volver a conectarte.")
    r = client.post(f"/tickets/{ticket['id']}/chat", json={"mensaje": MENSAJE_PARA_EL_MODELO}, headers=h)
    assert r.status_code == 200 and "reiniciar" in r.json()["respuesta"]


def test_agrupar_clases_raras_conserva_los_tickets_en_otros():
    import pandas as pd

    from app.ml.train_classifier import agrupar_clases_raras

    y = pd.Series(["SAP"] * 6 + ["Rara"] * 2 + ["Otra"] * 1)
    r = agrupar_clases_raras(y)
    assert len(r) == 9 and set(r) == {"SAP", "Otros"} and (r == "Otros").sum() == 3


def test_evaluacion_cv_calcula_precision_y_umbral_con_datos_separables():
    import pandas as pd

    from app.ml.train_classifier import evaluar_cv

    textos = pd.Series(
        ["error sap factura cierre contable"] * 20
        + ["salesforce oportunidad cliente cuenta lead"] * 20
        + ["impresora toner atasco papel"] * 20
    )
    y = pd.Series(["SAP"] * 20 + ["Salesforce"] * 20 + ["Impresora"] * 20)
    metricas, reporte = evaluar_cv("Prueba", textos, y)
    assert metricas["accuracy"] > 0.95 and metricas["clases"] == 3
    assert metricas["umbral"] is not None and metricas["precision_en_umbral"] >= 0.8
    assert "Precisión global" in reporte


def test_clasificar_ticket_devuelve_la_confianza_de_la_categoria():
    from app.services.classifier import clasificar_ticket

    r = clasificar_ticket("No puedo imprimir, la impresora del piso 2 no responde")
    assert 0 < r["confianza"] <= 1 and 0 < r["confianza_tipo"] <= 1
    assert r["categoria"] and r["tipo"]


def test_metricas_del_clasificador_solo_para_el_administrador(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    crear_cuenta("adm@ejemplo.com", "administrador")
    assert client.get("/reportes/clasificador", headers=entrar("usr@ejemplo.com")).status_code == 403
    assert client.get("/reportes/clasificador", headers=entrar("tec@ejemplo.com")).status_code == 403
    r = client.get("/reportes/clasificador", headers=entrar("adm@ejemplo.com"))
    assert r.status_code == 200 and "disponible" in r.json()


def test_el_tecnico_solo_recibe_el_umbral_de_confianza_no_las_metricas(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    assert client.get("/reportes/clasificador/umbral", headers=entrar("usr@ejemplo.com")).status_code == 403
    r = client.get("/reportes/clasificador/umbral", headers=entrar("tec@ejemplo.com"))
    assert r.status_code == 200 and list(r.json()) == ["umbral"]  # nada de precisión, F1 ni tamaños


def test_la_confianza_media_del_clasificador_solo_la_ve_el_administrador(client, crear_cuenta, entrar):
    for correo, rol in (("usr@ejemplo.com", "usuario"), ("tec@ejemplo.com", "tecnico"), ("adm@ejemplo.com", "administrador")):
        crear_cuenta(correo, rol)
    _crear_ticket(client, entrar("usr@ejemplo.com"))
    veo = {c: client.get("/reportes/resumen", headers=entrar(c)).json()["confianza_media"]
           for c in ("usr@ejemplo.com", "tec@ejemplo.com", "adm@ejemplo.com")}
    assert veo["usr@ejemplo.com"] is None and veo["tec@ejemplo.com"] is None
    assert veo["adm@ejemplo.com"] is not None


# ---------- el usuario confirma si Minutito resolvió ----------

def _ticket_con_chat(client, entrar, monkeypatch, texto_minutito="Prueba reiniciar el equipo."):
    h = entrar("usr@ejemplo.com")
    ticket = _crear_ticket(client, h)
    _chat_con(monkeypatch, texto_minutito)
    r = client.post(f"/tickets/{ticket['id']}/chat", json={"mensaje": MENSAJE_PARA_EL_MODELO}, headers=h)
    assert r.status_code == 200, r.text
    return ticket, h, r.json()


def test_el_chat_no_cierra_el_ticket_solo_pide_confirmacion(client, crear_cuenta, entrar, monkeypatch):
    crear_cuenta("usr@ejemplo.com", "usuario")
    ticket, h, chat = _ticket_con_chat(client, entrar, monkeypatch)
    assert chat["escalado"] is False and chat["requiere_confirmacion"] is True
    assert chat["estado_ticket"] == "abierto"
    assert client.get(f"/tickets/{ticket['id']}", headers=h).json()["resuelto_por"] is None


def test_si_minutito_deriva_el_caso_no_pide_confirmacion(client, crear_cuenta, entrar, monkeypatch):
    crear_cuenta("usr@ejemplo.com", "usuario")
    _, _, chat = _ticket_con_chat(client, entrar, monkeypatch, "Voy a escalar tu caso a un técnico.")
    assert chat["escalado"] is True and chat["requiere_confirmacion"] is False


def test_confirmar_resuelto_cierra_el_ticket_una_sola_vez_y_da_puntos(
    client, crear_cuenta, entrar, session, monkeypatch
):
    from app.models import Cliente, EventoGamificacion, HistorialEstadoTicket, InteraccionMinutito

    usuario = crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    ticket, h, _ = _ticket_con_chat(client, entrar, monkeypatch)

    r = client.post(f"/tickets/{ticket['id']}/confirmar-resolucion", json={"resuelto": True}, headers=h)
    assert r.status_code == 200 and r.json()["estado_ticket"] == "resuelto"
    t = client.get(f"/tickets/{ticket['id']}", headers=h).json()
    assert t["estado"] == "resuelto" and t["resuelto_por"] == "minutito" and t["cerrado_en"]

    session.expire_all()
    assert session.get(Cliente, usuario.id).puntos == 10
    assert session.exec(select(InteraccionMinutito)).one().marco_resuelto is True
    cambio = session.exec(select(HistorialEstadoTicket).where(HistorialEstadoTicket.estado_nuevo == "resuelto")).one()
    assert cambio.cambiado_por_id is None  # lo cerró Minutito con la confirmación del usuario

    # confirmar de nuevo no duplica puntos; el chat ya no admite mensajes
    assert client.post(f"/tickets/{ticket['id']}/confirmar-resolucion", json={"resuelto": True}, headers=h).status_code == 200
    session.expire_all()
    assert session.get(Cliente, usuario.id).puntos == 10
    assert len(session.exec(select(EventoGamificacion)).all()) == 1
    assert client.post(f"/tickets/{ticket['id']}/chat", json={"mensaje": "hola"}, headers=h).status_code == 409

    resumen = client.get("/reportes/resumen", headers=entrar("tec@ejemplo.com")).json()
    assert resumen["resueltos_por_minutito"] == 1 and resumen["pct_resolucion_autonoma"] == 100.0


def test_sin_confirmacion_el_indicador_de_resolucion_autonoma_no_sube(
    client, crear_cuenta, entrar, monkeypatch
):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    _ticket_con_chat(client, entrar, monkeypatch)  # Minutito respondió, nadie confirmó
    resumen = client.get("/reportes/resumen", headers=entrar("tec@ejemplo.com")).json()
    assert resumen["total"] == 1 and resumen["resueltos_por_minutito"] == 0
    assert resumen["pct_resolucion_autonoma"] == 0.0


def test_si_no_se_resolvio_el_ticket_queda_abierto_para_el_tecnico(
    client, crear_cuenta, entrar, session, monkeypatch
):
    from app.models import Cliente

    usuario = crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    ticket, h, _ = _ticket_con_chat(client, entrar, monkeypatch)

    r = client.post(f"/tickets/{ticket['id']}/confirmar-resolucion", json={"resuelto": False}, headers=h)
    assert r.status_code == 200 and r.json()["estado_ticket"] == "abierto"
    assert "técnico" in r.json()["mensaje"]

    ht = entrar("tec@ejemplo.com")
    client.patch(f"/tickets/{ticket['id']}", json={"estado": "resuelto", "resuelto_por": "tecnico"}, headers=ht)
    session.expire_all()
    assert session.get(Cliente, usuario.id).puntos == 3  # intentó el autoservicio antes de escalar
    assert client.get(f"/tickets/{ticket['id']}", headers=h).json()["resuelto_por"] == "tecnico"


def test_confirmar_resolucion_valida_dueno_conversacion_y_estado(client, crear_cuenta, entrar, monkeypatch):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("otro@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h = entrar("usr@ejemplo.com")
    ticket = _crear_ticket(client, h)
    url = f"/tickets/{ticket['id']}/confirmar-resolucion"

    # sin haber hablado con Minutito no hay nada que confirmar
    assert client.post(url, json={"resuelto": True}, headers=h).status_code == 400
    _chat_con(monkeypatch, "Prueba reiniciar.")
    client.post(f"/tickets/{ticket['id']}/chat", json={"mensaje": MENSAJE_PARA_EL_MODELO}, headers=h)

    assert client.post(url, json={"resuelto": True}, headers=entrar("otro@ejemplo.com")).status_code == 403
    assert client.post(url, json={"resuelto": True}, headers=entrar("tec@ejemplo.com")).status_code == 403
    # si un técnico ya tomó el ticket, no se le acredita a Minutito
    client.patch(f"/tickets/{ticket['id']}", json={"estado": "en_proceso"}, headers=entrar("tec@ejemplo.com"))
    assert client.post(url, json={"resuelto": True}, headers=h).status_code == 409


def test_resumen_incluye_tendencia_diaria_y_tickets_con_minutito(client, crear_cuenta, entrar, monkeypatch):
    from datetime import date

    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    h = entrar("usr@ejemplo.com")
    con = _crear_ticket(client, h)
    _crear_ticket(client, h)  # este no conversa con Minutito
    _chat_con(monkeypatch, "Prueba reiniciar.")
    client.post(f"/tickets/{con['id']}/chat", json={"mensaje": MENSAJE_PARA_EL_MODELO}, headers=h)

    r = client.get("/reportes/resumen", headers=entrar("tec@ejemplo.com")).json()
    assert r["total"] == 2 and r["con_minutito"] == 1
    assert len(r["ultimos_dias"]) == 14 and r["ultimos_dias"][-1]["etiqueta"] == date.today().isoformat()
    assert r["ultimos_dias"][-1]["total"] == 2 and sum(d["total"] for d in r["ultimos_dias"]) == 2


def test_historico_trae_dias_de_resolucion_por_mes(client, crear_cuenta, entrar, session, tmp_path):
    from app.services.historico import importar_csv

    crear_cuenta("adm@ejemplo.com", "administrador")
    csv = tmp_path / "export.csv"
    csv.write_text(CSV_HISTORICO, encoding="utf-8-sig")
    importar_csv(csv, session)
    datos = client.get("/reportes/historico", headers=entrar("adm@ejemplo.com")).json()
    assert datos["resolucion_por_mes"] == [{"etiqueta": "2026-09", "valor": 2.0}]


# ---------- consulta de los tickets importados (solo lectura, solo administrador) ----------

CSV_CON_DETALLE = (
    '"ID","Seleccione una opción para la respectiva atención.","Categoría","Prioridad","Creado",'
    '"Solicitante","Asignado a","Estado","Descripción","Fecha Solución"\n'
    '"101","Incidencia","Internet","Alta","03/09/2026 14:29","Ana Pérez","Luis Mora","Completado",'
    '"<p>No tengo <b>conexión</b> a la red&nbsp;WiFi</p><p>Desde ayer</p>","05/09/2026"\n'
    '"102","Solicitud","SAP","Normal","04/09/2026 09:22","Carla Ruiz","","En Curso","Acceso al módulo de compras",""\n'
    '"103","Solicitud","Salesforce","Baja","05/09/2026 10:00","Pedro Gil","Luis Mora","Nuevo","",""\n'
)


def _importar_detalle(session, tmp_path):
    from app.services.historico import importar_csv

    csv = tmp_path / "detalle.csv"
    csv.write_text(CSV_CON_DETALLE, encoding="utf-8-sig")
    importar_csv(csv, session)


def test_importar_guarda_descripcion_en_texto_plano_solicitante_y_quien_atendio(session, tmp_path):
    from app.models import TicketHistorico

    _importar_detalle(session, tmp_path)
    t = session.exec(select(TicketHistorico).where(TicketHistorico.id_externo == "101")).one()
    assert t.descripcion == "No tengo conexión a la red WiFi\nDesde ayer"  # sin etiquetas, con saltos
    assert t.solicitante == "Ana Pérez" and t.asignado_a == "Luis Mora"
    vacio = session.exec(select(TicketHistorico).where(TicketHistorico.id_externo == "103")).one()
    assert vacio.descripcion is None  # una descripción vacía no se guarda como texto


def test_tickets_importados_solo_los_ve_el_administrador(client, crear_cuenta, entrar, session, tmp_path):
    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    crear_cuenta("adm@ejemplo.com", "administrador")
    _importar_detalle(session, tmp_path)
    for correo in ("usr@ejemplo.com", "tec@ejemplo.com"):
        assert client.get("/historico/tickets", headers=entrar(correo)).status_code == 403
        assert client.get("/historico/tickets/1", headers=entrar(correo)).status_code == 403
    assert client.get("/historico/tickets", headers=entrar("adm@ejemplo.com")).status_code == 200


def test_listado_de_tickets_importados_filtra_busca_ignora_tildes_y_pagina(
    client, crear_cuenta, entrar, session, tmp_path
):
    crear_cuenta("adm@ejemplo.com", "administrador")
    h = entrar("adm@ejemplo.com")
    _importar_detalle(session, tmp_path)

    todo = client.get("/historico/tickets", headers=h).json()
    assert todo["total"] == 3
    assert [t["id_externo"] for t in todo["items"]] == ["103", "102", "101"]  # el más reciente primero
    assert todo["filtros"]["estados"] == ["Completado", "En Curso", "Nuevo"]
    assert "Internet" in todo["filtros"]["categorias"]

    assert client.get("/historico/tickets?estado=Nuevo", headers=h).json()["total"] == 1
    assert client.get("/historico/tickets?categoria=SAP&prioridad=Normal", headers=h).json()["total"] == 1
    # la búsqueda no distingue mayúsculas ni tildes, y mira descripción, solicitante y quien atendió
    assert client.get("/historico/tickets?q=CONEXION", headers=h).json()["total"] == 1
    assert client.get("/historico/tickets?q=perez", headers=h).json()["total"] == 1
    assert client.get("/historico/tickets?q=luis mora", headers=h).json()["total"] == 2
    assert client.get("/historico/tickets?q=nadie", headers=h).json()["total"] == 0

    pagina = client.get("/historico/tickets?por_pagina=2&pagina=2", headers=h).json()
    assert pagina["total"] == 3 and [t["id_externo"] for t in pagina["items"]] == ["101"]


def test_detalle_de_ticket_importado_trae_la_descripcion_completa(client, crear_cuenta, entrar, session, tmp_path):
    from app.models import TicketHistorico

    crear_cuenta("adm@ejemplo.com", "administrador")
    h = entrar("adm@ejemplo.com")
    _importar_detalle(session, tmp_path)
    pk = session.exec(select(TicketHistorico).where(TicketHistorico.id_externo == "101")).one().id

    r = client.get(f"/historico/tickets/{pk}", headers=h).json()
    assert r["descripcion"] == "No tengo conexión a la red WiFi\nDesde ayer" and r["asignado_a"] == "Luis Mora"
    assert client.get("/historico/tickets/9999", headers=h).status_code == 404


def test_los_tickets_importados_no_tocan_los_indicadores_de_la_plataforma(
    client, crear_cuenta, entrar, session, tmp_path
):
    crear_cuenta("adm@ejemplo.com", "administrador")
    _importar_detalle(session, tmp_path)
    resumen = client.get("/reportes/resumen", headers=entrar("adm@ejemplo.com")).json()
    assert resumen["total"] == 0 and resumen["resueltos"] == 0 and resumen["pct_resolucion_autonoma"] == 0.0
    assert client.get("/tickets", headers=entrar("adm@ejemplo.com")).json() == []


# ---------- crear ticket directo, sin pasar por Minutito ----------

def test_ticket_directo_queda_abierto_sin_conversacion_y_el_tecnico_lo_ve(client, crear_cuenta, entrar, session):
    from app.models import InteraccionMinutito

    crear_cuenta("usr@ejemplo.com", "usuario")
    crear_cuenta("tec@ejemplo.com", "tecnico")
    t = _crear_ticket(client, entrar("usr@ejemplo.com"), texto="  La impresora del piso 2 no responde  ")

    assert t["estado"] == "abierto" and t["resuelto_por"] is None
    assert t["texto"] == "La impresora del piso 2 no responde"  # se guarda sin espacios sobrantes
    assert session.exec(select(InteraccionMinutito)).all() == []  # Minutito no intervino

    cola = client.get("/tickets?estado=abierto", headers=entrar("tec@ejemplo.com")).json()
    assert [x["id"] for x in cola] == [t["id"]]
    resumen = client.get("/reportes/resumen", headers=entrar("tec@ejemplo.com")).json()
    assert resumen["total"] == 1 and resumen["con_minutito"] == 0  # cuenta como ticket, no como conversación


def test_ticket_con_texto_vacio_corto_o_enorme_se_rechaza(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com", "usuario")
    h = entrar("usr@ejemplo.com")
    for texto in ("", "   ", "hola"):
        assert client.post("/tickets", json={"texto": texto}, headers=h).status_code == 400, repr(texto)
    r = client.post("/tickets", json={"texto": "x" * 5001}, headers=h)
    assert r.status_code == 400 and "largo" in r.json()["detail"]
    assert client.get("/tickets", headers=h).json() == []  # no quedó ningún ticket a medias

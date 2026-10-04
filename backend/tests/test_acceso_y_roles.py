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


# ---------- altas por el administrador y activación por correo ----------

def test_admin_crea_usuario_y_este_activa_su_cuenta_desde_el_correo(
    client, crear_cuenta, entrar, correos, session
):
    admin = crear_cuenta("adm@ejemplo.com", "administrador")
    r = client.post(
        "/admin/usuarios",
        json={"nombre": "Nuevo Usuario", "email": "Nuevo@Ejemplo.com", "area_id": admin.area_id, "rol": "tecnico"},
        headers=entrar("adm@ejemplo.com"),
    )
    assert r.status_code == 200, r.text
    assert r.json()["correo"] == "archivo"
    assert r.json()["usuario"]["email"] == "nuevo@ejemplo.com"

    token = token_del_ultimo_correo(correos)
    # antes de activar no puede entrar
    assert client.post("/auth/login", json={"email": "nuevo@ejemplo.com", "password": PASSWORD}).status_code == 401

    assert client.post("/auth/establecer-password", json={"token": token, "password": PASSWORD}).status_code == 200
    login = client.post("/auth/login", json={"email": "nuevo@ejemplo.com", "password": PASSWORD})
    assert login.status_code == 200 and login.json()["cliente"]["rol"] == "tecnico"

    # el enlace es de un solo uso
    reuso = client.post("/auth/establecer-password", json={"token": token, "password": "OtraClave99"})
    assert reuso.status_code == 400


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

"""Pruebas de la auditoría de seguridad (noviembre de 2026): cada una reproduce un ataque
y comprueba que el sistema lo frena."""
import base64
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone

import jwt
from sqlmodel import select

from app.models import Seudonimo
from app.services import anonimizar, asignacion, minutito_chat
from app.services.auth import SECRET_KEY


def _b64(datos: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(datos).encode()).rstrip(b"=").decode()


# --- Sesiones (JWT) ---

def test_tokens_falsificados_no_entran(client, crear_cuenta, entrar):
    adm = crear_cuenta("adm@ejemplo.com", "administrador")
    usr = crear_cuenta("usr@ejemplo.com")
    vence = int(time.time()) + 3600
    sin_firma = _b64({"alg": "none", "typ": "JWT"}) + "." + _b64({"sub": str(adm.id), "ver": 0, "exp": vence}) + "."
    otra_clave = jwt.encode({"sub": str(adm.id), "ver": 0, "exp": vence}, "clave-adivinada", algorithm="HS256")
    vencido = jwt.encode(
        {"sub": str(usr.id), "ver": 0, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        SECRET_KEY, algorithm="HS256",
    )
    for token in (sin_firma, otra_clave, vencido):
        r = client.get("/admin/usuarios", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401
    # El rol se lee de la base, no del token: un usuario no se vuelve administrador.
    assert client.get("/admin/usuarios", headers=entrar("usr@ejemplo.com")).status_code == 403


# --- Fuerza bruta ---

def test_rociar_una_contrasena_contra_muchos_correos_se_frena_por_ip(client, crear_cuenta):
    crear_cuenta("real@ejemplo.com")
    for i in range(20):
        r = client.post("/auth/login", json={"email": f"victima{i}@ejemplo.com", "password": "Clave12345"})
        assert r.status_code == 401
    # El origen quedó bloqueado, aunque la contraseña de este correo sea la correcta.
    r = client.post("/auth/login", json={"email": "real@ejemplo.com", "password": "Clave12345"})
    assert r.status_code == 429
    # Otro origen (la IP real que reenvía Cloudflare) no se ve afectado.
    r = client.post(
        "/auth/login", json={"email": "real@ejemplo.com", "password": "Clave12345"},
        headers={"CF-Connecting-IP": "203.0.113.7"},
    )
    assert r.status_code == 200


def test_olvide_password_no_envia_correos_sin_limite_desde_un_origen(client, crear_cuenta, correos):
    for i in range(12):
        crear_cuenta(f"p{i}@ejemplo.com")
    for i in range(12):
        r = client.post("/auth/olvide-password", json={"email": f"p{i}@ejemplo.com"})
        assert r.status_code == 200  # la respuesta no delata el freno
    assert len(list(correos.glob("*.txt"))) == 10


# --- Tamaño de las peticiones ---

def test_un_cuerpo_json_enorme_se_rechaza_sin_procesarlo(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    h = entrar("usr@ejemplo.com")
    r = client.post("/tickets/sugerir", json={"texto": "impresora " * 200_000}, headers=h)
    assert r.status_code == 413
    r = client.post("/auth/login", json={"email": "a@ejemplo.com", "password": "x" * 2_000_000})
    assert r.status_code == 413


def test_los_adjuntos_de_mas_de_1_mb_siguen_funcionando(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    h = entrar("usr@ejemplo.com")
    t = client.post("/tickets", json={"texto": "La impresora del piso 3 no imprime nada"}, headers=h).json()
    r = client.post(
        f"/tickets/{t['id']}/adjuntos", content=b"0" * (3 * 1024 * 1024),
        headers={**h, "X-Nombre-Archivo": "registro.txt"},
    )
    assert r.status_code == 200, r.text


# --- Acceso a datos ajenos y archivos ---

def test_un_usuario_no_alcanza_nada_del_ticket_de_otro(client, crear_cuenta, entrar):
    crear_cuenta("a@ejemplo.com")
    crear_cuenta("b@ejemplo.com")
    ha, hb = entrar("a@ejemplo.com"), entrar("b@ejemplo.com")
    tid = client.post("/tickets", json={"texto": "La impresora del piso 3 no imprime nada"}, headers=hb).json()["id"]
    for ruta in ("", "/historial", "/sla", "/conversacion", "/adjuntos", "/interacciones", "/encuesta"):
        assert client.get(f"/tickets/{tid}{ruta}", headers=ha).status_code == 403, ruta
    assert client.post(f"/tickets/{tid}/mensajes", json={"texto": "hola"}, headers=ha).status_code == 403
    conv = client.post("/minutito/conversaciones", headers=hb).json()["id"]
    r = client.post(
        "/tickets", json={"texto": "No sincroniza el correo en Outlook", "conversacion_id": conv}, headers=ha
    )
    assert r.status_code in (403, 404)  # no se puede «adoptar» la conversación de otro


def test_no_se_aceptan_archivos_que_el_navegador_ejecutaria(client, crear_cuenta, entrar):
    crear_cuenta("usr@ejemplo.com")
    h = entrar("usr@ejemplo.com")
    tid = client.post("/tickets", json={"texto": "La impresora del piso 3 no imprime nada"}, headers=h).json()["id"]
    for nombre in ("x.html", "x.svg", "x.js", "x.exe"):
        r = client.post(f"/tickets/{tid}/adjuntos", content=b"<script>", headers={**h, "X-Nombre-Archivo": nombre})
        assert r.status_code == 400, nombre
    r = client.post(
        f"/tickets/{tid}/adjuntos", content=b"png", headers={**h, "X-Nombre-Archivo": "..%2F..%2Fapp%2Fmain.png"}
    )
    assert r.json()["nombre_original"] == "main.png"


def test_cors_no_acepta_otros_sitios(client):
    r = client.options("/tickets", headers={"Origin": "https://sitio-malicioso.com", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers


# --- Datos personales ---

def test_seudonimos_con_clave_y_paso_de_las_filas_antiguas(session):
    antigua = hashlib.sha256("solicitante:beto ruiz".encode()).hexdigest()
    session.add(Seudonimo(clave=antigua, alias="Solicitante 001"))
    session.commit()
    # Una fila creada con el hash anterior se reconoce: el alias se mantiene.
    assert anonimizar.alias(session, "Beto Ruiz", "solicitante") == "Solicitante 001"
    fila = session.exec(select(Seudonimo)).one()
    assert fila.clave != antigua and fila.clave == anonimizar.clave_de("Beto Ruiz", "solicitante")
    # Quien tenga la lista de empleados no puede recalcular la huella sin la clave.
    assert hashlib.sha256("solicitante:beto ruiz".encode()).hexdigest() != fila.clave
    assert anonimizar.alias(session, "Ana Paz", "solicitante") == "Solicitante 002"


def test_proteger_claves_antiguas_desde_los_nombres_del_csv(session):
    session.add(Seudonimo(clave=anonimizar.clave_antigua("Tito Pérez", "tecnico"), alias="Técnico 01"))
    session.commit()
    assert anonimizar.proteger_claves_antiguas(session, [("Tito Pérez", "tecnico"), ("Nadie", "tecnico")]) == 1
    assert session.exec(select(Seudonimo)).one().clave == anonimizar.clave_de("Tito Pérez", "tecnico")
    assert anonimizar.proteger_claves_antiguas(session, [("Tito Pérez", "tecnico")]) == 0


def test_los_casos_de_referencia_de_minutito_van_sin_datos_personales():
    texto = minutito_chat._casos(
        [("Soy Ana, mi correo es ana.paz@empresa.com y mi cédula 0912345678", "Llamar al 0991234567")]
    )
    assert "ana.paz@empresa.com" not in texto and "0912345678" not in texto and "0991234567" not in texto
    assert "confidenciales" in texto


def test_los_nombres_de_los_tecnicos_se_leen_de_un_archivo_fuera_del_codigo(tmp_path):
    archivo = tmp_path / "tabla.json"
    archivo.write_text(json.dumps({"SAP": ["Persona Uno", "Persona Dos"]}), encoding="utf-8")
    tabla = asignacion.cargar_tabla(archivo)
    assert tabla["SAP"] == ["Persona Uno", "Persona Dos"] and tabla["Otros"] == [asignacion.TODOS]
    ejemplo = asignacion.cargar_tabla(asignacion.ARCHIVO_EJEMPLO)
    assert set(ejemplo) >= {"SAP", "Office", "Otros"}

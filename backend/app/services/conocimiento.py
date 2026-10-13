"""Lo que Minutito sabe resolver sin inventar: fichas de pasos correctos para los
problemas más comunes y respuestas directas para lo que no necesita al modelo.

Por qué existe: con un modelo local pequeño, dejarlo improvisar los pasos da respuestas
genéricas o equivocadas. Con una ficha, la respuesta sale de pasos ya verificados, dichos
con aperturas y cierres variados para que no suene a plantilla. Las fichas se pueden ampliar
sin tocar el resto del código.
"""
import random
import re
from dataclasses import dataclass

from app.ml.train_classifier import quitar_tildes


@dataclass(frozen=True)
class Ficha:
    tema: str
    fuertes: tuple[str, ...]  # palabras (sin tildes ni mayúsculas) que identifican el tema: pesan 3
    debiles: tuple[str, ...]  # pistas que también aparecen en otros temas: pesan 1
    pasos: tuple[str, ...]


FICHAS = [
    Ficha(
        "OneDrive",
        ("onedrive",),
        ("sincroniz", "carpeta en la nube"),
        (
            "Mira el ícono de OneDrive (la nubecita junto al reloj): si tiene una cruz o una alerta, ahí dice el error.",
            "Cierra la sesión de OneDrive y vuelve a iniciarla con tu cuenta de la organización.",
            "Pausa la sincronización y reanúdala desde el mismo ícono.",
            "Reinicia el equipo y revisa que tengas espacio libre en el disco.",
        ),
    ),
    Ficha(
        "contraseña olvidada",
        ("olvide mi contrasena", "olvide la contrasena", "olvide mi clave", "no recuerdo mi contrasena", "no me acuerdo de mi contrasena"),
        (),
        (
            "Usa la opción «¿Olvidaste tu contraseña?» de la pantalla de inicio de sesión para crear una nueva.",
            "Revisa tu correo (y la carpeta de no deseado) o el celular asociado: ahí llega el enlace o el código. Suele vencer en pocos minutos.",
            "Elige una contraseña nueva de al menos 8 caracteres, con letras y números, y entra con ella.",
        ),
    ),
    Ficha(
        "VPN",
        ("vpn",),
        ("trabajo remoto", "desde casa", "conectarme a la red"),
        (
            "Comprueba que tengas internet sin la VPN, por ejemplo abriendo una página web.",
            "Cierra por completo el programa de la VPN y ábrelo otra vez.",
            "Revisa que el usuario y la contraseña estén bien escritos, sin espacios al final.",
            "Reinicia el equipo y vuelve a conectarte.",
        ),
    ),
    Ficha(
        "impresora",
        ("impresora", "imprimir", "imprime", "toner"),
        ("impresion", "atasco", "papel"),
        (
            "Mira que la impresora esté encendida, con papel y sin luces de error ni papel atascado.",
            "Apágala unos 10 segundos y vuelve a encenderla.",
            "Abre la cola de impresión de tu equipo y cancela los trabajos pendientes.",
            "Confirma que sea la impresora predeterminada y prueba con un documento sencillo.",
        ),
    ),
    Ficha(
        "videollamadas (Teams, Zoom)",
        ("teams", "zoom", "videollamada", "microfono", "camara", "auriculares"),
        ("no me escuchan", "no se escucha", "audio"),
        (
            "Revisa en los ajustes de la aplicación que el micrófono o la cámara elegidos sean los correctos.",
            "Comprueba que Windows permita a la aplicación usar el micrófono y la cámara.",
            "Desconecta y vuelve a conectar los auriculares, y prueba con otro puerto.",
            "Cierra la aplicación por completo y ábrela otra vez.",
        ),
    ),
    Ficha(
        "Office (Excel, Word, PowerPoint)",
        ("excel", "word", "powerpoint"),
        ("office", "no abre el archivo", "se cierra solo", "no responde"),
        (
            "Cierra el programa por completo y ábrelo de nuevo.",
            "Copia el archivo al escritorio y ábrelo desde ahí.",
            "Reinicia el equipo.",
            "Si falla con todos los archivos, repara Office desde Configuración > Aplicaciones > Microsoft Office > Modificar > Reparación rápida.",
        ),
    ),
    Ficha(
        "correo (Outlook)",
        ("outlook", "buzon"),
        ("correo", "email", "no me llegan", "no recibo"),
        (
            "Confirma que tengas internet y cierra y abre Outlook.",
            "Revisa la carpeta de correo no deseado.",
            "Si el buzón está lleno, vacía los elementos eliminados y archiva los correos viejos.",
            "Reinicia el equipo y vuelve a abrir Outlook.",
        ),
    ),
    Ficha(
        "internet o Wi-Fi",
        ("internet", "wifi", "wi-fi"),
        ("sin conexion", "no hay red", "red inalambrica", "no navega", "no carga la pagina"),
        (
            "Prueba abrir otra página, o la misma desde otro dispositivo, para saber si falla solo tu equipo.",
            "Apaga y vuelve a encender el Wi-Fi del equipo (o activa y desactiva el modo avión).",
            "Reinicia el equipo.",
            "Si estás en la oficina, acércate al punto de red o prueba con cable.",
        ),
    ),
    Ficha(
        "equipo que no enciende",
        ("no enciende", "no prende", "no arranca", "no inicia el equipo"),
        ("no da imagen",),
        (
            "Conecta el cargador y espera unos 5 minutos antes de intentar encenderlo.",
            "Mantén presionado el botón de encendido unos 15 segundos, suéltalo y vuelve a encender.",
            "Prueba con otra toma de corriente, o con otro cargador si tienes.",
        ),
    ),
    Ficha(
        "equipo lento",
        ("lenta", "lento", "se traba", "se congela", "tarda mucho"),
        ("congelad", "va despacio"),
        (
            "Guarda lo que tengas abierto y reinicia el equipo (si hace días que no lo apagas, ayuda bastante).",
            "Cierra los programas y pestañas que no estés usando.",
            "Revisa si hay actualizaciones pendientes y que el disco no esté casi lleno.",
        ),
    ),
    Ficha(
        "pantalla o monitor",
        ("monitor", "pantalla negra", "sin senal", "pantalla en negro"),
        ("no hay imagen",),
        (
            "Revisa que el cable de video esté bien conectado en los dos extremos y que el monitor esté encendido.",
            "Con el botón del monitor elige la entrada correcta (HDMI, DisplayPort, etc.).",
            "Reinicia el equipo, y si puedes prueba con otro cable o puerto.",
        ),
    ),
    Ficha(
        "mouse o teclado",
        ("mouse", "raton", "teclado"),
        (),
        (
            "Revisa las pilas, o que el cable o el receptor USB estén bien conectados.",
            "Desconéctalo y conéctalo en otro puerto USB.",
            "Reinicia el equipo.",
        ),
    ),
    # La contraseña va al final y con pistas fuertes muy específicas: «iniciar sesión» aparece
    # en muchos problemas (OneDrive, VPN...) y no debe decidir el tema.
    Ficha(
        "contraseña o acceso a una cuenta",
        ("contrasena", "password", "olvide mi clave", "cuenta bloqueada", "bloqueada mi cuenta"),
        ("clave", "credenciales", "inicio de sesion", "iniciar sesion", "no me deja entrar", "no puedo entrar"),
        (
            "Revisa que no tengas las mayúsculas activadas y escribe la contraseña con calma, sin copiarla.",
            "Prueba entrar desde otro navegador o en una ventana privada.",
            "Si no la recuerdas, usa la opción «¿Olvidaste tu contraseña?» de la pantalla de inicio de sesión para crear una nueva.",
            "Si la cuenta aparece como bloqueada, espera unos 15 minutos antes de volver a intentarlo.",
        ),
    ),
]

PASOS_POR_RESPUESTA = 3


def normalizar(texto: str) -> str:
    return quitar_tildes((texto or "").lower())


def buscar_ficha(*textos: str):
    """La ficha del tema que más aparece en los textos, o None si ninguno se reconoce."""
    junto = " ".join(normalizar(t) for t in textos if t)
    mejor, puntaje = None, 0
    for ficha in FICHAS:
        puntos = 3 * sum(p in junto for p in ficha.fuertes) + sum(p in junto for p in ficha.debiles)
        if puntos > puntaje:  # en empate gana la ficha más específica (la que va antes)
            mejor, puntaje = ficha, puntos
    return mejor


# ---------- respuesta con los pasos de una ficha ----------

_INTROS = [
    "Vamos a revisarlo por partes:",
    "Probemos esto, en este orden:",
    "Empecemos por lo más simple:",
    "Dale una revisada a esto:",
    "Hagamos lo siguiente:",
    "Veamos, empieza por aquí:",
]
_CIERRES = [
    "Avísame cómo te va.",
    "Si sigue igual, dime qué mensaje te sale o qué pasa justo al intentarlo.",
    "Cuéntame si alguno funciona.",
    "Si nada funciona, dímelo y lo dejamos para el equipo.",
    "",
    "",
]


def respuesta_con_ficha(ficha: Ficha, azar: random.Random = random) -> str:
    pasos = "\n".join(f"{i}. {p}" for i, p in enumerate(ficha.pasos[:PASOS_POR_RESPUESTA], 1))
    cierre = azar.choice(_CIERRES)
    return f"{azar.choice(_INTROS)}\n{pasos}" + (f"\n{cierre}" if cierre else "")


def ficha_ya_dada(ficha: Ficha, respuestas_anteriores: list[str]) -> bool:
    """¿Ya se le dieron estos pasos en la conversación? Entonces no se repiten."""
    primer_paso = ficha.pasos[0]
    return any(primer_paso in r for r in respuestas_anteriores)


# ---------- respuestas directas (no necesitan al modelo) ----------

_SALUDO = re.compile(
    r"^\W*(?:hola+|holi+|buenas(?: (?:tardes|noches|dias))?|buenos dias|buen dia|hey|ey|que tal|saludos)\W*$"
)
_GRACIAS = re.compile(r"^\W*(?:muchas |mil )?gracias(?: por todo| de todas formas)?\W*$|^\W*(?:ok|listo|vale|perfecto)[, ]+gracias\W*$")
_IDENTIDAD = re.compile(
    r"\b(?:eres|sos) (?:un |una )?(?:robot|bot|ia|inteligencia artificial|humano|humana|persona|maquina)\b"
    r"|\b(?:esto|esta) es (?:un |una )?(?:robot|bot|ia|maquina)\b"
    r"|\bcon quien (?:hablo|estoy hablando)\b|\bhablo con (?:un|una) (?:robot|bot|persona|humano)\b"
)
_PIDE_PERSONA = re.compile(
    r"\b(?:hablar|comunicarme|pasame|pasarme|contactar) con (?:una persona|un humano|un tecnico|alguien|el equipo|soporte)\b"
    r"|\bquiero (?:un tecnico|una persona|un humano)\b|\bnecesito (?:un tecnico|una persona|un humano)\b"
)
_SOLICITA_ACCESO = re.compile(
    r"\b(?:necesito|solicito|quiero|requiero|pido|piden|den|denme|dame|darme|otorguen|asignen|habiliten|activen|tramitar|gestionar)\b"
    r"[^.!?\n]{0,40}\b(?:acceso|accesos|permiso|permisos|licencia|licencias)\b"
    r"|\b(?:acceso|accesos|permisos?) (?:a|al|para|de)\b[^.!?\n]{0,40}\b(?:nuevo|nueva|colaborador|empleado|usuario)\b"
)
_ALTA_BAJA = re.compile(
    r"\b(?:alta|baja|crear|creen|dar de alta|dar de baja)\b[^.!?\n]{0,25}\b(?:usuario|cuenta|colaborador|empleado|correo)\b"
    r"|\b(?:usuario|cuenta|correo) (?:nuevo|nueva) para\b"
)
_INSTALAR = re.compile(r"\b(?:instalar|instalen|instalacion|instalame|instalarme|instale)\b")

_SALUDOS = [
    "¡Hola! ¿En qué te ayudo?",
    "¡Hola! Cuéntame qué pasó y lo vemos.",
    "¡Buenas! ¿Con qué te doy una mano?",
    "¡Hola! Dime qué necesitas.",
]
_GRACIAS_RESP = [
    "¡De nada! Si surge algo más, aquí estoy.",
    "¡Con gusto! Cualquier otra cosa, me avisas.",
    "Para eso estamos. Si necesitas algo más, escríbeme.",
]
_IDENTIDAD_RESP = [
    "Soy Minutito, el asistente virtual de soporte de MinutoDesk. Te ayudo con lo básico y, si hace falta, paso tu caso a una persona del equipo.",
    "Soy el asistente virtual de soporte, Minutito. Resuelvo lo sencillo y, si prefieres hablar con una persona, te paso con el equipo.",
]
_PERSONA_RESP = [
    "Claro, te paso con una persona del equipo: voy a escalar tu caso a un técnico. Cuéntame en una línea qué necesitas para dejarlo anotado.",
    "Listo, voy a escalar tu caso a un técnico para que te atienda una persona. Si quieres, ya mismo cuéntame el detalle y lo dejo en el ticket.",
]
_ACCESO_RESP = [
    "Los accesos y permisos los configura el equipo de sistemas, así que voy a escalar tu caso a un técnico. ¿A qué sistema o carpeta lo necesitas? Así lo dejo anotado.",
    "Eso lo gestiona el equipo: voy a escalar tu caso a un técnico. Dime a qué sistema o recurso necesitas el acceso y lo agrego al ticket.",
]
_ALTA_RESP = [
    "Las altas y bajas de usuarios las hace el equipo de sistemas, así que voy a escalar tu caso a un técnico. Para altas de colaboradores, usa «Crear ticket» → «Gestión de usuarios y accesos»: ahí van todos los datos.",
]
_INSTALAR_RESP = [
    "Instalar programas lo hace el equipo de sistemas, así que voy a escalar tu caso a un técnico. ¿Qué programa necesitas y en qué equipo?",
    "Para instalar software hace falta el equipo: voy a escalar tu caso a un técnico. Dime qué programa es y para qué lo necesitas.",
]


def respuesta_directa(mensaje: str, azar: random.Random = random) -> str | None:
    """Respuesta fija (variada) para lo que no necesita al modelo, o None si hay que consultarlo."""
    m = normalizar(mensaje).strip()
    if not m:
        return None
    if _SALUDO.match(m):
        return azar.choice(_SALUDOS)
    if _GRACIAS.match(m):
        return azar.choice(_GRACIAS_RESP)
    if _IDENTIDAD.search(m):
        return azar.choice(_IDENTIDAD_RESP)
    if _PIDE_PERSONA.search(m):
        return azar.choice(_PERSONA_RESP)
    if _ALTA_BAJA.search(m):
        return azar.choice(_ALTA_RESP)
    if _SOLICITA_ACCESO.search(m):
        return azar.choice(_ACCESO_RESP)
    if _INSTALAR.search(m):
        return azar.choice(_INSTALAR_RESP)
    return None

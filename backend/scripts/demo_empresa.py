"""Datos de demostración con aspecto de empresa real (para la presentación y las pruebas).

Uso (desde backend/):
    python scripts/demo_empresa.py cuentas
    python scripts/demo_empresa.py simular --casos 30

«cuentas» crea usuarios, jefes y técnicos con nombres ficticios. Sus correos usan el
alias de Gmail minutodesksoporte+nombre@gmail.com: todos llegan a la bandeja de soporte,
así se prueban «olvidé mi contraseña», las aprobaciones, etc. sin crear correos nuevos.
La contraseña común se genera al azar y queda en backend/cuentas_demo.txt (no se sube).

«simular» hace pasar casos de todo un poco por el flujo real: un colaborador simulado
conversa con Minutito (prueba_controlada.simular). Si Minutito le da lo que lo arregla,
la conversación queda resuelta (+10 puntos); si no, se crea el ticket con el resumen de
la conversación, el SVM lo clasifica y los técnicos lo atienden: algunos quedan nuevos,
otros en proceso (algunos con aprobación pendiente) y otros resueltos. Las fechas se
reparten en los últimos días para que Reportes muestre tiempos reales. Antes de empezar
copia la base a minutodesk.antes_demo.db, para poder volver atrás.
"""
import argparse
import random
import secrets
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database import engine, init_db
from app.models import (
    Aprobacion,
    Area,
    Cliente,
    ConversacionMinutito,
    EventoGamificacion,
    HistorialEstadoTicket,
    MensajeMinutito,
    MensajeTicket,
    Ticket,
)
from app.services import minutito_chat
from app.services.auth import hashear_password
from app.services.classifier import clasificar_ticket
from app.services.escenarios_prueba import ESCENARIOS, Escenario
from app.services.gamification_rules import evaluar_evento
from app.services.prueba_controlada import simular

BACKEND = Path(__file__).resolve().parent.parent
ARCHIVO_CLAVE = BACKEND / "cuentas_demo.txt"
BASE_CORREO = "minutodesksoporte"

# Nombres ficticios: ninguno corresponde a una persona de la empresa.
USUARIOS = [
    ("Andrea Villacís", "Contabilidad"),
    ("Jorge Moreira", "Obra Civil"),
    ("Valeria Chiriboga", "Ventas"),
    ("Diego Alvarado", "Marketing"),
    ("Paola Intriago", "Administración"),
    ("Kevin Zambrano", "Obra Civil"),
    ("Gabriela Montúfar", "Recursos Humanos"),
    ("Santiago Bravo", "Proyectos"),
    ("Mónica Cedeño", "Ventas"),
    ("Esteban Rivadeneira", "Contabilidad"),
]
JEFES = [("Ricardo Mena", "Obra Civil"), ("Patricia Andrade", "Administración")]
TECNICOS = [("Luis Paredes", "Sistemas"), ("Daniela Cevallos", "Sistemas"), ("Fernando Ortiz", "Sistemas")]

# Solicitudes que solo puede atender el equipo de sistemas (no son de primer nivel).
SOLICITUDES = [
    Escenario("sol-laptop", "Solicitudes", "Necesita una laptop para un colaborador que ingresa el lunes.", "", ""),
    Escenario("sol-carpeta", "Solicitudes", "Necesita acceso a la carpeta compartida de Proyectos.", "", ""),
    Escenario("sol-autocad", "Solicitudes", "Necesita una licencia de AutoCAD para revisar planos.", "", ""),
    Escenario("sol-usuario", "Solicitudes", "Hay que crear el usuario y el correo de un practicante nuevo.", "", ""),
    Escenario("sol-project", "Solicitudes", "Necesita que le instalen Microsoft Project.", "", ""),
    Escenario("sol-monitor", "Solicitudes", "Pide un segundo monitor para trabajar con planos.", "", ""),
    Escenario("sol-pantalla", "Solicitudes", "Se le cayó la laptop y la pantalla se rompió.", "", ""),
    Escenario("sol-sap", "Solicitudes", "Necesita permisos en SAP para aprobar órdenes de compra.", "", ""),
    Escenario("sol-internet-obra", "Solicitudes", "La obra nueva no tiene internet y necesitan conexión.", "", ""),
    Escenario("sol-celular", "Solicitudes", "Pide un celular corporativo para el residente de obra.", "", ""),
    Escenario("sol-powerbi", "Solicitudes", "Necesita acceso al reporte de ventas en Power BI.", "", ""),
    Escenario("sol-baja", "Solicitudes", "Hay que dar de baja el usuario de un colaborador que salió.", "", ""),
]
CON_APROBACION = {"sol-laptop", "sol-autocad", "sol-monitor", "sol-sap", "sol-celular", "sol-powerbi"}


def _correo(nombre: str) -> str:
    import unicodedata

    plano = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    return f"{BASE_CORREO}+{plano.replace(' ', '.')}@gmail.com"


def _area(session: Session, nombre: str) -> Area:
    area = session.exec(select(Area).where(Area.nombre == nombre)).first()
    if area is None:
        area = Area(nombre=nombre)
        session.add(area)
        session.commit()
        session.refresh(area)
    return area


def crear_cuentas() -> None:
    init_db()
    clave = ARCHIVO_CLAVE.read_text(encoding="utf-8").split(":", 1)[1].strip() if ARCHIVO_CLAVE.exists() else None
    clave = clave or f"Demo-{secrets.token_urlsafe(6)}"
    nuevas = 0
    with Session(engine) as session:
        for grupo, rol in ((USUARIOS, "usuario"), (JEFES, "usuario"), (TECNICOS, "tecnico")):
            for nombre, area in grupo:
                correo = _correo(nombre)
                if session.exec(select(Cliente).where(Cliente.email == correo)).first():
                    continue
                session.add(Cliente(
                    nombre=nombre, email=correo, area_id=_area(session, area).id, rol=rol,
                    password_hash=hashear_password(clave),
                ))
                nuevas += 1
        session.commit()
    ARCHIVO_CLAVE.write_text(f"Contraseña de las cuentas de demostración: {clave}\n", encoding="utf-8")
    print(f"Cuentas nuevas: {nuevas}. La contraseña quedó en {ARCHIVO_CLAVE.name}.")


def _hora_laboral(base: datetime) -> datetime:
    """Lleva una fecha a horario de oficina (lunes a viernes, 8:00–17:00)."""
    while base.weekday() >= 5:
        base -= timedelta(days=1)
    return base.replace(hour=random.randint(8, 16), minute=random.randint(0, 59), second=random.randint(0, 59))


def _persona(session: Session, nombres: list[tuple[str, str]]) -> list[Cliente]:
    correos = [_correo(n) for n, _ in nombres]
    return session.exec(select(Cliente).where(Cliente.email.in_(correos))).all()


def _guardar_conversacion(session, usuario, historial, inicio, estado) -> ConversacionMinutito:
    conversacion = ConversacionMinutito(cliente_id=usuario.id, estado=estado, creado_en=inicio)
    session.add(conversacion)
    session.flush()
    momento = inicio
    for rol, texto in historial:
        momento += timedelta(minutes=random.randint(1, 3))
        session.add(MensajeMinutito(conversacion_id=conversacion.id, rol=rol, texto=texto, creado_en=momento))
    conversacion.cerrado_en = momento + timedelta(minutes=1)
    return conversacion


def _estado(session, ticket, anterior, nuevo, por_id, fecha) -> None:
    session.add(HistorialEstadoTicket(
        ticket_id=ticket.id, estado_anterior=anterior, estado_nuevo=nuevo, cambiado_por_id=por_id, fecha=fecha,
    ))


def _atender(session, ticket, usuario, escenario, tecnicos, jefes, ahora) -> None:
    """Lo que haría el equipo según la antigüedad del ticket."""
    edad = ahora - ticket.creado_en
    if edad < timedelta(hours=4):
        return  # recién llegado: sigue nuevo
    tecnico = random.choice(tecnicos)
    tomado = ticket.creado_en + timedelta(minutes=random.randint(10, 180))
    ticket.tecnico_id, ticket.estado = tecnico.id, "en_proceso"
    _estado(session, ticket, "abierto", "en_proceso", tecnico.id, tomado)
    primero = usuario.nombre.split()[0]
    session.add(MensajeTicket(ticket_id=ticket.id, autor_id=tecnico.id, creado_en=tomado,
                              texto=f"Hola {primero}, soy {tecnico.nombre} de sistemas. Ya estoy revisando tu caso."))
    session.add(MensajeTicket(ticket_id=ticket.id, autor_id=usuario.id, creado_en=tomado + timedelta(minutes=random.randint(5, 40)),
                              texto="Gracias, quedo pendiente."))
    resuelve = edad > timedelta(days=1) and random.random() < 0.7
    if escenario.clave in CON_APROBACION:
        aprobada = tomado + timedelta(hours=random.randint(2, 20))
        session.add(Aprobacion(
            ticket_id=ticket.id, solicitada_por_id=tecnico.id, aprobador_id=random.choice(jefes).id,
            descripcion=f"Autorizar: {escenario.situacion}", creado_en=tomado + timedelta(minutes=15),
            estado="aprobada" if resuelve else "pendiente",
            comentario="Aprobado, procedan." if resuelve else None,
            respondida_en=aprobada if resuelve else None,
        ))
    if not resuelve:
        return
    cierre = tomado + timedelta(hours=random.uniform(1, 60))
    if not 8 <= cierre.hour < 18:  # se cierra en horario de oficina
        cierre = (cierre + timedelta(days=1 if cierre.hour >= 18 else 0)).replace(hour=random.randint(8, 11))
    cierre = min(cierre, ahora - timedelta(minutes=30))
    ticket.estado, ticket.resuelto_por, ticket.cerrado_en = "resuelto", "tecnico", cierre
    _estado(session, ticket, "en_proceso", "resuelto", tecnico.id, cierre)
    session.add(MensajeTicket(ticket_id=ticket.id, autor_id=tecnico.id, creado_en=cierre,
                              texto="Listo, quedó resuelto. Cualquier cosa me avisas."))
    session.flush()
    evento = evaluar_evento(ticket, usuario.id, session)
    if evento is not None:
        evento.creado_en = cierre
        session.add(evento)


def simular_operacion(casos: int, dias: int, semilla: int) -> None:
    init_db()
    db = Path("minutodesk.db")  # la misma ruta relativa que usa app.database
    copia = Path("minutodesk.antes_demo.db")
    if not copia.exists():
        shutil.copy2(db, copia)
        print(f"Copia de seguridad: {copia.name}")
    random.seed(semilla)
    n_solicitudes = max(1, round(casos * 0.35))  # en la empresa la mayoría son solicitudes
    elegidos = random.sample(ESCENARIOS, casos - n_solicitudes) + random.sample(
        SOLICITUDES, min(n_solicitudes, len(SOLICITUDES)))
    random.shuffle(elegidos)
    ahora = datetime.now()
    with Session(engine) as session:
        usuarios, jefes, tecnicos = _persona(session, USUARIOS), _persona(session, JEFES), _persona(session, TECNICOS)
        if not (usuarios and jefes and tecnicos):
            sys.exit("Primero crea las cuentas: python scripts/demo_empresa.py cuentas")
        for i, escenario in enumerate(elegidos, 1):
            usuario = random.choice(usuarios)
            inicio = _hora_laboral(ahora - timedelta(days=random.uniform(0, dias)))
            if inicio > ahora:
                inicio = ahora - timedelta(minutes=random.randint(30, 120))
            try:
                historial, termino = simular(session, escenario)
            except minutito_chat.MinutitoNoDisponible as e:
                sys.exit(f"Minutito no está disponible: {e}. Lo hecho quedó guardado.")
            if termino == "resuelto":
                conversacion = _guardar_conversacion(session, usuario, historial, inicio, "resuelta")
                session.add(EventoGamificacion(cliente_id=usuario.id, puntos_otorgados=10,
                                               motivo="Resuelto con Minutito", creado_en=conversacion.cerrado_en))
                usuario.puntos += 10
                session.add(usuario)
            else:
                conversacion = _guardar_conversacion(session, usuario, historial, inicio, "ticket")
                texto = minutito_chat.resumir_para_ticket(historial)[:5000]
                prediccion = clasificar_ticket(texto)
                ticket = Ticket(
                    cliente_id=usuario.id, texto=texto, creado_en=conversacion.cerrado_en,
                    tipo_predicho=prediccion["tipo"], categoria_predicha=prediccion["categoria"],
                    confianza_clasificacion=prediccion["confianza"],
                    prioridad=random.choice(["Normal", "Normal", "Normal", "Alta", "Baja"]),
                )
                session.add(ticket)
                session.flush()
                conversacion.ticket_id = ticket.id
                _estado(session, ticket, None, "abierto", usuario.id, ticket.creado_en)
                _atender(session, ticket, usuario, escenario, tecnicos, jefes, ahora)
            session.commit()
            print(f"{i}/{len(elegidos)} {escenario.clave}: {termino}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("cuentas")
    sim = sub.add_parser("simular")
    sim.add_argument("--casos", type=int, default=30)
    sim.add_argument("--dias", type=int, default=12, help="en cuántos días hacia atrás se reparten")
    sim.add_argument("--semilla", type=int, default=7)
    args = parser.parse_args()
    if args.comando == "cuentas":
        crear_cuentas()
    else:
        simular_operacion(args.casos, args.dias, args.semilla)

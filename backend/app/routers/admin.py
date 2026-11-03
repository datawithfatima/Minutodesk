"""Gestión de usuarios y áreas. Solo para el rol administrador."""
import re
import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlmodel import Session, select

from app.database import engine, get_session
from app.ml.train_classifier import quitar_tildes
from app.models import (
    Adjunto,
    Aprobacion,
    Area,
    Cliente,
    EventoGamificacion,
    HistorialEstadoTicket,
    MensajeTicket,
    TokenAcceso,
    Ticket,
)
from app.schemas import (
    AreaCreate,
    AreaRead,
    AreaUpdate,
    ClienteRead,
    EnlaceEnviado,
    MensajeRespuesta,
    UsuarioCreado,
    UsuarioCreate,
    UsuarioUpdate,
    SolucionEsperada,
    VeredictoEvaluacion,
)
from app.services import correo, evaluacion_minutito, prueba_controlada, tokens_acceso
from app.services.auth import requerir_admin
from app.services.usuarios import a_cliente_read, mapa_areas

router = APIRouter()

ROLES_VALIDOS = ("usuario", "tecnico", "administrador")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalizar(texto: str) -> str:
    return quitar_tildes(texto.strip().lower())


def _area_activa(session: Session, area_id: int) -> Area:
    area = session.get(Area, area_id)
    if area is None or not area.activo:
        raise HTTPException(status_code=400, detail="El área no existe o está inactiva")
    return area


def _nombre_de_area_libre(session: Session, nombre: str, excepto_id: Optional[int] = None) -> str:
    nombre = nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre del área no puede estar vacío")
    objetivo = _normalizar(nombre)
    for area in session.exec(select(Area)).all():
        if area.id != excepto_id and _normalizar(area.nombre) == objetivo:
            raise HTTPException(status_code=400, detail="Ya existe un área con ese nombre")
    return nombre


@router.get("/usuarios", response_model=list[ClienteRead])
def listar_usuarios(
    q: Optional[str] = None,
    rol: Optional[str] = None,
    activo: Optional[bool] = None,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    consulta = select(Cliente)
    if rol:
        consulta = consulta.where(Cliente.rol == rol)
    if activo is not None:
        consulta = consulta.where(Cliente.activo == activo)
    clientes = session.exec(consulta.order_by(Cliente.nombre)).all()
    if q:
        buscado = _normalizar(q)
        clientes = [c for c in clientes if buscado in _normalizar(f"{c.nombre} {c.email}")]
    areas = mapa_areas(session)
    return [a_cliente_read(c, areas) for c in clientes]


@router.post("/usuarios", response_model=UsuarioCreado)
def crear_usuario(
    data: UsuarioCreate,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    nombre = data.nombre.strip()
    email = data.email.strip().lower()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="El correo no es válido")
    if data.rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail="Rol no válido")
    area = _area_activa(session, data.area_id)
    if session.exec(select(Cliente).where(Cliente.email == email)).first():
        raise HTTPException(status_code=400, detail="Ese correo ya está registrado")

    # Sin contraseña: la persona la elige con el enlace que le llega a su correo.
    cliente = Cliente(nombre=nombre, email=email, area_id=area.id, rol=data.rol)
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    token = tokens_acceso.generar(
        session, cliente, "activacion", tokens_acceso.MINUTOS_ACTIVACION
    )
    envio = correo.enviar_activacion(cliente.email, cliente.nombre, token)
    return UsuarioCreado(usuario=a_cliente_read(cliente, {area.id: area}), envio=envio)


@router.patch("/usuarios/{usuario_id}", response_model=ClienteRead)
def actualizar_usuario(
    usuario_id: int,
    data: UsuarioUpdate,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    cliente = session.get(Cliente, usuario_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if cliente.id == admin.id and (
        (data.rol is not None and data.rol != cliente.rol) or data.activo is False
    ):
        raise HTTPException(
            status_code=400, detail="No puedes cambiar tu propio rol ni desactivar tu cuenta"
        )

    if data.nombre is not None:
        nombre = data.nombre.strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
        cliente.nombre = nombre
    if data.area_id is not None and data.area_id != cliente.area_id:
        cliente.area_id = _area_activa(session, data.area_id).id
    if data.rol is not None and data.rol != cliente.rol:
        if data.rol not in ROLES_VALIDOS:
            raise HTTPException(status_code=400, detail="Rol no válido")
        cliente.rol = data.rol
        cliente.version_token += 1  # cierra sus sesiones: el nuevo rol aplica al volver a entrar
    if data.activo is not None and data.activo != cliente.activo:
        cliente.activo = data.activo
        if not data.activo:
            cliente.version_token += 1

    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return a_cliente_read(cliente, mapa_areas(session))


@router.delete("/usuarios/{usuario_id}", response_model=MensajeRespuesta)
def eliminar_usuario(
    usuario_id: int,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    """Borra una cuenta sin actividad (p. ej. creada por error o nunca usada).

    Quien ya participó en tickets, cambios de estado o gamificación no se puede
    eliminar porque dejaría huérfano el historial; para esos casos se desactiva.
    """
    cliente = session.get(Cliente, usuario_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if cliente.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")

    tiene_actividad = (
        session.exec(
            select(Ticket.id).where(
                or_(Ticket.cliente_id == cliente.id, Ticket.tecnico_id == cliente.id)
            )
        ).first()
        is not None
        or session.exec(
            select(HistorialEstadoTicket.id).where(
                HistorialEstadoTicket.cambiado_por_id == cliente.id
            )
        ).first()
        is not None
        or session.exec(
            select(EventoGamificacion.id).where(EventoGamificacion.cliente_id == cliente.id)
        ).first()
        is not None
        or session.exec(select(Adjunto.id).where(Adjunto.subido_por_id == cliente.id)).first()
        is not None
        or session.exec(select(MensajeTicket.id).where(MensajeTicket.autor_id == cliente.id)).first()
        is not None
        or session.exec(
            select(Aprobacion.id).where(
                or_(
                    Aprobacion.aprobador_id == cliente.id,
                    Aprobacion.solicitada_por_id == cliente.id,
                )
            )
        ).first()
        is not None
    )
    if tiene_actividad:
        raise HTTPException(
            status_code=409,
            detail="Esta persona ya tiene actividad registrada (tickets, cambios o puntos) y "
            "no se puede eliminar sin perder el historial. Desactiva su cuenta en su lugar.",
        )

    for token in session.exec(
        select(TokenAcceso).where(TokenAcceso.cliente_id == cliente.id)
    ).all():
        session.delete(token)
    session.flush()  # los tokens deben salir antes que la cuenta a la que apuntan
    session.delete(cliente)
    session.commit()
    return MensajeRespuesta(mensaje="Usuario eliminado.")


@router.post("/usuarios/{usuario_id}/restablecer-password", response_model=EnlaceEnviado)
def restablecer_password(
    usuario_id: int,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    """Envía a la persona, a su correo, un enlace para elegir una contraseña nueva.
    El administrador nunca ve la contraseña. A una cuenta que aún no se activó se le
    reenvía el enlace de activación."""
    cliente = session.get(Cliente, usuario_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if cliente.id == admin.id:
        raise HTTPException(
            status_code=400, detail="Para tu propia cuenta usa «Cambiar contraseña»"
        )
    if not cliente.activo:
        raise HTTPException(status_code=400, detail="La cuenta está desactivada")

    if cliente.password_hash is None:
        token = tokens_acceso.generar(
            session, cliente, "activacion", tokens_acceso.MINUTOS_ACTIVACION
        )
        envio = correo.enviar_activacion(cliente.email, cliente.nombre, token)
    else:
        token = tokens_acceso.generar(
            session, cliente, "recuperacion", tokens_acceso.MINUTOS_RECUPERACION_ADMIN
        )
        envio = correo.enviar_recuperacion(cliente.email, cliente.nombre, token, "24 horas")
    if envio == "smtp":
        mensaje = f"Enviamos a {cliente.email} un enlace para elegir su contraseña."
    else:
        mensaje = (
            "No se pudo enviar el correo: revisa la configuración SMTP del servidor. "
            "El enlace quedó guardado en backend/correos_enviados/."
        )
    return EnlaceEnviado(mensaje=mensaje, envio=envio)


def _en_hilo(funcion, *args) -> None:
    """Las corridas con Ollama duran de minutos a una hora: van en un hilo aparte y no
    como tarea de la petición, que al reiniciarse el servidor lo dejaría esperando sin
    responder hasta que terminen. Si el servidor se reinicia, la corrida se corta y se
    retoma con «las que faltan»."""
    threading.Thread(target=funcion, args=args, daemon=True).start()


def _generar_en_segundo_plano(todas: bool) -> None:
    with Session(engine) as session:
        evaluacion_minutito.generar_pendientes(session, todas=todas)


@router.post("/evaluacion-minutito/generar", response_model=MensajeRespuesta)
def generar_evaluacion_minutito(
    todas: bool = False,
    admin: Cliente = Depends(requerir_admin),
):
    """Pide a Minutito, en segundo plano, la respuesta para los tickets cargados que aún
    no la tienen (con Ollama puede tardar varios segundos por ticket)."""
    if evaluacion_minutito.progreso["en_curso"]:
        return MensajeRespuesta(mensaje="Ya se están generando las respuestas; la pantalla muestra el avance.")
    evaluacion_minutito.progreso.update(en_curso=True, hechas=0, total=0)  # se ve en curso desde ya
    _en_hilo(_generar_en_segundo_plano, todas)
    return MensajeRespuesta(mensaje="Generando las respuestas de Minutito. Vuelve a cargar en unos minutos.")


@router.patch("/evaluacion-minutito/{evaluacion_id}/solucion")
def guardar_solucion_esperada(
    evaluacion_id: int,
    data: SolucionEsperada,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    try:
        registro = evaluacion_minutito.guardar_solucion(session, evaluacion_id, data.solucion)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": registro.id, "solucion_esperada": registro.solucion_esperada}


@router.post("/evaluacion-minutito/{evaluacion_id}")
def marcar_evaluacion_minutito(
    evaluacion_id: int,
    data: VeredictoEvaluacion,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    try:
        registro = evaluacion_minutito.marcar(session, evaluacion_id, data.veredicto, admin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": registro.id, "veredicto": registro.veredicto}


def _probar_en_segundo_plano(todas: bool) -> None:
    with Session(engine) as session:
        prueba_controlada.generar_pendientes(session, todas=todas)


@router.post("/prueba-controlada/generar", response_model=MensajeRespuesta)
def generar_prueba_controlada(
    todas: bool = False,
    admin: Cliente = Depends(requerir_admin),
):
    """Corre en segundo plano las conversaciones del colaborador simulado con Minutito
    (con Ollama, uno o dos minutos por escenario)."""
    if prueba_controlada.progreso["en_curso"]:
        return MensajeRespuesta(mensaje="La prueba ya está corriendo; la pantalla muestra el avance.")
    prueba_controlada.progreso.update(en_curso=True, hechas=0, total=0)  # se ve en curso desde ya
    _en_hilo(_probar_en_segundo_plano, todas)
    return MensajeRespuesta(mensaje="Corriendo la prueba con Minutito. Vuelve a cargar en unos minutos.")


@router.post("/prueba-controlada/{prueba_id}")
def marcar_prueba_controlada(
    prueba_id: int,
    data: VeredictoEvaluacion,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    try:
        registro = prueba_controlada.marcar(session, prueba_id, data.veredicto, admin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": registro.id, "veredicto": registro.veredicto}


@router.get("/areas", response_model=list[AreaRead])
def listar_areas(
    admin: Cliente = Depends(requerir_admin), session: Session = Depends(get_session)
):
    return session.exec(select(Area).order_by(Area.nombre)).all()


@router.post("/areas", response_model=AreaRead)
def crear_area(
    data: AreaCreate,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    area = Area(nombre=_nombre_de_area_libre(session, data.nombre))
    session.add(area)
    session.commit()
    session.refresh(area)
    return area


@router.patch("/areas/{area_id}", response_model=AreaRead)
def actualizar_area(
    area_id: int,
    data: AreaUpdate,
    admin: Cliente = Depends(requerir_admin),
    session: Session = Depends(get_session),
):
    area = session.get(Area, area_id)
    if area is None:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    if data.nombre is not None:
        area.nombre = _nombre_de_area_libre(session, data.nombre, excepto_id=area.id)
    if data.activo is not None:
        area.activo = data.activo
    session.add(area)
    session.commit()
    session.refresh(area)
    return area

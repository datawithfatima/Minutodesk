from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente
from app.schemas import (
    ClienteRead,
    EstablecerPasswordRequest,
    LoginRequest,
    MensajeRespuesta,
    OlvidePasswordRequest,
    TokenResponse,
)
from app.services import correo, tokens_acceso
from app.services.auth import (
    HASH_FALSO,
    crear_token,
    hashear_password,
    obtener_usuario_actual,
    validar_password,
    verificar_password,
)
from app.services.usuarios import a_cliente_read, mapa_areas

router = APIRouter()

MENSAJE_GENERICO = (
    "Si el correo está registrado, te enviamos instrucciones para restablecer tu contraseña."
)
ENLACE_INVALIDO = "El enlace no es válido o ya expiró. Solicita uno nuevo."


def _buscar_por_email(session: Session, email: str):
    return session.exec(select(Cliente).where(Cliente.email == email.strip().lower())).first()


@router.post("/login", response_model=TokenResponse)
def iniciar_sesion(data: LoginRequest, session: Session = Depends(get_session)):
    cliente = _buscar_por_email(session, data.email)
    hash_guardado = cliente.password_hash if cliente and cliente.password_hash else HASH_FALSO
    password_ok = verificar_password(data.password, hash_guardado)
    if cliente is None or cliente.password_hash is None or not password_ok:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    if not cliente.activo:
        raise HTTPException(
            status_code=403, detail="Tu cuenta está desactivada. Contacta al administrador."
        )
    return TokenResponse(
        access_token=crear_token(cliente),
        cliente=a_cliente_read(cliente, mapa_areas(session)),
    )


@router.post("/olvide-password", response_model=MensajeRespuesta)
def olvide_password(
    data: OlvidePasswordRequest,
    tareas: BackgroundTasks,
    session: Session = Depends(get_session),
):
    # La respuesta es siempre la misma, exista o no el correo, para no revelar quién tiene cuenta.
    cliente = _buscar_por_email(session, data.email)
    if (
        cliente is not None
        and cliente.activo
        and not tokens_acceso.demasiadas_recuperaciones(session, cliente)
    ):
        token = tokens_acceso.generar(
            session, cliente, "recuperacion", tokens_acceso.MINUTOS_RECUPERACION
        )
        tareas.add_task(correo.enviar_recuperacion, cliente.email, cliente.nombre, token)
    return MensajeRespuesta(mensaje=MENSAJE_GENERICO)


@router.post("/establecer-password", response_model=MensajeRespuesta)
def establecer_password(
    data: EstablecerPasswordRequest, session: Session = Depends(get_session)
):
    validar_password(data.password)
    registro = tokens_acceso.buscar_valido(session, data.token)
    if registro is None:
        raise HTTPException(status_code=400, detail=ENLACE_INVALIDO)
    cliente = session.get(Cliente, registro.cliente_id)
    if cliente is None or not cliente.activo:
        raise HTTPException(status_code=400, detail=ENLACE_INVALIDO)

    cliente.password_hash = hashear_password(data.password)
    cliente.version_token += 1
    tokens_acceso.marcar_usado(session, registro)
    session.add(cliente)
    session.commit()
    return MensajeRespuesta(mensaje="Tu contraseña quedó establecida. Ya puedes iniciar sesión.")


@router.get("/yo", response_model=ClienteRead)
def yo(
    usuario: Cliente = Depends(obtener_usuario_actual),
    session: Session = Depends(get_session),
):
    return a_cliente_read(usuario, mapa_areas(session))

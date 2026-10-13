from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Cliente
from app.schemas import (
    CambiarPasswordRequest,
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
    obtener_usuario_sesion,
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
    cliente.debe_cambiar_password = False  # eligió una contraseña propia
    cliente.version_token += 1
    tokens_acceso.marcar_usado(session, registro)
    session.add(cliente)
    session.commit()
    return MensajeRespuesta(mensaje="Tu contraseña quedó establecida. Ya puedes iniciar sesión.")


@router.post("/cambiar-password", response_model=TokenResponse)
def cambiar_password(
    data: CambiarPasswordRequest,
    usuario: Cliente = Depends(obtener_usuario_sesion),
    session: Session = Depends(get_session),
):
    """Cambio de contraseña con sesión iniciada; es obligatorio tras recibir una temporal."""
    if usuario.password_hash is None or not verificar_password(
        data.password_actual, usuario.password_hash
    ):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
    if data.password_nueva == data.password_actual:
        raise HTTPException(
            status_code=400, detail="La contraseña nueva debe ser distinta de la actual"
        )
    validar_password(data.password_nueva)

    usuario.password_hash = hashear_password(data.password_nueva)
    usuario.debe_cambiar_password = False
    usuario.version_token += 1  # cierra las demás sesiones; esta recibe un token nuevo
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return TokenResponse(
        access_token=crear_token(usuario),
        cliente=a_cliente_read(usuario, mapa_areas(session)),
    )


@router.get("/yo", response_model=ClienteRead)
def yo(
    usuario: Cliente = Depends(obtener_usuario_sesion),
    session: Session = Depends(get_session),
):
    return a_cliente_read(usuario, mapa_areas(session))

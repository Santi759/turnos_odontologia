"""Rutas de autenticacion: login, logout y /me (DD-23, DD-30).

Orden de rechazos del login: 403 (`Origin`) -> 400 (direccion del cliente) -> 415 (`Content-Type`)
-> 422 (cuerpo) -> 429 (bloqueo) -> 503 (Argon2 saturado) -> 401 (credenciales).
"""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.claves import token_csrf
from app.auth.concurrencia import ServicioOcupado
from app.auth.cookies import NOMBRE_COOKIE, borrar_cookie, emitir_cookie
from app.auth.dependencias import (
    IdentidadAutenticada,
    exigir_csrf,
    exigir_direccion_cliente,
    exigir_json,
    identidad_actual,
    obtener_servicio,
    obtener_sesion_db,
    obtener_settings,
    rechazo,
    verificar_origen,
)
from app.auth.servicio import LoginBloqueado, LoginRechazado, ServicioAuth
from app.core.config import Settings
from app.schemas.auth import (
    ConsultorioRespuesta,
    EntradaLogin,
    RespuestaIdentidad,
    UsuarioRespuesta,
)

registro = logging.getLogger(__name__)

DETALLE_LOGIN_RECHAZADO = "No se pudo iniciar sesión."
DETALLE_BLOQUEADO = "Demasiados intentos. Intente más tarde."
DETALLE_OCUPADO = "Servicio ocupado. Intente más tarde."
REINTENTO_OCUPADO_SEGUNDOS = "5"
NO_STORE = {"Cache-Control": "no-store"}


class RutaAuth(APIRoute):
    """Toda respuesta de estas rutas es `no-store` (DD-30) y el 422 nunca refleja la entrada (DD-23)."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def manejador(request: Request) -> Response:
            try:
                respuesta = await original(request)
            except RequestValidationError as error:
                # Solo tipo, ubicacion y mensaje: `input` y `ctx` podrian contener la contrasena.
                detalle = [
                    {"type": e["type"], "loc": list(e["loc"]), "msg": e["msg"]}
                    for e in error.errors()
                ]
                return JSONResponse({"detail": detalle}, status_code=422, headers=NO_STORE)
            respuesta.headers["Cache-Control"] = "no-store"
            return respuesta

        return manejador


router = APIRouter(prefix="/api/auth", tags=["auth"], route_class=RutaAuth)


def _identidad(
    nombre: str, email: str, rol: str, consultorio_nombre: str
) -> RespuestaIdentidad:
    return RespuestaIdentidad(
        usuario=UsuarioRespuesta(nombre=nombre, email=email, rol=rol),
        consultorio=ConsultorioRespuesta(nombre=consultorio_nombre),
    )


async def entrada_login(request: Request) -> EntradaLogin:
    """Lee y valida el cuerpo DESPUES de `Origin`, direccion y `Content-Type` (DD-30).

    FastAPI analiza el cuerpo antes de resolver las dependencias; hacerlo aqui conserva el orden
    403 -> 400 -> 415 -> 422 tambien con un JSON malformado.
    """
    try:
        datos = await request.json()
        return EntradaLogin.model_validate(datos)
    except ValidationError as error:
        raise RequestValidationError(
            [
                {"type": e["type"], "loc": ("body", *e["loc"]), "msg": e["msg"]}
                for e in error.errors(include_url=False, include_context=False, include_input=False)
            ]
        ) from None
    except ValueError:  # JSON malformado o no UTF-8
        raise RequestValidationError(
            [{"type": "json_invalid", "loc": ("body",), "msg": "JSON decode error"}]
        ) from None


@router.post(
    "/login",
    response_model=RespuestaIdentidad,
    dependencies=[Depends(verificar_origen)],
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": EntradaLogin.model_json_schema()}},
        }
    },
)
def login(
    request: Request,
    response: Response,
    ip: str = Depends(exigir_direccion_cliente),
    _json: None = Depends(exigir_json),
    entrada: EntradaLogin = Depends(entrada_login),
    settings: Settings = Depends(obtener_settings),
    servicio: ServicioAuth = Depends(obtener_servicio),
    db: Session = Depends(obtener_sesion_db),
) -> RespuestaIdentidad:
    try:
        iniciada = servicio.iniciar_sesion(
            db,
            codigo=entrada.codigo_consultorio,
            email=entrada.email,
            contrasena=entrada.contrasena,
            ip_normalizada=ip,
            token_entrante=request.cookies.get(NOMBRE_COOKIE),
        )
    except LoginBloqueado as bloqueo:
        raise rechazo(429, DETALLE_BLOQUEADO, **{"Retry-After": str(bloqueo.retry_after)}) from None
    except ServicioOcupado:
        registro.warning("verificacion_saturada")  # codigo fijo: nada de la peticion (DD-25)
        raise rechazo(
            503, DETALLE_OCUPADO, **{"Retry-After": REINTENTO_OCUPADO_SEGUNDOS}
        ) from None
    except LoginRechazado:
        registro.warning("login_rechazado")  # codigo fijo: sin email, codigo, IP ni contrasena
        raise rechazo(401, DETALLE_LOGIN_RECHAZADO) from None
    emitir_cookie(response, iniciada.token, settings)
    response.headers["X-CSRF-Token"] = token_csrf(servicio.config.clave_hmac, iniciada.sesion_id)
    return _identidad(iniciada.nombre, iniciada.email, iniciada.rol, iniciada.consultorio_nombre)


@router.get("/me", response_model=RespuestaIdentidad)
def me(
    response: Response,
    identidad: IdentidadAutenticada = Depends(identidad_actual),
    servicio: ServicioAuth = Depends(obtener_servicio),
) -> RespuestaIdentidad:
    """Identidad y rol SOLO desde la sesion; recupera el token CSRF tras recargar la pagina."""
    response.headers["X-CSRF-Token"] = token_csrf(servicio.config.clave_hmac, identidad.sesion_id)
    return _identidad(identidad.nombre, identidad.email, identidad.rol, identidad.consultorio_nombre)


@router.post("/logout", status_code=204, dependencies=[Depends(verificar_origen)])
def logout(
    identidad: IdentidadAutenticada = Depends(identidad_actual),
    _csrf: None = Depends(exigir_csrf),
    settings: Settings = Depends(obtener_settings),
    servicio: ServicioAuth = Depends(obtener_servicio),
    db: Session = Depends(obtener_sesion_db),
) -> Response:
    """`Origin`, sesion valida y token CSRF; revoca al instante solo esta sesion (DD-05)."""
    servicio.cerrar_sesion(db, identidad.sesion_id)
    respuesta = Response(status_code=204)
    borrar_cookie(respuesta, settings)
    return respuesta

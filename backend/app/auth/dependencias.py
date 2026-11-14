"""Dependencias de FastAPI para la identidad, `Origin`, CSRF, JSON y direccion del cliente (DD-01).

Este es el UNICO modulo de la aplicacion que construye `ContextoConsultorio`, y solo a partir
de una sesion validada (RN-MT-02, DD-27): nada que envie el cliente puede alterarlo.

Lee de `app.state` (la fabrica de la app lo configura en el grupo 8): `settings`,
`fabrica_sesiones` (sessionmaker) y `servicio_auth` (`ServicioAuth`).
"""

import hmac
import logging
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.claves import DireccionClienteNoDeterminable, normalizar_ip, token_csrf
from app.auth.cookies import NOMBRE_COOKIE, valor_cookie_borrada
from app.auth.servicio import ServicioAuth
from app.core.config import Settings
from app.core.contexto_bd import aplicar_contexto
from app.models.usuario import Rol
from app.repositories.contexto import ContextoConsultorio

registro = logging.getLogger(__name__)

DETALLE_NO_AUTENTICADO = "No autenticado."
DETALLE_RECHAZADA = "Solicitud rechazada."
DETALLE_NO_PROCESABLE = "No se pudo procesar la solicitud."
DETALLE_TIPO_NO_ADMITIDO = "Tipo de contenido no admitido."


@dataclass(frozen=True, slots=True)
class IdentidadAutenticada:
    sesion_id: uuid.UUID
    usuario_id: uuid.UUID
    rol: Rol
    nombre: str
    email: str
    consultorio_nombre: str
    contexto: ContextoConsultorio


def rechazo(estado: int, detalle: str, **cabeceras: str) -> HTTPException:
    """Error de las rutas de autenticacion: cuerpo `{"detail": ...}` y nunca almacenable (DD-30)."""
    return HTTPException(
        status_code=estado, detail=detalle, headers={"Cache-Control": "no-store", **cabeceras}
    )


PARAMETRO_CONSULTORIO = "consultorio_id"
CABECERA_CONSULTORIO = "X-Consultorio-Id"
DETALLE_CONSULTORIO_DEL_CLIENTE = "El consultorio no se acepta del cliente."


def _consultorio_del_cliente(ubicacion: str, nombre: str) -> HTTPException:
    """422 con tipo, ubicacion y mensaje fijos: nunca el valor ni la variante de mayusculas (X1)."""
    return HTTPException(
        status_code=422,
        detail=[
            {
                "type": "consultorio_no_admitido",
                "loc": [ubicacion, nombre],
                "msg": DETALLE_CONSULTORIO_DEL_CLIENTE,
            }
        ],
        headers={"Cache-Control": "no-store"},
    )


def rechazar_consultorio_del_cliente(request: Request) -> None:
    """Dependencia GLOBAL (DD-18, PD-02): el consultorio no se acepta de la query ni de cabeceras.

    Rechaza con 422, antes de cualquier otra dependencia, un parametro de query `consultorio_id` (sin
    distinguir mayusculas) o la cabecera `X-Consultorio-Id`. Es la UNICA cabecera de la lista: ninguna
    otra se rechaza ni se lee jamas como fuente de identidad o de consultorio (X1). No usa el valor.
    """
    if any(nombre.casefold() == PARAMETRO_CONSULTORIO for nombre in request.query_params):
        raise _consultorio_del_cliente("query", PARAMETRO_CONSULTORIO)
    if CABECERA_CONSULTORIO.casefold() in request.headers:
        raise _consultorio_del_cliente("header", CABECERA_CONSULTORIO)


def origen_permitido(origen: str | None, permitidos: list[str]) -> bool:
    """Igualdad exacta de cadena con un origen configurado (sin normalizar mayusculas ni barras)."""
    return origen is not None and origen in permitidos


MEDIO_JSON = "application/json"
CHARSET_ADMITIDO = "charset=utf-8"


def tipo_de_medio_json(valor: str | None) -> bool:
    """`application/json` (sin distinguir mayusculas) con, a lo sumo, el parametro `charset=utf-8`."""
    if valor is None:
        return False
    medio, *parametros = (parte.strip() for parte in valor.split(";"))
    if medio.lower() != MEDIO_JSON or len(parametros) > 1:
        return False
    return not parametros or parametros[0].replace('"', "").lower() == CHARSET_ADMITIDO


def token_csrf_coincide(clave: bytes, sesion_id: uuid.UUID, presentado: str | None) -> bool:
    """Compara en tiempo constante el token presentado con el derivado de la sesion (DD-07)."""
    if not presentado:
        return False
    esperado = token_csrf(clave, sesion_id).encode("ascii")
    return hmac.compare_digest(esperado, presentado.encode("utf-8"))


def obtener_settings(request: Request) -> Settings:
    return request.app.state.settings


def obtener_servicio(request: Request) -> ServicioAuth:
    return request.app.state.servicio_auth


def obtener_sesion_db(request: Request) -> Iterator[Session]:
    with request.app.state.fabrica_sesiones() as sesion:
        yield sesion


def obtener_sesion_login(request: Request) -> Iterator[Session]:
    """Sesion del rol `turnos_login`: SOLO `POST /api/auth/login` la declara (DD-28)."""
    with request.app.state.fabrica_sesiones_login() as sesion:
        yield sesion


METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS"})


def verificar_origen(request: Request, settings: Settings = Depends(obtener_settings)) -> None:
    """Todo metodo que cambia estado exige UN `Origin` igual a uno permitido (DD-08); sin `Referer`."""
    if request.method in METODOS_SEGUROS:
        return
    origenes = request.headers.getlist("origin")
    if len(origenes) != 1 or not origen_permitido(origenes[0], settings.cors_allowed_origins):
        raise rechazo(403, DETALLE_RECHAZADA)


def exigir_direccion_cliente(request: Request) -> str:
    """Direccion de la conexion directa, normalizada (DD-19, PC-05).

    Sin cliente o con un host que no es una IP, el login se rechaza con 400 ANTES de buscar
    credenciales, ejecutar Argon2 o registrar intentos. Nunca se lee `X-Forwarded-For`.
    """
    host = request.client.host if request.client is not None else None
    try:
        return normalizar_ip(host)
    except DireccionClienteNoDeterminable:
        registro.warning("direccion_cliente_no_determinable")  # codigo fijo: sin IP ni datos (DD-25)
        raise rechazo(400, DETALLE_NO_PROCESABLE) from None


def exigir_json(request: Request) -> None:
    """415 si el tipo de medio no es JSON: obliga al preflight CORS en peticiones de otro sitio (DD-30)."""
    if not tipo_de_medio_json(request.headers.get("content-type")):
        raise rechazo(415, DETALLE_TIPO_NO_ADMITIDO)


def identidad_actual(
    request: Request,
    settings: Settings = Depends(obtener_settings),
    servicio: ServicioAuth = Depends(obtener_servicio),
    db: Session = Depends(obtener_sesion_db),
) -> IdentidadAutenticada:
    """Identidad SOLO desde la cookie `turnos_session` (RN-MT-02); nada del cliente la altera."""
    identidad = servicio.resolver_identidad(db, request.cookies.get(NOMBRE_COOKIE))
    if identidad is None:
        raise rechazo(
            401, DETALLE_NO_AUTENTICADO, **{"Set-Cookie": valor_cookie_borrada(settings)}
        )
    try:
        rol = Rol(identidad.rol)
    except ValueError:
        # Un rol fuera de los admitidos no autentica (DD-16); codigo fijo, sin el valor ni la cuenta.
        registro.warning("rol_desconocido")
        raise rechazo(
            401, DETALLE_NO_AUTENTICADO, **{"Set-Cookie": valor_cookie_borrada(settings)}
        ) from None
    # UNICA construccion de ContextoConsultorio de la aplicacion: del consultorio de la sesion.
    contexto = ContextoConsultorio(identidad.consultorio_id)
    # Sin transaccion abierta (el servicio confirmo): la primera consulta de la ruta abre una
    # transaccion que ya lleva el contexto (DD-05).
    aplicar_contexto(db, contexto)
    return IdentidadAutenticada(
        sesion_id=identidad.sesion_id,
        usuario_id=identidad.usuario_id,
        rol=rol,
        nombre=identidad.nombre,
        email=identidad.email,
        consultorio_nombre=identidad.consultorio_nombre,
        contexto=contexto,
    )


def contexto_consultorio(
    identidad: IdentidadAutenticada = Depends(identidad_actual),
) -> ContextoConsultorio:
    return identidad.contexto


def exigir_csrf(
    request: Request,
    identidad: IdentidadAutenticada = Depends(identidad_actual),
    servicio: ServicioAuth = Depends(obtener_servicio),
) -> None:
    """Token CSRF de la propia sesion en la cabecera `X-CSRF-Token` (DD-07)."""
    if not token_csrf_coincide(
        servicio.config.clave_hmac, identidad.sesion_id, request.headers.get("x-csrf-token")
    ):
        raise rechazo(403, DETALLE_RECHAZADA)

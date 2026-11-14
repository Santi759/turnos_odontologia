"""Arnes de las pruebas de aislamiento con roles reales (2.5, DD-20, DD-21).

Solo contra `db-test`. Conexiones REALES de `turnos_app` y `turnos_login` (nunca la fixture de
transaccion revertida): la preparacion y limpieza de datos las hace el motor de administracion
(`app` de `db-test`) con transacciones confirmadas. Si falta una contrasena de rol, la suite
FALLA (no se omite). Las contrasenas viven solo en el entorno del proceso (las genera el runner).
"""

import os
import secrets
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.engine import URL, make_url

from app.auth.concurrencia import LimitadorArgon2
from app.auth.servicio import ConfigAuth, ServicioAuth
from app.core.config import Settings, cargar_configuracion
from app.core.database import crear_engine_desde_url, validar_url_de_pruebas, verificar_conexion
from app.core.roles_bd import ROL_APP, ROL_LOGIN
from app.models.usuario import Rol
from tests.integration.app_auth import ORIGEN, settings_de_prueba
from tests.integration.datos_auth import RelojFijo, VerificadorEspia, hasher_rapido

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
VARIABLE_CLAVE_APP = "TURNOS_APP_TEST_PASSWORD"
VARIABLE_CLAVE_LOGIN = "TURNOS_LOGIN_TEST_PASSWORD"
TABLAS_DE_DATOS = "intento_login, sesion, usuario, consultorio"


@pytest.fixture(scope="session")
def settings_de_pruebas() -> Settings:
    settings = cargar_configuracion()
    url_pruebas = (
        settings.test_database_url.get_secret_value()
        if settings.test_database_url is not None
        else None
    )
    validar_url_de_pruebas(
        url_pruebas,
        settings.database_url.get_secret_value(),
        url_login=(
            settings.database_login_url.get_secret_value()
            if settings.database_login_url is not None
            else None
        ),
        url_migracion=(
            settings.database_migration_url.get_secret_value()
            if settings.database_migration_url is not None
            else None
        ),
    )
    return settings


@pytest.fixture(scope="session")
def url_admin(settings_de_pruebas: Settings) -> URL:
    assert settings_de_pruebas.test_database_url is not None
    return make_url(settings_de_pruebas.test_database_url.get_secret_value())


def _url_de_rol(url_admin: URL, rol: str, variable: str) -> URL:
    clave = os.environ.get(variable)
    # Falla (no omite): una suite de aislamiento que se omite en silencio no prueba nada.
    assert clave, f"falta {variable}: el runner scripts/test.ps1 la genera por ejecucion"
    return url_admin.set(username=rol, password=clave)


@pytest.fixture(scope="session")
def url_app(url_admin: URL) -> URL:
    return _url_de_rol(url_admin, ROL_APP, VARIABLE_CLAVE_APP)


@pytest.fixture(scope="session")
def url_login(url_admin: URL) -> URL:
    return _url_de_rol(url_admin, ROL_LOGIN, VARIABLE_CLAVE_LOGIN)


def _verificar_rol(motor: Engine, esperado: str) -> None:
    with motor.connect() as conexion:
        actual, superusuario, base = conexion.execute(
            text(
                "SELECT current_user, "
                "(SELECT rolsuper FROM pg_roles WHERE rolname = current_user), "
                "current_database()"
            )
        ).one()
    assert actual == esperado, "el motor no conecta con el rol esperado"
    assert superusuario is False, "el rol de pruebas no puede ser superusuario"
    assert base.endswith("_test"), "las pruebas de aislamiento solo usan la base *_test"


@pytest.fixture(scope="session")
def motor_admin(url_admin: URL) -> Iterator[Engine]:
    motor = crear_engine_desde_url(url_admin.render_as_string(hide_password=False))
    try:
        verificar_conexion(motor)
        yield motor
    finally:
        motor.dispose()


@pytest.fixture(scope="session")
def base_en_head(motor_admin: Engine) -> Engine:
    """La base de `db-test` en `head` (el runner ya la migro; aqui es idempotente)."""
    configuracion = Config(str(RAIZ_BACKEND / "alembic.ini"))
    configuracion.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    url = motor_admin.url.render_as_string(hide_password=False).replace("%", "%%")
    configuracion.set_main_option("sqlalchemy.url", url)
    command.upgrade(configuracion, "head")
    return motor_admin


@pytest.fixture(scope="session")
def motor_app(url_app: URL, base_en_head: Engine) -> Iterator[Engine]:
    motor = crear_engine_desde_url(url_app.render_as_string(hide_password=False))
    try:
        _verificar_rol(motor, ROL_APP)
        yield motor
    finally:
        motor.dispose()


@pytest.fixture(scope="session")
def motor_login(url_login: URL, base_en_head: Engine) -> Iterator[Engine]:
    motor = crear_engine_desde_url(url_login.render_as_string(hide_password=False))
    try:
        _verificar_rol(motor, ROL_LOGIN)
        yield motor
    finally:
        motor.dispose()


# --- Datos ficticios A y B ------------------------------------------------------------------


@dataclass(frozen=True)
class UsuarioDePrueba:
    id: uuid.UUID
    email: str
    rol: Rol
    contrasena: str


@dataclass(frozen=True)
class ConsultorioDePrueba:
    id: uuid.UUID
    codigo: str
    nombre: str
    usuarios: dict[Rol, UsuarioDePrueba]


@dataclass(frozen=True)
class DatosAB:
    a: ConsultorioDePrueba
    b: ConsultorioDePrueba


def limpiar_datos(motor_admin: Engine) -> None:
    with motor_admin.begin() as conexion:
        conexion.execute(text(f"TRUNCATE {TABLAS_DE_DATOS}"))


def _crear_consultorio(conexion, letra: str, hash_de: Callable[[str], str]) -> ConsultorioDePrueba:
    codigo = f"consultorio-{letra}-{secrets.token_hex(3)}"
    nombre = f"Consultorio Ficticio {letra.upper()}"
    consultorio_id = conexion.execute(
        text("INSERT INTO consultorio (nombre, codigo) VALUES (:n, :c) RETURNING id"),
        {"n": nombre, "c": codigo},
    ).scalar_one()
    usuarios: dict[Rol, UsuarioDePrueba] = {}
    for rol in Rol:
        email = f"{rol.value}.{letra}@example.test"
        contrasena = secrets.token_urlsafe(18)
        usuario_id = conexion.execute(
            text(
                "INSERT INTO usuario (consultorio_id, email, nombre, rol, credencial) "
                "VALUES (:c, :e, :n, :r, :h) RETURNING id"
            ),
            {
                "c": consultorio_id,
                "e": email,
                "n": f"Persona Ficticia {rol.value} {letra.upper()}",
                "r": rol.value,
                "h": hash_de(contrasena),
            },
        ).scalar_one()
        usuarios[rol] = UsuarioDePrueba(usuario_id, email, rol, contrasena)
    return ConsultorioDePrueba(consultorio_id, codigo, nombre, usuarios)


def preparar_datos(motor_admin: Engine) -> DatosAB:
    """TRUNCATE y alta confirmada de dos consultorios con un usuario por rol cada uno."""
    limpiar_datos(motor_admin)
    hasher = hasher_rapido()
    with motor_admin.begin() as conexion:
        return DatosAB(
            a=_crear_consultorio(conexion, "a", hasher.hash),
            b=_crear_consultorio(conexion, "b", hasher.hash),
        )


@pytest.fixture
def datos_ab(motor_admin: Engine, base_en_head: Engine) -> Iterator[DatosAB]:
    datos = preparar_datos(motor_admin)
    try:
        yield datos
    finally:
        limpiar_datos(motor_admin)


# --- La API real con los roles reales (4.4, 5.6, 5.7, 9.4) -----------------------------------------


@dataclass
class ApiReal:
    """`crear_app` sobre `db-test` con conexiones reales de `turnos_app` y `turnos_login`.

    Solo se sustituyen el servicio (reloj y verificador de prueba, igual que las pruebas de
    concurrencia de C-03) y, opcionalmente, el motor de login; rutas, dependencias, motores,
    pools y guardias son los de produccion.
    """

    app: FastAPI
    servicio: ServicioAuth
    reloj: RelojFijo
    verificador: VerificadorEspia
    settings: Settings

    def cliente(self, ip: str = "203.0.113.7", puerto: int = 50000) -> TestClient:
        return TestClient(
            self.app,
            base_url="https://testserver",
            client=(ip, puerto),
            raise_server_exceptions=False,
        )

    def login(self, cliente: TestClient, codigo: str, email: str, contrasena: str, **cabeceras):
        return cliente.post(
            "/api/auth/login",
            json={"codigo_consultorio": codigo, "email": email, "contrasena": contrasena},
            headers={"Origin": ORIGEN, **cabeceras},
        )


def construir_api(
    url_api: URL,
    url_login_api: URL,
    *,
    limitador: LimitadorArgon2 | None = None,
    verificador: VerificadorEspia | None = None,
    motor_api_con: URL | None = None,
    motor_login_con: URL | None = None,
) -> ApiReal:
    """`motor_*_con` simula una configuracion equivocada que la validacion de `Settings` no detecta.

    Sustituye el motor por otro creado con las funciones de produccion (pool y guardia incluidos)
    a partir de otra URL: es la prueba de la SEGUNDA capa (guardia de rol en cada conexion).
    """
    from app.core.contexto_bd import crear_fabrica_de_sesiones, registrar_reset_del_pool
    from app.core.database import (
        POOL_APP_DESBORDE,
        POOL_APP_TAMANO,
        POOL_LOGIN_DESBORDE,
        POOL_LOGIN_TAMANO,
        _crear_engine_de_la_api,
        crear_fabrica_de_sesiones_login,
    )
    from app.core.roles_bd import ROL_APP as _ROL_APP
    from app.core.roles_bd import ROL_LOGIN as _ROL_LOGIN
    from app.main import crear_app

    settings = settings_de_prueba(
        DATABASE_URL=url_api.render_as_string(hide_password=False),
        DATABASE_LOGIN_URL=url_login_api.render_as_string(hide_password=False),
    )
    app = crear_app(settings)
    if motor_api_con is not None:
        app.state.engine.dispose()
        motor = _crear_engine_de_la_api(
            motor_api_con.render_as_string(hide_password=False),
            _ROL_APP,
            POOL_APP_TAMANO,
            POOL_APP_DESBORDE,
        )
        registrar_reset_del_pool(motor)
        app.state.engine = motor
        app.state.fabrica_sesiones = crear_fabrica_de_sesiones(motor)
    if motor_login_con is not None:
        app.state.engine_login.dispose()
        motor = _crear_engine_de_la_api(
            motor_login_con.render_as_string(hide_password=False),
            _ROL_LOGIN,
            POOL_LOGIN_TAMANO,
            POOL_LOGIN_DESBORDE,
        )
        app.state.engine_login = motor
        app.state.fabrica_sesiones_login = crear_fabrica_de_sesiones_login(motor)
    reloj = RelojFijo()
    verificador = verificador or VerificadorEspia()
    servicio = ServicioAuth(
        ConfigAuth.desde_settings(settings), reloj, verificador, limitador or LimitadorArgon2()
    )
    app.state.servicio_auth = servicio
    return ApiReal(app, servicio, reloj, verificador, settings)


@pytest.fixture
def api_real(url_app: URL, url_login: URL, base_en_head: Engine) -> Iterator[ApiReal]:
    api = construir_api(url_app, url_login)
    try:
        yield api
    finally:
        api.app.state.engine.dispose()
        api.app.state.engine_login.dispose()

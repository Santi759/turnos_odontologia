"""Guardias de rol de las conexiones de la API con conexiones reales (4.4; DD-29, R2-05).

Cada motor de la API verifica en cada conexion NUEVA que `current_user` sea exactamente su rol y que
los privilegios sean los esperados. Solo contra `db-test`.
"""

import secrets

import pytest
from sqlalchemy import text

from app.auth import acceso_login, acceso_previo
from app.core import database
from app.core.config import Settings
from app.core.database import RolDeConexionInvalido, crear_engine_admin, verificar_conexion
from app.core.roles_bd import ROL_APP
from app.models.usuario import Rol
from tests.isolation.conftest import construir_api


def _credenciales(datos_ab):
    usuario = datos_ab.a.usuarios[Rol.SECRETARIA]
    return datos_ab.a.codigo, usuario.email, usuario.contrasena


def _contar(motor_admin, tabla: str) -> int:
    with motor_admin.connect() as conexion:
        return conexion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


def _espiar(monkeypatch, modulo, nombre: str) -> list[int]:
    """Cuenta las consultas que TERMINARON: una conexion rechazada por la guardia no cuenta."""
    llamadas: list[int] = []
    original = getattr(modulo, nombre)

    def espia(*a, **k):
        resultado = original(*a, **k)
        llamadas.append(1)
        return resultado

    monkeypatch.setattr(modulo, nombre, espia)
    return llamadas


def _sesion_abierta(api_real, datos_ab):
    cliente = api_real.cliente()
    respuesta = api_real.login(cliente, *_credenciales(datos_ab))
    assert respuesta.status_code == 200
    return cliente


def test_configuracion_correcta_login_me_y_logout_responden_200(api_real, datos_ab):
    cliente = _sesion_abierta(api_real, datos_ab)

    me = cliente.get("/api/auth/me")

    assert me.status_code == 200
    assert me.json()["usuario"]["email"] == datos_ab.a.usuarios[Rol.SECRETARIA].email


@pytest.mark.parametrize("url_mala", ["url_admin", "url_login"])
def test_database_url_con_otro_rol_hace_fallar_me_sin_consultar_sesion(
    request, monkeypatch, api_real, datos_ab, url_login, url_app, url_mala
):
    cliente_ok = _sesion_abierta(api_real, datos_ab)
    mala = construir_api(url_app, url_login, motor_api_con=request.getfixturevalue(url_mala))
    resolver = _espiar(monkeypatch, acceso_previo, "resolver_sesion")
    try:
        cliente = mala.cliente()
        cliente.cookies.update(cliente_ok.cookies)

        respuesta = cliente.get("/api/auth/me")

        assert respuesta.status_code == 500
        assert datos_ab.a.usuarios[Rol.SECRETARIA].email not in respuesta.text
        assert resolver == []
    finally:
        mala.app.state.engine.dispose()
        mala.app.state.engine_login.dispose()


@pytest.fixture
def rol_clon_de_la_aplicacion(motor_admin, url_admin):
    """Un rol con los mismos privilegios minimos que `turnos_app` pero OTRO nombre."""
    nombre = f"clon_de_app_{secrets.token_hex(4)}"
    clave = secrets.token_urlsafe(24)
    with motor_admin.begin() as conexion:
        conexion.execute(text(f"CREATE ROLE {nombre} LOGIN PASSWORD '{clave}'"))
        conexion.execute(text(f"GRANT USAGE ON SCHEMA public, acceso TO {nombre}"))
        conexion.execute(text(f"GRANT SELECT ON public.consultorio TO {nombre}"))
        conexion.execute(
            text(f"GRANT SELECT (id, consultorio_id, email, nombre, rol, activo) ON public.usuario TO {nombre}")
        )
    try:
        yield url_admin.set(username=nombre, password=clave)
    finally:
        with motor_admin.begin() as conexion:
            conexion.execute(text(f"DROP OWNED BY {nombre}"))
            conexion.execute(text(f"DROP ROLE {nombre}"))


def test_un_rol_con_los_mismos_privilegios_y_otro_nombre_falla_por_current_user(
    rol_clon_de_la_aplicacion,
):
    motor = database._crear_engine_de_la_api(
        rol_clon_de_la_aplicacion.render_as_string(hide_password=False), ROL_APP, 5, 10
    )
    try:
        with pytest.raises(RolDeConexionInvalido) as info:
            motor.connect()
    finally:
        motor.dispose()

    assert str(info.value) == f"la conexion no cumple el rol {ROL_APP}: ROL_INESPERADO"


def test_database_url_con_un_rol_clonado_hace_fallar_me(
    api_real, datos_ab, rol_clon_de_la_aplicacion, url_app, url_login
):
    cliente_ok = _sesion_abierta(api_real, datos_ab)
    mala = construir_api(url_app, url_login, motor_api_con=rol_clon_de_la_aplicacion)
    try:
        cliente = mala.cliente()
        cliente.cookies.update(cliente_ok.cookies)

        assert cliente.get("/api/auth/me").status_code == 500
    finally:
        mala.app.state.engine.dispose()
        mala.app.state.engine_login.dispose()


@pytest.mark.parametrize("url_mala", ["url_app", "url_admin"])
def test_database_login_url_como_app_o_admin_hace_fallar_el_login_sin_cuenta_ni_sesion(
    request, monkeypatch, datos_ab, motor_admin, url_app, url_login, url_mala
):
    mala = construir_api(url_app, url_login, motor_login_con=request.getfixturevalue(url_mala))
    buscar = _espiar(monkeypatch, acceso_login, "buscar_cuenta")
    try:
        respuesta = mala.login(mala.cliente(), *_credenciales(datos_ab))

        assert respuesta.status_code == 500
        assert buscar == []
        assert mala.verificador.llamadas == 0
        assert _contar(motor_admin, "sesion") == 0
        assert _contar(motor_admin, "intento_login") == 0
    finally:
        mala.app.state.engine.dispose()
        mala.app.state.engine_login.dispose()


def test_los_motores_de_administracion_no_tienen_guardia(url_admin):
    settings = Settings(
        DATABASE_URL="postgresql+psycopg://turnos_app:clave-a@host-api.invalid/turnos",
        DATABASE_LOGIN_URL="postgresql+psycopg://turnos_login:clave-l@host-login.invalid/turnos",
        DATABASE_MIGRATION_URL=url_admin.render_as_string(hide_password=False),
        CORS_ALLOWED_ORIGINS="http://localhost:5173",
        APP_ENV="local",
        AUTH_SECRET_KEY=secrets.token_urlsafe(48),
    )
    motor = crear_engine_admin(settings)
    try:
        verificar_conexion(motor)  # `app` es superusuario: una guardia lo habria rechazado
    finally:
        motor.dispose()

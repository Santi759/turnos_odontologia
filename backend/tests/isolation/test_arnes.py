"""El arnes de aislamiento prueba lo que promete (2.5, DD-20)."""

import os

from sqlalchemy import text

from app.core.roles_bd import ROL_APP, ROL_LOGIN
from app.models.usuario import Rol
from tests.isolation.conftest import (
    VARIABLE_CLAVE_APP,
    VARIABLE_CLAVE_LOGIN,
    limpiar_datos,
    preparar_datos,
)

TABLAS = ("intento_login", "sesion", "usuario", "consultorio")


def _cuenta(motor_admin, tabla: str) -> int:
    with motor_admin.connect() as conexion:
        return conexion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


def _identidad(motor):
    with motor.connect() as conexion:
        return conexion.execute(
            text(
                "SELECT current_user, (SELECT rolsuper FROM pg_roles WHERE rolname = current_user), "
                "current_database()"
            )
        ).one()


def test_motor_app_conecta_como_turnos_app_no_superusuario_en_base_de_pruebas(motor_app):
    usuario, superusuario, base = _identidad(motor_app)

    assert usuario == ROL_APP
    assert superusuario is False
    assert base.endswith("_test")


def test_motor_login_conecta_como_turnos_login_no_superusuario_en_base_de_pruebas(motor_login):
    usuario, superusuario, base = _identidad(motor_login)

    assert usuario == ROL_LOGIN
    assert superusuario is False
    assert base.endswith("_test")


def test_las_contrasenas_de_los_roles_son_distintas_y_no_estan_vacias():
    app, login = os.environ.get(VARIABLE_CLAVE_APP), os.environ.get(VARIABLE_CLAVE_LOGIN)

    assert app and login and app != login


def test_las_urls_derivadas_cambian_solo_usuario_y_contrasena(url_admin, url_app, url_login):
    for derivada, rol in ((url_app, ROL_APP), (url_login, ROL_LOGIN)):
        assert derivada.username == rol
        assert (derivada.host, derivada.port, derivada.database) == (
            url_admin.host,
            url_admin.port,
            url_admin.database,
        )
        assert derivada.password != url_admin.password


def test_los_datos_a_y_b_tienen_un_usuario_por_rol_confirmados(datos_ab, motor_admin):
    assert datos_ab.a.id != datos_ab.b.id
    assert datos_ab.a.codigo != datos_ab.b.codigo
    for consultorio in (datos_ab.a, datos_ab.b):
        assert set(consultorio.usuarios) == set(Rol)
    assert _cuenta(motor_admin, "consultorio") == 2
    assert _cuenta(motor_admin, "usuario") == 6
    with motor_admin.connect() as conexion:  # otra conexion: estan confirmados
        credenciales = conexion.execute(
            text("SELECT count(*) FROM usuario WHERE credencial LIKE '$argon2id$%'")
        ).scalar_one()
    assert credenciales == 6


def test_preparar_datos_dos_veces_no_acumula_filas(motor_admin, base_en_head):
    preparar_datos(motor_admin)
    preparar_datos(motor_admin)
    try:
        assert _cuenta(motor_admin, "consultorio") == 2
    finally:
        limpiar_datos(motor_admin)


def test_limpieza_deja_todas_las_tablas_vacias(motor_admin, base_en_head):
    preparar_datos(motor_admin)
    limpiar_datos(motor_admin)

    for tabla in TABLAS:
        assert _cuenta(motor_admin, tabla) == 0


def test_limpieza_al_terminar_la_prueba_anterior(motor_admin, base_en_head):
    """Tras la prueba con `datos_ab` el finalizador dejo la base sin filas."""
    for tabla in TABLAS:
        assert _cuenta(motor_admin, tabla) == 0


def test_una_contrasena_de_rol_ausente_hace_fallar_el_arnes_sin_revelar_valores(monkeypatch):
    # Spec `pruebas-aislamiento`, "Contrasena ausente": la suite FALLA (no se omite) y el error no
    # contiene contrasenas. Se usa una contrasena ficticia en la OTRA variable para comprobarlo.
    import pytest
    from sqlalchemy.engine import make_url

    from tests.isolation.conftest import _url_de_rol

    otra = "clave-ficticia-de-la-otra-variable"
    monkeypatch.setenv(VARIABLE_CLAVE_APP, otra)
    monkeypatch.delenv(VARIABLE_CLAVE_LOGIN, raising=False)
    url_admin = make_url("postgresql+psycopg://app:clave-admin-ficticia@host-prueba.invalid:5432/turnos_test")

    with pytest.raises(AssertionError) as error:
        _url_de_rol(url_admin, ROL_LOGIN, VARIABLE_CLAVE_LOGIN)

    mensaje = str(error.value)
    assert VARIABLE_CLAVE_LOGIN in mensaje
    assert otra not in mensaje and "clave-admin-ficticia" not in mensaje

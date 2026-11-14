"""Catalogo de los cuatro roles con conexiones reales (3.5, DD-01, DD-13).

Solo contra `db-test`. Lee `pg_roles` y `pg_auth_members` con el motor de administracion y
comprueba, con los roles de conexion reales, lo que NO pueden hacer.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from app.core.roles_bd import (
    ROL_ACCESO_LOGIN,
    ROL_ACCESO_PREVIO,
    ROL_APP,
    ROL_LOGIN,
    ROLES_CON_LOGIN,
    ROLES_DUENOS,
    TODOS_LOS_ROLES,
    violaciones_de_rol,
)


def _fila_de_rol(motor_admin, rol: str) -> dict:
    with motor_admin.connect() as conexion:
        fila = conexion.execute(
            text("SELECT * FROM pg_roles WHERE rolname = :r"), {"r": rol}
        ).mappings().one()
    return dict(fila)


@pytest.mark.parametrize("rol", TODOS_LOS_ROLES)
def test_cada_rol_existe_sin_atributos_indebidos(motor_admin, rol):
    fila = _fila_de_rol(motor_admin, rol)

    assert violaciones_de_rol(fila) == ()
    assert fila["rolsuper"] is False
    assert fila["rolbypassrls"] is False
    assert fila["rolcreaterole"] is False
    assert fila["rolcreatedb"] is False
    assert fila["rolreplication"] is False


@pytest.mark.parametrize("rol", ROLES_CON_LOGIN)
def test_los_roles_de_conexion_tienen_login(motor_admin, rol):
    assert _fila_de_rol(motor_admin, rol)["rolcanlogin"] is True


@pytest.mark.parametrize("rol", ROLES_DUENOS)
def test_los_duenos_de_funciones_no_tienen_login(motor_admin, rol):
    assert _fila_de_rol(motor_admin, rol)["rolcanlogin"] is False


def test_ningun_rol_es_miembro_de_otro_ni_tiene_miembros(motor_admin):
    with motor_admin.connect() as conexion:
        miembros = conexion.execute(
            text(
                "SELECT a.rolname, b.rolname FROM pg_auth_members m "
                "JOIN pg_roles a ON a.oid = m.member JOIN pg_roles b ON b.oid = m.roleid "
                "WHERE a.rolname = ANY(:roles) OR b.rolname = ANY(:roles)"
            ),
            {"roles": list(TODOS_LOS_ROLES)},
        ).all()

    assert miembros == []


def test_los_roles_son_distintos_y_ninguno_es_el_de_administracion(motor_admin):
    assert len(set(TODOS_LOS_ROLES)) == 4
    with motor_admin.connect() as conexion:
        actual = conexion.execute(text("SELECT current_user")).scalar_one()
    assert actual not in TODOS_LOS_ROLES


def test_ningun_rol_es_duenio_de_tablas_ni_de_esquemas(motor_admin):
    with motor_admin.connect() as conexion:
        de_tablas = conexion.execute(
            text(
                "SELECT count(*) FROM pg_class c JOIN pg_roles r ON r.oid = c.relowner "
                "WHERE r.rolname = ANY(:roles)"
            ),
            {"roles": list(TODOS_LOS_ROLES)},
        ).scalar_one()
        de_esquemas = conexion.execute(
            text(
                "SELECT count(*) FROM pg_namespace n JOIN pg_roles r ON r.oid = n.nspowner "
                "WHERE r.rolname = ANY(:roles)"
            ),
            {"roles": list(TODOS_LOS_ROLES)},
        ).scalar_one()

    assert de_tablas == 0
    assert de_esquemas == 0


@pytest.mark.parametrize("motor_fixture", ["motor_app", "motor_login"])
def test_los_roles_de_conexion_no_pueden_cambiar_de_rol(request, motor_fixture):
    motor = request.getfixturevalue(motor_fixture)
    propio = ROL_APP if motor_fixture == "motor_app" else ROL_LOGIN
    # `SET ROLE` al propio rol siempre se permite y no cambia nada: se excluye.
    for destino in (ROL_APP, ROL_LOGIN, ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN, "app"):
        if destino == propio:
            continue
        with motor.connect() as conexion:
            with pytest.raises((ProgrammingError, DBAPIError)):
                conexion.execute(text(f'SET ROLE "{destino}"'))


@pytest.mark.parametrize("motor_fixture", ["motor_app", "motor_login"])
def test_los_roles_de_conexion_no_pueden_crear_roles_ni_tablas(request, motor_fixture):
    motor = request.getfixturevalue(motor_fixture)
    for sentencia in (
        "CREATE ROLE rol_no_permitido",
        "CREATE TABLE public.tabla_no_permitida (id int)",
        "CREATE SCHEMA esquema_no_permitido",
    ):
        with motor.connect() as conexion:
            with pytest.raises((ProgrammingError, DBAPIError)):
                conexion.execute(text(sentencia))

"""Constantes de los roles de PostgreSQL y evaluacion pura de sus atributos (2.1, DD-01)."""

import pytest

from app.core import roles_bd
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


def _fila(nombre: str, **cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "rolname": nombre,
        "rolcanlogin": nombre in ROLES_CON_LOGIN,
        "rolsuper": False,
        "rolbypassrls": False,
        "rolcreaterole": False,
        "rolcreatedb": False,
        "rolreplication": False,
    }
    base.update(cambios)
    return base


def test_los_nombres_de_los_cuatro_roles_son_los_del_diseno():
    assert (ROL_APP, ROL_LOGIN, ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN) == (
        "turnos_app",
        "turnos_login",
        "turnos_acceso_previo",
        "turnos_acceso_login",
    )
    assert set(TODOS_LOS_ROLES) == {ROL_APP, ROL_LOGIN, ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN}
    assert set(ROLES_CON_LOGIN) == {ROL_APP, ROL_LOGIN}
    assert set(ROLES_DUENOS) == {ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN}


@pytest.mark.parametrize("nombre", TODOS_LOS_ROLES)
def test_un_rol_con_los_atributos_esperados_no_tiene_violaciones(nombre):
    assert violaciones_de_rol(_fila(nombre)) == ()


@pytest.mark.parametrize("nombre", TODOS_LOS_ROLES)
@pytest.mark.parametrize(
    ("columna", "codigo"),
    [
        ("rolbypassrls", "BYPASSRLS"),
        ("rolsuper", "SUPERUSER"),
        ("rolcreaterole", "CREATEROLE"),
        ("rolcreatedb", "CREATEDB"),
        ("rolreplication", "REPLICATION"),
    ],
)
def test_cada_atributo_indebido_se_informa_por_su_codigo(nombre, columna, codigo):
    assert violaciones_de_rol(_fila(nombre, **{columna: True})) == (codigo,)


@pytest.mark.parametrize("nombre", [ROL_APP, ROL_LOGIN])
def test_un_rol_de_conexion_sin_login_se_informa(nombre):
    assert violaciones_de_rol(_fila(nombre, rolcanlogin=False)) == ("SIN_LOGIN",)


@pytest.mark.parametrize("nombre", [ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN])
def test_un_duenio_con_login_se_informa(nombre):
    assert violaciones_de_rol(_fila(nombre, rolcanlogin=True)) == ("CON_LOGIN",)


def test_varias_violaciones_se_informan_juntas_y_ordenadas():
    fila = _fila(ROL_APP, rolsuper=True, rolbypassrls=True)

    assert violaciones_de_rol(fila) == ("SUPERUSER", "BYPASSRLS")


def test_un_nombre_que_no_es_de_los_cuatro_roles_se_rechaza():
    with pytest.raises(ValueError, match="rol no gestionado"):
        violaciones_de_rol(_fila("otro_rol"))


def test_el_modulo_no_importa_infraestructura():
    assert not hasattr(roles_bd, "create_engine")

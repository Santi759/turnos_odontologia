"""Guardia de rol de las conexiones de la API: evaluacion pura (4.4, DD-29, R2-05)."""

import pytest

from app.core import roles_bd
from app.core.roles_bd import ROL_ACCESO_LOGIN, ROL_APP, ROL_LOGIN


def _conexion(rol: str, **cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "usuario_actual": rol,
        "rolsuper": False,
        "rolbypassrls": False,
        "rolcreaterole": False,
        "rolcreatedb": False,
        "rolreplication": False,
        "duenio_de_objetos": False,
        "con_membresias": False,
        "lee_credencial": False,
        "escribe_credencial": False,
        "escribe_usuario": False,
        "ejecuta_buscar_cuenta": rol == ROL_LOGIN,
        "privilegio_en_tablas": False,
    }
    base.update(cambios)
    return base


@pytest.mark.parametrize("rol", [ROL_APP, ROL_LOGIN])
def test_la_conexion_correcta_no_tiene_violaciones(rol):
    assert roles_bd.violaciones_de_conexion(rol, _conexion(rol)) == ()


def test_un_rol_con_los_mismos_privilegios_pero_otro_nombre_se_rechaza():
    fila = _conexion("otro_rol_equivalente")

    assert roles_bd.violaciones_de_conexion(ROL_APP, fila) == ("ROL_INESPERADO",)


def test_el_rol_de_login_donde_se_espera_la_aplicacion_se_rechaza():
    violaciones = roles_bd.violaciones_de_conexion(ROL_APP, _conexion(ROL_LOGIN))

    assert "ROL_INESPERADO" in violaciones
    assert "EJECUTA_LOGIN" in violaciones


@pytest.mark.parametrize(
    ("rol", "cambios", "codigo"),
    [
        (ROL_APP, {"rolsuper": True}, "SUPERUSER"),
        (ROL_APP, {"rolbypassrls": True}, "BYPASSRLS"),
        (ROL_LOGIN, {"rolcreaterole": True}, "CREATEROLE"),
        (ROL_LOGIN, {"rolcreatedb": True}, "CREATEDB"),
        (ROL_APP, {"rolreplication": True}, "REPLICATION"),
        (ROL_APP, {"duenio_de_objetos": True}, "DUENIO_DE_OBJETOS"),
        (ROL_LOGIN, {"con_membresias": True}, "MEMBRESIAS"),
        (ROL_APP, {"lee_credencial": True}, "LEE_CREDENCIAL"),
        (ROL_APP, {"escribe_credencial": True}, "ESCRIBE_CREDENCIAL"),
        (ROL_LOGIN, {"escribe_credencial": True}, "ESCRIBE_CREDENCIAL"),
        (ROL_LOGIN, {"escribe_usuario": True}, "ESCRIBE_USUARIO"),
        (ROL_LOGIN, {"privilegio_en_tablas": True}, "TABLAS_ACCESIBLES"),
        (ROL_LOGIN, {"ejecuta_buscar_cuenta": False}, "SIN_BUSCAR_CUENTA"),
    ],
)
def test_cada_incumplimiento_se_informa_por_su_codigo(rol, cambios, codigo):
    assert codigo in roles_bd.violaciones_de_conexion(rol, _conexion(rol, **cambios))


def test_las_violaciones_no_incluyen_valores():
    fila = _conexion(ROL_APP, usuario_actual="secreto-ficticio", rolsuper=True)

    for codigo in roles_bd.violaciones_de_conexion(ROL_APP, fila):
        assert "secreto-ficticio" not in codigo


def test_solo_se_admiten_los_dos_roles_de_conexion():
    with pytest.raises(ValueError):
        roles_bd.violaciones_de_conexion(ROL_ACCESO_LOGIN, _conexion(ROL_ACCESO_LOGIN))

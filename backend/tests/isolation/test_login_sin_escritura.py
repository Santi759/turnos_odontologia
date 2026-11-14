"""El camino de login nunca escribe `usuario.credencial` (5.3; R2-01, R2-03; DD-26).

Primera parte (catalogo y sentencias directas) y segunda parte (login HTTP con los roles reales,
credencial byte a byte y `xmin`; sentencias del login sin escrituras sobre `usuario`).
"""

import re

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.roles_bd import (
    FUNCIONES_DE_LOGIN,
    ROL_ACCESO_LOGIN,
    ROL_ACCESO_PREVIO,
    ROL_APP,
    ROL_LOGIN,
)
from app.models.usuario import Rol
from app.schemas.auth import MAXIMO_CODIGO, MAXIMO_EMAIL

HMAC = b"\x02" * 32


def _sqlstate(error: BaseException) -> str:
    return getattr(getattr(error, "orig", None), "sqlstate", "") or ""


def test_la_funcion_de_rehash_no_existe_y_su_llamada_falla_sin_cambios(motor_admin, motor_login, datos_ab):
    with motor_admin.connect() as conexion:
        assert (
            conexion.execute(
                text(
                    "SELECT to_regprocedure("
                    "'acceso.reemplazar_credencial_por_rehash(uuid,uuid,text,text)')"
                )
            ).scalar_one()
            is None
        )
        antes = conexion.execute(text("SELECT id, credencial, xmin::text FROM usuario ORDER BY id")).all()

    with pytest.raises(DBAPIError) as info:
        with motor_login.begin() as conexion:
            conexion.execute(
                text(
                    "SELECT acceso.reemplazar_credencial_por_rehash("
                    "gen_random_uuid(), gen_random_uuid(), 'x', 'y')"
                )
            )
    assert _sqlstate(info.value) == "42883"  # undefined_function

    with motor_admin.connect() as conexion:
        despues = conexion.execute(text("SELECT id, credencial, xmin::text FROM usuario ORDER BY id")).all()
    assert despues == antes


def test_ninguna_funcion_ejecutable_por_turnos_login_pertenece_a_un_rol_con_escritura_en_usuario(
    motor_admin, base_en_head
):
    with motor_admin.connect() as conexion:
        filas = conexion.execute(
            text(
                "SELECT p.proname, r.rolname, "
                "has_table_privilege(r.oid, 'public.usuario', 'UPDATE') AS upd_tabla, "
                "has_table_privilege(r.oid, 'public.usuario', 'INSERT') AS ins_tabla, "
                "has_table_privilege(r.oid, 'public.usuario', 'DELETE') AS del_tabla, "
                "has_column_privilege(r.oid, 'public.usuario', 'credencial', 'UPDATE') AS upd_col "
                "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                "JOIN pg_roles r ON r.oid = p.proowner "
                "WHERE n.nspname = 'acceso' AND has_function_privilege(:login, p.oid, 'EXECUTE')"
            ),
            {"login": ROL_LOGIN},
        ).all()

    assert {fila.proname for fila in filas} == set(FUNCIONES_DE_LOGIN)
    for fila in filas:
        assert fila.rolname == ROL_ACCESO_LOGIN
        assert (fila.upd_tabla, fila.ins_tabla, fila.del_tabla, fila.upd_col) == (
            False,
            False,
            False,
            False,
        )
        assert "rehash" not in fila.proname


@pytest.mark.parametrize("rol", [ROL_LOGIN, ROL_ACCESO_LOGIN, ROL_APP, ROL_ACCESO_PREVIO])
def test_ningun_rol_del_camino_de_la_api_escribe_usuario(motor_admin, rol):
    with motor_admin.connect() as conexion:
        for privilegio in ("INSERT", "UPDATE", "DELETE"):
            assert not conexion.execute(
                text("SELECT has_table_privilege(:r, 'public.usuario', :p)"),
                {"r": rol, "p": privilegio},
            ).scalar_one()
        for privilegio in ("INSERT", "UPDATE"):
            assert not conexion.execute(
                text("SELECT has_column_privilege(:r, 'public.usuario', 'credencial', :p)"),
                {"r": rol, "p": privilegio},
            ).scalar_one()


def test_ningun_rol_nuevo_tiene_politica_de_actualizacion_sobre_usuario(motor_admin):
    with motor_admin.connect() as conexion:
        politicas = conexion.execute(
            text(
                "SELECT polname, polcmd, polroles::regrole[]::text[] FROM pg_policy "
                "WHERE polrelid = 'public.usuario'::regclass ORDER BY polname"
            )
        ).all()

    assert all(p.polcmd in ("*", "r") for p in politicas)
    for nombre, comando, _roles in politicas:
        assert comando != "w", nombre  # ninguna FOR UPDATE
        assert comando != "d", nombre


@pytest.mark.parametrize("motor_fixture", ["motor_login", "motor_app"])
def test_update_de_credencial_falla_para_los_roles_de_conexion(request, motor_fixture, datos_ab, motor_admin):
    motor = request.getfixturevalue(motor_fixture)
    with motor_admin.connect() as conexion:
        antes = conexion.execute(text("SELECT credencial, xmin::text FROM usuario ORDER BY id")).all()

    with pytest.raises(DBAPIError) as info:
        with motor.begin() as conexion:
            conexion.execute(text("UPDATE usuario SET credencial = 'otra'"))

    assert _sqlstate(info.value) == "42501"
    with motor_admin.connect() as conexion:
        assert conexion.execute(text("SELECT credencial, xmin::text FROM usuario ORDER BY id")).all() == antes


def test_buscar_cuenta_acota_las_longitudes_de_codigo_y_email(motor_login, datos_ab):
    def buscar(codigo: str, email: str):
        with motor_login.begin() as conexion:
            return conexion.execute(
                text("SELECT * FROM acceso.buscar_cuenta(:c, :e)"), {"c": codigo, "e": email}
            ).one()

    # En el limite: valido (sin cuenta).
    assert buscar("a" * MAXIMO_CODIGO, "a@example.test").o_usuario_id is None
    assert buscar("codigo", "a" * (MAXIMO_EMAIL - 5) + "@x.ts").o_usuario_id is None
    for codigo, email in (
        ("a" * (MAXIMO_CODIGO + 1), "a@example.test"),
        ("codigo", "a" * (MAXIMO_EMAIL + 1)),
    ):
        with pytest.raises(DBAPIError) as info:
            buscar(codigo, email)
        assert _sqlstate(info.value) == "22023"


def test_buscar_cuenta_devuelve_la_credencial_solo_de_cuentas_utilizables(motor_login, motor_admin, datos_ab):
    usuario = datos_ab.a.usuarios[Rol.SECRETARIA]

    def credencial():
        with motor_login.begin() as conexion:
            return conexion.execute(
                text("SELECT o_credencial, o_usuario_id FROM acceso.buscar_cuenta(:c, :e)"),
                {"c": datos_ab.a.codigo, "e": usuario.email},
            ).one()

    activa = credencial()
    assert activa.o_credencial is not None and activa.o_credencial.startswith("$argon2")
    assert activa.o_usuario_id == usuario.id

    with motor_admin.begin() as conexion:
        conexion.execute(text("UPDATE usuario SET activo = false WHERE id = :i"), {"i": usuario.id})
    assert credencial().o_credencial is None

    with motor_admin.begin() as conexion:
        conexion.execute(text("UPDATE usuario SET activo = true WHERE id = :i"), {"i": usuario.id})
        conexion.execute(text("UPDATE consultorio SET activo = false WHERE id = :i"), {"i": datos_ab.a.id})
    assert credencial().o_credencial is None

    with motor_admin.begin() as conexion:
        conexion.execute(text("UPDATE consultorio SET activo = true WHERE id = :i"), {"i": datos_ab.a.id})
        conexion.execute(text("UPDATE usuario SET credencial = NULL WHERE id = :i"), {"i": usuario.id})
    sin_credencial = credencial()
    assert sin_credencial.o_credencial is None
    assert sin_credencial.o_usuario_id == usuario.id


def test_buscar_cuenta_inexistente_no_devuelve_cuenta(motor_login, datos_ab):
    with motor_login.begin() as conexion:
        fila = conexion.execute(
            text("SELECT * FROM acceso.buscar_cuenta('no-existe', 'nadie@example.test')")
        ).one()

    assert all(valor is None for valor in fila)


# --- Segunda parte: login HTTP con los roles reales (R2-01, DD-26) ---------------------------------


def _hasher_real(time_cost: int):
    from argon2 import PasswordHasher, Type

    return PasswordHasher(
        time_cost=time_cost, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID
    )


def _api_con_verificador_real(url_app, url_login):
    from app.auth.contrasenas import VerificadorContrasenas
    from tests.isolation.conftest import construir_api

    return construir_api(url_app, url_login, verificador=VerificadorContrasenas())  # type: ignore[arg-type]


def _fijar_hash(motor_admin, usuario_id, hash_: str) -> None:
    with motor_admin.begin() as conexion:
        conexion.execute(
            text("UPDATE usuario SET credencial = :h WHERE id = :i"), {"h": hash_, "i": usuario_id}
        )


def _huella(motor_admin, usuario_id):
    with motor_admin.connect() as conexion:
        return conexion.execute(
            text("SELECT credencial, xmin::text FROM usuario WHERE id = :i"), {"i": usuario_id}
        ).one()


def test_login_http_con_hash_anterior_vigente_y_rechazado_deja_la_credencial_y_el_xmin_intactos(
    url_app, url_login, datos_ab, motor_admin
):
    from sqlalchemy import event

    consultorio = datos_ab.a
    usuario = consultorio.usuarios[Rol.SECRETARIA]
    api = _api_con_verificador_real(url_app, url_login)
    sentencias: list[str] = []
    for motor in (api.app.state.engine, api.app.state.engine_login):
        event.listen(
            motor,
            "before_cursor_execute",
            lambda c, cur, sentencia, *r: sentencias.append(sentencia),
        )
    try:
        for hash_, contrasena, esperado in (
            (_hasher_real(2).hash(usuario.contrasena), usuario.contrasena, 200),  # parametros anteriores (t=2)
            (_hasher_real(3).hash(usuario.contrasena), usuario.contrasena, 200),  # parametros vigentes
            (_hasher_real(2).hash(usuario.contrasena), "contrasena-incorrecta-1", 401),
        ):
            _fijar_hash(motor_admin, usuario.id, hash_)
            antes = _huella(motor_admin, usuario.id)

            respuesta = api.login(api.cliente(), consultorio.codigo, usuario.email, contrasena)

            assert respuesta.status_code == esperado
            assert _huella(motor_admin, usuario.id) == antes  # credencial byte a byte y xmin
    finally:
        api.app.state.engine.dispose()
        api.app.state.engine_login.dispose()

    escrituras = [
        s for s in sentencias if re.search(r"\b(UPDATE|INSERT\s+INTO|DELETE\s+FROM)\s+(public\.)?usuario\b", s, re.I)
    ]
    assert escrituras == []
    assert any("acceso.buscar_cuenta" in s for s in sentencias)  # el login si paso por la funcion

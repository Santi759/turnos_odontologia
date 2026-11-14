"""Migracion 0004 (aislamiento por roles y RLS) sobre db-test (3.1, DD-13).

Todo ocurre en la base de PRUEBAS efimera. Las pruebas que alteran un rol del cluster lo
restauran en `finally`. La verificacion previa de roles debe dejar la base en `0003` sin cambios.
"""

import secrets
from collections.abc import Iterator

import pytest
from alembic import command
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.roles_bd import (
    ROL_ACCESO_LOGIN,
    ROL_ACCESO_PREVIO,
    ROL_APP,
    ROL_LOGIN,
    TODOS_LOS_ROLES,
)
from tests.integration.datos_auth import (
    AHORA,
    crear_consultorio,
    crear_usuario,
    insertar_fallo,
    insertar_sesion,
)

TABLAS = ("consultorio", "usuario", "sesion", "intento_login")


@pytest.fixture
def base_en_0003(motor: Engine, config_alembic) -> Iterator[Engine]:
    """Base de PRUEBAS en la revision 0003; al terminar la deja en `head`."""
    command.downgrade(config_alembic, "base")
    command.upgrade(config_alembic, "0003")
    try:
        yield motor
    finally:
        command.downgrade(config_alembic, "base")
        command.upgrade(config_alembic, "head")


def _revision(motor: Engine) -> str | None:
    with motor.connect() as conexion:
        return conexion.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()


def _existe_esquema_acceso(motor: Engine) -> bool:
    with motor.connect() as conexion:
        return conexion.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'acceso')")
        ).scalar_one()


def _ddl_de_rol(motor: Engine, sentencia: str) -> None:
    with motor.begin() as conexion:
        conexion.execute(text(sentencia))


def _huella(motor: Engine) -> dict[str, tuple[int, str | None]]:
    huella: dict[str, tuple[int, str | None]] = {}
    with motor.connect() as conexion:
        for tabla in TABLAS:
            huella[tabla] = tuple(  # type: ignore[assignment]
                conexion.execute(
                    text(f"SELECT count(*), md5(string_agg(t::text, '|' ORDER BY t::text)) FROM {tabla} t")
                ).one()
            )
    return huella


def _catalogo(motor: Engine) -> dict[str, list]:
    """Instantanea normalizada del catalogo que 0004 toca (ACL nulas = ACL por defecto)."""
    consultas = {
        "tablas": (
            "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, "
            "COALESCE(c.relacl, acldefault('r', c.relowner))::text "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' ORDER BY 1"
        ),
        "columnas": (
            "SELECT c.relname, a.attname, a.attacl::text FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' AND a.attnum > 0 "
            "AND NOT a.attisdropped AND a.attacl IS NOT NULL ORDER BY 1, 2"
        ),
        "politicas": (
            "SELECT tablename, policyname, cmd, roles::text, qual, with_check "
            "FROM pg_policies WHERE schemaname = 'public' ORDER BY 1, 2"
        ),
        "esquemas": (
            "SELECT nspname, COALESCE(nspacl, acldefault('n', nspowner))::text "
            "FROM pg_namespace WHERE nspname IN ('public', 'acceso') ORDER BY 1"
        ),
        "funciones": (
            "SELECT p.proname, pg_get_userbyid(p.proowner), p.prosecdef, p.proconfig::text, p.proacl::text "
            "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'acceso' ORDER BY 1"
        ),
    }
    with motor.connect() as conexion:
        return {nombre: [tuple(f) for f in conexion.execute(text(sql))] for nombre, sql in consultas.items()}


def _roles_existentes(motor: Engine) -> set[str]:
    with motor.connect() as conexion:
        filas = conexion.execute(
            text("SELECT rolname FROM pg_roles WHERE rolname = ANY(:n)"), {"n": list(TODOS_LOS_ROLES)}
        )
        return {f[0] for f in filas}


def _subir_esperando_fallo(config, motor: Engine, nombre_en_mensaje: str | None) -> None:
    with pytest.raises(DBAPIError) as error:
        command.upgrade(config, "0004")
    if nombre_en_mensaje is not None:
        assert nombre_en_mensaje in str(error.value.orig)
    assert _revision(motor) == "0003"
    assert not _existe_esquema_acceso(motor)


# --- Roles ausentes ---------------------------------------------------------------------------


@pytest.mark.parametrize("rol", TODOS_LOS_ROLES)
def test_roles_ausentes_la_subida_falla_nombrando_el_rol_y_deja_0003(base_en_0003, config_alembic, rol):
    temporal = f"{rol}_ausente_{secrets.token_hex(2)}"
    _ddl_de_rol(base_en_0003, f"ALTER ROLE {rol} RENAME TO {temporal}")
    try:
        _subir_esperando_fallo(config_alembic, base_en_0003, rol)
    finally:
        _ddl_de_rol(base_en_0003, f"ALTER ROLE {temporal} RENAME TO {rol}")
    assert _roles_existentes(base_en_0003) == set(TODOS_LOS_ROLES)


# --- Roles con atributos o membresias indebidos -----------------------------------------------


@pytest.mark.parametrize(
    ("rol", "alterar", "restaurar"),
    [
        (ROL_APP, "BYPASSRLS", "NOBYPASSRLS"),
        (ROL_APP, "CREATEDB", "NOCREATEDB"),
        (ROL_LOGIN, "SUPERUSER", "NOSUPERUSER"),
        (ROL_LOGIN, "CREATEROLE", "NOCREATEROLE"),
        (ROL_ACCESO_PREVIO, "LOGIN", "NOLOGIN"),
        (ROL_ACCESO_LOGIN, "REPLICATION", "NOREPLICATION"),
        (ROL_APP, "NOLOGIN", "LOGIN"),
    ],
)
def test_atributos_indebidos_la_subida_falla_nombrando_el_rol(
    base_en_0003, config_alembic, rol, alterar, restaurar
):
    _ddl_de_rol(base_en_0003, f"ALTER ROLE {rol} {alterar}")
    try:
        _subir_esperando_fallo(config_alembic, base_en_0003, rol)
    finally:
        _ddl_de_rol(base_en_0003, f"ALTER ROLE {rol} {restaurar}")


@pytest.mark.parametrize(
    ("miembro", "grupo"),
    [(ROL_LOGIN, ROL_APP), (ROL_APP, "pg_read_all_data"), (ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN)],
)
def test_membresias_indebidas_la_subida_falla(base_en_0003, config_alembic, miembro, grupo):
    _ddl_de_rol(base_en_0003, f"GRANT {grupo} TO {miembro}")
    try:
        _subir_esperando_fallo(config_alembic, base_en_0003, None)
    finally:
        _ddl_de_rol(base_en_0003, f"REVOKE {grupo} FROM {miembro}")


def test_un_rol_dueno_de_objetos_impide_la_subida(base_en_0003, config_alembic):
    _ddl_de_rol(base_en_0003, f"CREATE TABLE tabla_ajena_a_c04 (id int)")
    _ddl_de_rol(base_en_0003, f"ALTER TABLE tabla_ajena_a_c04 OWNER TO {ROL_LOGIN}")
    try:
        _subir_esperando_fallo(config_alembic, base_en_0003, ROL_LOGIN)
    finally:
        _ddl_de_rol(base_en_0003, "DROP TABLE tabla_ajena_a_c04")


# --- Subida con datos previos -----------------------------------------------------------------


def _sembrar_datos_previos(motor: Engine) -> None:
    with Session(motor) as sesion:
        for letra in ("a", "b"):
            consultorio = crear_consultorio(sesion, f"previo-{letra}-{secrets.token_hex(2)}")
            usuario = crear_usuario(sesion, consultorio, email=f"previo.{letra}@example.test")
            insertar_sesion(sesion, consultorio, usuario)
        insertar_fallo(sesion, secrets.token_bytes(32), secrets.token_bytes(32), AHORA)
        sesion.commit()


def test_subida_desde_0003_con_datos_previos_no_modifica_ninguna_fila(base_en_0003, config_alembic):
    _sembrar_datos_previos(base_en_0003)
    antes = _huella(base_en_0003)
    assert antes["consultorio"][0] == 2 and antes["intento_login"][0] == 1

    command.upgrade(config_alembic, "0004")

    assert _revision(base_en_0003) == "0004"
    assert _huella(base_en_0003) == antes


def test_la_subida_crea_el_esquema_acceso_y_activa_rls_forzada(base_en_0003, config_alembic):
    command.upgrade(config_alembic, "0004")

    assert _existe_esquema_acceso(base_en_0003)
    with base_en_0003.connect() as conexion:
        filas = conexion.execute(
            text(
                "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE relname = ANY(:t) AND relkind = 'r' ORDER BY 1"
            ),
            {"t": list(TABLAS)},
        ).all()
    assert [tuple(f) for f in filas] == [(t, True, True) for t in sorted(TABLAS)]


# --- Bajada a 0003 ----------------------------------------------------------------------------


def test_la_bajada_a_0003_restaura_el_catalogo_y_conserva_los_roles(base_en_0003, config_alembic):
    antes = _catalogo(base_en_0003)

    command.upgrade(config_alembic, "0004")
    en_0004 = _catalogo(base_en_0003)
    assert en_0004 != antes  # control: la migracion cambia el catalogo
    command.downgrade(config_alembic, "0003")

    assert _revision(base_en_0003) == "0003"
    assert _catalogo(base_en_0003) == antes
    assert _roles_existentes(base_en_0003) == set(TODOS_LOS_ROLES)

    command.upgrade(config_alembic, "0004")
    assert _catalogo(base_en_0003) == en_0004


def test_la_bajada_conserva_las_filas(base_en_0003, config_alembic):
    _sembrar_datos_previos(base_en_0003)
    command.upgrade(config_alembic, "0004")
    antes = _huella(base_en_0003)

    command.downgrade(config_alembic, "0003")

    assert _huella(base_en_0003) == antes


# --- UNIQUE (consultorio_id, id) en sesion (DD-08, decision del autor 2026-11-10) -------------


def _clave_compuesta_de_sesion(motor: Engine) -> list[str]:
    with motor.connect() as conexion:
        return list(
            conexion.execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = 'public.sesion'::regclass AND contype = 'u' "
                    "AND conname = 'uq_sesion_consultorio_id_id'"
                )
            ).scalars()
        )


def test_la_subida_crea_uq_sesion_consultorio_id_id(base_en_0003, config_alembic):
    assert _clave_compuesta_de_sesion(base_en_0003) == []

    command.upgrade(config_alembic, "0004")

    assert _clave_compuesta_de_sesion(base_en_0003) == ["UNIQUE (consultorio_id, id)"]


def test_la_bajada_elimina_uq_sesion_y_conserva_la_unicidad_del_token(base_en_0003, config_alembic):
    command.upgrade(config_alembic, "0004")
    command.downgrade(config_alembic, "0003")

    assert _clave_compuesta_de_sesion(base_en_0003) == []
    with base_en_0003.connect() as conexion:
        restantes = conexion.execute(
            text(
                "SELECT conname FROM pg_constraint WHERE conrelid = 'public.sesion'::regclass "
                "AND contype = 'u' ORDER BY 1"
            )
        ).scalars().all()
    assert restantes == ["uq_sesion_token_hmac"]

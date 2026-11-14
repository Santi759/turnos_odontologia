"""Matriz de privilegios con conexiones reales (3.5, DD-07, DD-25; delta `aislamiento-base-de-datos`).

Compara, rol por rol, el privilegio EFECTIVO por tabla y columna (`has_*_privilege`) con la
matriz de `design.md`: ni de mas ni de menos. Solo contra `db-test`.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.roles_bd import (
    FUNCIONES_DE_LOGIN,
    FUNCIONES_DE_SESION,
    ROL_ACCESO_LOGIN,
    ROL_ACCESO_PREVIO,
    ROL_APP,
    ROL_LOGIN,
    TODOS_LOS_ROLES,
)

TABLAS = ("consultorio", "usuario", "sesion", "intento_login", "alembic_version")
TODAS = "*"

_SESION_LECTURA = {
    "id", "consultorio_id", "usuario_id", "creada_en", "ultimo_uso_en", "vence_absoluto_en",
    "revocada_en",
}
_SESION_INSERCION = {
    "consultorio_id", "usuario_id", "token_hmac", "creada_en", "ultimo_uso_en",
    "vence_absoluto_en",
}

# rol -> (tabla, privilegio) -> columnas con ese privilegio ("*" = todas).
ESPERADO: dict[str, dict[tuple[str, str], object]] = {
    ROL_APP: {
        ("consultorio", "SELECT"): TODAS,
        ("usuario", "SELECT"): {
            "id", "consultorio_id", "email", "nombre", "rol", "activo", "creado_en",
        },
        ("sesion", "SELECT"): _SESION_LECTURA,
        ("sesion", "INSERT"): _SESION_INSERCION,
        ("sesion", "UPDATE"): {"revocada_en"},
    },
    ROL_LOGIN: {},
    ROL_ACCESO_PREVIO: {
        ("consultorio", "SELECT"): {"id", "nombre", "activo"},
        ("usuario", "SELECT"): {"id", "consultorio_id", "email", "nombre", "rol", "activo"},
        ("sesion", "SELECT"): TODAS,
        ("sesion", "UPDATE"): {"ultimo_uso_en", "revocada_en"},
    },
    ROL_ACCESO_LOGIN: {
        ("consultorio", "SELECT"): {"id", "codigo", "nombre", "activo"},
        ("usuario", "SELECT"): {
            "id", "consultorio_id", "email", "nombre", "rol", "credencial", "activo",
        },
        ("intento_login", "SELECT"): TODAS,
        ("intento_login", "INSERT"): {"clave_cuenta", "clave_ip", "ocurrido_en"},
        ("intento_login", "UPDATE"): {"descartado_para_cuenta"},
    },
}
# Privilegios de tabla completos (DELETE, TRUNCATE, TRIGGER no existen por columna).
ESPERADO_TABLA = {
    ROL_APP: set(),
    ROL_LOGIN: set(),
    ROL_ACCESO_PREVIO: {("sesion", "DELETE")},
    ROL_ACCESO_LOGIN: {("intento_login", "DELETE")},
}
PRIVILEGIOS_DE_COLUMNA = ("SELECT", "INSERT", "UPDATE", "REFERENCES")
PRIVILEGIOS_DE_TABLA = ("DELETE", "TRUNCATE", "TRIGGER")


def _columnas(motor_admin) -> dict[str, list[str]]:
    with motor_admin.connect() as conexion:
        filas = conexion.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = ANY(:t)"
            ),
            {"t": list(TABLAS)},
        ).all()
    columnas: dict[str, list[str]] = {t: [] for t in TABLAS}
    for tabla, columna in filas:
        columnas[tabla].append(columna)
    return columnas


def _efectivos(motor_admin, rol: str) -> tuple[dict, set]:
    columnas = _columnas(motor_admin)
    por_columna: dict[tuple[str, str], set[str]] = {}
    por_tabla: set[tuple[str, str]] = set()
    with motor_admin.connect() as conexion:
        for tabla, lista in columnas.items():
            for privilegio in PRIVILEGIOS_DE_TABLA:
                if conexion.execute(
                    text("SELECT has_table_privilege(:r, :t, :p)"),
                    {"r": rol, "t": f"public.{tabla}", "p": privilegio},
                ).scalar_one():
                    por_tabla.add((tabla, privilegio))
            for privilegio in PRIVILEGIOS_DE_COLUMNA:
                con = {
                    c
                    for c in lista
                    if conexion.execute(
                        text("SELECT has_column_privilege(:r, :t, :c, :p)"),
                        {"r": rol, "t": f"public.{tabla}", "c": c, "p": privilegio},
                    ).scalar_one()
                }
                if con:
                    por_columna[(tabla, privilegio)] = con
    return por_columna, por_tabla


@pytest.mark.parametrize("rol", TODOS_LOS_ROLES)
def test_privilegios_efectivos_exactamente_iguales_a_la_matriz(motor_admin, rol):
    columnas = _columnas(motor_admin)
    esperado = {
        clave: set(columnas[clave[0]]) if valor == TODAS else set(valor)
        for clave, valor in ESPERADO[rol].items()
    }

    por_columna, por_tabla = _efectivos(motor_admin, rol)

    assert por_columna == esperado
    assert por_tabla == ESPERADO_TABLA[rol]


@pytest.mark.parametrize("rol", TODOS_LOS_ROLES)
def test_las_columnas_esperadas_existen(motor_admin, rol):
    # Si una columna esperada no existiera, la igualdad anterior seria vacua en esa fila.
    columnas = _columnas(motor_admin)
    for (tabla, _privilegio), valor in ESPERADO[rol].items():
        if valor != TODAS:
            assert set(valor) <= set(columnas[tabla])


def test_ningun_rol_de_la_api_puede_escribir_la_credencial(motor_admin):
    with motor_admin.connect() as conexion:
        for rol in TODOS_LOS_ROLES:
            for privilegio in ("INSERT", "UPDATE", "REFERENCES"):
                assert (
                    conexion.execute(
                        text(
                            "SELECT has_column_privilege(:r, 'public.usuario', 'credencial', :p)"
                        ),
                        {"r": rol, "p": privilegio},
                    ).scalar_one()
                    is False
                )


def test_solo_turnos_acceso_login_lee_la_credencial(motor_admin):
    with motor_admin.connect() as conexion:
        lectores = [
            rol
            for rol in TODOS_LOS_ROLES
            if conexion.execute(
                text("SELECT has_column_privilege(:r, 'public.usuario', 'credencial', 'SELECT')"),
                {"r": rol},
            ).scalar_one()
        ]

    assert lectores == [ROL_ACCESO_LOGIN]


def test_nadie_lee_token_hmac_ni_alembic_version_fuera_de_la_administracion(motor_admin):
    with motor_admin.connect() as conexion:
        for rol in (ROL_APP, ROL_LOGIN, ROL_ACCESO_LOGIN):
            assert (
                conexion.execute(
                    text("SELECT has_column_privilege(:r, 'public.sesion', 'token_hmac', 'SELECT')"),
                    {"r": rol},
                ).scalar_one()
                is False
            )
        for rol in TODOS_LOS_ROLES:
            assert (
                conexion.execute(
                    text("SELECT has_table_privilege(:r, 'public.alembic_version', 'SELECT')"),
                    {"r": rol},
                ).scalar_one()
                is False
            )


# --- Esquemas y funciones -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rol", "esquema", "uso_esperado"),
    [
        (ROL_APP, "public", True),
        (ROL_APP, "acceso", True),
        (ROL_LOGIN, "acceso", True),
        (ROL_ACCESO_PREVIO, "public", True),
        (ROL_ACCESO_PREVIO, "acceso", False),
        (ROL_ACCESO_LOGIN, "public", True),
        (ROL_ACCESO_LOGIN, "acceso", False),
    ],
)
def test_uso_de_esquemas_y_nunca_creacion(motor_admin, rol, esquema, uso_esperado):
    with motor_admin.connect() as conexion:
        uso = conexion.execute(
            text("SELECT has_schema_privilege(:r, :e, 'USAGE')"), {"r": rol, "e": esquema}
        ).scalar_one()
        crear = conexion.execute(
            text("SELECT has_schema_privilege(:r, :e, 'CREATE')"), {"r": rol, "e": esquema}
        ).scalar_one()

    assert uso is uso_esperado
    assert crear is False


def test_turnos_login_sin_creacion_en_ningun_esquema(motor_admin):
    with motor_admin.connect() as conexion:
        for esquema in ("public", "acceso"):
            assert (
                conexion.execute(
                    text("SELECT has_schema_privilege(:r, :e, 'CREATE')"),
                    {"r": ROL_LOGIN, "e": esquema},
                ).scalar_one()
                is False
            )


def _ejecutables(motor_admin, rol: str) -> set[str]:
    with motor_admin.connect() as conexion:
        filas = conexion.execute(
            text(
                "SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname IN ('public', 'acceso') "
                "AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = p.oid "
                "AND d.deptype = 'e') "
                "AND has_function_privilege(:r, p.oid, 'EXECUTE')"
            ),
            {"r": rol},
        ).all()
    return {fila[0] for fila in filas}


@pytest.mark.parametrize(
    ("rol", "permitidas"),
    [
        (ROL_APP, set(FUNCIONES_DE_SESION)),
        (ROL_LOGIN, set(FUNCIONES_DE_LOGIN)),
        # Cada dueno ejecuta solo las suyas (privilegio implicito del dueno).
        (ROL_ACCESO_PREVIO, set(FUNCIONES_DE_SESION)),
        (ROL_ACCESO_LOGIN, set(FUNCIONES_DE_LOGIN)),
    ],
)
def test_ejecucion_de_funciones_exactamente_la_de_la_matriz(motor_admin, rol, permitidas):
    assert _ejecutables(motor_admin, rol) == permitidas


# --- Conexiones reales: lo denegado se niega de verdad --------------------------------------


def _sqlstate(motor, sentencia: str) -> str:
    with motor.connect() as conexion:
        with pytest.raises(DBAPIError) as info:
            conexion.execute(text(sentencia))
    return getattr(info.value.orig, "sqlstate", None) or getattr(info.value.orig, "pgcode", "")


@pytest.mark.parametrize(
    "sentencia",
    [
        "SELECT credencial FROM usuario",
        "SELECT * FROM usuario",
        "SELECT token_hmac FROM sesion",
        "SELECT * FROM sesion",
        "SELECT * FROM intento_login",
        "SELECT * FROM alembic_version",
        "UPDATE usuario SET credencial = 'x'",
        "UPDATE usuario SET nombre = 'x'",
        "INSERT INTO usuario (consultorio_id, email, nombre, rol) "
        "VALUES (gen_random_uuid(), 'a@example.test', 'n', 'admin')",
        "DELETE FROM sesion",
        "DELETE FROM usuario",
        "INSERT INTO intento_login (clave_cuenta, clave_ip, ocurrido_en) "
        "VALUES (decode('00', 'hex'), decode('00', 'hex'), now())",
        "UPDATE consultorio SET nombre = 'x'",
        "TRUNCATE sesion",
    ],
)
def test_turnos_app_recibe_42501_en_lo_denegado(motor_app, datos_ab, sentencia):
    assert _sqlstate(motor_app, sentencia) == "42501"


@pytest.mark.parametrize(
    "sentencia",
    [
        "SELECT id FROM consultorio",
        "SELECT id FROM usuario",
        "SELECT id FROM sesion",
        "SELECT id FROM intento_login",
        "SELECT credencial FROM usuario",
        "UPDATE usuario SET credencial = 'x'",
        "INSERT INTO sesion (consultorio_id) VALUES (gen_random_uuid())",
        "DELETE FROM sesion",
        "SELECT * FROM alembic_version",
    ],
)
def test_turnos_login_no_tiene_acceso_a_ninguna_tabla(motor_login, datos_ab, sentencia):
    assert _sqlstate(motor_login, sentencia) == "42501"


def test_turnos_login_si_puede_consultar_sin_tablas(motor_login):
    with motor_login.connect() as conexion:
        assert conexion.execute(text("SELECT 1")).scalar_one() == 1


def test_turnos_app_lee_lo_permitido_con_contexto(motor_app, datos_ab):
    with motor_app.begin() as conexion:
        conexion.execute(
            text("SELECT set_config('app.consultorio_id', :c, true)"), {"c": str(datos_ab.a.id)}
        )
        usuarios = conexion.execute(
            text("SELECT id, email, nombre, rol, activo FROM usuario")
        ).all()
        sesiones = conexion.execute(text("SELECT id, revocada_en FROM sesion")).all()
        consultorios = conexion.execute(text("SELECT * FROM consultorio")).all()

    assert len(usuarios) == 3
    assert sesiones == []
    assert len(consultorios) == 1


def test_complemento_con_set_role_desde_administracion(motor_admin, datos_ab):
    """La misma denegacion vista con SET ROLE (administracion; transaccion siempre revertida)."""
    with motor_admin.connect() as conexion:
        transaccion = conexion.begin()
        try:
            conexion.execute(text(f'SET LOCAL ROLE "{ROL_APP}"'))
            with pytest.raises(DBAPIError):
                with conexion.begin_nested():
                    conexion.execute(text("SELECT credencial FROM usuario"))
            conexion.execute(text(f'SET LOCAL ROLE "{ROL_LOGIN}"'))
            with pytest.raises(DBAPIError):
                with conexion.begin_nested():
                    conexion.execute(text("SELECT id FROM consultorio"))
        finally:
            transaccion.rollback()

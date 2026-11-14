"""Funciones del esquema `acceso` con conexiones reales (5.1; DD-09, DD-25; delta `acceso-previo-al-contexto`).

Catalogo (dueno, `SECURITY DEFINER`, `search_path`, ACL de un unico rol, sin parametros `uuid`,
una fila, `plpgsql`, sin SQL dinamico) y casos de abuso (HMAC de 31 y 33 bytes, instantes futuros,
conteos acotados a la clave, limpieza de a lo sumo 100). Solo contra `db-test`.
"""

import os
import re
import secrets
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.core.roles_bd import (
    FUNCIONES_DE_LOGIN,
    FUNCIONES_DE_SESION,
    ROL_ACCESO_LOGIN,
    ROL_ACCESO_PREVIO,
    ROL_APP,
    ROL_LOGIN,
)

DUENO = {
    **{nombre: ROL_ACCESO_LOGIN for nombre in FUNCIONES_DE_LOGIN},
    **{nombre: ROL_ACCESO_PREVIO for nombre in FUNCIONES_DE_SESION},
}
EJECUTA = {
    **{nombre: ROL_LOGIN for nombre in FUNCIONES_DE_LOGIN},
    **{nombre: ROL_APP for nombre in FUNCIONES_DE_SESION},
}
HMAC_OK = b"\x01" * 32
AHORA = lambda: datetime.now(UTC)  # noqa: E731

# Llamada valida por funcion (para probar la denegacion de privilegios con argumentos correctos).
LLAMADAS = {
    "buscar_cuenta": ("SELECT * FROM acceso.buscar_cuenta('codigo', 'a@example.test')", {}),
    "registrar_fallo": (
        "SELECT acceso.registrar_fallo(:k, :i, :t)",
        {"k": HMAC_OK, "i": HMAC_OK, "t": None},
    ),
    "fallos_de_cuenta": ("SELECT acceso.fallos_de_cuenta(:k, :t)", {"k": HMAC_OK, "t": None}),
    "fallos_de_ip": ("SELECT acceso.fallos_de_ip(:k, :t)", {"k": HMAC_OK, "t": None}),
    "descartar_fallos_de_cuenta": ("SELECT acceso.descartar_fallos_de_cuenta(:k)", {"k": HMAC_OK}),
    "limpiar_intentos": ("SELECT acceso.limpiar_intentos(:t)", {"t": None}),
    "resolver_sesion": ("SELECT * FROM acceso.resolver_sesion(:k)", {"k": HMAC_OK}),
    "renovar_sesion": ("SELECT acceso.renovar_sesion(:k, :t)", {"k": HMAC_OK, "t": None}),
    "revocar_sesion_por_token": (
        "SELECT acceso.revocar_sesion_por_token(:k, :t)",
        {"k": HMAC_OK, "t": None},
    ),
    "limpiar_sesiones": ("SELECT acceso.limpiar_sesiones(:t, 30)", {"t": None}),
}


def _llamar(motor, nombre: str, **cambios):
    sentencia, params = LLAMADAS[nombre]
    params = {k: (AHORA() if v is None and k == "t" else v) for k, v in params.items()}
    params.update(cambios)
    with motor.begin() as conexion:
        return conexion.execute(text(sentencia), params).all()


def _sqlstate(error: BaseException) -> str:
    return getattr(getattr(error, "orig", None), "sqlstate", "") or ""


# --- Catalogo -------------------------------------------------------------------------------


def _funciones(motor_admin) -> list[dict]:
    with motor_admin.connect() as conexion:
        filas = conexion.execute(
            text(
                "SELECT p.proname AS nombre, p.oid AS oid, r.rolname AS dueno, p.prosecdef, "
                "p.proconfig, p.proretset, l.lanname AS lenguaje, p.prosrc, "
                "p.proargtypes::oid[] AS tipos_entrada, "
                "COALESCE((SELECT array_agg(a.grantee::regrole::text ORDER BY a.grantee) "
                "FROM aclexplode(p.proacl) a WHERE a.privilege_type = 'EXECUTE' "
                "AND a.grantee <> p.proowner AND a.grantee <> 0), ARRAY[]::text[]) AS grantees, "
                "COALESCE((SELECT bool_or(a.grantee = 0) FROM aclexplode(p.proacl) a), false) "
                "AS publico "
                "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                "JOIN pg_roles r ON r.oid = p.proowner JOIN pg_language l ON l.oid = p.prolang "
                "WHERE n.nspname = 'acceso' ORDER BY p.proname"
            )
        ).mappings().all()
    return [dict(f) for f in filas]


def test_el_conjunto_de_funciones_es_exactamente_el_de_las_convenciones(motor_admin, base_en_head):
    nombres = sorted(f["nombre"] for f in _funciones(motor_admin))

    assert nombres == sorted([*FUNCIONES_DE_LOGIN, *FUNCIONES_DE_SESION])
    assert len(nombres) == 10


@pytest.mark.parametrize("nombre", sorted(DUENO))
def test_catalogo_de_cada_funcion(motor_admin, base_en_head, nombre):
    funcion = next(f for f in _funciones(motor_admin) if f["nombre"] == nombre)

    assert funcion["dueno"] == DUENO[nombre]
    assert funcion["prosecdef"] is True
    assert funcion["proconfig"] == ["search_path=pg_catalog, pg_temp"]
    assert funcion["publico"] is False
    assert funcion["grantees"] == [EJECUTA[nombre]]
    assert funcion["lenguaje"] == "plpgsql"
    assert funcion["proretset"] is False
    assert re.search(r"\bEXECUTE\b", funcion["prosrc"], re.IGNORECASE) is None


def test_ninguna_funcion_recibe_parametros_uuid(motor_admin, base_en_head):
    with motor_admin.connect() as conexion:
        uuid_oid = conexion.execute(text("SELECT 'uuid'::regtype::oid")).scalar_one()

    for funcion in _funciones(motor_admin):
        assert uuid_oid not in funcion["tipos_entrada"], funcion["nombre"]


def test_el_duenio_de_las_funciones_de_sesion_no_toca_credenciales_ni_intentos(motor_admin):
    with motor_admin.connect() as conexion:
        for privilegio in ("SELECT", "UPDATE", "INSERT"):
            assert not conexion.execute(
                text("SELECT has_column_privilege(:r, 'public.usuario', 'credencial', :p)"),
                {"r": ROL_ACCESO_PREVIO, "p": privilegio},
            ).scalar_one()
        for privilegio in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            assert not conexion.execute(
                text("SELECT has_table_privilege(:r, 'public.intento_login', :p)"),
                {"r": ROL_ACCESO_PREVIO, "p": privilegio},
            ).scalar_one()


def test_la_funcion_de_rehash_de_la_primera_revision_no_existe(motor_admin, base_en_head):
    with motor_admin.connect() as conexion:
        assert conexion.execute(
            text("SELECT to_regprocedure('acceso.reemplazar_credencial_por_rehash(uuid,uuid,text,text)')")
        ).scalar_one() is None


# --- Rol sin concesion y creacion de objetos ------------------------------------------------


@pytest.fixture
def rol_sin_concesion(motor_admin, url_admin, base_en_head):
    nombre = f"prueba_sin_concesion_{secrets.token_hex(4)}"
    clave = secrets.token_urlsafe(24)
    with motor_admin.begin() as conexion:
        conexion.execute(text(f"CREATE ROLE {nombre} LOGIN PASSWORD '{clave}'"))
    motor = create_engine(url_admin.set(username=nombre, password=clave))
    try:
        yield motor
    finally:
        motor.dispose()
        with motor_admin.begin() as conexion:
            conexion.execute(text(f"DROP ROLE {nombre}"))


@pytest.mark.parametrize("nombre", sorted(LLAMADAS))
def test_un_rol_sin_concesion_no_ejecuta_ninguna_funcion(rol_sin_concesion, nombre):
    with pytest.raises(DBAPIError) as info:
        _llamar(rol_sin_concesion, nombre)

    assert _sqlstate(info.value) == "42501"


@pytest.mark.parametrize("motor_fixture", ["motor_app", "motor_login"])
def test_los_roles_de_conexion_no_crean_funciones_en_acceso(request, motor_fixture, base_en_head):
    motor = request.getfixturevalue(motor_fixture)

    with pytest.raises(DBAPIError) as info:
        with motor.begin() as conexion:
            conexion.execute(
                text("CREATE FUNCTION acceso.x() RETURNS int LANGUAGE sql AS 'SELECT 1'")
            )

    assert _sqlstate(info.value) == "42501"


@pytest.mark.parametrize("nombre", sorted(FUNCIONES_DE_LOGIN))
def test_turnos_app_no_ejecuta_las_funciones_de_login_ni_cambia_filas(
    motor_app, motor_admin, datos_ab, nombre
):
    with pytest.raises(DBAPIError) as info:
        _llamar(motor_app, nombre)

    assert _sqlstate(info.value) == "42501"
    assert _contar(motor_admin, "intento_login") == 0


@pytest.mark.parametrize("nombre", sorted(FUNCIONES_DE_SESION))
def test_turnos_login_no_ejecuta_las_funciones_de_sesion(motor_login, datos_ab, nombre):
    with pytest.raises(DBAPIError) as info:
        _llamar(motor_login, nombre)

    assert _sqlstate(info.value) == "42501"


@pytest.mark.parametrize("nombre", sorted(FUNCIONES_DE_LOGIN))
def test_turnos_login_si_ejecuta_las_funciones_de_login(motor_login, datos_ab, nombre):
    _llamar(motor_login, nombre)  # no falla


@pytest.mark.parametrize("nombre", sorted(FUNCIONES_DE_SESION))
def test_turnos_app_si_ejecuta_las_funciones_de_sesion(motor_app, datos_ab, nombre):
    _llamar(motor_app, nombre)  # no falla


# --- Abuso: entradas invalidas ---------------------------------------------------------------


def _contar(motor_admin, tabla: str) -> int:
    with motor_admin.connect() as conexion:
        return conexion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


@pytest.mark.parametrize("longitud", [31, 33])
def test_hmac_de_longitud_invalida_en_resolver_sesion(motor_app, datos_ab, longitud):
    with pytest.raises(DBAPIError) as info:
        _llamar(motor_app, "resolver_sesion", k=os.urandom(longitud))

    assert _sqlstate(info.value) == "22023"


@pytest.mark.parametrize("longitud", [31, 33])
@pytest.mark.parametrize("nombre", ["renovar_sesion", "revocar_sesion_por_token"])
def test_hmac_de_longitud_invalida_en_funciones_de_sesion_no_cambia_filas(
    motor_app, motor_admin, datos_ab, nombre, longitud
):
    with pytest.raises(DBAPIError) as info:
        _llamar(motor_app, nombre, k=os.urandom(longitud))

    assert _sqlstate(info.value) == "22023"


@pytest.mark.parametrize("longitud", [31, 33])
@pytest.mark.parametrize("campo", ["k", "i"])
def test_hmac_de_longitud_invalida_en_registrar_fallo_no_inserta(
    motor_login, motor_admin, datos_ab, longitud, campo
):
    with pytest.raises(DBAPIError) as info:
        _llamar(motor_login, "registrar_fallo", **{campo: os.urandom(longitud)})

    assert _sqlstate(info.value) == "22023"
    assert _contar(motor_admin, "intento_login") == 0


@pytest.mark.parametrize("longitud", [31, 33])
@pytest.mark.parametrize("nombre", ["fallos_de_cuenta", "fallos_de_ip", "descartar_fallos_de_cuenta"])
def test_hmac_de_longitud_invalida_en_conteos_y_descarte(motor_login, datos_ab, nombre, longitud):
    with pytest.raises(DBAPIError) as info:
        _llamar(motor_login, nombre, k=os.urandom(longitud))

    assert _sqlstate(info.value) == "22023"


def _insertar_fallos(motor_admin, clave_cuenta: bytes, clave_ip: bytes, cantidad: int, hace: timedelta):
    with motor_admin.begin() as conexion:
        for n in range(cantidad):
            conexion.execute(
                text(
                    "INSERT INTO intento_login (clave_cuenta, clave_ip, ocurrido_en) "
                    "VALUES (:c, :i, :t)"
                ),
                {"c": clave_cuenta, "i": clave_ip, "t": AHORA() - hace + timedelta(seconds=n)},
            )


def test_instante_una_hora_en_el_futuro_rechazado_en_funciones_de_escritura(
    motor_login, motor_app, motor_admin, datos_ab
):
    _insertar_fallos(motor_admin, os.urandom(32), os.urandom(32), 3, timedelta(hours=30))
    futuro = AHORA() + timedelta(hours=1)

    for motor, nombre in (
        (motor_login, "limpiar_intentos"),
        (motor_login, "registrar_fallo"),
        (motor_app, "limpiar_sesiones"),
        (motor_app, "renovar_sesion"),
        (motor_app, "revocar_sesion_por_token"),
    ):
        with pytest.raises(DBAPIError) as info:
            _llamar(motor, nombre, t=futuro)
        assert _sqlstate(info.value) == "22023", nombre

    assert _contar(motor_admin, "intento_login") == 3


def test_el_instante_dentro_de_los_cinco_minutos_se_acepta(motor_login, datos_ab):
    _llamar(motor_login, "limpiar_intentos", t=AHORA() + timedelta(minutes=4))


# --- Abuso: conteos y limpieza ---------------------------------------------------------------


def test_conteo_de_cuenta_limitado_a_la_clave_y_a_cinco(motor_login, motor_admin, datos_ab):
    k1, k2, ip = os.urandom(32), os.urandom(32), os.urandom(32)
    _insertar_fallos(motor_admin, k1, ip, 7, timedelta(minutes=10))
    _insertar_fallos(motor_admin, k2, ip, 3, timedelta(minutes=10))

    (fila,) = _llamar(motor_login, "fallos_de_cuenta", k=k1, t=AHORA() - timedelta(minutes=30))

    instantes = fila[0]
    assert len(instantes) == 5
    assert instantes == sorted(instantes)
    with motor_admin.connect() as conexion:
        mas_recientes = conexion.execute(
            text(
                "SELECT ocurrido_en FROM intento_login WHERE clave_cuenta = :c "
                "ORDER BY ocurrido_en DESC LIMIT 5"
            ),
            {"c": k1},
        ).scalars().all()
    assert instantes == sorted(mas_recientes)


def test_conteo_de_ip_limitado_a_treinta(motor_login, motor_admin, datos_ab):
    ip, otra = os.urandom(32), os.urandom(32)
    _insertar_fallos(motor_admin, os.urandom(32), ip, 35, timedelta(minutes=10))
    _insertar_fallos(motor_admin, os.urandom(32), otra, 4, timedelta(minutes=10))

    (fila,) = _llamar(motor_login, "fallos_de_ip", k=ip, t=AHORA() - timedelta(minutes=30))

    assert len(fila[0]) == 30


def test_el_conteo_de_cuenta_ignora_los_fallos_descartados(motor_login, motor_admin, datos_ab):
    k, ip = os.urandom(32), os.urandom(32)
    _insertar_fallos(motor_admin, k, ip, 4, timedelta(minutes=10))
    assert _llamar(motor_login, "descartar_fallos_de_cuenta", k=k) == [(4,)]

    (cuenta,) = _llamar(motor_login, "fallos_de_cuenta", k=k, t=AHORA() - timedelta(minutes=30))
    (por_ip,) = _llamar(motor_login, "fallos_de_ip", k=ip, t=AHORA() - timedelta(minutes=30))

    assert cuenta[0] == []
    assert len(por_ip[0]) == 4


def test_limpiar_intentos_borra_exactamente_cien_de_ciento_cincuenta(
    motor_login, motor_admin, datos_ab
):
    _insertar_fallos(motor_admin, os.urandom(32), os.urandom(32), 150, timedelta(hours=30))

    assert _llamar(motor_login, "limpiar_intentos", t=AHORA()) == [(100,)]

    assert _contar(motor_admin, "intento_login") == 50


def test_limpiar_intentos_no_borra_fallos_recientes(motor_login, motor_admin, datos_ab):
    _insertar_fallos(motor_admin, os.urandom(32), os.urandom(32), 5, timedelta(minutes=20))

    assert _llamar(motor_login, "limpiar_intentos", t=AHORA()) == [(0,)]

    assert _contar(motor_admin, "intento_login") == 5

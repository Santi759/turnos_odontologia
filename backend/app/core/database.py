from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.roles_bd import ROL_APP, ROL_LOGIN, violaciones_de_conexion

_PUERTO_POR_DEFECTO = 5432
_SUFIJO_BASE_DE_PRUEBAS = "_test"


# Configuracion inicial de los pools del MVP (PD-04, R3-01, DD-33), por proceso y sujeta a
# validacion por `tests/isolation/test_pool_login.py`. No se cambian sin aplicar la regla ante
# fallos de 5.7. Presupuesto: (4 + 11) + (5 + 10) = 30 conexiones por proceso.
POOL_LOGIN_TAMANO = 4
POOL_LOGIN_DESBORDE = 11
POOL_APP_TAMANO = 5
POOL_APP_DESBORDE = 10
POOL_ESPERA_SEGUNDOS = 30
CONNECT_TIMEOUT_SEGUNDOS = 5


def crear_engine_desde_url(url: str) -> Engine:
    """Motor generico (administracion y pruebas): sin conectar, con `pre_ping` y `connect_timeout`."""
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SEGUNDOS},
    )


class RolDeConexionInvalido(RuntimeError):
    """La conexion no cumple el rol esperado (DD-29); el mensaje es fijo y no incluye valores."""


# Consulta de catalogo de la guardia: nada de datos de negocio.
_SQL_GUARDIA = """
SELECT current_user AS usuario_actual,
       r.rolsuper, r.rolbypassrls, r.rolcreaterole, r.rolcreatedb, r.rolreplication,
       (EXISTS (SELECT 1 FROM pg_catalog.pg_class c WHERE c.relowner = r.oid)
        OR EXISTS (SELECT 1 FROM pg_catalog.pg_proc p WHERE p.proowner = r.oid)
        OR EXISTS (SELECT 1 FROM pg_catalog.pg_namespace s WHERE s.nspowner = r.oid))
         AS duenio_de_objetos,
       EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members m
                WHERE m.member = r.oid OR m.roleid = r.oid) AS con_membresias,
       has_column_privilege(current_user, 'public.usuario', 'credencial', 'SELECT')
         AS lee_credencial,
       (has_column_privilege(current_user, 'public.usuario', 'credencial', 'UPDATE')
        OR has_column_privilege(current_user, 'public.usuario', 'credencial', 'INSERT'))
         AS escribe_credencial,
       (has_table_privilege(current_user, 'public.usuario', 'INSERT')
        OR has_table_privilege(current_user, 'public.usuario', 'UPDATE')
        OR has_table_privilege(current_user, 'public.usuario', 'DELETE')) AS escribe_usuario,
       COALESCE((SELECT bool_or(has_function_privilege(current_user, f.oid, 'EXECUTE'))
                   FROM pg_catalog.pg_proc f
                   JOIN pg_catalog.pg_namespace n ON n.oid = f.pronamespace
                  WHERE n.nspname = 'acceso' AND f.proname = 'buscar_cuenta'), false)
         AS ejecuta_buscar_cuenta,
       COALESCE((SELECT bool_or(
                   has_table_privilege(current_user, t, 'SELECT')
                   OR has_table_privilege(current_user, t, 'INSERT')
                   OR has_table_privilege(current_user, t, 'UPDATE')
                   OR has_table_privilege(current_user, t, 'DELETE')
                   OR has_any_column_privilege(current_user, t, 'SELECT')
                   OR has_any_column_privilege(current_user, t, 'INSERT')
                   OR has_any_column_privilege(current_user, t, 'UPDATE'))
                   FROM unnest(ARRAY['public.consultorio', 'public.usuario', 'public.sesion',
                                     'public.intento_login']) AS t), false)
         AS privilegio_en_tablas
  FROM pg_catalog.pg_roles r
 WHERE r.rolname = current_user
"""


def verificar_rol_de_conexion(dbapi_connection, esperado: str) -> None:
    """Guardia de DD-29 sobre una conexion DBAPI recien abierta.

    Si no cumple, cierra la conexion y falla con un mensaje fijo que solo lista codigos. Deja la
    conexion sin transaccion abierta cuando cumple.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(_SQL_GUARDIA)
        valores = cursor.fetchone()
        columnas = [descripcion[0] for descripcion in cursor.description]
    finally:
        cursor.close()
    dbapi_connection.rollback()
    violaciones = violaciones_de_conexion(esperado, dict(zip(columnas, valores, strict=True)))
    if violaciones:
        dbapi_connection.close()
        raise RolDeConexionInvalido(
            f"la conexion no cumple el rol {esperado}: {', '.join(violaciones)}"
        )


def registrar_guardia_de_rol(engine: Engine, esperado: str) -> None:
    """Verifica el rol en cada conexion NUEVA, antes de entregarla al pool (DD-29)."""

    def guardia(dbapi_connection, _registro) -> None:
        verificar_rol_de_conexion(dbapi_connection, esperado)

    guardia.rol_esperado = esperado  # type: ignore[attr-defined]
    event.listen(engine, "connect", guardia)


def _crear_engine_de_la_api(url: str, rol: str, tamano: int, desborde: int) -> Engine:
    """Motor de un rol de la API con su pool explicito (PD-04) y la guardia de rol (DD-29)."""
    motor = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=tamano,
        max_overflow=desborde,
        pool_timeout=POOL_ESPERA_SEGUNDOS,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SEGUNDOS},
    )
    registrar_guardia_de_rol(motor, rol)
    return motor


def crear_engine(settings: Settings) -> Engine:
    """Motor de `turnos_app` (`DATABASE_URL`): pool 5/10/30 s y guardia de rol."""
    return _crear_engine_de_la_api(
        settings.database_url.get_secret_value(), ROL_APP, POOL_APP_TAMANO, POOL_APP_DESBORDE
    )


class LoginNoConfigurado(RuntimeError):
    """Falta `DATABASE_LOGIN_URL`; el mensaje es fijo y no incluye valores."""


def crear_engine_login(settings: Settings) -> Engine:
    """Motor del rol `turnos_login` (solo `POST /api/auth/login`); no conecta al crearse."""
    if settings.database_login_url is None:
        raise LoginNoConfigurado(
            "DATABASE_LOGIN_URL no esta definida: la API requiere la credencial del rol de login"
        )
    return _crear_engine_de_la_api(
        settings.database_login_url.get_secret_value(),
        ROL_LOGIN,
        POOL_LOGIN_TAMANO,
        POOL_LOGIN_DESBORDE,
    )


def crear_fabrica_de_sesiones_login(engine: Engine) -> sessionmaker[Session]:
    """Fabrica de sesiones del login: sin evento de contexto (`turnos_login` no lee tablas)."""
    return sessionmaker(bind=engine, expire_on_commit=False)


class AdministracionNoConfigurada(RuntimeError):
    """Falta `DATABASE_MIGRATION_URL`; el mensaje es fijo y no incluye valores."""


def crear_engine_admin(settings: Settings) -> Engine:
    """Motor de los comandos locales (rol `app`): solo `DATABASE_MIGRATION_URL` (DD-02).

    Nunca recurre a `DATABASE_URL` ni a `DATABASE_LOGIN_URL`. No conecta al crearse.
    """
    if settings.database_migration_url is None:
        raise AdministracionNoConfigurada(
            "DATABASE_MIGRATION_URL no esta definida: los comandos locales requieren "
            "la credencial de administracion"
        )
    return crear_engine_desde_url(settings.database_migration_url.get_secret_value())


def abrir_sesion_de_administracion(settings: Settings) -> Session:
    """Sesion por defecto de los comandos locales (sin contexto de consultorio)."""
    return sessionmaker(bind=crear_engine_admin(settings), expire_on_commit=False)()


def verificar_conexion(engine: Engine) -> None:
    """Ejecuta SELECT 1 y deja propagar cualquier error de conexion."""
    with engine.connect() as conexion:
        conexion.execute(text("SELECT 1"))


def _destino(url: str) -> tuple[str | None, int, str | None]:
    parseada = make_url(url)
    return (parseada.host, parseada.port or _PUERTO_POR_DEFECTO, parseada.database)


def validar_url_de_pruebas(
    url_pruebas: str | None,
    url_desarrollo: str,
    *,
    url_login: str | None = None,
    url_migracion: str | None = None,
) -> None:
    """Guardia: se niega a usar una base de pruebas que pueda ser la de desarrollo.

    Compara host, puerto y base con `DATABASE_URL` y, si se pasan, con las URLs de login y de
    migracion (aunque cambien las credenciales). Los mensajes nunca incluyen las URLs.
    """
    if not url_pruebas:
        raise ValueError(
            "TEST_DATABASE_URL no esta definida: las pruebas de integracion "
            "requieren una base de pruebas separada"
        )
    destino_pruebas = _destino(url_pruebas)
    comparadas = (
        ("DATABASE_URL", url_desarrollo),
        ("DATABASE_LOGIN_URL", url_login),
        ("DATABASE_MIGRATION_URL", url_migracion),
    )
    for variable, url in comparadas:
        if url and destino_pruebas == _destino(url):
            raise ValueError(
                f"TEST_DATABASE_URL apunta al mismo host, puerto y base que "
                f"{variable} (base de desarrollo): se rechaza ejecutar las pruebas"
            )
    nombre = make_url(url_pruebas).database or ""
    if not nombre.endswith(_SUFIJO_BASE_DE_PRUEBAS):
        raise ValueError(
            "el nombre de la base de pruebas debe terminar en '_test'"
        )

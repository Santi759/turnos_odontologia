"""`crear_app` deja motor, fabrica de sesiones y servicio de autenticacion en `app.state` (8.5, DD-20).

Sin conectar a la base al crear la app ni al arrancarla (el health no usa la base).
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.auth.servicio import ServicioAuth
from app.main import crear_app


def test_la_app_guarda_configuracion_motor_fabrica_y_servicio_en_su_estado(fabrica_settings):
    settings = fabrica_settings()

    app = crear_app(settings)

    assert getattr(app.state, "settings", None) is settings
    assert isinstance(getattr(app.state, "engine", None), Engine)
    assert getattr(app.state, "fabrica_sesiones", None) is not None
    assert isinstance(getattr(app.state, "servicio_auth", None), ServicioAuth)


def test_el_servicio_usa_la_clave_y_los_tiempos_de_la_configuracion(fabrica_settings):
    settings = fabrica_settings()

    servicio = getattr(crear_app(settings).state, "servicio_auth", None)

    assert servicio is not None
    assert servicio.config.clave_hmac == settings.auth_hmac_key
    assert servicio.config.minutos_inactividad == settings.auth_session_minutes
    assert servicio.config.horas_maximas == settings.auth_session_max_hours


def test_la_fabrica_de_sesiones_usa_el_motor_de_la_app(fabrica_settings):
    app = crear_app(fabrica_settings())

    fabrica = getattr(app.state, "fabrica_sesiones", None)
    assert fabrica is not None
    with fabrica() as sesion:
        assert sesion.get_bind() is app.state.engine


def test_cada_app_tiene_su_propio_estado(fabrica_settings):
    una = crear_app(fabrica_settings())
    otra = crear_app(fabrica_settings())

    servicio_una = getattr(una.state, "servicio_auth", None)
    servicio_otra = getattr(otra.state, "servicio_auth", None)
    assert servicio_una is not None and servicio_otra is not None
    assert servicio_una is not servicio_otra
    assert servicio_una.limitador is not servicio_otra.limitador
    assert una.state.engine is not otra.state.engine


def test_no_se_conecta_a_la_base_al_crear_ni_al_arrancar_la_app(fabrica_settings):
    conexiones: list[object] = []

    def registrar(dialect, conn_rec, cargs, cparams):
        conexiones.append(cparams.get("host"))

    event.listen(Engine, "do_connect", registrar)
    try:
        settings = fabrica_settings(
            database_url="postgresql+psycopg://app:app@host-inexistente.invalid:5432/turnos"
        )
        app = crear_app(settings)
        with TestClient(app) as cliente:  # ejecuta el arranque (lifespan) de la app
            assert cliente.get("/api/health").status_code == 200
    finally:
        event.remove(Engine, "do_connect", registrar)

    assert conexiones == []


# --- 1.5 `crear_app` exige la URL del rol de login (DD-02) ---------------------------------


def test_crear_app_sin_database_login_url_falla_con_mensaje_fijo_sin_abrir_conexiones(
    fabrica_settings,
):
    conexiones: list[object] = []
    registrar = lambda dialect, rec, cargs, cparams: conexiones.append(1)  # noqa: E731
    event.listen(Engine, "do_connect", registrar)
    try:
        with pytest.raises(RuntimeError, match="DATABASE_LOGIN_URL") as error:
            crear_app(fabrica_settings(database_login_url=None))
    finally:
        event.remove(Engine, "do_connect", registrar)

    assert conexiones == []
    assert "postgresql" not in str(error.value)
    assert "@" not in str(error.value)


def test_el_motor_de_login_apunta_a_database_login_url_y_el_de_la_api_a_database_url(
    fabrica_settings,
):
    app = crear_app(
        fabrica_settings(
            database_url="postgresql+psycopg://turnos_app:x@host-api.invalid:5432/turnos",
            database_login_url="postgresql+psycopg://turnos_login:y@host-login.invalid:5432/turnos",
        )
    )

    assert app.state.engine.url.host == "host-api.invalid"
    assert app.state.engine_login.url.host == "host-login.invalid"
    assert app.state.engine_login is not app.state.engine


# --- Guardia de credenciales de administracion (DD-34, RT3-01) ------------------------------------
# Reemplaza a `test_ningun_motor_de_la_app_apunta_a_database_migration_url`: la app ya no se construye
# con la credencial de administracion; su presencia hace fallar la creacion.

CLAVE_ADMIN_FICTICIA = "clave-admin-ficticia"
VALOR_FICTICIO_DEL_ENTORNO = "valor-ficticio-de-la-guardia"
VARIABLES_DE_ADMINISTRACION = ["DATABASE_MIGRATION_URL", "POSTGRES_PASSWORD", "PGPASSWORD"]


@pytest.fixture
def motores_espiados(monkeypatch):
    """Registra cualquier intento de crear motores: la guardia debe fallar antes."""
    import app.main as modulo

    llamadas: list[str] = []

    def espia(nombre):
        def fabrica(*_args, **_kwargs):
            llamadas.append(nombre)
            raise AssertionError(f"se creo el motor {nombre} antes de la guardia")

        return fabrica

    monkeypatch.setattr(modulo, "crear_engine", espia("crear_engine"))
    monkeypatch.setattr(modulo, "crear_engine_login", espia("crear_engine_login"))
    return llamadas


def _sin_variables_de_administracion(monkeypatch) -> None:
    for variable in VARIABLES_DE_ADMINISTRACION:
        monkeypatch.delenv(variable, raising=False)


def test_rechaza_la_configuracion_con_database_migration_url(
    fabrica_settings, monkeypatch, motores_espiados
):
    from app.main import CredencialAdministrativaEnLaApi

    _sin_variables_de_administracion(monkeypatch)
    settings = fabrica_settings().model_copy(
        update={
            "database_migration_url": SecretStr(
                f"postgresql+psycopg://app:{CLAVE_ADMIN_FICTICIA}@host-admin.invalid:5432/turnos"
            )
        }
    )

    with pytest.raises(CredencialAdministrativaEnLaApi) as error:
        crear_app(settings)

    assert "DATABASE_MIGRATION_URL" in str(error.value)
    assert CLAVE_ADMIN_FICTICIA not in str(error.value)
    assert "host-admin.invalid" not in str(error.value)
    assert motores_espiados == []


@pytest.mark.parametrize("variable", VARIABLES_DE_ADMINISTRACION)
def test_rechaza_una_variable_de_administracion_en_el_entorno_del_proceso(
    variable, fabrica_settings, monkeypatch, motores_espiados
):
    from app.main import CredencialAdministrativaEnLaApi

    _sin_variables_de_administracion(monkeypatch)
    # La configuracion se carga antes: la variable aparece solo en el entorno del proceso.
    settings = fabrica_settings()
    monkeypatch.setenv(variable, VALOR_FICTICIO_DEL_ENTORNO)

    with pytest.raises(CredencialAdministrativaEnLaApi) as error:
        crear_app(settings)

    mensaje = str(error.value)
    assert variable in mensaje
    assert VALOR_FICTICIO_DEL_ENTORNO not in mensaje
    otras = [nombre for nombre in VARIABLES_DE_ADMINISTRACION if nombre != variable]
    assert all(nombre not in mensaje for nombre in otras)
    assert motores_espiados == []


def test_nombra_todas_las_variables_de_administracion_presentes(
    fabrica_settings, monkeypatch, motores_espiados
):
    from app.main import CredencialAdministrativaEnLaApi

    _sin_variables_de_administracion(monkeypatch)
    settings = fabrica_settings()
    for variable in VARIABLES_DE_ADMINISTRACION:
        monkeypatch.setenv(variable, VALOR_FICTICIO_DEL_ENTORNO)

    with pytest.raises(CredencialAdministrativaEnLaApi) as error:
        crear_app(settings)

    mensaje = str(error.value)
    assert all(variable in mensaje for variable in VARIABLES_DE_ADMINISTRACION)
    assert VALOR_FICTICIO_DEL_ENTORNO not in mensaje
    assert motores_espiados == []


def test_con_un_entorno_sin_credenciales_de_administracion_la_app_se_crea(
    fabrica_settings, monkeypatch
):
    _sin_variables_de_administracion(monkeypatch)
    settings = fabrica_settings(
        database_url="postgresql+psycopg://turnos_app:x@host-api.invalid:5432/turnos",
        database_login_url="postgresql+psycopg://turnos_login:y@host-login.invalid:5432/turnos",
    )

    app = crear_app(settings)

    assert settings.database_migration_url is None
    assert {app.state.engine.url.host, app.state.engine_login.url.host} == {
        "host-api.invalid",
        "host-login.invalid",
    }


def test_la_app_web_no_arranca_con_el_entorno_administrativo(monkeypatch, motores_espiados):
    """Entorno como el del servicio `admin` (DD-34): `crear_app()` sin argumentos, como `uvicorn --factory`."""
    from app.main import CredencialAdministrativaEnLaApi

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://turnos_app:x@host-api.invalid:5432/turnos")
    monkeypatch.setenv(
        "DATABASE_LOGIN_URL", "postgresql+psycopg://turnos_login:y@host-login.invalid:5432/turnos"
    )
    monkeypatch.setenv(
        "DATABASE_MIGRATION_URL",
        f"postgresql+psycopg://app:{CLAVE_ADMIN_FICTICIA}@host-admin.invalid:5432/turnos",
    )
    monkeypatch.setenv("POSTGRES_PASSWORD", VALOR_FICTICIO_DEL_ENTORNO)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("APP_ENV", "local")

    with pytest.raises(CredencialAdministrativaEnLaApi) as error:
        crear_app()

    mensaje = str(error.value)
    assert "DATABASE_MIGRATION_URL" in mensaje and "POSTGRES_PASSWORD" in mensaje
    assert CLAVE_ADMIN_FICTICIA not in mensaje and VALOR_FICTICIO_DEL_ENTORNO not in mensaje
    assert motores_espiados == []


MODULOS_ADMINISTRATIVOS = [
    "app/seed/__main__.py",
    "app/seed/aplicar.py",
    "app/credenciales/__main__.py",
    "app/roles_postgres/__main__.py",
    "app/mantenimiento/__main__.py",
    "app/mantenimiento/limpieza.py",
    "alembic/env.py",
]


@pytest.mark.parametrize("ruta", MODULOS_ADMINISTRATIVOS)
def test_los_comandos_administrativos_no_crean_la_app_web(ruta):
    """La guardia es de la app web: Alembic y los comandos locales no la usan (DD-34)."""
    import ast
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    arbol = ast.parse((raiz / ruta).read_text(encoding="utf-8"))
    importados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module)
        elif isinstance(nodo, ast.Import):
            importados.update(alias.name for alias in nodo.names)
    nombres = {nodo.id for nodo in ast.walk(arbol) if isinstance(nodo, ast.Name)}
    assert "app.main" not in importados
    assert "crear_app" not in nombres


def test_la_fabrica_de_login_usa_el_motor_de_login(fabrica_settings):
    app = crear_app(fabrica_settings())

    with app.state.fabrica_sesiones_login() as sesion:
        assert sesion.get_bind() is app.state.engine_login

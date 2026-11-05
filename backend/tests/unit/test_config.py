import pytest
from pydantic import ValidationError

from app.core.config import cargar_configuracion

URL_VALIDA = "postgresql+psycopg://app:app@db:5432/turnos"


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    for nombre in ("DATABASE_URL", "TEST_DATABASE_URL", "CORS_ALLOWED_ORIGINS", "APP_ENV"):
        monkeypatch.delenv(nombre, raising=False)


def test_carga_de_valores_validos(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL_VALIDA)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("APP_ENV", "local")

    configuracion = cargar_configuracion()

    assert configuracion.database_url.get_secret_value() == URL_VALIDA
    assert configuracion.app_env == "local"
    assert configuracion.cors_allowed_origins == ["http://localhost:5173"]


def _cargar_esperando_error(monkeypatch, **entorno):
    for nombre, valor in entorno.items():
        monkeypatch.setenv(nombre, valor)
    with pytest.raises(ValidationError) as excinfo:
        cargar_configuracion()
    return str(excinfo.value)


def _entorno_valido(**cambios):
    entorno = {
        "DATABASE_URL": URL_VALIDA,
        "CORS_ALLOWED_ORIGINS": "http://localhost:5173",
        "APP_ENV": "local",
    }
    entorno.update(cambios)
    return entorno


def test_falta_database_url_menciona_la_variable(monkeypatch):
    entorno = _entorno_valido()
    del entorno["DATABASE_URL"]

    mensaje = _cargar_esperando_error(monkeypatch, **entorno)

    assert "DATABASE_URL" in mensaje


def test_falta_app_env_menciona_la_variable(monkeypatch):
    entorno = _entorno_valido()
    del entorno["APP_ENV"]

    mensaje = _cargar_esperando_error(monkeypatch, **entorno)

    assert "APP_ENV" in mensaje


def test_app_env_no_admitido_menciona_la_variable(monkeypatch):
    mensaje = _cargar_esperando_error(monkeypatch, **_entorno_valido(APP_ENV="produccion"))

    assert "APP_ENV" in mensaje


def test_el_error_no_revela_la_contrasena(monkeypatch):
    entorno = _entorno_valido(
        DATABASE_URL="postgresql+psycopg://app:clave-ficticia@db:5432/turnos",
        APP_ENV="produccion",
    )

    mensaje = _cargar_esperando_error(monkeypatch, **entorno)

    assert "clave-ficticia" not in mensaje
    assert "APP_ENV" in mensaje


def test_el_error_no_muestra_el_valor_recibido(monkeypatch):
    mensaje = _cargar_esperando_error(
        monkeypatch, **_entorno_valido(APP_ENV="valor-secreto-ficticio")
    )

    assert "valor-secreto-ficticio" not in mensaje


def test_varios_origenes_separados_por_comas(monkeypatch):
    for nombre, valor in _entorno_valido(
        CORS_ALLOWED_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
    ).items():
        monkeypatch.setenv(nombre, valor)

    configuracion = cargar_configuracion()

    assert configuracion.cors_allowed_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_origenes_con_espacios_se_recortan(monkeypatch):
    for nombre, valor in _entorno_valido(
        CORS_ALLOWED_ORIGINS=" http://localhost:5173 , http://127.0.0.1:5173 "
    ).items():
        monkeypatch.setenv(nombre, valor)

    assert cargar_configuracion().cors_allowed_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@pytest.mark.parametrize("valor", ["*", "http://localhost:5173,*", "", " , "])
def test_origenes_invalidos_se_rechazan(monkeypatch, valor):
    mensaje = _cargar_esperando_error(
        monkeypatch, **_entorno_valido(CORS_ALLOWED_ORIGINS=valor)
    )

    assert "CORS_ALLOWED_ORIGINS" in mensaje


def test_test_database_url_ausente_es_none(monkeypatch):
    for nombre, valor in _entorno_valido().items():
        monkeypatch.setenv(nombre, valor)

    assert cargar_configuracion().test_database_url is None


def test_test_database_url_presente_se_carga_como_secreto(monkeypatch):
    url = "postgresql+psycopg://app:clave-ficticia@db-test:5432/turnos_test"
    for nombre, valor in _entorno_valido(TEST_DATABASE_URL=url).items():
        monkeypatch.setenv(nombre, valor)

    configuracion = cargar_configuracion()

    assert configuracion.test_database_url is not None
    assert configuracion.test_database_url.get_secret_value() == url
    assert "clave-ficticia" not in repr(configuracion)

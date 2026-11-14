import argparse
import io
import secrets
from pathlib import Path

import pytest
from pydantic import SecretStr
from alembic import command
from alembic.config import Config

from app.core.config import Settings
from app.core.migraciones import resolver_url_de_migracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

URL_DESARROLLO = "postgresql+psycopg://app:clave-dev@db:5432/turnos"
URL_PRUEBAS = "postgresql+psycopg://app:clave-test@db-test:5432/turnos_test"
# Desde C-04 `DATABASE_URL` es del rol de la API; la migracion de desarrollo usa la de administracion.
URL_API = "postgresql+psycopg://turnos_app:clave-api@db:5432/turnos"


def _settings(
    test_database_url: str | None = URL_PRUEBAS, migracion: str | None = URL_DESARROLLO
) -> Settings:
    datos: dict[str, str | None] = {
        "DATABASE_URL": URL_API,
        "DATABASE_MIGRATION_URL": migracion,
        "CORS_ALLOWED_ORIGINS": "http://localhost:5173",
        "APP_ENV": "local",
        "AUTH_SECRET_KEY": secrets.token_urlsafe(48),
        # Siempre explicita (aunque sea None): el entorno del contenedor ya define
        # TEST_DATABASE_URL y no debe filtrarse a la prueba.
        "TEST_DATABASE_URL": test_database_url,
    }
    return Settings(**datos)


# --- Destino de desarrollo ---------------------------------------------------


def test_sin_destino_ni_url_explicita_resuelve_la_base_de_desarrollo():
    assert resolver_url_de_migracion(_settings(), None, None) == URL_DESARROLLO


def test_destino_desarrollo_explicito_resuelve_la_base_de_desarrollo():
    assert (
        resolver_url_de_migracion(_settings(), "desarrollo", None) == URL_DESARROLLO
    )


def test_desarrollo_no_exige_ni_valida_la_url_de_pruebas():
    # Aunque TEST_DATABASE_URL sea insegura o falte, el destino de desarrollo
    # sigue funcionando: la guardia solo protege el destino de pruebas.
    assert (
        resolver_url_de_migracion(_settings(test_database_url=None), None, None)
        == URL_DESARROLLO
    )
    assert (
        resolver_url_de_migracion(_settings(URL_DESARROLLO), None, None)
        == URL_DESARROLLO
    )


# --- Destino de pruebas (-x target=test) ------------------------------------


def test_destino_test_valido_resuelve_la_base_de_pruebas():
    assert resolver_url_de_migracion(_settings(), "test", None) == URL_PRUEBAS


def test_destino_test_sin_url_de_pruebas_se_rechaza():
    with pytest.raises(ValueError, match="TEST_DATABASE_URL"):
        resolver_url_de_migracion(_settings(test_database_url=None), "test", None)


def test_destino_test_con_url_de_pruebas_vacia_se_rechaza():
    with pytest.raises(ValueError, match="TEST_DATABASE_URL"):
        resolver_url_de_migracion(_settings(test_database_url=""), "test", None)


@pytest.mark.parametrize(
    "url_insegura",
    [
        URL_DESARROLLO,
        "postgresql+psycopg://otro:otra-clave@db:5432/turnos",
        "postgresql+psycopg://app:clave-dev@db/turnos",
    ],
    ids=["identica", "otras-credenciales", "puerto-implicito"],
)
def test_destino_test_apuntando_a_desarrollo_se_rechaza(url_insegura):
    with pytest.raises(ValueError, match="mismo host, puerto y base"):
        resolver_url_de_migracion(_settings(url_insegura), "test", None)


def test_destino_test_con_nombre_sin_sufijo_test_se_rechaza():
    with pytest.raises(ValueError, match="_test"):
        resolver_url_de_migracion(
            _settings("postgresql+psycopg://app:x@db-test:5432/turnos_prueba"),
            "test",
            None,
        )


# --- URL explicita (sqlalchemy.url fijada por codigo) -----------------------


def test_url_explicita_valida_de_pruebas_se_acepta():
    assert resolver_url_de_migracion(_settings(), None, URL_PRUEBAS) == URL_PRUEBAS


def test_url_explicita_valida_junto_a_destino_test_se_acepta():
    assert resolver_url_de_migracion(_settings(), "test", URL_PRUEBAS) == URL_PRUEBAS


def test_url_explicita_que_apunta_a_desarrollo_se_rechaza():
    with pytest.raises(ValueError, match="mismo host, puerto y base"):
        resolver_url_de_migracion(_settings(), None, URL_DESARROLLO)


def test_url_explicita_con_nombre_sin_sufijo_test_se_rechaza():
    with pytest.raises(ValueError, match="_test"):
        resolver_url_de_migracion(
            _settings(), None, "postgresql+psycopg://app:x@db-test:5432/otra"
        )


def test_url_explicita_junto_a_destino_desarrollo_se_rechaza_por_ambigua():
    with pytest.raises(ValueError, match="ambiguo"):
        resolver_url_de_migracion(_settings(), "desarrollo", URL_PRUEBAS)


# --- Destino desconocido -----------------------------------------------------


@pytest.mark.parametrize("destino", ["prod", "Test", "", "tests"])
def test_destino_desconocido_se_rechaza_listando_los_valores_admitidos(destino):
    with pytest.raises(ValueError, match="desarrollo.*test"):
        resolver_url_de_migracion(_settings(), destino, None)


# --- Los errores nunca revelan URLs ni credenciales (X1) --------------------


@pytest.mark.parametrize(
    ("test_url", "destino", "explicita"),
    [
        (URL_DESARROLLO, "test", None),
        ("postgresql+psycopg://app:clave-test@db-test:5432/otra", "test", None),
        (URL_PRUEBAS, None, URL_DESARROLLO),
        (URL_PRUEBAS, "desarrollo", URL_PRUEBAS),
        (URL_PRUEBAS, "prod", None),
    ],
)
def test_los_errores_no_incluyen_contrasenas_ni_urls(test_url, destino, explicita):
    with pytest.raises(ValueError) as error:
        resolver_url_de_migracion(_settings(test_url), destino, explicita)

    mensaje = str(error.value)
    assert "clave-dev" not in mensaje
    assert "clave-test" not in mensaje
    assert "postgresql" not in mensaje


# --- alembic/env.py de extremo a extremo, sin base (modo offline --sql) -----


def _ejecutar_upgrade_sql(
    monkeypatch: pytest.MonkeyPatch,
    *,
    database_url: str,
    test_database_url: str | None,
    argumentos_x: list[str],
    migration_url: str | None = None,
) -> str:
    monkeypatch.setenv("DATABASE_URL", database_url)
    if migration_url is None:
        monkeypatch.delenv("DATABASE_MIGRATION_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_MIGRATION_URL", migration_url)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    if test_database_url is None:
        monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("TEST_DATABASE_URL", test_database_url)

    salida = io.StringIO()
    configuracion = Config(str(RAIZ_BACKEND / "alembic.ini"), output_buffer=salida)
    configuracion.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    configuracion.cmd_opts = argparse.Namespace(x=argumentos_x)
    command.upgrade(configuracion, "head", sql=True)
    return salida.getvalue()


def test_env_py_rechaza_target_test_cuando_la_url_de_pruebas_es_la_de_desarrollo(
    monkeypatch,
):
    with pytest.raises(ValueError, match="mismo host, puerto y base"):
        _ejecutar_upgrade_sql(
            monkeypatch,
            database_url=URL_DESARROLLO,
            test_database_url=URL_DESARROLLO,
            argumentos_x=["target=test"],
        )


def test_env_py_rechaza_target_test_sin_url_de_pruebas(monkeypatch):
    with pytest.raises(ValueError, match="TEST_DATABASE_URL"):
        _ejecutar_upgrade_sql(
            monkeypatch,
            database_url=URL_DESARROLLO,
            test_database_url=None,
            argumentos_x=["target=test"],
        )


def test_env_py_rechaza_un_destino_desconocido(monkeypatch):
    with pytest.raises(ValueError, match="desarrollo.*test"):
        _ejecutar_upgrade_sql(
            monkeypatch,
            database_url=URL_DESARROLLO,
            test_database_url=URL_PRUEBAS,
            argumentos_x=["target=prod"],
        )


def test_env_py_con_target_test_valido_genera_el_sql_de_la_migracion(monkeypatch):
    sql = _ejecutar_upgrade_sql(
        monkeypatch,
        database_url=URL_DESARROLLO,
        test_database_url=URL_PRUEBAS,
        argumentos_x=["target=test"],
    )

    assert "CREATE EXTENSION IF NOT EXISTS btree_gist" in sql


def test_env_py_sin_destino_sigue_usando_la_base_de_desarrollo(monkeypatch):
    # Con una TEST_DATABASE_URL insegura, el destino de desarrollo no se ve afectado.
    # Ajuste C-04: desarrollo usa DATABASE_MIGRATION_URL y `DATABASE_URL` es del rol de la API.
    sql = _ejecutar_upgrade_sql(
        monkeypatch,
        database_url=URL_API,
        test_database_url=URL_DESARROLLO,
        argumentos_x=[],
        migration_url=URL_DESARROLLO,
    )

    assert "CREATE EXTENSION IF NOT EXISTS btree_gist" in sql


# --- 1.3 El destino de desarrollo usa DATABASE_MIGRATION_URL (delta base-de-datos-local) ---


def test_desarrollo_usa_la_url_de_migracion_y_nunca_la_de_la_api():
    resuelta = resolver_url_de_migracion(_settings(), None, None)

    assert resuelta == URL_DESARROLLO
    assert resuelta != URL_API


def test_desarrollo_sin_url_de_migracion_falla_mencionandola_sin_valores():
    with pytest.raises(ValueError, match="DATABASE_MIGRATION_URL") as excinfo:
        resolver_url_de_migracion(_settings(migracion=None), "desarrollo", None)

    assert "clave-api" not in str(excinfo.value)
    assert "turnos_app" not in str(excinfo.value)


def test_los_destinos_de_pruebas_no_exigen_la_url_de_migracion():
    assert resolver_url_de_migracion(_settings(migracion=None), "test", None) == URL_PRUEBAS
    assert resolver_url_de_migracion(_settings(migracion=None), None, URL_PRUEBAS) == URL_PRUEBAS


def test_la_guardia_de_pruebas_tambien_compara_con_la_url_de_migracion():
    configuracion = _settings(test_database_url="postgresql+psycopg://x:y@admin-host:5432/turnos")
    configuracion = configuracion.model_copy(
        update={
            "database_migration_url": SecretStr("postgresql+psycopg://app:z@admin-host:5432/turnos")
        }
    )
    with pytest.raises(ValueError, match="DATABASE_MIGRATION_URL"):
        resolver_url_de_migracion(configuracion, "test", None)

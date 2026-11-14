"""La documentacion de la API (Swagger, ReDoc, OpenAPI) solo existe con APP_ENV=local (8.3, DD-18)."""

import secrets

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import crear_app

RUTAS_DE_DOCUMENTACION = ["/docs", "/redoc", "/openapi.json"]


def _settings(app_env: str) -> Settings:
    return Settings(
        DATABASE_URL="postgresql+psycopg://app:app@db:5432/turnos",
        DATABASE_LOGIN_URL="postgresql+psycopg://turnos_login:login@db:5432/turnos",
        CORS_ALLOWED_ORIGINS="http://localhost:5173",
        APP_ENV=app_env,
        AUTH_SECRET_KEY=secrets.token_urlsafe(48),
        AUTH_COOKIE_SECURE=True,
    )


@pytest.mark.parametrize("ruta", RUTAS_DE_DOCUMENTACION)
def test_con_app_env_test_la_documentacion_responde_404(ruta):
    cliente = TestClient(crear_app(_settings("test")))

    assert cliente.get(ruta).status_code == 404


@pytest.mark.parametrize("ruta", RUTAS_DE_DOCUMENTACION)
def test_con_app_env_local_la_documentacion_responde_200(ruta):
    cliente = TestClient(crear_app(_settings("local")))

    assert cliente.get(ruta).status_code == 200


@pytest.mark.parametrize("app_env", ["test", "local"])
def test_la_ruta_de_redireccion_oauth_no_existe_en_ningun_entorno(app_env):
    cliente = TestClient(crear_app(_settings(app_env)))

    assert cliente.get("/docs/oauth2-redirect").status_code == 404


@pytest.mark.parametrize("ruta", RUTAS_DE_DOCUMENTACION)
def test_un_entorno_distinto_de_local_deja_la_documentacion_denegada(ruta):
    # Denegado por defecto: un valor futuro de APP_ENV no la habilita (el modelo no valida al copiar).
    settings = _settings("local").model_copy(update={"app_env": "produccion"})
    cliente = TestClient(crear_app(settings))

    assert cliente.get(ruta).status_code == 404

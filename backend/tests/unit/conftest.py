from __future__ import annotations

import secrets
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from app.core.config import Settings

ORIGEN_FRONTEND = "http://localhost:5173"


@pytest.fixture(autouse=True)
def entorno_auth_aislado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aisla cada prueba unitaria de las AUTH_* heredadas del proceso (D2, 2026-11-06).

    El contenedor carga el `.env` del autor; sus valores (por ejemplo,
    `AUTH_COOKIE_SECURE=false`) no deben alterar pruebas con `APP_ENV=test`. Solo se
    tocan variables AUTH_*; monkeypatch las restaura al terminar cada prueba.
    """
    monkeypatch.setenv("AUTH_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_SESSION_MINUTES", "30")
    monkeypatch.setenv("AUTH_SESSION_MAX_HOURS", "12")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")


@pytest.fixture
def fabrica_settings() -> Callable[..., Settings]:
    # Importacion perezosa: las pruebas de dominio puro siguen corriendo sin las
    # dependencias de ejecucion instaladas (por ejemplo, en el venv del host).
    from app.core.config import Settings

    def crear(
        database_url: str = "postgresql+psycopg://app:app@db:5432/turnos",
        origenes: str = ORIGEN_FRONTEND,
    ) -> Settings:
        return Settings(
            DATABASE_URL=database_url,
            CORS_ALLOWED_ORIGINS=origenes,
            APP_ENV="local",
            # Clave ficticia generada al ejecutar: nunca un literal (DD-17).
            AUTH_SECRET_KEY=secrets.token_urlsafe(48),
        )

    return crear

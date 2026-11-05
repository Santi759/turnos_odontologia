from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from app.core.config import Settings

ORIGEN_FRONTEND = "http://localhost:5173"


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
        )

    return crear

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine

from app.core.config import cargar_configuracion
from app.core.database import (
    crear_engine_desde_url,
    validar_url_de_pruebas,
    verificar_conexion,
)


@pytest.fixture(scope="session")
def motor() -> Iterator[Engine]:
    """Motor contra la base de PRUEBAS (db-test). Nunca omite: si falla, la suite falla."""
    settings = cargar_configuracion()
    url_pruebas = (
        settings.test_database_url.get_secret_value()
        if settings.test_database_url is not None
        else None
    )
    validar_url_de_pruebas(url_pruebas, settings.database_url.get_secret_value())
    assert url_pruebas is not None
    motor = crear_engine_desde_url(url_pruebas)
    try:
        verificar_conexion(motor)
        yield motor
    finally:
        motor.dispose()

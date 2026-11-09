from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine
from sqlalchemy.orm import Session

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


RAIZ_BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture
def config_alembic(motor: Engine) -> Config:
    """Configuracion de Alembic apuntada al motor de PRUEBAS (URL explicita, guardada)."""
    configuracion = Config(str(RAIZ_BACKEND / "alembic.ini"))
    configuracion.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    url = motor.url.render_as_string(hide_password=False).replace("%", "%%")
    configuracion.set_main_option("sqlalchemy.url", url)
    return configuracion


@pytest.fixture
def revision_actual(motor: Engine) -> Callable[[], str | None]:
    def leer() -> str | None:
        with motor.connect() as conexion:
            return MigrationContext.configure(conexion).get_current_revision()

    return leer


@pytest.fixture
def base_migrada(motor: Engine, config_alembic: Config) -> Engine:
    command.upgrade(config_alembic, "head")
    return motor


@pytest.fixture
def sesion(base_migrada: Engine) -> Iterator[Session]:
    """Sesion sobre una transaccion exterior que siempre se revierte (DM-11).

    Las inserciones que deben fallar se ejecutan dentro de `begin_nested()`.
    """
    conexion = base_migrada.connect()
    transaccion = conexion.begin()
    sesion = Session(bind=conexion, join_transaction_mode="create_savepoint")
    try:
        yield sesion
    finally:
        sesion.close()
        transaccion.rollback()
        conexion.close()


@pytest.fixture
def base_en_0002(motor: Engine, config_alembic: Config) -> Iterator[Engine]:
    """Base de PRUEBAS vacia en la revision 0002 (para probar la migracion 0003).

    Al terminar descarta todo lo que el test haya insertado y deja la base en `head`.
    """
    command.downgrade(config_alembic, "base")
    command.upgrade(config_alembic, "0002")
    try:
        yield motor
    finally:
        command.downgrade(config_alembic, "base")
        command.upgrade(config_alembic, "head")

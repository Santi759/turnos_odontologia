from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


def _configuracion_alembic(motor: Engine) -> Config:
    configuracion = Config(str(RAIZ_BACKEND / "alembic.ini"))
    configuracion.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    url = motor.url.render_as_string(hide_password=False).replace("%", "%%")
    configuracion.set_main_option("sqlalchemy.url", url)
    return configuracion


def _revision_actual(motor: Engine) -> str | None:
    with motor.connect() as conexion:
        return MigrationContext.configure(conexion).get_current_revision()


@pytest.fixture
def base_migrada(motor: Engine) -> Engine:
    command.upgrade(_configuracion_alembic(motor), "head")
    return motor


def test_extension_btree_gist_instalada_tras_migrar(base_migrada: Engine):
    with base_migrada.connect() as conexion:
        extensiones = conexion.execute(
            text("SELECT extname FROM pg_extension")
        ).scalars().all()

    assert "btree_gist" in extensiones


def test_restriccion_de_exclusion_utilizable_y_sin_residuos(base_migrada: Engine):
    with base_migrada.connect() as conexion:
        transaccion = conexion.begin()
        conexion.execute(
            text(
                "CREATE TEMP TABLE reserva_prueba ("
                "recurso integer, periodo tstzrange, "
                "EXCLUDE USING gist (recurso WITH =, periodo WITH &&))"
            )
        )
        insertar = text(
            "INSERT INTO reserva_prueba VALUES (:recurso, "
            "tstzrange(:inicio, :fin, '[)'))"
        )
        conexion.execute(
            insertar,
            {
                "recurso": 1,
                "inicio": "2026-11-02 10:00:00-03:00",
                "fin": "2026-11-02 10:30:00-03:00",
            },
        )
        with pytest.raises(IntegrityError) as excinfo:
            conexion.execute(
                insertar,
                {
                    "recurso": 1,
                    "inicio": "2026-11-02 10:15:00-03:00",
                    "fin": "2026-11-02 10:45:00-03:00",
                },
            )
        transaccion.rollback()

    assert getattr(excinfo.value.orig, "sqlstate", None) == "23P01"
    with base_migrada.connect() as conexion:
        residuos = conexion.execute(
            text("SELECT count(*) FROM pg_class WHERE relname = 'reserva_prueba'")
        ).scalar_one()
    assert residuos == 0


def test_la_restriccion_acepta_periodos_consecutivos_y_otro_recurso(
    base_migrada: Engine,
):
    with base_migrada.connect() as conexion:
        transaccion = conexion.begin()
        conexion.execute(
            text(
                "CREATE TEMP TABLE reserva_prueba ("
                "recurso integer, periodo tstzrange, "
                "EXCLUDE USING gist (recurso WITH =, periodo WITH &&))"
            )
        )
        insertar = text(
            "INSERT INTO reserva_prueba VALUES (:recurso, "
            "tstzrange(:inicio, :fin, '[)'))"
        )
        base = "2026-11-02 {}:00-03:00"
        for recurso, inicio, fin in [
            (1, "10:00", "10:30"),
            (1, "10:30", "11:00"),
            (2, "10:15", "10:45"),
        ]:
            conexion.execute(
                insertar,
                {"recurso": recurso, "inicio": base.format(inicio), "fin": base.format(fin)},
            )
        cantidad = conexion.execute(
            text("SELECT count(*) FROM reserva_prueba")
        ).scalar_one()
        transaccion.rollback()

    assert cantidad == 3


def test_el_comando_explicito_deja_la_base_al_dia(motor: Engine):
    configuracion = _configuracion_alembic(motor)
    ultima = ScriptDirectory.from_config(configuracion).get_current_head()

    command.downgrade(configuracion, "base")
    assert _revision_actual(motor) is None

    command.upgrade(configuracion, "head")
    assert _revision_actual(motor) == ultima

    command.upgrade(configuracion, "head")  # idempotente
    assert _revision_actual(motor) == ultima


def test_sin_tablas_de_dominio(base_migrada: Engine):
    with base_migrada.connect() as conexion:
        tablas = conexion.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        ).scalars().all()

    assert tablas == ["alembic_version"]

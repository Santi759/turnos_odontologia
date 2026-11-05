from collections.abc import Callable

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from app.models.base import Base


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


def test_el_comando_explicito_deja_la_base_al_dia(
    motor: Engine, config_alembic: Config, revision_actual: Callable[[], str | None]
):
    ultima = ScriptDirectory.from_config(config_alembic).get_current_head()

    command.downgrade(config_alembic, "base")
    assert revision_actual() is None

    command.upgrade(config_alembic, "head")
    assert revision_actual() == ultima

    command.upgrade(config_alembic, "head")  # idempotente
    assert revision_actual() == ultima


def _tablas_publicas(motor: Engine) -> list[str]:
    with motor.connect() as conexion:
        return sorted(
            conexion.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            .scalars()
            .all()
        )


def _filas(motor: Engine, tabla: str) -> int:
    with motor.connect() as conexion:
        return conexion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


def test_sin_tablas_de_dominio(base_migrada: Engine):
    # C-02 (delta MODIFIED de base-de-datos-local): antes exigia solo alembic_version.
    assert _tablas_publicas(base_migrada) == [
        "alembic_version",
        "consultorio",
        "usuario",
    ]


def test_tablas_del_modelo_base_vacias_tras_migrar(base_migrada: Engine):
    assert _filas(base_migrada, "consultorio") == 0
    assert _filas(base_migrada, "usuario") == 0


def test_cadena_de_revisiones_head_0002_sobre_0001(config_alembic: Config):
    scripts = ScriptDirectory.from_config(config_alembic)

    head = scripts.get_revision(scripts.get_current_head())

    assert head.revision == "0002"
    assert head.down_revision == "0001"


def test_subida_desde_0001_crea_las_tablas_vacias(
    motor: Engine, config_alembic: Config, revision_actual: Callable[[], str | None]
):
    command.downgrade(config_alembic, "0001")
    assert revision_actual() == "0001"
    assert _tablas_publicas(motor) == ["alembic_version"]

    command.upgrade(config_alembic, "head")

    assert _tablas_publicas(motor) == ["alembic_version", "consultorio", "usuario"]
    assert _filas(motor, "consultorio") == 0
    assert _filas(motor, "usuario") == 0


def test_bajada_a_0001_elimina_las_tablas_y_conserva_btree_gist(
    motor: Engine, config_alembic: Config, revision_actual: Callable[[], str | None]
):
    command.upgrade(config_alembic, "head")

    command.downgrade(config_alembic, "0001")

    assert revision_actual() == "0001"
    assert _tablas_publicas(motor) == ["alembic_version"]
    with motor.connect() as conexion:
        extensiones = (
            conexion.execute(text("SELECT extname FROM pg_extension")).scalars().all()
        )
    assert "btree_gist" in extensiones

    command.upgrade(config_alembic, "head")
    assert _tablas_publicas(motor) == ["alembic_version", "consultorio", "usuario"]


def test_migrar_desde_base_no_carga_datos(motor: Engine, config_alembic: Config):
    command.downgrade(config_alembic, "base")

    command.upgrade(config_alembic, "head")

    assert _filas(motor, "consultorio") == 0
    assert _filas(motor, "usuario") == 0


def test_los_modelos_coinciden_con_la_base_migrada(base_migrada: Engine):
    with base_migrada.connect() as conexion:
        contexto = MigrationContext.configure(conexion)
        diferencias = compare_metadata(contexto, Base.metadata)

    assert diferencias == []


def test_nombres_de_restricciones_segun_la_convencion(base_migrada: Engine):
    with base_migrada.connect() as conexion:
        filas = conexion.execute(
            text(
                "SELECT conrelid::regclass::text AS tabla, conname, contype "
                "FROM pg_constraint WHERE connamespace = 'public'::regnamespace "
                "AND contype IN ('p', 'f', 'u', 'c') "  # PG 18 lista tambien los NOT NULL (n)
                "AND conrelid IN ('consultorio'::regclass, 'usuario'::regclass)"
            )
        ).all()

    por_tabla = {(f.tabla, f.conname) for f in filas}
    assert por_tabla == {
        ("consultorio", "pk_consultorio"),
        ("consultorio", "ck_consultorio_anticipacion_no_negativa"),
        ("usuario", "pk_usuario"),
        ("usuario", "fk_usuario_consultorio_id_consultorio"),
        ("usuario", "uq_usuario_consultorio_id_id"),
        ("usuario", "uq_usuario_consultorio_id_email"),
        ("usuario", "ck_usuario_rol_valido"),
        ("usuario", "ck_usuario_email_normalizado"),
        ("usuario", "ck_usuario_credencial_no_vacia"),
    }
    prefijos = {"p": "pk_", "f": "fk_", "u": "uq_", "c": "ck_"}
    assert all(f.conname.startswith(prefijos[f.contype]) for f in filas)

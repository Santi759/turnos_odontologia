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


TABLAS_TRAS_MIGRAR = [
    "alembic_version",
    "consultorio",
    "intento_login",
    "sesion",
    "usuario",
]
TABLAS_CON_DATOS_DEL_MODELO = ("consultorio", "usuario", "sesion", "intento_login")


def _filas(motor: Engine, tabla: str) -> int:
    with motor.connect() as conexion:
        return conexion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


def test_sin_tablas_de_dominio(base_migrada: Engine):
    # C-02 y C-03 (deltas MODIFIED de base-de-datos-local): antes exigia solo
    # alembic_version; C-03 suma sesion e intento_login.
    assert _tablas_publicas(base_migrada) == TABLAS_TRAS_MIGRAR


def test_tablas_del_modelo_base_vacias_tras_migrar(base_migrada: Engine):
    for tabla in TABLAS_CON_DATOS_DEL_MODELO:
        assert _filas(base_migrada, tabla) == 0, tabla


def test_cadena_de_revisiones_0001_0002_0003_0004(config_alembic: Config):
    # Ajuste C-04: la cadena crece con 0004 (head) y 0003 deja de ser head.
    scripts = ScriptDirectory.from_config(config_alembic)

    head = scripts.get_revision(scripts.get_current_head())
    autenticacion = scripts.get_revision("0003")
    modelo_base = scripts.get_revision("0002")

    assert head.revision == "0004"
    assert head.down_revision == "0003"
    assert autenticacion.down_revision == "0002"
    assert modelo_base.down_revision == "0001"
    assert set(modelo_base.nextrev) == {"0003"}
    assert set(autenticacion.nextrev) == {"0004"}


def test_subida_desde_0001_crea_las_tablas_vacias(
    motor: Engine, config_alembic: Config, revision_actual: Callable[[], str | None]
):
    command.downgrade(config_alembic, "0001")
    assert revision_actual() == "0001"
    assert _tablas_publicas(motor) == ["alembic_version"]

    command.upgrade(config_alembic, "head")

    assert _tablas_publicas(motor) == TABLAS_TRAS_MIGRAR
    for tabla in TABLAS_CON_DATOS_DEL_MODELO:
        assert _filas(motor, tabla) == 0, tabla


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
    assert _tablas_publicas(motor) == TABLAS_TRAS_MIGRAR


def test_migrar_desde_base_no_carga_datos(motor: Engine, config_alembic: Config):
    command.downgrade(config_alembic, "base")

    command.upgrade(config_alembic, "head")

    for tabla in TABLAS_CON_DATOS_DEL_MODELO:
        assert _filas(motor, tabla) == 0, tabla


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
                "AND conrelid IN ('consultorio'::regclass, 'usuario'::regclass, "
                "'sesion'::regclass, 'intento_login'::regclass)"
            )
        ).all()

    por_tabla = {(f.tabla, f.conname) for f in filas}
    assert por_tabla == {
        ("consultorio", "pk_consultorio"),
        ("consultorio", "ck_consultorio_anticipacion_no_negativa"),
        ("consultorio", "uq_consultorio_codigo"),
        ("consultorio", "ck_consultorio_codigo_formato"),
        ("sesion", "pk_sesion"),
        ("sesion", "uq_sesion_token_hmac"),
        ("sesion", "uq_sesion_consultorio_id_id"),  # C-04 (0004, DD-08)
        ("sesion", "fk_sesion_consultorio_id_usuario"),
        ("sesion", "ck_sesion_token_hmac_longitud"),
        ("sesion", "ck_sesion_vencimientos_coherentes"),
        ("sesion", "ck_sesion_revocacion_posterior"),
        ("intento_login", "pk_intento_login"),
        ("intento_login", "ck_intento_login_claves_longitud"),
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

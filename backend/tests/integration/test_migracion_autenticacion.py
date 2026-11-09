"""Migracion 0003 (autenticacion): codigo de consultorio, `sesion` e `intento_login`.

Todas las pruebas usan SOLO la base de pruebas (db-test). Parten de la revision 0002 con
datos ficticios y suben a 0003 con el comando de Alembic (nunca contra desarrollo).
"""

import uuid
from collections.abc import Callable

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text

ID_A = uuid.UUID("01a1a95a-dd90-73e7-9496-c7d08d776d19")
ID_B = uuid.UUID("01a1a95a-dd90-73e7-9496-c7d1647cab52")
# Mismos 12 digitos finales que ID_A y menor que ID_A: colision del codigo corto.
ID_COLISION = uuid.UUID("01a1a95a-dd90-7000-8000-c7d08d776d19")

COLUMNAS_CONSULTORIO_0002 = (
    "id, nombre, zona_horaria, anticipacion_cancelacion_horas, activo, creado_en"
)


def _insertar_consultorios(motor: Engine, ids: list[uuid.UUID]) -> None:
    with motor.begin() as conexion:
        for numero, consultorio_id in enumerate(ids):
            conexion.execute(
                text("INSERT INTO consultorio (id, nombre) VALUES (:id, :nombre)"),
                {"id": consultorio_id, "nombre": f"Consultorio Ficticio {numero}"},
            )


def _insertar_usuarios(motor: Engine, consultorio_id: uuid.UUID, cantidad: int) -> None:
    with motor.begin() as conexion:
        for numero in range(cantidad):
            conexion.execute(
                text(
                    "INSERT INTO usuario (consultorio_id, email, nombre, rol) "
                    "VALUES (:c, :email, 'Persona Ficticia', 'secretaria')"
                ),
                {"c": consultorio_id, "email": f"persona{numero}@example.test"},
            )


def _codigos(motor: Engine) -> dict[uuid.UUID, str]:
    with motor.connect() as conexion:
        filas = conexion.execute(text("SELECT id, codigo FROM consultorio")).all()
    return {fila.id: fila.codigo for fila in filas}


def _columnas(motor: Engine, tabla: str) -> set[str]:
    with motor.connect() as conexion:
        return set(
            conexion.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :t"
                ),
                {"t": tabla},
            )
            .scalars()
            .all()
        )


# --- Cadena de revisiones ------------------------------------------------------


def test_la_revision_head_es_0003_y_depende_de_0002(config_alembic: Config):
    scripts = ScriptDirectory.from_config(config_alembic)

    head = scripts.get_revision(scripts.get_current_head())

    assert head.revision == "0003"
    assert head.down_revision == "0002"


# --- Migracion reversible -------------------------------------------------------


def test_la_subida_agrega_la_columna_codigo_y_la_bajada_la_elimina(
    base_en_0002: Engine,
    config_alembic: Config,
    revision_actual: Callable[[], str | None],
):
    assert "codigo" not in _columnas(base_en_0002, "consultorio")

    command.upgrade(config_alembic, "0003")
    assert revision_actual() == "0003"
    assert "codigo" in _columnas(base_en_0002, "consultorio")

    command.downgrade(config_alembic, "0002")
    assert revision_actual() == "0002"
    assert "codigo" not in _columnas(base_en_0002, "consultorio")


# --- Backfill determinista del codigo -------------------------------------------


def test_backfill_de_los_consultorios_del_seed(
    base_en_0002: Engine, config_alembic: Config
):
    _insertar_consultorios(base_en_0002, [ID_A, ID_B])

    command.upgrade(config_alembic, "0003")

    assert _codigos(base_en_0002) == {ID_A: "c-c7d08d776d19", ID_B: "c-c7d1647cab52"}


def test_backfill_con_colision_resuelta_de_forma_determinista_y_repetible(
    base_en_0002: Engine, config_alembic: Config
):
    _insertar_consultorios(base_en_0002, [ID_A, ID_COLISION])

    command.upgrade(config_alembic, "0003")

    esperado = {
        ID_COLISION: "c-c7d08d776d19",  # menor id: conserva el corto
        ID_A: "c-01a1a95add9073e79496c7d08d776d19",  # el otro recibe el largo
    }
    assert _codigos(base_en_0002) == esperado

    command.downgrade(config_alembic, "0002")
    command.upgrade(config_alembic, "0003")

    assert _codigos(base_en_0002) == esperado


def test_backfill_sin_consultorios(base_en_0002: Engine, config_alembic: Config):
    command.upgrade(config_alembic, "0003")

    assert _codigos(base_en_0002) == {}


# --- El backfill solo escribe la columna nueva ------------------------------------


def _huella(motor: Engine) -> tuple[str, str, int, int]:
    """Huella de las columnas que existen en 0002 y cantidad de filas."""
    with motor.connect() as conexion:
        consultorios = conexion.execute(
            text(
                f"SELECT md5(string_agg(row({COLUMNAS_CONSULTORIO_0002})::text, "
                "chr(10) ORDER BY id)), count(*) FROM consultorio"
            )
        ).one()
        usuarios = conexion.execute(
            text("SELECT md5(string_agg(u::text, chr(10) ORDER BY id)), count(*) FROM usuario u")
        ).one()
    return consultorios[0], usuarios[0], consultorios[1], usuarios[1]


def test_el_backfill_solo_escribe_la_columna_nueva(
    base_en_0002: Engine, config_alembic: Config
):
    _insertar_consultorios(base_en_0002, [ID_A, ID_B, ID_COLISION])
    _insertar_usuarios(base_en_0002, ID_A, 2)
    _insertar_usuarios(base_en_0002, ID_B, 1)
    antes = _huella(base_en_0002)
    assert antes[2:] == (3, 3)

    command.upgrade(config_alembic, "0003")

    assert _huella(base_en_0002) == antes


# --- Sin disparadores ni funciones para el codigo ---------------------------------

DISPARADORES_DE_CONSULTORIO = (
    "SELECT tgname FROM pg_trigger "
    "WHERE tgrelid = 'consultorio'::regclass AND NOT tgisinternal"
)
FUNCIONES_PROPIAS_EN_PUBLIC = (
    "SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
    "WHERE n.nspname = 'public' AND NOT EXISTS ("
    "SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_proc'::regclass "
    "AND d.objid = p.oid AND d.deptype = 'e')"
)


def test_sin_disparadores_ni_funciones_propias_tras_migrar(base_migrada: Engine):
    with base_migrada.connect() as conexion:
        disparadores = conexion.execute(text(DISPARADORES_DE_CONSULTORIO)).all()
        funciones = conexion.execute(text(FUNCIONES_PROPIAS_EN_PUBLIC)).all()

    assert disparadores == []
    assert funciones == []


def test_las_consultas_de_catalogo_detectan_un_disparador_y_una_funcion_propios(
    base_migrada: Engine,
):
    # Sensibilidad de la prueba anterior: dentro de una transaccion que se revierte se
    # crean una funcion y un disparador y las mismas consultas los encuentran.
    with base_migrada.connect() as conexion:
        transaccion = conexion.begin()
        conexion.execute(
            text(
                "CREATE FUNCTION public.f_prueba() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$"
            )
        )
        conexion.execute(
            text(
                "CREATE TRIGGER t_prueba BEFORE INSERT ON consultorio "
                "FOR EACH ROW EXECUTE FUNCTION public.f_prueba()"
            )
        )
        disparadores = conexion.execute(text(DISPARADORES_DE_CONSULTORIO)).scalars().all()
        funciones = conexion.execute(text(FUNCIONES_PROPIAS_EN_PUBLIC)).scalars().all()
        transaccion.rollback()

    assert disparadores == ["t_prueba"]
    assert funciones == ["f_prueba"]


# --- Migracion reversible con datos previos ---------------------------------------


def _tablas(motor: Engine) -> list[str]:
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


def test_subida_desde_0002_con_datos_previos_crea_tablas_vacias_y_conserva_usuarios(
    base_en_0002: Engine, config_alembic: Config
):
    _insertar_consultorios(base_en_0002, [ID_A, ID_B])
    _insertar_usuarios(base_en_0002, ID_A, 2)
    _insertar_usuarios(base_en_0002, ID_B, 1)
    usuarios_antes = _huella(base_en_0002)[1]

    command.upgrade(config_alembic, "0003")

    assert "sesion" in _tablas(base_en_0002) and "intento_login" in _tablas(base_en_0002)
    assert (_filas(base_en_0002, "sesion"), _filas(base_en_0002, "intento_login")) == (0, 0)
    assert _filas(base_en_0002, "usuario") == 3
    assert _huella(base_en_0002)[1] == usuarios_antes


def test_bajada_a_0002_elimina_solo_lo_agregado_y_conserva_los_datos(
    base_en_0002: Engine, config_alembic: Config
):
    _insertar_consultorios(base_en_0002, [ID_A, ID_B])
    _insertar_usuarios(base_en_0002, ID_A, 2)
    antes = _huella(base_en_0002)
    command.upgrade(config_alembic, "0003")

    command.downgrade(config_alembic, "0002")

    assert _tablas(base_en_0002) == ["alembic_version", "consultorio", "usuario"]
    assert "codigo" not in _columnas(base_en_0002, "consultorio")
    with base_en_0002.connect() as conexion:
        restricciones = conexion.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conname IN ('uq_consultorio_codigo', 'ck_consultorio_codigo_formato')"
            )
        ).all()
    assert restricciones == []
    assert _huella(base_en_0002) == antes

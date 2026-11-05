from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import cargar_configuracion
from app.core.migraciones import resolver_url_de_migracion
from app.models.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _obtener_url() -> str:
    """Solo lee las entradas y delega la decision (y la guardia) en el dominio."""
    return resolver_url_de_migracion(
        cargar_configuracion(),
        context.get_x_argument(as_dictionary=True).get("target"),
        config.get_main_option("sqlalchemy.url"),
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_obtener_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    motor = create_engine(_obtener_url(), poolclass=pool.NullPool)
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    motor.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

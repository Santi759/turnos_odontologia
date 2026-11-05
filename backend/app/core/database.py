from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings

_PUERTO_POR_DEFECTO = 5432
_SUFIJO_BASE_DE_PRUEBAS = "_test"


def crear_engine_desde_url(url: str) -> Engine:
    """Crea el motor sin conectar: la conexion se abre en el primer uso."""
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


def crear_engine(settings: Settings) -> Engine:
    return crear_engine_desde_url(settings.database_url.get_secret_value())


def crear_fabrica_de_sesiones(engine: Engine) -> sessionmaker[Session]:
    """Fabrica de sesiones sobre un motor dado; no crea instancias globales (DM-09).

    `expire_on_commit=False` para poder leer los objetos devueltos tras el commit.
    """
    return sessionmaker(bind=engine, expire_on_commit=False)


def verificar_conexion(engine: Engine) -> None:
    """Ejecuta SELECT 1 y deja propagar cualquier error de conexion."""
    with engine.connect() as conexion:
        conexion.execute(text("SELECT 1"))


def validar_url_de_pruebas(url_pruebas: str | None, url_desarrollo: str) -> None:
    """Guardia: se niega a usar una base de pruebas que pueda ser la de desarrollo.

    Los mensajes de error nunca incluyen las URLs (contienen credenciales).
    """
    if not url_pruebas:
        raise ValueError(
            "TEST_DATABASE_URL no esta definida: las pruebas de integracion "
            "requieren una base de pruebas separada"
        )
    pruebas = make_url(url_pruebas)
    desarrollo = make_url(url_desarrollo)
    destino_pruebas = (
        pruebas.host,
        pruebas.port or _PUERTO_POR_DEFECTO,
        pruebas.database,
    )
    destino_desarrollo = (
        desarrollo.host,
        desarrollo.port or _PUERTO_POR_DEFECTO,
        desarrollo.database,
    )
    if destino_pruebas == destino_desarrollo:
        raise ValueError(
            "TEST_DATABASE_URL apunta al mismo host, puerto y base que "
            "DATABASE_URL (base de desarrollo): se rechaza ejecutar las pruebas"
        )
    nombre = pruebas.database or ""
    if not nombre.endswith(_SUFIJO_BASE_DE_PRUEBAS):
        raise ValueError(
            "el nombre de la base de pruebas debe terminar en '_test'"
        )

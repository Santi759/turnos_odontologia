"""Comando explicito del seed: `python -m app.seed` (DC-07, DM-08).

Separado de las migraciones y del arranque de la API. Solo con APP_ENV=local y solo
contra `DATABASE_MIGRATION_URL`. Salida: unicamente cantidades.
"""
import sys
from collections.abc import Callable

from pydantic import ValidationError
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.config import Settings, cargar_configuracion
from app.core.database import AdministracionNoConfigurada, abrir_sesion_de_administracion
from app.seed.aplicar import aplicar_seed
from app.seed.entorno import validar_entorno_de_seed

_TABLA_INEXISTENTE = "42P01"


def _abrir_sesion_por_defecto(settings: Settings) -> Session:
    return abrir_sesion_de_administracion(settings)


def _error(mensaje: str) -> int:
    print(f"error: {mensaje}", file=sys.stderr)
    return 1


def main(
    abrir_sesion: Callable[[Settings], Session] = _abrir_sesion_por_defecto,
) -> int:
    """`abrir_sesion` es una costura de pruebas; el comando real usa el valor por defecto."""
    try:
        settings = cargar_configuracion()
    except ValidationError:
        return _error("configuracion invalida; revisar las variables de entorno")

    try:
        validar_entorno_de_seed(settings)
    except RuntimeError as exc:
        return _error(str(exc))

    try:
        sesion = abrir_sesion(settings)
    except AdministracionNoConfigurada as exc:
        return _error(str(exc))
    try:
        with sesion:
            resumen = aplicar_seed(sesion)
            sesion.commit()
    except ProgrammingError as exc:
        sesion.rollback()
        if getattr(exc.orig, "sqlstate", None) == _TABLA_INEXISTENTE:
            return _error("faltan tablas; aplicar primero las migraciones")
        return _error("no se pudo aplicar el seed")
    except Exception:
        sesion.rollback()
        return _error("no se pudo aplicar el seed")

    print(resumen.texto())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

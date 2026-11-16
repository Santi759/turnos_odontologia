"""Comando local de mantenimiento (DD-28, PC-03, DT-02).

Borra, por lotes, las sesiones vencidas o revocadas y los intentos de login de mas de 24 horas.

Uso (solo desarrollo local):

    docker compose run --rm --no-deps admin python -m app.mantenimiento limpiar [--max-lotes N]

Servicio `admin` (DD-34): el unico que recibe `DATABASE_MIGRATION_URL`; con `api` el comando falla sin
conectar.

- `--max-lotes N`: entero entre 1 y 1000 (por defecto 100). Cada lote borra hasta 1000 filas en su
  propia transaccion; por ejecucion se borran como maximo `1000 x N` filas por tabla.
- Solo corre con `APP_ENV=local` y solo sobre `DATABASE_MIGRATION_URL`; con otro entorno, o con argumentos
  invalidos, falla antes de abrir ninguna conexion.
- Nunca borra sesiones validas ni intentos dentro de la retencion de 24 horas, ni toca otras tablas.
- La salida solo contiene cantidades (`sesiones eliminadas: N; intentos eliminados: M`).

Deuda tecnica (DT-02): este comando es manual. Antes de cualquier despliegue fuera de local hace
falta un mecanismo de mantenimiento periodico autorizado por el autor.
"""

import sys
from argparse import ArgumentTypeError
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.reloj import Reloj, RelojSistema
from app.core.config import Settings, cargar_configuracion
from app.core.database import AdministracionNoConfigurada, abrir_sesion_de_administracion
from app.core.linea_de_comandos import AnalizadorSinEco, ArgumentosInvalidos
from app.mantenimiento.limpieza import limpiar

MAX_LOTES_POR_DEFECTO = 100
MAX_LOTES_LIMITE = 1000


@dataclass(frozen=True, slots=True)
class ArgumentosLimpieza:
    max_lotes: int


def _lotes(texto: str) -> int:
    try:
        valor = int(texto)
    except ValueError:
        raise ArgumentTypeError("entero requerido") from None
    if not 1 <= valor <= MAX_LOTES_LIMITE:
        raise ArgumentTypeError("fuera de rango")
    return valor


def analizar(argv: Sequence[str]) -> ArgumentosLimpieza:
    """Valida el subcomando y `--max-lotes` sin repetir lo recibido (lanza `ArgumentosInvalidos`)."""
    analizador = AnalizadorSinEco(prog="python -m app.mantenimiento")
    subcomandos = analizador.add_subparsers(dest="comando", required=True)
    limpiar_ = subcomandos.add_parser("limpiar")
    limpiar_.add_argument("--max-lotes", type=_lotes, default=MAX_LOTES_POR_DEFECTO)
    return ArgumentosLimpieza(max_lotes=analizador.parse_args(list(argv)).max_lotes)


def _abrir_sesion_por_defecto(settings: Settings) -> Session:
    return abrir_sesion_de_administracion(settings)


def _fallar(mensaje: str) -> int:
    print(f"error: {mensaje}", file=sys.stderr)
    return 1


def main(
    argv: Sequence[str] | None = None,
    *,
    abrir_sesion: Callable[[Settings], Session] = _abrir_sesion_por_defecto,
    reloj: Reloj | None = None,
) -> int:
    """`abrir_sesion` y `reloj` son costuras de pruebas; el comando real usa los valores por defecto."""
    try:
        argumentos = analizar(sys.argv[1:] if argv is None else argv)
    except ArgumentosInvalidos as exc:
        return _fallar(str(exc))
    try:
        settings = cargar_configuracion()
    except ValidationError:
        return _fallar("configuracion invalida; revisar las variables de entorno")
    if settings.app_env != "local":
        return _fallar("el comando de mantenimiento solo se ejecuta con APP_ENV=local")

    try:
        sesion = abrir_sesion(settings)
    except AdministracionNoConfigurada as exc:
        return _fallar(str(exc))
    try:
        resumen = limpiar(
            sesion,
            (reloj or RelojSistema()).ahora(),
            settings.auth_session_minutes,
            argumentos.max_lotes,
        )
    except Exception:
        sesion.rollback()
        return _fallar("no se pudo completar la limpieza")
    finally:
        sesion.close()
    print(resumen.texto())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

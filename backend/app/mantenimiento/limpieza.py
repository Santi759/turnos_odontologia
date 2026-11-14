"""Limpieza por lotes de sesiones e intentos vencidos (DD-28, PC-03).

Cada lote borra como maximo `TAMANO_DE_LOTE` filas en su propia transaccion (`commit` por lote).
Las sentencias de borrado viven en `app.auth.acceso_admin` (rol de administracion).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.auth import acceso_admin

TAMANO_DE_LOTE = 1000


@dataclass(frozen=True, slots=True)
class ResumenLimpieza:
    """Solo cantidades (X1)."""

    sesiones: int
    intentos: int

    def texto(self) -> str:
        return f"sesiones eliminadas: {self.sesiones}; intentos eliminados: {self.intentos}"


def _borrar_por_lotes(sesion: Session, borrar_lote: Callable[[], int], max_lotes: int) -> int:
    """Hasta `max_lotes` lotes; se detiene antes si un lote borra menos de `TAMANO_DE_LOTE`."""
    total = 0
    for _ in range(max_lotes):
        borradas = borrar_lote()
        sesion.commit()
        total += borradas
        if borradas < TAMANO_DE_LOTE:
            break
    return total


def limpiar(
    sesion: Session, ahora: datetime, minutos_inactividad: int, max_lotes: int
) -> ResumenLimpieza:
    sesiones = _borrar_por_lotes(
        sesion,
        lambda: acceso_admin.limpiar_sesiones(
            sesion, ahora, minutos_inactividad, TAMANO_DE_LOTE
        ),
        max_lotes,
    )
    intentos = _borrar_por_lotes(
        sesion, lambda: acceso_admin.limpiar_intentos(sesion, ahora, TAMANO_DE_LOTE), max_lotes
    )
    return ResumenLimpieza(sesiones=sesiones, intentos=intentos)

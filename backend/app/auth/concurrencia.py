"""Concurrencia acotada de las verificaciones Argon2 por proceso (DD-29, PC-02)."""

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Protocol, TypeVar

CUPOS_POR_PROCESO = 4
ESPERA_MAXIMA_SEGUNDOS = 3.0

T = TypeVar("T")


class ServicioOcupado(Exception):
    """No hubo cupo de Argon2 dentro de la espera maxima (se traduce en 503)."""


class _Semaforo(Protocol):
    def acquire(self, timeout: float | None = ...) -> bool: ...
    def release(self) -> None: ...


class LimitadorArgon2:
    """Limita las verificaciones simultaneas; el cupo se libera siempre en `finally`."""

    def __init__(
        self,
        cupos: int = CUPOS_POR_PROCESO,
        espera_segundos: float = ESPERA_MAXIMA_SEGUNDOS,
        semaforo: _Semaforo | None = None,
    ) -> None:
        self.semaforo: _Semaforo = semaforo if semaforo is not None else threading.BoundedSemaphore(cupos)
        self._espera_segundos = espera_segundos

    @contextmanager
    def cupo(self) -> Iterator[None]:
        # Si `acquire` falla o se cancela durante la espera, no se tomo ningun cupo.
        if not self.semaforo.acquire(timeout=self._espera_segundos):
            raise ServicioOcupado
        try:
            yield
        finally:
            self.semaforo.release()

    def ejecutar(self, funcion: Callable[..., T], *args: object) -> T:
        with self.cupo():
            return funcion(*args)

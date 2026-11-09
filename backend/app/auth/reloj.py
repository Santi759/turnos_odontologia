"""Reloj de la aplicacion, inyectable (DD-03)."""

from datetime import UTC, datetime
from typing import Protocol


class Reloj(Protocol):
    def ahora(self) -> datetime: ...


class RelojSistema:
    def ahora(self) -> datetime:
        return datetime.now(UTC)

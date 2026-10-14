"""Validacion de superposicion de turnos del mismo profesional (dominio puro).

Intervalos semiabiertos ``[inicio, fin)`` con instantes con zona horaria
(RN-AG-02, RN-AG-04). Sin I/O, sin persistencia, sin estados de turno.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Final

MENSAJE_SUPERPOSICION: Final[str] = (
    "El horario se superpone con otro turno del mismo profesional."
)


class SuperposicionError(Exception):
    """El candidato se superpone con un turno del mismo profesional."""


class IntervaloInvalidoError(ValueError):
    """Un intervalo recibido no es valido (orden o zona horaria)."""


@dataclass(frozen=True)
class IntervaloDeTurno:
    profesional_id: str
    inicio: datetime
    fin: datetime


def _tiene_zona_horaria(instante: datetime) -> bool:
    return instante.tzinfo is not None and instante.utcoffset() is not None


def _validar_intervalo(intervalo: IntervaloDeTurno) -> None:
    if not (_tiene_zona_horaria(intervalo.inicio) and _tiene_zona_horaria(intervalo.fin)):
        raise IntervaloInvalidoError("Los instantes deben tener zona horaria.")
    if intervalo.inicio >= intervalo.fin:
        raise IntervaloInvalidoError("El inicio debe ser anterior al fin.")


def _se_superponen(a: IntervaloDeTurno, b: IntervaloDeTurno) -> bool:
    return a.inicio < b.fin and b.inicio < a.fin


def validar_sin_superposicion(
    candidato: IntervaloDeTurno,
    turnos_que_ocupan_agenda: Iterable[IntervaloDeTurno],
) -> None:
    turnos = list(turnos_que_ocupan_agenda)
    for intervalo in (candidato, *turnos):
        _validar_intervalo(intervalo)
    for existente in turnos:
        if existente.profesional_id != candidato.profesional_id:
            continue
        if _se_superponen(candidato, existente):
            raise SuperposicionError(MENSAJE_SUPERPOSICION)

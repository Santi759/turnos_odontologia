"""Politica pura de bloqueo por intentos fallidos de login (DD-09, DD-10, PC-04).

La politica no hace I/O ni usa reloj propio: recibe los instantes de los fallos y `ahora`.
La orquestacion (locks consultivos y lectura de fallos) esta al final y solo llama a
`acceso_login`. Los bloqueos no se guardan; se calculan desde los fallos. Los contadores de cuenta y de IP son
independientes: el de cuenta ignora los fallos descartados (`descartado_para_cuenta`)
y el de IP los cuenta todos.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import acceso_login

HORIZONTE_DE_CONSULTA = timedelta(minutes=30)


@dataclass(frozen=True)
class Politica:
    umbral: int
    ventana: timedelta
    duracion_bloqueo: timedelta


POLITICA_CUENTA = Politica(umbral=5, ventana=timedelta(minutes=15), duracion_bloqueo=timedelta(minutes=15))
POLITICA_IP = Politica(umbral=30, ventana=timedelta(minutes=15), duracion_bloqueo=timedelta(minutes=15))


@dataclass(frozen=True)
class Intento:
    ocurrido_en: datetime
    descartado_para_cuenta: bool = False


def evaluar_bloqueo(fallos: Iterable[datetime], ahora: datetime, politica: Politica) -> int | None:
    """Segundos de `Retry-After` si hay bloqueo vigente; `None` si no lo hay.

    Bloquea si los `umbral` fallos mas recientes de los ultimos 30 minutos caben en la ventana
    y `ahora` esta antes del fin del bloqueo, contado desde el fallo mas reciente.
    """
    recientes = sorted(f for f in fallos if f > ahora - HORIZONTE_DE_CONSULTA)
    ultimos = recientes[-politica.umbral :]
    if len(ultimos) < politica.umbral:
        return None
    mas_reciente, mas_antiguo = ultimos[-1], ultimos[0]
    fin = mas_reciente + politica.duracion_bloqueo
    if mas_reciente - mas_antiguo > politica.ventana or ahora >= fin:
        return None
    return max(1, math.ceil((fin - ahora).total_seconds()))


def evaluar_cuenta(intentos: Sequence[Intento], ahora: datetime) -> int | None:
    """Bloqueo por (codigo, email): ignora los fallos descartados por un login exitoso."""
    contables = (i.ocurrido_en for i in intentos if not i.descartado_para_cuenta)
    return evaluar_bloqueo(contables, ahora, POLITICA_CUENTA)


def evaluar_ip(intentos: Sequence[Intento], ahora: datetime) -> int | None:
    """Bloqueo por IP: cuenta todos los fallos, incluidos los descartados para la cuenta."""
    return evaluar_bloqueo((i.ocurrido_en for i in intentos), ahora, POLITICA_IP)


def descartar_para_cuenta(intentos: Iterable[Intento]) -> list[Intento]:
    """Efecto de un login exitoso sobre el par: marca los fallos sin borrarlos ni mutarlos."""
    return [replace(i, descartado_para_cuenta=True) for i in intentos]


# --- Orquestacion con locks consultivos (DD-09, DD-10; atomicidad por par y por IP) -------------


def clave_de_lock(clave: bytes) -> int:
    """Primeros 8 bytes de la clave como `bigint` con signo (clave del lock consultivo)."""
    return int.from_bytes(clave[:8], "big", signed=True)


def tomar_locks(db: Session, clave_cuenta: bytes, clave_ip: bytes) -> None:
    """Locks de transaccion por cuenta y luego por IP, SIEMPRE en ese orden (sin interbloqueos)."""
    for clave in (clave_cuenta, clave_ip):
        db.execute(text("SELECT pg_advisory_xact_lock(:clave)"), {"clave": clave_de_lock(clave)})


def bloqueo_vigente(db: Session, clave_cuenta: bytes, clave_ip: bytes, ahora: datetime) -> int | None:
    """Mayor `Retry-After` entre el bloqueo de la cuenta y el de la IP; `None` si no hay ninguno."""
    desde = ahora - HORIZONTE_DE_CONSULTA
    de_cuenta = evaluar_bloqueo(
        acceso_login.fallos_de_cuenta(db, clave_cuenta, desde),
        ahora,
        POLITICA_CUENTA,
    )
    de_ip = evaluar_bloqueo(
        acceso_login.fallos_de_ip(db, clave_ip, desde), ahora, POLITICA_IP
    )
    vigentes = [segundos for segundos in (de_cuenta, de_ip) if segundos is not None]
    return max(vigentes) if vigentes else None

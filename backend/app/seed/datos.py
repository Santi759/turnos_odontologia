"""Datos ficticios del seed (D1, DD-13). Solo dominio reservado `example.test`.

Los identificadores son UUIDv7 literales, generados una sola vez con `uuid.uuid7()`
(DP-04): el seed es determinista y todos los `id` del sistema siguen siendo version 7.
El codigo de cada consultorio es un literal explicito (los ultimos 12 digitos
hexadecimales del `id`, con prefijo `c-`; una prueba comprueba la igualdad con la regla
de derivacion). No hay credenciales: los usuarios del seed quedan sin credencial (DC-08).
"""
import uuid
from dataclasses import dataclass

from app.models.usuario import Rol


@dataclass(frozen=True, slots=True)
class ConsultorioSeed:
    id: uuid.UUID
    nombre: str
    codigo: str


@dataclass(frozen=True, slots=True)
class UsuarioSeed:
    id: uuid.UUID
    consultorio_id: uuid.UUID
    email: str
    nombre: str
    rol: Rol


_ID_CONSULTORIO_A = uuid.UUID("01a1a95a-dd90-73e7-9496-c7d08d776d19")
_ID_CONSULTORIO_B = uuid.UUID("01a1a95a-dd90-73e7-9496-c7d1647cab52")

CONSULTORIOS: tuple[ConsultorioSeed, ...] = (
    ConsultorioSeed(_ID_CONSULTORIO_A, "Consultorio Demo A", "c-c7d08d776d19"),
    ConsultorioSeed(_ID_CONSULTORIO_B, "Consultorio Demo B", "c-c7d1647cab52"),
)

USUARIOS: tuple[UsuarioSeed, ...] = (
    UsuarioSeed(
        uuid.UUID("01a1a95a-dd90-73e7-9496-c7d22e827a4f"),
        _ID_CONSULTORIO_A,
        "administracion.a@example.test",
        "Administración Demo A",
        Rol.ADMINISTRADOR,
    ),
    UsuarioSeed(
        uuid.UUID("01a1a95a-dd90-73e7-9496-c7d32a7f9bed"),
        _ID_CONSULTORIO_A,
        "secretaria.a@example.test",
        "Secretaría Demo A",
        Rol.SECRETARIA,
    ),
    UsuarioSeed(
        uuid.UUID("01a1a95a-dd90-73e7-9496-c7d4c7fdd969"),
        _ID_CONSULTORIO_A,
        "odontologia.a@example.test",
        "Odontología Demo A",
        Rol.ODONTOLOGO,
    ),
    UsuarioSeed(
        uuid.UUID("01a1a95a-dd90-73e7-9496-c7d52b80648e"),
        _ID_CONSULTORIO_B,
        "administracion.b@example.test",
        "Administración Demo B",
        Rol.ADMINISTRADOR,
    ),
    UsuarioSeed(
        uuid.UUID("01a1a95a-dd90-73e7-9496-c7d686f326a4"),
        _ID_CONSULTORIO_B,
        "secretaria.b@example.test",
        "Secretaría Demo B",
        Rol.SECRETARIA,
    ),
    UsuarioSeed(
        uuid.UUID("01a1a95a-dd90-73e7-9496-c7d78488bdaf"),
        _ID_CONSULTORIO_B,
        "odontologia.b@example.test",
        "Odontología Demo B",
        Rol.ODONTOLOGO,
    ),
)

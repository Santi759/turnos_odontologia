"""Tipos de datos del acceso previo al contexto: cuenta y sesion resuelta (DD-25).

Solo dataclasses inmutables, sin I/O: los comparten los modulos de acceso (`acceso_login`,
`acceso_previo`, `acceso_admin`) sin importarse entre si.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Cuenta:
    """Usuario y consultorio encontrados por (codigo, email), con los datos para decidir el login."""

    usuario_id: uuid.UUID
    consultorio_id: uuid.UUID
    email: str
    nombre: str
    rol: str
    credencial: str | None
    usuario_activo: bool
    consultorio_nombre: str
    consultorio_activo: bool


@dataclass(frozen=True, slots=True)
class SesionResuelta:
    """Sesion con su usuario y consultorio; la validez la decide el servicio (DD-04)."""

    sesion_id: uuid.UUID
    consultorio_id: uuid.UUID
    usuario_id: uuid.UUID
    email: str
    nombre: str
    rol: str
    consultorio_nombre: str
    usuario_activo: bool
    consultorio_activo: bool
    creada_en: datetime
    ultimo_uso_en: datetime
    vence_absoluto_en: datetime
    revocada_en: datetime | None

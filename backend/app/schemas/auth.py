"""Esquemas de autenticacion (DA-13, DD-23)."""

from pydantic import BaseModel, Field

from app.schemas.base import EsquemaEntrada

MAXIMO_CONTRASENA = 128  # puntos de codigo de la entrada SIN normalizar (DD-16)
MAXIMO_CODIGO = 64
MAXIMO_EMAIL = 254


class EntradaLogin(EsquemaEntrada):
    codigo_consultorio: str = Field(max_length=MAXIMO_CODIGO)
    email: str = Field(max_length=MAXIMO_EMAIL)
    contrasena: str = Field(max_length=MAXIMO_CONTRASENA)


class UsuarioRespuesta(BaseModel):
    nombre: str
    email: str
    rol: str


class ConsultorioRespuesta(BaseModel):
    nombre: str


class RespuestaIdentidad(BaseModel):
    """Exactamente usuario (nombre, email, rol) y consultorio (nombre): ningun id ni secreto."""

    usuario: UsuarioRespuesta
    consultorio: ConsultorioRespuesta

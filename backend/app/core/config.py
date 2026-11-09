import base64
import re
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Valor de AUTH_SECRET_KEY que declara .env.example: un marcador que se rechaza (DD-17);
# una prueba verifica que coincide con la plantilla.
VALOR_PLANTILLA_AUTH_SECRET_KEY = "REEMPLAZAR_generar_con_secrets_token_urlsafe_48"

# Un mensaje fijo por regla: nombran la variable y nunca incluyen el valor (DD-17).
MENSAJE_CLAVE_VACIA = "AUTH_SECRET_KEY no puede estar vacia ni contener espacios"
MENSAJE_CLAVE_MAL_CODIFICADA = "AUTH_SECRET_KEY debe ser texto base64url valido"
MENSAJE_CLAVE_CORTA = "AUTH_SECRET_KEY debe decodificarse a al menos 32 bytes"
MENSAJE_CLAVE_POCA_DIVERSIDAD = "AUTH_SECRET_KEY tiene poca diversidad de caracteres"
MENSAJE_CLAVE_PERIODICA = "AUTH_SECRET_KEY no puede ser la repeticion de un bloque"
MENSAJE_CLAVE_CON_MARCADOR = "AUTH_SECRET_KEY contiene un marcador de ejemplo"
MENSAJE_CLAVE_ES_LA_PLANTILLA = "AUTH_SECRET_KEY no puede ser el valor de la plantilla .env.example"

_ALFABETO_BASE64URL = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")
_BYTES_MINIMOS_DE_LA_CLAVE = 32
_DISTINTOS_MINIMOS_DE_LA_CLAVE = 20
_MARCADORES_DE_LA_CLAVE = (
    "cambiar",
    "reemplazar",
    "ficticio",
    "ficticia",
    "example",
    "ejemplo",
    "changeme",
    "secret",
    "password",
    "contrasena",
)


def _es_periodica(texto: str) -> bool:
    return any(
        texto == (texto[:periodo] * (len(texto) // periodo + 1))[: len(texto)]
        for periodo in range(1, len(texto) // 2 + 1)
    )


def _decodificar_clave(texto: str) -> bytes | None:
    """Decodifica base64url estricto (relleno opcional pero correcto); None si es invalido."""
    if not _ALFABETO_BASE64URL.match(texto):
        return None
    sin_relleno = texto.rstrip("=")
    relleno = len(texto) - len(sin_relleno)
    faltante = -len(sin_relleno) % 4
    if len(sin_relleno) % 4 == 1 or (relleno and relleno != faltante):
        return None
    return base64.urlsafe_b64decode(sin_relleno + "=" * faltante)


def _error_de_clave(texto: str) -> str | None:
    if not texto or texto != texto.strip() or any(c.isspace() for c in texto):
        return MENSAJE_CLAVE_VACIA
    decodificada = _decodificar_clave(texto)
    if decodificada is None:
        return MENSAJE_CLAVE_MAL_CODIFICADA
    if len(decodificada) < _BYTES_MINIMOS_DE_LA_CLAVE:
        return MENSAJE_CLAVE_CORTA
    sin_relleno = texto.rstrip("=")
    if len(set(sin_relleno)) < _DISTINTOS_MINIMOS_DE_LA_CLAVE:
        return MENSAJE_CLAVE_POCA_DIVERSIDAD
    if _es_periodica(sin_relleno):
        return MENSAJE_CLAVE_PERIODICA
    if any(marcador in texto.lower() for marcador in _MARCADORES_DE_LA_CLAVE):
        return MENSAJE_CLAVE_CON_MARCADOR
    if texto == VALOR_PLANTILLA_AUTH_SECRET_KEY:
        return MENSAJE_CLAVE_ES_LA_PLANTILLA
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False, populate_by_name=True, hide_input_in_errors=True
    )

    database_url: SecretStr = Field(validation_alias="DATABASE_URL")
    test_database_url: SecretStr | None = Field(
        default=None, validation_alias="TEST_DATABASE_URL"
    )
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        validation_alias="CORS_ALLOWED_ORIGINS"
    )
    app_env: Literal["local", "test"] = Field(validation_alias="APP_ENV")
    auth_secret_key: SecretStr = Field(validation_alias="AUTH_SECRET_KEY")
    auth_session_minutes: int = Field(
        default=30, ge=5, le=480, validation_alias="AUTH_SESSION_MINUTES"
    )
    auth_session_max_hours: int = Field(
        default=12, ge=1, le=24, validation_alias="AUTH_SESSION_MAX_HOURS"
    )
    auth_cookie_secure: bool = Field(default=True, validation_alias="AUTH_COOKIE_SECURE")

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _separar_origenes(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [origen.strip() for origen in valor.split(",") if origen.strip()]
        return valor

    @field_validator("cors_allowed_origins")
    @classmethod
    def _validar_origenes(cls, origenes: list[str]) -> list[str]:
        if not origenes:
            raise ValueError("debe listar al menos un origen")
        if "*" in origenes:
            raise ValueError("no se admite el comodin '*'")
        return origenes

    @field_validator("auth_secret_key")
    @classmethod
    def _validar_clave(cls, clave: SecretStr) -> SecretStr:
        error = _error_de_clave(clave.get_secret_value())
        if error is not None:
            raise ValueError(error)
        return clave

    @model_validator(mode="after")
    def _validar_coherencia_de_autenticacion(self) -> "Settings":
        if self.auth_session_minutes > self.auth_session_max_hours * 60:
            raise ValueError(
                "AUTH_SESSION_MINUTES no puede superar AUTH_SESSION_MAX_HOURS"
            )
        if not self.auth_cookie_secure and self.app_env != "local":
            raise ValueError("AUTH_COOKIE_SECURE=false solo se admite con APP_ENV=local")
        return self

    @property
    def auth_hmac_key(self) -> bytes:
        return base64.urlsafe_b64decode(self._clave_sin_relleno() + "===")

    def _clave_sin_relleno(self) -> str:
        return self.auth_secret_key.get_secret_value().rstrip("=")


def cargar_configuracion() -> Settings:
    return Settings()

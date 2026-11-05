from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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


def cargar_configuracion() -> Settings:
    return Settings()

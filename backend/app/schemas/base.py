from pydantic import BaseModel, ConfigDict


class EsquemaEntrada(BaseModel):
    """Base de todo esquema de entrada de la API: rechaza campos no declarados."""

    model_config = ConfigDict(extra="forbid")

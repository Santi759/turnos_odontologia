from typing import Literal

from pydantic import BaseModel


class RespuestaSalud(BaseModel):
    status: Literal["ok"]

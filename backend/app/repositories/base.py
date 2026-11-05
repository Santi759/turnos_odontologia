from typing import ClassVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.repositories.contexto import ContextoConsultorio


class RepositorioAcotado[M: Base]:
    """Base de los repositorios de tablas con `consultorio_id`.

    Toda lectura parte de `_seleccionar()` y toda modificacion incluye
    `_condicion_de_consultorio()`: el consultorio sale SIEMPRE del contexto, nunca
    de un parametro del llamador. No hace `commit`; el llamador controla la
    transaccion.

    Advertencia: este filtro (y los UUIDv7 no secuenciales) es defensa en
    profundidad, NO autorizacion ni barrera en la base. RBAC y RLS son de C-04
    (RN-MT-06).
    """

    modelo: ClassVar[type[Base]]

    def __init__(self, sesion: Session, contexto: ContextoConsultorio) -> None:
        if not isinstance(contexto, ContextoConsultorio):
            raise TypeError("se requiere un ContextoConsultorio")
        self._sesion = sesion
        self._contexto = contexto

    @property
    def contexto(self) -> ContextoConsultorio:
        return self._contexto

    def _condicion_de_consultorio(self):
        return self.modelo.consultorio_id == self._contexto.consultorio_id  # type: ignore[attr-defined]

    def _seleccionar(self) -> Select[tuple[M]]:
        return select(self.modelo).where(self._condicion_de_consultorio())  # type: ignore[return-value]

    def _seleccionar_por_id(self, id_: UUID) -> Select[tuple[M]]:
        return self._seleccionar().where(self.modelo.id == id_)  # type: ignore[attr-defined]

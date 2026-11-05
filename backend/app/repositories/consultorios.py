from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.consultorio import Consultorio
from app.repositories.contexto import ContextoConsultorio


class ConsultorioRepositorio:
    """Solo el consultorio del contexto (PA-05 = solo seed: sin listar ni crear).

    No deriva de RepositorioAcotado porque `consultorio` no tiene `consultorio_id`:
    se acota por su propio `id`. Devuelve el consultorio aunque este inactivo (DP-03
    se decide en C-03). No reemplaza la autorizacion ni RLS de C-04 (RN-MT-06).
    """

    def __init__(self, sesion: Session, contexto: ContextoConsultorio) -> None:
        if not isinstance(contexto, ContextoConsultorio):
            raise TypeError("se requiere un ContextoConsultorio")
        self._sesion = sesion
        self._contexto = contexto

    def _consulta_actual(self) -> Select[tuple[Consultorio]]:
        return select(Consultorio).where(Consultorio.id == self._contexto.consultorio_id)

    def obtener_actual(self) -> Consultorio | None:
        return self._sesion.scalars(self._consulta_actual()).first()

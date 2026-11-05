import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContextoConsultorio:
    """Consultorio sobre el que opera una peticion, confiable y solo del servidor.

    Se construye UNICAMENTE en codigo del servidor. En C-03 lo construira la
    dependencia `contexto_consultorio` a partir de la identidad autenticada
    (RN-MT-02); en C-02 solo lo construyen las pruebas. No es un esquema de
    entrada: nunca debe armarse con datos del cuerpo, query o encabezados.

    Los repositorios acotados por este contexto y los UUIDv7 no reemplazan la
    autorizacion por rol ni la barrera en la base (RLS), que corresponden a C-04
    (RN-MT-06).
    """

    consultorio_id: uuid.UUID

    def __post_init__(self) -> None:
        if not isinstance(self.consultorio_id, uuid.UUID):
            raise TypeError("consultorio_id debe ser un uuid.UUID")

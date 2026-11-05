from dataclasses import dataclass

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.consultorio import Consultorio
from app.models.usuario import Usuario
from app.seed.datos import CONSULTORIOS, USUARIOS


@dataclass(frozen=True, slots=True)
class ResumenSeed:
    """Solo cantidades (X1): nunca emails, nombres, URLs ni credenciales."""

    consultorios_insertados: int
    consultorios_omitidos: int
    usuarios_insertados: int
    usuarios_omitidos: int

    def texto(self) -> str:
        return (
            f"consultorios: {self.consultorios_insertados} insertados, "
            f"{self.consultorios_omitidos} omitidos; "
            f"usuarios: {self.usuarios_insertados} insertados, "
            f"{self.usuarios_omitidos} omitidos"
        )


def aplicar_seed(sesion: Session) -> ResumenSeed:
    """Inserta el seed sin tocar filas existentes.

    Solo `INSERT ... ON CONFLICT DO NOTHING` sin destino de conflicto: cualquier
    restriccion de unicidad (clave primaria o `(consultorio_id, email)`) omite la fila.
    Nunca actualiza ni borra. No hace `commit`; el llamador controla la transaccion.
    """
    consultorios_insertados = 0
    for consultorio in CONSULTORIOS:
        filas = sesion.execute(
            insert(Consultorio)
            .values(id=consultorio.id, nombre=consultorio.nombre)
            .on_conflict_do_nothing()
            .returning(Consultorio.id)
        ).all()
        consultorios_insertados += len(filas)

    usuarios_insertados = 0
    for usuario in USUARIOS:
        filas = sesion.execute(
            insert(Usuario)
            .values(
                id=usuario.id,
                consultorio_id=usuario.consultorio_id,
                email=usuario.email,
                nombre=usuario.nombre,
                rol=usuario.rol.value,
            )
            .on_conflict_do_nothing()
            .returning(Usuario.id)
        ).all()
        usuarios_insertados += len(filas)

    return ResumenSeed(
        consultorios_insertados=consultorios_insertados,
        consultorios_omitidos=len(CONSULTORIOS) - consultorios_insertados,
        usuarios_insertados=usuarios_insertados,
        usuarios_omitidos=len(USUARIOS) - usuarios_insertados,
    )

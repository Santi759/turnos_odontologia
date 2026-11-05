from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, update

from app.models.usuario import Rol, Usuario, normalizar_email
from app.repositories.base import RepositorioAcotado


@dataclass(frozen=True, slots=True)
class NuevoUsuario:
    """Datos de alta de un usuario. Sin `consultorio_id` ni credencial (D5)."""

    email: str
    nombre: str
    rol: Rol


class UsuarioRepositorio(RepositorioAcotado[Usuario]):
    """Usuarios del consultorio del contexto (ver advertencia en RepositorioAcotado)."""

    modelo = Usuario

    def _consulta_listar(self) -> Select[tuple[Usuario]]:
        return self._seleccionar().order_by(Usuario.creado_en, Usuario.id)

    def _consulta_obtener_por_id(self, usuario_id: UUID) -> Select[tuple[Usuario]]:
        return self._seleccionar_por_id(usuario_id)

    def _consulta_buscar_por_email(self, email: str) -> Select[tuple[Usuario]]:
        return self._seleccionar().where(Usuario.email == normalizar_email(email))

    def listar(self) -> list[Usuario]:
        return list(self._sesion.scalars(self._consulta_listar()))

    def obtener_por_id(self, usuario_id: UUID) -> Usuario | None:
        return self._sesion.scalars(self._consulta_obtener_por_id(usuario_id)).first()

    def buscar_por_email(self, email: str) -> Usuario | None:
        return self._sesion.scalars(self._consulta_buscar_por_email(email)).first()

    def crear(self, datos: NuevoUsuario) -> Usuario:
        usuario = Usuario(
            consultorio_id=self._contexto.consultorio_id,
            email=normalizar_email(datos.email),
            nombre=datos.nombre,
            rol=Rol(datos.rol).value,
        )
        self._sesion.add(usuario)
        self._sesion.flush()
        return usuario

    def desactivar(self, usuario_id: UUID) -> bool:
        resultado = self._sesion.execute(
            update(Usuario)
            .where(self._condicion_de_consultorio(), Usuario.id == usuario_id)
            .values(activo=False)
        )
        return resultado.rowcount > 0

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Rol(StrEnum):
    ADMINISTRADOR = "administrador"
    SECRETARIA = "secretaria"
    ODONTOLOGO = "odontologo"


def normalizar_email(email: str) -> str:
    """Normaliza un email para guardarlo y buscarlo (DM-03): sin espacios en los
    extremos y en minusculas. Debe coincidir con `lower(btrim(email))` de la base."""
    return email.strip().lower()


_ROLES_SQL = ", ".join(f"'{rol.value}'" for rol in Rol)


class Usuario(Base):
    """Usuario de un unico consultorio (SU-02). `credencial` nula = sin credencial."""

    __tablename__ = "usuario"
    __table_args__ = (
        UniqueConstraint("consultorio_id", "id", name="uq_usuario_consultorio_id_id"),
        UniqueConstraint(
            "consultorio_id", "email", name="uq_usuario_consultorio_id_email"
        ),
        CheckConstraint(f"rol IN ({_ROLES_SQL})", name="rol_valido"),
        CheckConstraint(
            "email = lower(btrim(email)) AND email <> ''", name="email_normalizado"
        ),
        CheckConstraint(
            "credencial IS NULL OR credencial <> ''", name="credencial_no_vacia"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuidv7()")
    )
    consultorio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("consultorio.id", ondelete="RESTRICT"), nullable=False
    )
    email: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    # Diferida con raiseload (C-04, DD-30): `turnos_app` no puede leerla y `select(Usuario)` nunca la
    # pide. Solo se carga con `undefer(Usuario.credencial)` desde un rol que la tenga concedida.
    credencial: Mapped[str | None] = mapped_column(
        Text, nullable=True, deferred=True, deferred_raiseload=True
    )
    rol: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Consultorio(Base):
    """Consultorio (tenant). El `id` lo genera PostgreSQL 18 con `uuidv7()`."""

    __tablename__ = "consultorio"
    __table_args__ = (
        CheckConstraint(
            "anticipacion_cancelacion_horas >= 0",
            name="anticipacion_no_negativa",
        ),
        UniqueConstraint("codigo", name="uq_consultorio_codigo"),
        CheckConstraint(
            "codigo ~ '^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$'", name="codigo_formato"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuidv7()")
    )
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    # Obligatorio y SIN valor por defecto (C-03): siempre lo indica quien inserta.
    codigo: Mapped[str] = mapped_column(Text, nullable=False)
    zona_horaria: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'America/Argentina/Buenos_Aires'")
    )
    anticipacion_cancelacion_horas: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("24")
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

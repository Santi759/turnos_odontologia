import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Text, Uuid, text
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
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuidv7()")
    )
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
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

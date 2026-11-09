import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Sesion(Base):
    """Sesion de un usuario (DA-01). Solo guarda el HMAC del token, nunca el token."""

    __tablename__ = "sesion"
    __table_args__ = (
        UniqueConstraint("token_hmac", name="uq_sesion_token_hmac"),
        ForeignKeyConstraint(
            ["consultorio_id", "usuario_id"],
            ["usuario.consultorio_id", "usuario.id"],
            name="fk_sesion_consultorio_id_usuario",
            ondelete="CASCADE",
        ),
        CheckConstraint("octet_length(token_hmac) = 32", name="token_hmac_longitud"),
        CheckConstraint(
            "creada_en < vence_absoluto_en AND ultimo_uso_en >= creada_en "
            "AND ultimo_uso_en <= vence_absoluto_en",
            name="vencimientos_coherentes",
        ),
        CheckConstraint(
            "revocada_en IS NULL OR revocada_en >= creada_en",
            name="revocacion_posterior",
        ),
        Index("ix_sesion_consultorio_id_usuario_id", "consultorio_id", "usuario_id"),
        Index("ix_sesion_vence_absoluto_en", "vence_absoluto_en"),
        Index("ix_sesion_ultimo_uso_en", "ultimo_uso_en"),
        Index("ix_sesion_revocada_en", "revocada_en"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuidv7()")
    )
    consultorio_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    token_hmac: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ultimo_uso_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    vence_absoluto_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revocada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

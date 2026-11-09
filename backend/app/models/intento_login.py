from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Identity,
    Index,
    LargeBinary,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IntentoLogin(Base):
    """Fallo de login evaluado (DD-09, DD-10). Solo claves HMAC: sin codigo, email ni IP."""

    __tablename__ = "intento_login"
    __table_args__ = (
        CheckConstraint(
            "octet_length(clave_cuenta) = 32 AND octet_length(clave_ip) = 32",
            name="claves_longitud",
        ),
        Index(
            "ix_intento_login_clave_cuenta_ocurrido_en", "clave_cuenta", "ocurrido_en"
        ),
        Index("ix_intento_login_clave_ip_ocurrido_en", "clave_ip", "ocurrido_en"),
        Index("ix_intento_login_ocurrido_en", "ocurrido_en"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    clave_cuenta: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    clave_ip: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    ocurrido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    descartado_para_cuenta: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false()
    )

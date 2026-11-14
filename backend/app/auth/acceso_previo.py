"""Sesion antes de conocer el consultorio, con el rol `turnos_app` (DD-25, DD-27).

Resolver, renovar y revocar por el HMAC del token usan funciones `SECURITY DEFINER` del esquema
`acceso` (dueno `turnos_acceso_previo`, que no puede leer credenciales ni `intento_login`). La
creacion de la sesion y la revocacion por `id` (logout) son sentencias directas bajo el contexto
transaccional del consultorio y RLS. Este modulo no conoce credenciales.
"""

import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.cuenta import SesionResuelta


def resolver_sesion(sesion: Session, token_hmac: bytes) -> SesionResuelta | None:
    """Sesion por el HMAC de su token, sin juzgar su validez (sin `token_hmac` ni credencial)."""
    fila = sesion.execute(
        text("SELECT * FROM acceso.resolver_sesion(:token_hmac)"), {"token_hmac": token_hmac}
    ).one()
    if fila.o_sesion_id is None:
        return None
    return SesionResuelta(
        sesion_id=fila.o_sesion_id,
        consultorio_id=fila.o_consultorio_id,
        usuario_id=fila.o_usuario_id,
        email=fila.o_email,
        nombre=fila.o_nombre,
        rol=fila.o_rol,
        consultorio_nombre=fila.o_consultorio_nombre,
        usuario_activo=fila.o_usuario_activo,
        consultorio_activo=fila.o_consultorio_activo,
        creada_en=fila.o_creada_en,
        ultimo_uso_en=fila.o_ultimo_uso_en,
        vence_absoluto_en=fila.o_vence_absoluto_en,
        revocada_en=fila.o_revocada_en,
    )


def renovar_sesion(sesion: Session, token_hmac: bytes, ahora: datetime) -> bool:
    """Renueva `ultimo_uso_en` solo si pasaron >= 60 s, sin revocar y antes del absoluto (DD-04)."""
    return sesion.execute(
        text("SELECT acceso.renovar_sesion(:token_hmac, :ahora)"),
        {"token_hmac": token_hmac, "ahora": ahora},
    ).scalar_one()


def revocar_sesion_por_token(sesion: Session, token_hmac: bytes, ahora: datetime) -> bool:
    """Revoca la sesion entrante por el HMAC de su token (login exitoso, DD-06)."""
    return sesion.execute(
        text("SELECT acceso.revocar_sesion_por_token(:token_hmac, :ahora)"),
        {"token_hmac": token_hmac, "ahora": ahora},
    ).scalar_one()


def limpiar_sesiones(sesion: Session, ahora: datetime, minutos_inactividad: int) -> int:
    """Borra como maximo 100 sesiones revocadas o vencidas (absoluto o inactividad, DD-21)."""
    return sesion.execute(
        text("SELECT acceso.limpiar_sesiones(:ahora, :minutos)"),
        {"ahora": ahora, "minutos": minutos_inactividad},
    ).scalar_one()


def crear_sesion(
    sesion: Session,
    consultorio_id: uuid.UUID,
    usuario_id: uuid.UUID,
    token_hmac: bytes,
    creada_en: datetime,
    vence_absoluto_en: datetime,
) -> uuid.UUID:
    """Inserta la sesion guardando solo el HMAC del token (nunca el token, DA-01).

    Corre como `turnos_app` con el contexto de la cuenta verificada: la politica `WITH CHECK`
    rechaza un `consultorio_id` distinto del contexto.
    """
    return sesion.execute(
        text(
            "INSERT INTO sesion (consultorio_id, usuario_id, token_hmac, creada_en, "
            "ultimo_uso_en, vence_absoluto_en) "
            "VALUES (:consultorio_id, :usuario_id, :token_hmac, :creada_en, :creada_en, "
            ":vence_absoluto_en) RETURNING id"
        ),
        {
            "consultorio_id": consultorio_id,
            "usuario_id": usuario_id,
            "token_hmac": token_hmac,
            "creada_en": creada_en,
            "vence_absoluto_en": vence_absoluto_en,
        },
    ).scalar_one()


def revocar_sesion(sesion: Session, sesion_id: uuid.UUID, ahora: datetime) -> bool:
    """Revoca por `id` (logout): RLS la limita a las sesiones del consultorio del contexto."""
    resultado = sesion.execute(
        text("UPDATE sesion SET revocada_en = :ahora WHERE id = :id AND revocada_en IS NULL"),
        {"id": sesion_id, "ahora": ahora},
    )
    return resultado.rowcount > 0

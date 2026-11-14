"""Consultas de administracion de los comandos locales, con el rol `app` (DD-02, DD-26, DD-32).

Solo se importa desde los comandos locales (`credenciales`, `mantenimiento`, `seed`) y las pruebas:
ninguna ruta, dependencia ni modulo de autenticacion lo usa (prueba estatica). Es el UNICO modulo
de `app/` con un `UPDATE usuario SET credencial`: la API nunca escribe credenciales.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.cuenta import Cuenta
from app.models.codigo import codigo_corto, codigo_largo
from app.models.usuario import normalizar_email


class CodigoConsultorioNoDisponible(Exception):
    """Ni el codigo corto ni el largo del `id` estan libres (fallo seguro, DD-13)."""


@dataclass(frozen=True, slots=True)
class ConsultorioCreado:
    id: uuid.UUID
    codigo: str


def _id_de_postgres(sesion: Session) -> uuid.UUID:
    return sesion.execute(text("SELECT uuidv7()")).scalar_one()


def _insertar(sesion: Session, consultorio_id: uuid.UUID, nombre: str, codigo: str) -> None:
    sesion.execute(
        text("INSERT INTO consultorio (id, nombre, codigo) VALUES (:id, :nombre, :codigo)"),
        {"id": consultorio_id, "nombre": nombre, "codigo": codigo},
    )


UNIQUE_VIOLATION = "23505"
RESTRICCION_CODIGO = "uq_consultorio_codigo"


def _es_colision_de_codigo(error: IntegrityError) -> bool:
    """Solo la violacion de `uq_consultorio_codigo` (SQLSTATE 23505 con ese nombre)."""
    origen = error.orig
    return (
        getattr(origen, "sqlstate", None) == UNIQUE_VIOLATION
        and getattr(getattr(origen, "diag", None), "constraint_name", None)
        == RESTRICCION_CODIGO
    )


def insertar_consultorio(
    sesion: Session,
    nombre: str,
    *,
    generar_id: Callable[[Session], uuid.UUID] = _id_de_postgres,
) -> ConsultorioCreado:
    consultorio_id = generar_id(sesion)
    codigo = codigo_corto(consultorio_id)
    try:
        with sesion.begin_nested():
            _insertar(sesion, consultorio_id, nombre, codigo)
    except IntegrityError as error:
        if not _es_colision_de_codigo(error):
            raise
        codigo = codigo_largo(consultorio_id)
        try:
            with sesion.begin_nested():
                _insertar(sesion, consultorio_id, nombre, codigo)
        except IntegrityError as segundo:
            if not _es_colision_de_codigo(segundo):
                raise
            raise CodigoConsultorioNoDisponible from segundo
    return ConsultorioCreado(consultorio_id, codigo)


def buscar_cuenta(sesion: Session, codigo: str, email: str) -> Cuenta | None:
    """Cuenta del comando local, con la credencial TAMBIEN de usuarios o consultorios inactivos."""
    fila = sesion.execute(
        text(
            "SELECT u.id AS usuario_id, u.consultorio_id, u.email, u.nombre, u.rol, u.credencial, "
            "u.activo AS usuario_activo, c.nombre AS consultorio_nombre, "
            "c.activo AS consultorio_activo "
            "FROM usuario u JOIN consultorio c ON c.id = u.consultorio_id "
            "WHERE c.codigo = :codigo AND u.email = :email"
        ),
        {"codigo": codigo.strip().lower(), "email": normalizar_email(email)},
    ).one_or_none()
    return Cuenta(**fila._mapping) if fila is not None else None


@dataclass(frozen=True, slots=True)
class CredencialParaRevision:
    """Credencial almacenada de un usuario, solo para clasificarla en memoria (DD-32)."""

    consultorio_id: uuid.UUID
    usuario_id: uuid.UUID
    credencial: str | None

    def __repr__(self) -> str:  # nunca muestra el hash
        return f"CredencialParaRevision(consultorio_id={self.consultorio_id}, usuario_id={self.usuario_id})"


def listar_credenciales_para_revision(sesion: Session) -> list[CredencialParaRevision]:
    """Credencial de TODOS los usuarios (activos o no), en una transaccion `READ ONLY` (DD-32).

    `SET TRANSACTION READ ONLY` es lo primero que se ejecuta: ninguna sentencia posterior de la
    misma transaccion puede escribir. Orden estable por consultorio y usuario.
    """
    sesion.execute(text("SET TRANSACTION READ ONLY"))
    filas = sesion.execute(
        text(
            "SELECT consultorio_id, id AS usuario_id, credencial FROM usuario "
            "ORDER BY consultorio_id, id"
        )
    ).all()
    return [CredencialParaRevision(f.consultorio_id, f.usuario_id, f.credencial) for f in filas]


def escribir_credencial(
    sesion: Session,
    consultorio_id: uuid.UUID,
    usuario_id: uuid.UUID,
    nueva: str,
    esperada: str | None,
) -> bool:
    """Escribe la credencial solo si sigue siendo la leida (control optimista).

    `esperada=None` solo completa credenciales nulas. Devuelve si escribio.
    """
    resultado = sesion.execute(
        text(
            "UPDATE usuario SET credencial = :nueva "
            "WHERE id = :usuario_id AND consultorio_id = :consultorio_id "
            "AND credencial IS NOT DISTINCT FROM :esperada"
        ),
        {
            "nueva": nueva,
            "usuario_id": usuario_id,
            "consultorio_id": consultorio_id,
            "esperada": esperada,
        },
    )
    return resultado.rowcount > 0


def revocar_sesiones_de_usuario(
    sesion: Session, consultorio_id: uuid.UUID, usuario_id: uuid.UUID, ahora: datetime
) -> int:
    resultado = sesion.execute(
        text(
            "UPDATE sesion SET revocada_en = :ahora "
            "WHERE consultorio_id = :consultorio_id AND usuario_id = :usuario_id "
            "AND revocada_en IS NULL"
        ),
        {"ahora": ahora, "consultorio_id": consultorio_id, "usuario_id": usuario_id},
    )
    return resultado.rowcount


RETENCION_DE_INTENTOS = timedelta(hours=24)
LIMITE_DE_LIMPIEZA = 100


def limpiar_intentos(sesion: Session, ahora: datetime, limite: int = LIMITE_DE_LIMPIEZA) -> int:
    """Borra como maximo `limite` fallos de mas de 24 horas (lotes del mantenimiento local)."""
    resultado = sesion.execute(
        text(
            "DELETE FROM intento_login WHERE id IN ("
            "SELECT id FROM intento_login WHERE ocurrido_en < :corte "
            "ORDER BY ocurrido_en LIMIT :limite)"
        ),
        {"corte": ahora - RETENCION_DE_INTENTOS, "limite": limite},
    )
    return resultado.rowcount


def limpiar_sesiones(
    sesion: Session, ahora: datetime, minutos_inactividad: int, limite: int = LIMITE_DE_LIMPIEZA
) -> int:
    """Borra como maximo `limite` sesiones revocadas o vencidas (lotes del mantenimiento local)."""
    resultado = sesion.execute(
        text(
            "DELETE FROM sesion WHERE id IN ("
            "SELECT id FROM sesion WHERE revocada_en IS NOT NULL "
            "OR vence_absoluto_en <= :ahora "
            "OR ultimo_uso_en + make_interval(mins => :minutos) <= :ahora "
            "ORDER BY ultimo_uso_en LIMIT :limite)"
        ),
        {"ahora": ahora, "minutos": minutos_inactividad, "limite": limite},
    )
    return resultado.rowcount

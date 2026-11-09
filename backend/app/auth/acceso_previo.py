"""Acceso previo al contexto de consultorio (DD-27).

Unico modulo que consulta o escribe `consultorio`, `usuario`, `sesion` e `intento_login`
sin un `ContextoConsultorio`. Este archivo se completa por etapas en el Change; aqui,
por ahora, el alta de consultorios.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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


@dataclass(frozen=True, slots=True)
class Cuenta:
    """Usuario y consultorio encontrados por (codigo, email), con los datos para decidir el login."""

    usuario_id: uuid.UUID
    consultorio_id: uuid.UUID
    email: str
    nombre: str
    rol: str
    credencial: str | None
    usuario_activo: bool
    consultorio_nombre: str
    consultorio_activo: bool


@dataclass(frozen=True, slots=True)
class SesionResuelta:
    """Sesion con su usuario y consultorio; la validez la decide el servicio (DD-04)."""

    sesion_id: uuid.UUID
    consultorio_id: uuid.UUID
    usuario_id: uuid.UUID
    email: str
    nombre: str
    rol: str
    consultorio_nombre: str
    usuario_activo: bool
    consultorio_activo: bool
    creada_en: datetime
    ultimo_uso_en: datetime
    vence_absoluto_en: datetime
    revocada_en: datetime | None


def buscar_cuenta(sesion: Session, codigo: str, email: str) -> Cuenta | None:
    """Cuenta por (codigo de consultorio, email), ambos normalizados (DM-03, DD-13)."""
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


def resolver_sesion(sesion: Session, token_hmac: bytes) -> SesionResuelta | None:
    """Sesion por el HMAC de su token (igualdad sobre el indice unico), sin juzgar su validez."""
    fila = sesion.execute(
        text(
            "SELECT s.id AS sesion_id, s.consultorio_id, s.usuario_id, u.email, u.nombre, u.rol, "
            "c.nombre AS consultorio_nombre, u.activo AS usuario_activo, "
            "c.activo AS consultorio_activo, s.creada_en, s.ultimo_uso_en, "
            "s.vence_absoluto_en, s.revocada_en "
            "FROM sesion s "
            "JOIN usuario u ON u.consultorio_id = s.consultorio_id AND u.id = s.usuario_id "
            "JOIN consultorio c ON c.id = s.consultorio_id "
            "WHERE s.token_hmac = :token_hmac"
        ),
        {"token_hmac": token_hmac},
    ).one_or_none()
    return SesionResuelta(**fila._mapping) if fila is not None else None


INTERVALO_MINIMO_DE_RENOVACION = timedelta(seconds=60)


def crear_sesion(
    sesion: Session,
    consultorio_id: uuid.UUID,
    usuario_id: uuid.UUID,
    token_hmac: bytes,
    creada_en: datetime,
    vence_absoluto_en: datetime,
) -> uuid.UUID:
    """Inserta la sesion guardando solo el HMAC del token (nunca el token, DA-01)."""
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


def renovar_sesion(sesion: Session, sesion_id: uuid.UUID, ahora: datetime) -> bool:
    """Renueva `ultimo_uso_en` solo si pasaron >= 60 s, sin revocar y antes del absoluto (DD-04)."""
    resultado = sesion.execute(
        text(
            "UPDATE sesion SET ultimo_uso_en = :ahora "
            "WHERE id = :id AND revocada_en IS NULL AND :ahora < vence_absoluto_en "
            "AND :ahora - ultimo_uso_en >= :intervalo"
        ),
        {"id": sesion_id, "ahora": ahora, "intervalo": INTERVALO_MINIMO_DE_RENOVACION},
    )
    return resultado.rowcount > 0


def revocar_sesion(sesion: Session, sesion_id: uuid.UUID, ahora: datetime) -> bool:
    resultado = sesion.execute(
        text("UPDATE sesion SET revocada_en = :ahora WHERE id = :id AND revocada_en IS NULL"),
        {"id": sesion_id, "ahora": ahora},
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


def registrar_fallo(
    sesion: Session, clave_cuenta: bytes, clave_ip: bytes, ocurrido_en: datetime
) -> None:
    """Un fallo evaluado: solo claves HMAC y el instante (DD-11, X1)."""
    sesion.execute(
        text(
            "INSERT INTO intento_login (clave_cuenta, clave_ip, ocurrido_en) "
            "VALUES (:clave_cuenta, :clave_ip, :ocurrido_en)"
        ),
        {"clave_cuenta": clave_cuenta, "clave_ip": clave_ip, "ocurrido_en": ocurrido_en},
    )


def _ultimos(sesion: Session, filtro: str, parametros: dict, limite: int) -> list[datetime]:
    """Los `limite` instantes mas recientes que cumplen `filtro`, del mas antiguo al mas reciente."""
    filas = sesion.execute(
        text(
            "SELECT ocurrido_en FROM ("
            f"SELECT ocurrido_en FROM intento_login WHERE {filtro} AND ocurrido_en > :desde "
            "ORDER BY ocurrido_en DESC LIMIT :limite) AS recientes ORDER BY ocurrido_en"
        ),
        {**parametros, "limite": limite},
    )
    return [fila.ocurrido_en for fila in filas]


def fallos_de_cuenta(
    sesion: Session, clave_cuenta: bytes, desde: datetime, limite: int
) -> list[datetime]:
    """Fallos recientes del par SIN los descartados por un login exitoso (DD-09)."""
    return _ultimos(
        sesion,
        "clave_cuenta = :clave AND NOT descartado_para_cuenta",
        {"clave": clave_cuenta, "desde": desde},
        limite,
    )


def fallos_de_ip(sesion: Session, clave_ip: bytes, desde: datetime, limite: int) -> list[datetime]:
    """Fallos recientes de la IP, TODOS (el contador de IP nunca mira la marca, DD-10)."""
    return _ultimos(sesion, "clave_ip = :clave", {"clave": clave_ip, "desde": desde}, limite)


def descartar_fallos_de_cuenta(sesion: Session, clave_cuenta: bytes) -> int:
    """Marca los fallos del par como descartados para la cuenta; no los borra (PC-04)."""
    resultado = sesion.execute(
        text(
            "UPDATE intento_login SET descartado_para_cuenta = true "
            "WHERE clave_cuenta = :clave AND NOT descartado_para_cuenta"
        ),
        {"clave": clave_cuenta},
    )
    return resultado.rowcount


def limpiar_intentos(sesion: Session, ahora: datetime, limite: int = LIMITE_DE_LIMPIEZA) -> int:
    """Borra como maximo `limite` fallos de mas de 24 horas (DD-21)."""
    resultado = sesion.execute(
        text(
            "DELETE FROM intento_login WHERE id IN ("
            "SELECT id FROM intento_login WHERE ocurrido_en < :corte "
            "ORDER BY ocurrido_en LIMIT :limite)"
        ),
        {"corte": ahora - RETENCION_DE_INTENTOS, "limite": limite},
    )
    return resultado.rowcount


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


def limpiar_sesiones(
    sesion: Session, ahora: datetime, minutos_inactividad: int, limite: int = LIMITE_DE_LIMPIEZA
) -> int:
    """Borra como maximo `limite` sesiones revocadas o vencidas (absoluto o inactividad, DD-21)."""
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

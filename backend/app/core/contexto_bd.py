"""Contexto transaccional de consultorio en la base (DD-04, DD-05; RN-MT-06).

Unico modulo de `app/` que menciona el parametro `app.consultorio_id`. Siempre se fija con
`set_config(..., true)` (local a la transaccion): nunca con `SET` de sesion ni `is_local = false`,
para que no persista en una conexion del pool. Sin identidad el valor es `''` y la politica RLS
no devuelve filas (falla cerrado).
"""

import uuid

from sqlalchemy import Connection, Engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.repositories.contexto import ContextoConsultorio

CLAVE = "consultorio_id"
PARAMETRO = "app.consultorio_id"

_FIJAR = text(f"SELECT pg_catalog.set_config('{PARAMETRO}', :valor, true)")
_RESET = f"RESET {PARAMETRO}"


def _despues_de_begin(sesion: Session, _transaccion: object, conexion: Connection) -> None:
    """Cada transaccion que empieza recibe el contexto vigente de la `Session` (o `''`)."""
    consultorio_id = sesion.info.get(CLAVE)
    conexion.execute(_FIJAR, {"valor": "" if consultorio_id is None else str(consultorio_id)})


def registrar_contexto_transaccional(fabrica: sessionmaker[Session]) -> None:
    event.listen(fabrica, "after_begin", _despues_de_begin)


def aplicar_contexto(db: Session, contexto: ContextoConsultorio) -> None:
    """Guarda el consultorio en la `Session` y, si ya hay transaccion, lo fija de inmediato."""
    if not isinstance(contexto, ContextoConsultorio):
        raise TypeError("el contexto debe ser un ContextoConsultorio")
    db.info[CLAVE] = contexto.consultorio_id
    if db.in_transaction():
        db.execute(_FIJAR, {"valor": str(contexto.consultorio_id)})


def fijar_consultorio_de_login(db: Session, consultorio_id: uuid.UUID) -> None:
    """Solo el login (T2): fija la transaccion actual al consultorio de la cuenta verificada.

    No toca `db.info`: la `Session` del login no conserva identidad para transacciones futuras.
    """
    if not isinstance(consultorio_id, uuid.UUID):
        raise TypeError("consultorio_id debe ser un uuid.UUID")
    db.execute(_FIJAR, {"valor": str(consultorio_id)})


def crear_fabrica_de_sesiones(engine_o_conexion, **opciones: object) -> sessionmaker[Session]:
    """Fabrica de sesiones de `turnos_app` (y de las pruebas): registra siempre el evento.

    `expire_on_commit=False` para poder leer los objetos devueltos tras el commit (DM-09).
    """
    opciones.setdefault("expire_on_commit", False)
    fabrica = sessionmaker(bind=engine_o_conexion, **opciones)  # type: ignore[arg-type]
    registrar_contexto_transaccional(fabrica)
    return fabrica


def _reset_del_contexto(dbapi_connection, _registro, estado=None) -> None:
    """Defensa adicional: al devolver la conexion al pool, `RESET app.consultorio_id` confirmado.

    Primero revierte lo pendiente (nunca confirma trabajo ajeno) y luego confirma solo el RESET.
    Si falla, la excepcion hace que el pool invalide la conexion.
    """
    if getattr(estado, "terminate_only", False):
        return
    dbapi_connection.rollback()
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(_RESET)
    finally:
        cursor.close()
    dbapi_connection.commit()


def registrar_reset_del_pool(engine: Engine) -> None:
    event.listen(engine, "reset", _reset_del_contexto)

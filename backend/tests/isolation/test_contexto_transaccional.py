"""Contexto transaccional con conexiones reales de `turnos_app` (4.2, DD-04, DD-05).

El valor se lee con `current_setting('app.consultorio_id', true)` dentro de cada transaccion.
Solo contra `db-test`.
"""

import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.contexto_bd import (
    aplicar_contexto,
    crear_fabrica_de_sesiones,
    fijar_consultorio_de_login,
    registrar_reset_del_pool,
)
from app.repositories.contexto import ContextoConsultorio

LEER = text("SELECT current_setting('app.consultorio_id', true)")
ID_A = uuid.UUID("0199a000-0000-7000-8000-00000000000a")
ID_B = uuid.UUID("0199a000-0000-7000-8000-00000000000b")


def _valor(db: Session) -> str | None:
    return db.execute(LEER).scalar_one()


def _vacio(valor: str | None) -> bool:
    return valor in (None, "")


@pytest.fixture
def fabrica(motor_app):
    return crear_fabrica_de_sesiones(motor_app)


def test_el_contexto_se_recupera_tras_commit(fabrica):
    with fabrica() as db:
        aplicar_contexto(db, ContextoConsultorio(ID_A))
        assert _valor(db) == str(ID_A)
        db.commit()

        assert _valor(db) == str(ID_A)  # nueva transaccion de la misma Session
        db.commit()
        assert _valor(db) == str(ID_A)


def test_el_contexto_se_recupera_tras_rollback(fabrica):
    with fabrica() as db:
        aplicar_contexto(db, ContextoConsultorio(ID_A))
        assert _valor(db) == str(ID_A)
        db.rollback()

        assert _valor(db) == str(ID_A)


def test_rollback_to_savepoint_revierte_lo_fijado_despues_y_conserva_lo_anterior(fabrica):
    with fabrica() as db:
        aplicar_contexto(db, ContextoConsultorio(ID_A))
        assert _valor(db) == str(ID_A)

        savepoint = db.begin_nested()
        fijar_consultorio_de_login(db, ID_B)
        assert _valor(db) == str(ID_B)
        savepoint.rollback()

        assert _valor(db) == str(ID_A)


def test_savepoint_liberado_conserva_lo_fijado_dentro(fabrica):
    with fabrica() as db:
        aplicar_contexto(db, ContextoConsultorio(ID_A))
        _valor(db)

        with db.begin_nested():
            fijar_consultorio_de_login(db, ID_B)

        assert _valor(db) == str(ID_B)


def test_la_transaccion_sin_identidad_usa_cadena_vacia_y_no_ve_filas(fabrica, datos_ab):
    with fabrica() as db:
        assert _valor(db) == ""
        assert db.execute(text("SELECT count(*) FROM usuario")).scalar_one() == 0
        assert db.execute(text("SELECT count(*) FROM consultorio")).scalar_one() == 0


def test_con_identidad_la_misma_session_ve_solo_su_consultorio(fabrica, datos_ab):
    with fabrica() as db:
        aplicar_contexto(db, ContextoConsultorio(datos_ab.a.id))

        ids = db.execute(text("SELECT DISTINCT consultorio_id FROM usuario")).scalars().all()

        assert ids == [datos_ab.a.id]


def test_aplicar_contexto_dentro_de_una_transaccion_abierta_fija_de_inmediato(fabrica, datos_ab):
    with fabrica() as db:
        assert _valor(db) == ""
        aplicar_contexto(db, ContextoConsultorio(datos_ab.b.id))

        assert db.execute(text("SELECT count(*) FROM usuario")).scalar_one() == 3


def _motor_de_una_conexion(url_app):
    return create_engine(
        url_app.render_as_string(hide_password=False),
        pool_size=1,
        max_overflow=0,
        pool_timeout=5,
    )


def test_conexion_reutilizada_del_pool_empieza_sin_contexto(url_app, datos_ab):
    motor = _motor_de_una_conexion(url_app)
    registrar_reset_del_pool(motor)
    fabrica = crear_fabrica_de_sesiones(motor)
    try:
        with fabrica() as db:
            aplicar_contexto(db, ContextoConsultorio(datos_ab.a.id))
            assert db.execute(text("SELECT count(*) FROM usuario")).scalar_one() == 3
            db.commit()
        pid_1 = _pid(motor)
        with fabrica() as otra:  # sin identidad: reutiliza la unica conexion
            assert _pid(motor) == pid_1
            assert _vacio(_valor_de_conexion(motor))
            assert otra.execute(text("SELECT count(*) FROM usuario")).scalar_one() == 0
    finally:
        motor.dispose()


def _pid(motor) -> int:
    with motor.connect() as conexion:
        return conexion.execute(text("SELECT pg_backend_pid()")).scalar_one()


def _valor_de_conexion(motor) -> str | None:
    with motor.connect() as conexion:
        return conexion.execute(LEER).scalar_one()


def test_el_reset_del_pool_limpia_un_valor_de_sesion_filtrado(url_app):
    motor = _motor_de_una_conexion(url_app)
    registrar_reset_del_pool(motor)
    try:
        with motor.connect() as conexion:
            pid = conexion.execute(text("SELECT pg_backend_pid()")).scalar_one()
            conexion.exec_driver_sql(f"SET app.consultorio_id = '{ID_A}'")  # fuga simulada
            conexion.commit()
            assert conexion.execute(LEER).scalar_one() == str(ID_A)
        with motor.connect() as conexion:
            assert conexion.execute(text("SELECT pg_backend_pid()")).scalar_one() == pid
            assert _vacio(conexion.execute(LEER).scalar_one())
    finally:
        motor.dispose()


def test_sin_el_reset_del_pool_la_fuga_persistiria(url_app):
    """Control negativo: demuestra que el RESET es lo que limpia, no el pool por si solo."""
    motor = _motor_de_una_conexion(url_app)
    try:
        with motor.connect() as conexion:
            pid = conexion.execute(text("SELECT pg_backend_pid()")).scalar_one()
            conexion.exec_driver_sql(f"SET app.consultorio_id = '{ID_A}'")
            conexion.commit()
        with motor.connect() as conexion:
            assert conexion.execute(text("SELECT pg_backend_pid()")).scalar_one() == pid
            assert conexion.execute(LEER).scalar_one() == str(ID_A)
    finally:
        motor.dispose()

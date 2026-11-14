"""Contexto transaccional de la base (4.1, DD-04) con conexion espia, sin base real."""

import uuid

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.core import contexto_bd
from app.core.contexto_bd import (
    CLAVE,
    aplicar_contexto,
    crear_fabrica_de_sesiones,
    fijar_consultorio_de_login,
    registrar_contexto_transaccional,
)
from app.core.database import crear_fabrica_de_sesiones_login
from app.repositories.contexto import ContextoConsultorio

ID_A = uuid.UUID("0199a000-0000-7000-8000-00000000000a")
ID_B = uuid.UUID("0199a000-0000-7000-8000-00000000000b")


class ConexionEspia:
    def __init__(self) -> None:
        self.llamadas: list[tuple[str, dict]] = []

    def execute(self, sentencia, parametros=None):
        self.llamadas.append((str(sentencia), dict(parametros or {})))


class SesionEspia:
    def __init__(self, en_transaccion: bool) -> None:
        self.info: dict = {}
        self._en_transaccion = en_transaccion
        self.ejecutadas: list[tuple[str, dict]] = []

    def in_transaction(self) -> bool:
        return self._en_transaccion

    def execute(self, sentencia, parametros=None):
        self.ejecutadas.append((str(sentencia), dict(parametros or {})))


def _motor_sin_conectar():
    return create_engine("postgresql+psycopg://rol:clave@host.invalid:5432/base_test")


def test_after_begin_sin_contexto_fija_cadena_vacia_local_a_la_transaccion():
    conexion = ConexionEspia()

    contexto_bd._despues_de_begin(SesionEspia(False), None, conexion)

    (sentencia, parametros), = conexion.llamadas
    assert "set_config('app.consultorio_id'" in sentencia
    assert sentencia.rstrip().endswith("true)")
    assert parametros == {"valor": ""}


def test_after_begin_con_contexto_fija_el_uuid():
    conexion = ConexionEspia()
    sesion = SesionEspia(False)
    sesion.info[CLAVE] = ID_A

    contexto_bd._despues_de_begin(sesion, None, conexion)

    assert conexion.llamadas[0][1] == {"valor": str(ID_A)}


def test_after_begin_toma_el_contexto_vigente_de_cada_transaccion():
    conexion = ConexionEspia()
    sesion = SesionEspia(False)
    sesion.info[CLAVE] = ID_A
    contexto_bd._despues_de_begin(sesion, None, conexion)
    sesion.info[CLAVE] = ID_B
    contexto_bd._despues_de_begin(sesion, None, conexion)

    assert [p["valor"] for _s, p in conexion.llamadas] == [str(ID_A), str(ID_B)]


def test_aplicar_contexto_fuera_de_transaccion_solo_guarda_en_info():
    sesion = SesionEspia(False)

    aplicar_contexto(sesion, ContextoConsultorio(ID_A))

    assert sesion.info[CLAVE] == ID_A
    assert sesion.ejecutadas == []


def test_aplicar_contexto_dentro_de_transaccion_guarda_y_fija_de_inmediato():
    sesion = SesionEspia(True)

    aplicar_contexto(sesion, ContextoConsultorio(ID_B))

    assert sesion.info[CLAVE] == ID_B
    (sentencia, parametros), = sesion.ejecutadas
    assert "set_config" in sentencia
    assert parametros == {"valor": str(ID_B)}


def test_aplicar_contexto_exige_un_contexto_tipado():
    with pytest.raises(TypeError):
        aplicar_contexto(SesionEspia(False), ID_A)  # type: ignore[arg-type]


def test_fijar_consultorio_de_login_fija_la_transaccion_sin_tocar_info():
    sesion = SesionEspia(True)

    fijar_consultorio_de_login(sesion, ID_A)

    assert sesion.info == {}
    assert sesion.ejecutadas[0][1] == {"valor": str(ID_A)}


def test_fijar_consultorio_de_login_exige_uuid():
    with pytest.raises(TypeError):
        fijar_consultorio_de_login(SesionEspia(True), str(ID_A))  # type: ignore[arg-type]


def test_la_fabrica_de_la_api_registra_siempre_el_evento():
    fabrica = crear_fabrica_de_sesiones(_motor_sin_conectar())

    assert event.contains(fabrica, "after_begin", contexto_bd._despues_de_begin)


def test_la_fabrica_acepta_opciones_de_sessionmaker():
    fabrica = crear_fabrica_de_sesiones(
        _motor_sin_conectar(), join_transaction_mode="create_savepoint"
    )

    assert fabrica.kw["join_transaction_mode"] == "create_savepoint"
    assert event.contains(fabrica, "after_begin", contexto_bd._despues_de_begin)


def test_la_fabrica_de_login_no_registra_el_evento():
    fabrica = crear_fabrica_de_sesiones_login(_motor_sin_conectar())

    assert not event.contains(fabrica, "after_begin", contexto_bd._despues_de_begin)


def test_registrar_contexto_transaccional_sobre_una_fabrica_existente():
    from sqlalchemy.orm import sessionmaker

    fabrica = sessionmaker(bind=_motor_sin_conectar())
    assert not event.contains(fabrica, "after_begin", contexto_bd._despues_de_begin)

    registrar_contexto_transaccional(fabrica)

    assert event.contains(fabrica, "after_begin", contexto_bd._despues_de_begin)


def test_una_session_real_con_la_fabrica_no_conecta_al_crearse():
    fabrica = crear_fabrica_de_sesiones(_motor_sin_conectar())

    with fabrica() as sesion:
        assert isinstance(sesion, Session)
        assert not sesion.in_transaction()


def test_el_reset_del_pool_ejecuta_reset_del_parametro_y_confirma():
    from app.core.contexto_bd import registrar_reset_del_pool

    class Cursor:
        def __init__(self, registro):
            self.registro = registro

        def execute(self, sentencia):
            self.registro.append(("execute", sentencia))

        def close(self):
            self.registro.append(("cursor.close", None))

    class Dbapi:
        def __init__(self):
            self.registro = []

        def rollback(self):
            self.registro.append(("rollback", None))

        def commit(self):
            self.registro.append(("commit", None))

        def cursor(self):
            return Cursor(self.registro)

    motor = _motor_sin_conectar()
    registrar_reset_del_pool(motor)
    dbapi = Dbapi()

    class Estado:
        terminate_only = False

    motor.pool.dispatch.reset(dbapi, None, Estado())

    pasos = [paso for paso, _ in dbapi.registro]
    assert pasos[0] == "rollback"
    assert ("execute", "RESET app.consultorio_id") in dbapi.registro
    assert pasos[-1] == "commit" or pasos[-2:] == ["commit", "cursor.close"]


def test_el_reset_del_pool_no_hace_nada_si_la_conexion_se_descarta():
    from app.core.contexto_bd import registrar_reset_del_pool

    motor = _motor_sin_conectar()
    registrar_reset_del_pool(motor)

    class Dbapi:
        def __getattr__(self, nombre):
            raise AssertionError("no debe tocar la conexion")

    class Estado:
        terminate_only = True

    motor.pool.dispatch.reset(Dbapi(), None, Estado())

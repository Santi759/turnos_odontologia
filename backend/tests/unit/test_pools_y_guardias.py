"""Pools de PD-04 y guardias de rol en los motores de la API (5.5, 4.4; DD-29, DD-33)."""

import pytest
from app.core import database
from app.core.database import (
    RolDeConexionInvalido,
    crear_engine,
    crear_engine_login,
    verificar_rol_de_conexion,
)
from app.core.roles_bd import ROL_LOGIN, ROL_APP


def _pool(motor):
    pool = motor.pool
    return {
        "tamano": pool.size(),
        "desborde": pool._max_overflow,
        "espera": pool.timeout(),
        "pre_ping": pool._pre_ping,
    }


def test_el_motor_de_login_usa_la_configuracion_de_pd_04(fabrica_settings):
    motor = crear_engine_login(fabrica_settings())

    assert _pool(motor) == {"tamano": 4, "desborde": 11, "espera": 30, "pre_ping": True}


def test_el_motor_de_turnos_app_usa_la_configuracion_de_pd_04_explicita(fabrica_settings):
    motor = crear_engine(fabrica_settings())

    assert _pool(motor) == {"tamano": 5, "desborde": 10, "espera": 30, "pre_ping": True}


def test_los_argumentos_de_conexion_se_pasan_de_forma_explicita(monkeypatch, fabrica_settings):
    capturados: list[dict] = []
    original = database.create_engine

    def espia(url, **kwargs):
        capturados.append(kwargs)
        return original(url, **kwargs)

    monkeypatch.setattr(database, "create_engine", espia)

    crear_engine(fabrica_settings())
    crear_engine_login(fabrica_settings())

    assert len(capturados) == 2
    for kwargs in capturados:
        assert kwargs["connect_args"] == {"connect_timeout": 5}
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["pool_timeout"] == 30
    assert (capturados[0]["pool_size"], capturados[0]["max_overflow"]) == (5, 10)
    assert (capturados[1]["pool_size"], capturados[1]["max_overflow"]) == (4, 11)


def test_las_constantes_de_los_pools_tienen_nombre_propio():
    assert (database.POOL_LOGIN_TAMANO, database.POOL_LOGIN_DESBORDE) == (4, 11)
    assert (database.POOL_APP_TAMANO, database.POOL_APP_DESBORDE) == (5, 10)
    assert database.POOL_ESPERA_SEGUNDOS == 30
    assert database.CONNECT_TIMEOUT_SEGUNDOS == 5


def _roles_con_guardia(motor) -> list[str]:
    return [
        funcion.rol_esperado
        for funcion in motor.pool.dispatch.connect
        if hasattr(funcion, "rol_esperado")
    ]


def test_cada_motor_de_la_api_registra_su_guardia_de_rol_exacto(fabrica_settings):
    assert _roles_con_guardia(crear_engine(fabrica_settings())) == [ROL_APP]
    assert _roles_con_guardia(crear_engine_login(fabrica_settings())) == [ROL_LOGIN]


def test_el_motor_de_administracion_y_los_genericos_no_tienen_guardia():
    import secrets

    from app.core.config import Settings

    admin = database.crear_engine_admin(
        Settings(
            DATABASE_URL="postgresql+psycopg://turnos_app:clave-a@host-api.invalid/turnos",
            DATABASE_LOGIN_URL="postgresql+psycopg://turnos_login:clave-l@host-login.invalid/turnos",
            DATABASE_MIGRATION_URL="postgresql+psycopg://app:clave-m@host-admin.invalid/turnos",
            CORS_ALLOWED_ORIGINS="http://localhost:5173",
            APP_ENV="local",
            AUTH_SECRET_KEY=secrets.token_urlsafe(48),
        )
    )
    generico = database.crear_engine_desde_url("postgresql+psycopg://app:app@host.invalid/x")

    for motor in (admin, generico):
        assert _roles_con_guardia(motor) == []


class _Cursor:
    def __init__(self, fila: dict):
        self._fila = fila
        self.description = [(nombre,) for nombre in fila]

    def execute(self, *_a, **_k):
        return None

    def fetchone(self):
        return tuple(self._fila.values())

    def close(self):
        pass


class _Conexion:
    def __init__(self, fila: dict):
        self.fila = fila
        self.cerrada = False
        self.revertida = False

    def cursor(self):
        return _Cursor(self.fila)

    def rollback(self):
        self.revertida = True

    def close(self):
        self.cerrada = True


def _fila(rol: str, **cambios):
    base = {
        "usuario_actual": rol,
        "rolsuper": False,
        "rolbypassrls": False,
        "rolcreaterole": False,
        "rolcreatedb": False,
        "rolreplication": False,
        "duenio_de_objetos": False,
        "con_membresias": False,
        "lee_credencial": False,
        "escribe_credencial": False,
        "escribe_usuario": False,
        "ejecuta_buscar_cuenta": rol == ROL_LOGIN,
        "privilegio_en_tablas": False,
    }
    base.update(cambios)
    return base


@pytest.mark.parametrize("rol", [ROL_APP, ROL_LOGIN])
def test_la_guardia_acepta_la_conexion_correcta_y_la_deja_sin_transaccion(rol):
    conexion = _Conexion(_fila(rol))

    verificar_rol_de_conexion(conexion, rol)

    assert conexion.revertida is True
    assert conexion.cerrada is False


def test_la_guardia_cierra_la_conexion_y_falla_con_mensaje_fijo_sin_valores():
    conexion = _Conexion(_fila("un_rol_ficticio_secreto", rolsuper=True))

    with pytest.raises(RolDeConexionInvalido) as info:
        verificar_rol_de_conexion(conexion, ROL_APP)

    assert conexion.cerrada is True
    assert "un_rol_ficticio_secreto" not in str(info.value)
    assert ROL_APP in str(info.value)

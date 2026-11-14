"""Validacion de PD-04: pools reales del login y de la aplicacion (5.7, R3-02, DD-33).

App real de `crear_app` con la CONFIGURACION REAL de los pools (login 4/11/30 s, app 5/10/30 s,
`pre_ping`, `connect_timeout` 5; nunca el `pool_size=50` de las pruebas de C-03) y conexiones reales de
`turnos_login` y `turnos_app`, solo en `db-test`. Regla ante fallos (R3-03): si una condicion falla NO se
cambian expectativas ni parametros; se investiga y se consulta al autor.

Condiciones: (1) 40 intentos de la misma IP sobre 40 pares -> 30 x 401 y 10 x 429; (2) 10 de la misma cuenta
-> 5 x 401 y 5 x 429; (3) 8 cuentas e IP distintas -> 8 x 401; (4) a lo sumo 4 verificaciones Argon2
simultaneas; (5) agotamiento forzado del pool -> 503; (6) sin contaminacion de contexto; (7) ningun 503
registra un intento; (8) sin conexiones prestadas ni locks al terminar; (9) presupuesto de conexiones (en
`tests/unit/test_presupuesto_conexiones.py`).
"""

import threading
from collections import Counter

import pytest
from sqlalchemy import create_engine, text

from app.api.auth import DETALLE_OCUPADO
from app.auth.concurrencia import LimitadorArgon2
from app.core.database import (
    CONNECT_TIMEOUT_SEGUNDOS,
    crear_fabrica_de_sesiones_login,
    registrar_guardia_de_rol,
)
from app.core.roles_bd import ROL_APP, ROL_LOGIN
from app.models.usuario import Rol
from tests.integration.datos_auth import VerificadorEspia
from tests.isolation.conftest import construir_api

INCORRECTA = "contrasena-incorrecta-"


def _escalar(motor_admin, sql: str, **params):
    with motor_admin.connect() as conexion:
        return conexion.execute(text(sql), params).scalar_one()


def _sin_residuos(api, motor_admin) -> None:
    """Condicion 8: ni conexiones prestadas en ninguno de los dos pools ni locks consultivos."""
    assert api.app.state.engine_login.pool.checkedout() == 0
    assert api.app.state.engine.pool.checkedout() == 0
    locks = _escalar(
        motor_admin,
        "SELECT count(*) FROM pg_locks l JOIN pg_stat_activity a ON a.pid = l.pid "
        "WHERE l.locktype = 'advisory' AND a.usename IN (:l, :a)",
        l=ROL_LOGIN,
        a=ROL_APP,
    )
    assert locks == 0


@pytest.fixture
def api(api_real, motor_admin):
    yield api_real
    _sin_residuos(api_real, motor_admin)


def _concurrentes(api, pedidos: list[tuple[str, str, str, str]]) -> Counter:
    """Un hilo por pedido (codigo, email, contrasena, ip), liberados a la vez; cuenta los estados."""
    barrera = threading.Barrier(len(pedidos))
    estados: list[int] = []
    errores: list[BaseException] = []

    def pedir(indice: int, codigo: str, email: str, contrasena: str, ip: str) -> None:
        try:
            cliente = api.cliente(ip, 40000 + indice)
            barrera.wait(timeout=60)
            estados.append(api.login(cliente, codigo, email, contrasena).status_code)
        except BaseException as error:  # noqa: BLE001 - se reporta en el hilo principal
            errores.append(error)

    hilos = [threading.Thread(target=pedir, args=(i, *p)) for i, p in enumerate(pedidos)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=120)
    assert not errores, errores
    assert not any(hilo.is_alive() for hilo in hilos)
    return Counter(estados)


def _usuarios(datos_ab):
    return [c.usuarios[rol] for c in (datos_ab.a, datos_ab.b) for rol in Rol]


# --- 1 ---------------------------------------------------------------------------------------------


def test_1_cuarenta_intentos_de_la_misma_ip_sobre_cuarenta_pares_dan_30_401_y_10_429(
    api, datos_ab, motor_admin
):
    pedidos = [
        (datos_ab.a.codigo, f"nadie{i}@example.test", INCORRECTA + "x", "203.0.113.7")
        for i in range(40)
    ]

    resultado = _concurrentes(api, pedidos)

    assert resultado == {401: 30, 429: 10}
    assert _escalar(motor_admin, "SELECT count(*) FROM intento_login") == 30


# --- 2 ---------------------------------------------------------------------------------------------


def test_2_diez_intentos_de_la_misma_cuenta_dan_5_401_y_5_429(api, datos_ab, motor_admin):
    usuario = datos_ab.a.usuarios[Rol.SECRETARIA]
    pedidos = [(datos_ab.a.codigo, usuario.email, INCORRECTA + "y", "203.0.113.7")] * 10

    resultado = _concurrentes(api, pedidos)

    assert resultado == {401: 5, 429: 5}
    assert _escalar(motor_admin, "SELECT count(*) FROM intento_login") == 5


# --- 3 ---------------------------------------------------------------------------------------------


def test_3_ocho_cuentas_distintas_desde_ip_distintas_dan_8_401(api, datos_ab):
    cuentas = [(datos_ab.a.codigo, u.email) for u in _usuarios(datos_ab)[:3]]
    cuentas += [(datos_ab.b.codigo, u.email) for u in _usuarios(datos_ab)[3:6]]
    cuentas += [(datos_ab.a.codigo, "otra1@example.test"), (datos_ab.b.codigo, "otra2@example.test")]
    pedidos = [
        (codigo, email, INCORRECTA + "z", f"198.51.100.{10 + i}")
        for i, (codigo, email) in enumerate(cuentas)
    ]
    assert len(pedidos) == 8

    assert _concurrentes(api, pedidos) == {401: 8}


# --- 4 ---------------------------------------------------------------------------------------------


class VerificadorBloqueado(VerificadorEspia):
    """Cuenta las verificaciones simultaneas y las retiene hasta una senal."""

    def __init__(self) -> None:
        super().__init__()
        self.compuerta = threading.Event()
        self._candado = threading.Lock()
        self.actual = 0
        self.maximo = 0

    def verificar(self, contrasena, almacenado):
        with self._candado:
            self.actual += 1
            self.maximo = max(self.maximo, self.actual)
        try:
            self.compuerta.wait(timeout=30)
            return super().verificar(contrasena, almacenado)
        finally:
            with self._candado:
                self.actual -= 1


def _esperar(condicion, descripcion: str, segundos: float = 20.0) -> None:
    import time

    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if condicion():
            return
        time.sleep(0.01)
    raise AssertionError(f"no se cumplio a tiempo: {descripcion}")


def test_4_a_lo_sumo_cuatro_verificaciones_argon2_simultaneas(url_app, url_login, datos_ab, motor_admin):
    verificador = VerificadorBloqueado()
    limitador = LimitadorArgon2(espera_segundos=20.0)
    api = construir_api(url_app, url_login, verificador=verificador, limitador=limitador)
    estados: list[int] = []
    errores: list[BaseException] = []

    def pedir(indice: int) -> None:
        try:
            usuario = _usuarios(datos_ab)[indice % 6]
            c = datos_ab.a if indice % 6 < 3 else datos_ab.b
            cliente = api.cliente(f"198.51.100.{20 + indice}", 41000 + indice)
            estados.append(api.login(cliente, c.codigo, usuario.email, INCORRECTA + "w").status_code)
        except BaseException as error:  # noqa: BLE001
            errores.append(error)

    hilos = [threading.Thread(target=pedir, args=(i,)) for i in range(8)]
    try:
        for hilo in hilos:
            hilo.start()
        _esperar(lambda: verificador.actual == 4, "4 verificaciones simultaneas")
        assert verificador.maximo == 4  # las otras 4 esperan cupo
    finally:
        verificador.compuerta.set()
        for hilo in hilos:
            hilo.join(timeout=60)
    try:
        assert not errores, errores
        assert verificador.maximo == 4
        assert verificador.actual == 0
        assert Counter(estados) == {401: 8}
    finally:
        _sin_residuos(api, motor_admin)
        api.app.state.engine.dispose()
        api.app.state.engine_login.dispose()


# --- 5 y 7 ------------------------------------------------------------------------------------------


def _api_con_pool_de_login_de_una_conexion(url_app, url_login, **opciones):
    api = construir_api(url_app, url_login, **opciones)
    api.app.state.engine_login.dispose()
    motor = create_engine(
        url_login.render_as_string(hide_password=False),
        pool_size=1,
        max_overflow=0,
        pool_timeout=0.2,
        pool_pre_ping=True,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SEGUNDOS},
    )
    registrar_guardia_de_rol(motor, ROL_LOGIN)
    api.app.state.engine_login = motor
    api.app.state.fabrica_sesiones_login = crear_fabrica_de_sesiones_login(motor)
    return api


def test_5_y_7_pool_de_login_agotado_responde_503_sin_verificar_ni_registrar_intento(
    url_app, url_login, datos_ab, motor_admin
):
    api = _api_con_pool_de_login_de_una_conexion(url_app, url_login)
    usuario = datos_ab.a.usuarios[Rol.SECRETARIA]
    retenida = api.app.state.engine_login.connect()  # la unica conexion del pool, retenida por la prueba
    try:
        intentos_antes = _escalar(motor_admin, "SELECT count(*) FROM intento_login")

        respuesta = api.login(api.cliente(), datos_ab.a.codigo, usuario.email, INCORRECTA + "p")

        assert respuesta.status_code == 503
        assert respuesta.json() == {"detail": DETALLE_OCUPADO}
        assert respuesta.headers["retry-after"] == "5"
        assert respuesta.headers["cache-control"] == "no-store"
        assert api.verificador.llamadas == 0
        assert _escalar(motor_admin, "SELECT count(*) FROM sesion") == 0
        assert _escalar(motor_admin, "SELECT count(*) FROM intento_login") == intentos_antes  # condicion 7
    finally:
        retenida.close()

    try:
        siguiente = api.login(api.cliente(), datos_ab.a.codigo, usuario.email, INCORRECTA + "q")

        assert siguiente.status_code == 401  # liberada la conexion, el login se evalua
        assert api.verificador.llamadas == 1
    finally:
        _sin_residuos(api, motor_admin)
        api.app.state.engine.dispose()
        api.app.state.engine_login.dispose()


def test_7_el_503_por_cupo_de_argon2_tampoco_registra_un_intento(url_app, url_login, datos_ab, motor_admin):
    limitador = LimitadorArgon2(cupos=1, espera_segundos=0)
    api = construir_api(url_app, url_login, limitador=limitador)
    usuario = datos_ab.a.usuarios[Rol.SECRETARIA]
    assert limitador.semaforo.acquire(timeout=0)  # el unico cupo, retenido por la prueba
    try:
        respuesta = api.login(api.cliente(), datos_ab.a.codigo, usuario.email, INCORRECTA + "r")

        assert respuesta.status_code == 503
        assert respuesta.headers["retry-after"] == "5"
        assert api.verificador.llamadas == 0
        assert _escalar(motor_admin, "SELECT count(*) FROM intento_login") == 0
        assert _escalar(motor_admin, "SELECT count(*) FROM sesion") == 0
    finally:
        limitador.semaforo.release()
        _sin_residuos(api, motor_admin)
        api.app.state.engine.dispose()
        api.app.state.engine_login.dispose()


# --- 6 ---------------------------------------------------------------------------------------------


def test_6_las_conexiones_reutilizadas_del_pool_de_la_aplicacion_empiezan_sin_contexto(
    api, datos_ab
):
    a, b = datos_ab.a, datos_ab.b
    for c in (a, b):
        usuario = c.usuarios[Rol.SECRETARIA]
        cliente = api.cliente()
        assert api.login(cliente, c.codigo, usuario.email, usuario.contrasena).status_code == 200
        assert cliente.get("/api/auth/me").status_code == 200
    motor = api.app.state.engine
    libres = motor.pool.checkedin()
    assert libres >= 1  # hay conexiones reutilizables ya usadas con contexto

    prestadas = [motor.connect() for _ in range(libres)]
    try:
        valores = [
            conexion.execute(text("SELECT current_setting('app.consultorio_id', true)")).scalar_one()
            for conexion in prestadas
        ]
    finally:
        for conexion in prestadas:
            conexion.close()

    assert all(valor in (None, "") for valor in valores), valores


# --- 8 ---------------------------------------------------------------------------------------------


def test_8_el_pool_de_login_cierra_cada_transaccion_y_sus_locks(api, datos_ab, motor_admin):
    usuario = datos_ab.a.usuarios[Rol.SECRETARIA]
    for contrasena, esperado in ((INCORRECTA + "m", 401), (usuario.contrasena, 200)):
        assert api.login(api.cliente(), datos_ab.a.codigo, usuario.email, contrasena).status_code == esperado
        _sin_residuos(api, motor_admin)

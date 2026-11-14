"""Login en dos transacciones con los roles reales (5.6; DD-26, DD-27; spec `acceso-previo-al-contexto`).

App real de `crear_app` sobre `db-test`, con conexiones reales de `turnos_login` (T1) y `turnos_app`
(T2). Solo cambian el servicio (reloj y verificador de prueba) y, donde se indica, el tamano de los pools.
"""

import secrets
import threading
from collections import Counter

import pytest
from sqlalchemy import create_engine, event, text

from app.auth import acceso_previo
from app.auth.claves import clave_de_cuenta, clave_de_ip, normalizar_ip
from app.core.contexto_bd import crear_fabrica_de_sesiones, registrar_reset_del_pool
from app.core.database import (
    CONNECT_TIMEOUT_SEGUNDOS,
    _crear_engine_de_la_api,
    crear_fabrica_de_sesiones_login,
)
from app.core.roles_bd import ROL_APP, ROL_LOGIN
from app.models.usuario import Rol
from tests.integration.datos_auth import VerificadorEspia
from tests.isolation.conftest import construir_api

IP = "203.0.113.7"


def _datos(datos_ab, consultorio: str = "a"):
    c = getattr(datos_ab, consultorio)
    usuario = c.usuarios[Rol.SECRETARIA]
    return c, usuario


def _grabar_sentencias(motor, etiqueta: str, registro: list[tuple[str, str]]) -> None:
    @event.listens_for(motor, "before_cursor_execute")
    def _(conexion, cursor, sentencia, parametros, contexto, many):  # noqa: ANN001
        registro.append((etiqueta, sentencia.split()[0].upper()))


def _escalar(motor_admin, sql: str, **params):
    with motor_admin.connect() as conexion:
        return conexion.execute(text(sql), params).scalar_one()


# --- Rol de cada transaccion -------------------------------------------------------------------


def test_rol_de_cada_transaccion_y_t1_termina_antes_de_que_empiece_t2(api_real, datos_ab):
    registro: list[tuple[str, str]] = []
    _grabar_sentencias(api_real.app.state.engine_login, "login", registro)
    _grabar_sentencias(api_real.app.state.engine, "app", registro)
    consultorio, usuario = _datos(datos_ab)

    respuesta = api_real.login(api_real.cliente(), consultorio.codigo, usuario.email, usuario.contrasena)

    assert respuesta.status_code == 200
    etiquetas = [etiqueta for etiqueta, _ in registro]
    assert set(etiquetas) == {"login", "app"}
    primer_app = etiquetas.index("app")
    ultimo_login = len(etiquetas) - 1 - etiquetas[::-1].index("login")
    assert ultimo_login < primer_app  # T1 completa antes de T2: no coexisten
    # Las guardias de DD-29 garantizan el `current_user` de cada motor en cada conexion.
    assert api_real.app.state.engine_login.pool.checkedout() == 0
    assert api_real.app.state.engine.pool.checkedout() == 0


def test_los_motores_conectan_con_el_rol_que_corresponde(api_real, datos_ab):
    consultorio, usuario = _datos(datos_ab)
    api_real.login(api_real.cliente(), consultorio.codigo, usuario.email, usuario.contrasena)

    for motor, rol in ((api_real.app.state.engine_login, ROL_LOGIN), (api_real.app.state.engine, ROL_APP)):
        with motor.connect() as conexion:
            assert conexion.execute(text("SELECT current_user")).scalar_one() == rol


# --- Fallo al crear la sesion --------------------------------------------------------------------


def test_fallo_al_crear_la_sesion_deja_los_fallos_descartados_y_la_credencial_intacta(
    api_real, datos_ab, motor_admin, monkeypatch
):
    consultorio, usuario = _datos(datos_ab)
    clave = api_real.servicio.config.clave_hmac
    clave_c = clave_de_cuenta(clave, consultorio.codigo, usuario.email)
    clave_i = clave_de_ip(clave, normalizar_ip(IP))
    with motor_admin.begin() as conexion:
        for n in range(4):
            conexion.execute(
                text(
                    "INSERT INTO intento_login (clave_cuenta, clave_ip, ocurrido_en) "
                    "VALUES (:c, :i, :t)"
                ),
                {"c": clave_c, "i": clave_i, "t": api_real.reloj.ahora().replace(second=n)},
            )
    antes = _escalar(motor_admin, "SELECT credencial || xmin::text FROM usuario WHERE id = :i", i=usuario.id)

    def falla(*_a, **_k):
        raise RuntimeError("fallo inyectado")

    original = acceso_previo.crear_sesion
    monkeypatch.setattr(acceso_previo, "crear_sesion", falla)
    respuesta = api_real.login(api_real.cliente(), consultorio.codigo, usuario.email, usuario.contrasena)

    assert respuesta.status_code == 500
    assert "set-cookie" not in respuesta.headers
    assert "x-csrf-token" not in respuesta.headers
    assert _escalar(motor_admin, "SELECT count(*) FROM sesion") == 0
    assert _escalar(motor_admin, "SELECT count(*) FROM intento_login WHERE descartado_para_cuenta") == 4
    assert _escalar(motor_admin, "SELECT credencial || xmin::text FROM usuario WHERE id = :i", i=usuario.id) == antes

    monkeypatch.setattr(acceso_previo, "crear_sesion", original)
    assert api_real.login(api_real.cliente(), consultorio.codigo, usuario.email, usuario.contrasena).status_code == 200


# --- Sin contaminacion entre logins ---------------------------------------------------------------


def test_pools_de_una_conexion_no_conservan_contexto_entre_logins_de_a_y_b(
    url_app, url_login, datos_ab, motor_admin
):
    api = construir_api(url_app, url_login)
    api.app.state.engine.dispose()
    api.app.state.engine_login.dispose()
    registrar_pool = dict(pool_size=1, max_overflow=0, pool_timeout=10)
    motor_app = create_engine(
        url_app.render_as_string(hide_password=False),
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SEGUNDOS},
        pool_pre_ping=True,
        **registrar_pool,
    )
    motor_login = create_engine(
        url_login.render_as_string(hide_password=False),
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SEGUNDOS},
        pool_pre_ping=True,
        **registrar_pool,
    )
    from app.core.database import registrar_guardia_de_rol

    registrar_guardia_de_rol(motor_app, ROL_APP)
    registrar_guardia_de_rol(motor_login, ROL_LOGIN)
    registrar_reset_del_pool(motor_app)
    api.app.state.engine, api.app.state.engine_login = motor_app, motor_login
    api.app.state.fabrica_sesiones = crear_fabrica_de_sesiones(motor_app)
    api.app.state.fabrica_sesiones_login = crear_fabrica_de_sesiones_login(motor_login)
    try:
        a, ua = _datos(datos_ab, "a")
        b, ub = _datos(datos_ab, "b")
        assert api.login(api.cliente(), a.codigo, ua.email, ua.contrasena).status_code == 200
        pid_app = _pid(motor_app)
        assert api.login(api.cliente(), b.codigo, ub.email, ub.contrasena).status_code == 200

        assert _pid(motor_app) == pid_app  # misma conexion reutilizada
        with motor_admin.connect() as conexion:
            asignadas = dict(
                conexion.execute(text("SELECT usuario_id, consultorio_id FROM sesion")).all()
            )
        assert asignadas == {ua.id: a.id, ub.id: b.id}
        for motor in (motor_app, motor_login):
            with motor.connect() as conexion:
                assert conexion.execute(
                    text("SELECT current_setting('app.consultorio_id', true)")
                ).scalar_one() in (None, "")
    finally:
        motor_app.dispose()
        motor_login.dispose()


def _pid(motor) -> int:
    with motor.connect() as conexion:
        return conexion.execute(text("SELECT pg_backend_pid()")).scalar_one()


# --- Verificacion con los locks tomados --------------------------------------------------------------


class VerificadorConSonda(VerificadorEspia):
    def __init__(self, sonda) -> None:
        super().__init__()
        self.sonda = sonda
        self.observaciones: list = []

    def verificar(self, contrasena, almacenado):
        self.observaciones.append(self.sonda())
        return super().verificar(contrasena, almacenado)


def test_la_verificacion_corre_con_los_locks_tomados_y_sin_conexion_de_app(
    url_app, url_login, datos_ab, motor_admin
):
    def sonda():
        with motor_admin.connect() as conexion:
            locks = conexion.execute(
                text(
                    "SELECT count(*) FROM pg_locks l JOIN pg_stat_activity a ON a.pid = l.pid "
                    "WHERE l.locktype = 'advisory' AND l.granted AND a.usename = :r"
                ),
                {"r": ROL_LOGIN},
            ).scalar_one()
            transacciones_app = conexion.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE usename = :r AND xact_start IS NOT NULL"
                ),
                {"r": ROL_APP},
            ).scalar_one()
            login_en_transaccion = conexion.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE usename = :r AND xact_start IS NOT NULL AND pid <> pg_backend_pid()"
                ),
                {"r": ROL_LOGIN},
            ).scalar_one()
        return locks, transacciones_app, login_en_transaccion

    verificador = VerificadorConSonda(sonda)
    api = construir_api(url_app, url_login, verificador=verificador)
    try:
        a, ua = _datos(datos_ab)
        assert api.login(api.cliente(), a.codigo, ua.email, ua.contrasena).status_code == 200
    finally:
        api.app.state.engine.dispose()
        api.app.state.engine_login.dispose()

    (locks, transacciones_app, login_en_transaccion), = verificador.observaciones
    assert locks == 2  # el de la cuenta y el de la IP
    assert transacciones_app == 0  # ninguna conexion de turnos_app abierta por la peticion
    assert login_en_transaccion == 1  # la de T1, con los locks tomados


# --- Conteo atomico con los roles de conexion --------------------------------------------------------


def test_diez_logins_concurrentes_del_mismo_par_dan_cinco_401_y_cinco_429(api_real, datos_ab, motor_admin):
    consultorio, usuario = _datos(datos_ab)
    barrera = threading.Barrier(10)
    estados: list[int] = []
    errores: list[BaseException] = []

    def pedir(puerto: int) -> None:
        try:
            cliente = api_real.cliente(IP, puerto)
            barrera.wait(timeout=30)
            estados.append(
                api_real.login(cliente, consultorio.codigo, usuario.email, "otra-" + secrets.token_hex(4)).status_code
            )
        except BaseException as error:  # noqa: BLE001
            errores.append(error)

    hilos = [threading.Thread(target=pedir, args=(40000 + i,)) for i in range(10)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=60)

    assert not errores, errores
    assert Counter(estados) == {401: 5, 429: 5}
    assert _escalar(motor_admin, "SELECT count(*) FROM intento_login") == 5

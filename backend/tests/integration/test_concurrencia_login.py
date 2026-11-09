"""Concurrencia real del control de intentos (tarea 6.4; DD-09, DD-10, locks consultivos de transaccion).

Hilos y conexiones REALES a db-test (cada hilo con su propia sesion y transaccion), sin transaccion
exterior revertible: los datos se confirman y se eliminan al terminar (solo en la base de pruebas).
"""

import threading
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.auth.claves import normalizar_ip
from app.auth.concurrencia import LimitadorArgon2
from app.auth.contrasenas import VerificadorContrasenas
from app.auth.servicio import (
    ConfigAuth,
    LoginBloqueado,
    LoginRechazado,
    ServicioAuth,
)
from app.main import crear_app
from tests.integration.app_auth import ORIGEN, settings_de_prueba
from tests.integration.datos_auth import (
    CLAVE_HMAC,
    CONTRASENA_A,
    EMAIL,
    RelojFijo,
    VerificadorEspia,
    crear_consultorio,
    crear_usuario,
    hash_rapido,
    hasher_rapido,
)

IP = normalizar_ip("203.0.113.7")
OTRA_CONTRASENA = "otra-contrasena-ficticia"
TABLAS_EN_ORDEN_DE_BORRADO = ("sesion", "intento_login", "usuario", "consultorio")


@pytest.fixture
def base_concurrente(base_migrada: Engine) -> Iterator[sessionmaker[Session]]:
    """Fabrica de sesiones con pool amplio sobre db-test, con un consultorio y un usuario confirmados."""
    assert (base_migrada.url.database or "").endswith("_test")
    motor = create_engine(
        base_migrada.url.render_as_string(hide_password=False), pool_size=50, max_overflow=0
    )
    fabrica = sessionmaker(bind=motor, expire_on_commit=False)
    try:
        with fabrica() as sesion:
            consultorio = crear_consultorio(sesion, "ficticio-a", "Consultorio Ficticio A")
            crear_usuario(sesion, consultorio, credencial=hash_rapido(CONTRASENA_A))
            sesion.commit()
        yield fabrica
    finally:
        with fabrica() as sesion:
            for tabla in TABLAS_EN_ORDEN_DE_BORRADO:
                sesion.execute(text(f"DELETE FROM {tabla}"))
            sesion.commit()
        motor.dispose()


def _servicio() -> ServicioAuth:
    return ServicioAuth(
        ConfigAuth(clave_hmac=CLAVE_HMAC, minutos_inactividad=30, horas_maximas=12),
        RelojFijo(),
        VerificadorEspia(),
        LimitadorArgon2(),
    )


def _lanzar(fabrica: sessionmaker[Session], servicio: ServicioAuth, pedidos: list[dict]) -> Counter:
    """Un hilo por pedido, liberados a la vez con una barrera; cuenta resultados 401 / 429."""
    barrera = threading.Barrier(len(pedidos))
    resultados: list[str] = []
    errores: list[BaseException] = []

    def intentar(pedido: dict) -> None:
        try:
            with fabrica() as sesion:
                barrera.wait(timeout=30)
                try:
                    servicio.iniciar_sesion(sesion, **pedido)
                    resultados.append("200")
                except LoginRechazado:
                    resultados.append("401")
                except LoginBloqueado:
                    resultados.append("429")
        except BaseException as error:  # noqa: BLE001 - se reporta en el hilo principal
            errores.append(error)

    hilos = [threading.Thread(target=intentar, args=(pedido,)) for pedido in pedidos]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=60)
    assert not errores, errores
    assert not any(hilo.is_alive() for hilo in hilos)
    return Counter(resultados)


def _fallos(fabrica: sessionmaker[Session]) -> int:
    with fabrica() as sesion:
        return sesion.execute(text("SELECT count(*) FROM intento_login")).scalar_one()


@pytest.mark.parametrize("ronda", range(2))
def test_diez_intentos_concurrentes_del_mismo_par_dan_exactamente_5_y_5(
    base_concurrente: sessionmaker[Session], ronda: int
):
    pedidos = [
        {"codigo": "ficticio-a", "email": EMAIL, "contrasena": OTRA_CONTRASENA, "ip_normalizada": IP}
    ] * 10

    resultado = _lanzar(base_concurrente, _servicio(), pedidos)

    assert resultado == {"401": 5, "429": 5}
    assert _fallos(base_concurrente) == 5


@pytest.mark.parametrize("ronda", range(2))
def test_cuarenta_intentos_concurrentes_desde_la_misma_ip_dan_exactamente_30_y_10(
    base_concurrente: sessionmaker[Session], ronda: int
):
    pedidos = [
        {
            "codigo": "ficticio-a",
            "email": f"nadie{i}@example.test",
            "contrasena": OTRA_CONTRASENA,
            "ip_normalizada": IP,
        }
        for i in range(40)
    ]

    resultado = _lanzar(base_concurrente, _servicio(), pedidos)

    assert resultado == {"401": 30, "429": 10}
    assert _fallos(base_concurrente) == 30


# --- 12.2: limite de cuatro verificaciones simultaneas por HTTP (8 logins reales concurrentes) -----


class _VerificadorQueSeBloquea(VerificadorContrasenas):
    """Se bloquea hasta recibir la senal y registra cuantas verificaciones corren a la vez."""

    def __init__(self, compuerta: threading.Event) -> None:
        super().__init__(hasher_rapido())
        self.compuerta = compuerta
        self.candado = threading.Lock()
        self.actual = 0
        self.maximo = 0

    def verificar(self, contrasena: str, almacenado: str | None) -> bool:
        with self.candado:
            self.actual += 1
            self.maximo = max(self.maximo, self.actual)
        try:
            assert self.compuerta.wait(timeout=30), "la senal nunca llego"
            return super().verificar(contrasena, almacenado)
        finally:
            with self.candado:
                self.actual -= 1


class _LimitadorQueCuentaLlegadas(LimitadorArgon2):
    """Igual que el real; ademas cuenta cuantos logins llegaron a pedir cupo."""

    def __init__(self) -> None:
        super().__init__()
        self.llegadas = 0
        self._candado = threading.Lock()

    @contextmanager
    def cupo(self) -> Iterator[None]:
        with self._candado:
            self.llegadas += 1
        with super().cupo():
            yield


def _esperar(condicion, descripcion: str, limite: float = 15.0) -> None:
    fin = time.monotonic() + limite
    while not condicion():
        assert time.monotonic() < fin, f"tiempo agotado esperando: {descripcion}"
        time.sleep(0.005)


def test_ocho_logins_http_concurrentes_ejecutan_a_lo_sumo_cuatro_verificaciones_a_la_vez(
    base_concurrente: sessionmaker[Session],
):
    emails = [f"persona{i}.ficticia@example.test" for i in range(8)]
    with base_concurrente() as sesion:
        consultorio = sesion.execute(text("SELECT id FROM consultorio")).scalar_one()
        for email in emails:
            crear_usuario(sesion, consultorio, email=email, credencial=hash_rapido(CONTRASENA_A))
        sesion.commit()
    compuerta = threading.Event()
    verificador = _VerificadorQueSeBloquea(compuerta)
    limitador = _LimitadorQueCuentaLlegadas()
    servicio = ServicioAuth(
        ConfigAuth(clave_hmac=CLAVE_HMAC, minutos_inactividad=30, horas_maximas=12),
        RelojFijo(),
        verificador,
        limitador,
    )
    app = crear_app(settings_de_prueba())
    app.state.fabrica_sesiones = base_concurrente
    app.state.servicio_auth = servicio
    respuestas: dict[int, int] = {}
    errores: list[BaseException] = []

    def pedir(indice: int) -> None:
        try:
            cliente = TestClient(
                app, base_url="https://testserver", client=(f"203.0.113.{10 + indice}", 50000 + indice)
            )
            respuesta = cliente.post(
                "/api/auth/login",
                json={
                    "codigo_consultorio": "ficticio-a",
                    "email": emails[indice],
                    "contrasena": OTRA_CONTRASENA,
                },
                headers={"Origin": ORIGEN},
            )
            respuestas[indice] = respuesta.status_code
        except BaseException as error:  # noqa: BLE001 - se reporta en el hilo principal
            errores.append(error)

    hilos = [threading.Thread(target=pedir, args=(i,)) for i in range(8)]
    try:
        for hilo in hilos:
            hilo.start()
        # Condicion observable, no una pausa: los 8 ya pidieron cupo y hay 4 verificaciones corriendo.
        _esperar(lambda: limitador.llegadas == 8, "las 8 solicitudes pidieron cupo")
        _esperar(lambda: verificador.actual == 4, "4 verificaciones simultaneas")
        assert verificador.maximo == 4  # los otros 4 esperan cupo: nunca hay mas de 4 a la vez
    finally:
        compuerta.set()
        for hilo in hilos:
            hilo.join(timeout=30)

    assert not errores, errores
    assert not any(hilo.is_alive() for hilo in hilos)
    assert verificador.maximo == 4
    assert verificador.actual == 0
    assert sorted(respuestas) == list(range(8))
    assert set(respuestas.values()) == {401}  # los 8 terminan con 401: ninguno 503 ni bloqueado
    # Recursos liberados y sin bloqueo permanente: los 4 cupos vuelven y el siguiente login funciona.
    disponibles = 0
    while limitador.semaforo.acquire(timeout=0):
        disponibles += 1
    for _ in range(disponibles):
        limitador.semaforo.release()
    assert disponibles == 4
    cliente = TestClient(app, base_url="https://testserver", client=("203.0.113.99", 40000))
    siguiente = cliente.post(
        "/api/auth/login",
        json={"codigo_consultorio": "ficticio-a", "email": emails[0], "contrasena": CONTRASENA_A},
        headers={"Origin": ORIGEN},
    )
    assert siguiente.status_code == 200
    with base_concurrente() as sesion:
        assert sesion.execute(text("SELECT count(*) FROM intento_login")).scalar_one() == 8


# --- 12.2: conteo atomico por HTTP (los logins concurrentes son solicitudes reales) -------------------


def _lanzar_por_http(
    fabrica: sessionmaker[Session], cuerpos: list[dict], direccion: str = "203.0.113.7"
) -> Counter:
    app = crear_app(settings_de_prueba())
    app.state.fabrica_sesiones = fabrica
    app.state.servicio_auth = _servicio()
    barrera = threading.Barrier(len(cuerpos))
    estados: list[int] = []
    errores: list[BaseException] = []

    def pedir(cuerpo: dict, puerto: int) -> None:
        try:
            cliente = TestClient(app, base_url="https://testserver", client=(direccion, puerto))
            barrera.wait(timeout=30)
            estados.append(
                cliente.post(
                    "/api/auth/login", json=cuerpo, headers={"Origin": ORIGEN}
                ).status_code
            )
        except BaseException as error:  # noqa: BLE001 - se reporta en el hilo principal
            errores.append(error)

    hilos = [
        threading.Thread(target=pedir, args=(cuerpo, 40000 + i)) for i, cuerpo in enumerate(cuerpos)
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=60)
    assert not errores, errores
    assert not any(hilo.is_alive() for hilo in hilos)
    return Counter(estados)


def test_diez_logins_http_concurrentes_del_mismo_par_dan_exactamente_5_401_y_5_429(
    base_concurrente: sessionmaker[Session],
):
    cuerpos = [
        {"codigo_consultorio": "ficticio-a", "email": EMAIL, "contrasena": OTRA_CONTRASENA}
    ] * 10

    resultado = _lanzar_por_http(base_concurrente, cuerpos)

    assert resultado == {401: 5, 429: 5}
    assert _fallos(base_concurrente) == 5


def test_cuarenta_logins_http_concurrentes_desde_la_misma_ip_dan_exactamente_30_401_y_10_429(
    base_concurrente: sessionmaker[Session],
):
    cuerpos = [
        {
            "codigo_consultorio": "ficticio-a",
            "email": f"nadie{i}@example.test",
            "contrasena": OTRA_CONTRASENA,
        }
        for i in range(40)
    ]

    resultado = _lanzar_por_http(base_concurrente, cuerpos)

    assert resultado == {401: 30, 429: 10}
    assert _fallos(base_concurrente) == 30

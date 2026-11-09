"""Pruebas de `app.auth.concurrencia` (tarea 3.5; DD-29, PC-02)."""

import asyncio
import threading
import time

import pytest

from app.auth.concurrencia import (
    CUPOS_POR_PROCESO,
    ESPERA_MAXIMA_SEGUNDOS,
    LimitadorArgon2,
    ServicioOcupado,
)


def _cupos_libres(limitador: LimitadorArgon2) -> int:
    """Cuenta cuantos cupos pueden tomarse a la vez (y los devuelve al salir)."""
    tomados: list = []
    try:
        while True:
            contexto = limitador.cupo()
            contexto.__enter__()
            tomados.append(contexto)
    except ServicioOcupado:
        return len(tomados)
    finally:
        for contexto in reversed(tomados):
            contexto.__exit__(None, None, None)


def test_los_valores_por_defecto_son_4_cupos_y_3_segundos():
    assert CUPOS_POR_PROCESO == 4
    assert ESPERA_MAXIMA_SEGUNDOS == 3.0
    assert _cupos_libres(LimitadorArgon2(espera_segundos=0.01)) == 4


def test_con_8_hilos_la_concurrencia_maxima_observada_es_4():
    limitador = LimitadorArgon2(espera_segundos=10.0)
    liberar = threading.Event()
    candado = threading.Lock()
    estado = {"actual": 0, "maximo": 0}
    resultados: list[int] = []

    def verificador(valor: int) -> int:
        with candado:
            estado["actual"] += 1
            estado["maximo"] = max(estado["maximo"], estado["actual"])
        liberar.wait(timeout=10)
        with candado:
            estado["actual"] -= 1
        return valor

    hilos = [
        threading.Thread(target=lambda v=v: resultados.append(limitador.ejecutar(verificador, v)))
        for v in range(8)
    ]
    for hilo in hilos:
        hilo.start()
    tiempo_limite = time.monotonic() + 5
    while estado["actual"] < 4 and time.monotonic() < tiempo_limite:
        time.sleep(0.005)
    time.sleep(0.1)  # los otros 4 deben seguir esperando cupo
    assert estado["actual"] == 4
    liberar.set()
    for hilo in hilos:
        hilo.join(timeout=10)

    assert sorted(resultados) == list(range(8))
    assert estado["maximo"] == 4
    asercion_rapida = LimitadorArgon2(semaforo=limitador.semaforo, espera_segundos=0.01)
    assert _cupos_libres(asercion_rapida) == 4


def test_sin_cupo_dentro_de_la_espera_inyectada_lanza_servicio_ocupado_sin_ejecutar():
    limitador = LimitadorArgon2(cupos=2, espera_segundos=0.05)
    llamadas: list[int] = []

    with limitador.cupo(), limitador.cupo():
        inicio = time.monotonic()
        with pytest.raises(ServicioOcupado):
            limitador.ejecutar(lambda: llamadas.append(1))
        espera = time.monotonic() - inicio

    assert 0.04 <= espera < 2
    assert llamadas == []
    assert _cupos_libres(limitador) == 2


def test_el_cupo_se_libera_exactamente_una_vez_ante_excepciones_seguidas():
    limitador = LimitadorArgon2(espera_segundos=0.01)

    def falla() -> None:
        raise RuntimeError("fallo del verificador")

    for _ in range(4):
        with pytest.raises(RuntimeError):
            limitador.ejecutar(falla)

    assert _cupos_libres(limitador) == 4
    assert limitador.ejecutar(lambda: "ok") == "ok"


def test_el_cupo_se_libera_ante_cancelacion_del_verificador():
    limitador = LimitadorArgon2(espera_segundos=0.01)

    def cancelado() -> None:
        raise asyncio.CancelledError

    for _ in range(4):
        with pytest.raises(asyncio.CancelledError):
            limitador.ejecutar(cancelado)

    assert _cupos_libres(limitador) == 4


def test_una_interrupcion_de_teclado_tambien_libera_el_cupo():
    limitador = LimitadorArgon2(espera_segundos=0.01)

    def interrumpido() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        limitador.ejecutar(interrumpido)

    assert _cupos_libres(limitador) == 4


class _SemaforoQueSeCancelaEsperando:
    """Simula la cancelacion durante la espera: `acquire` lanza y nunca toma el cupo."""

    def __init__(self) -> None:
        self.liberaciones = 0

    def acquire(self, timeout: float | None = None) -> bool:
        raise asyncio.CancelledError

    def release(self) -> None:
        self.liberaciones += 1


def test_la_cancelacion_durante_la_espera_no_toma_ni_libera_ningun_cupo():
    semaforo = _SemaforoQueSeCancelaEsperando()
    limitador = LimitadorArgon2(semaforo=semaforo)

    with pytest.raises(asyncio.CancelledError):
        limitador.ejecutar(lambda: pytest.fail("no debe ejecutarse"))

    assert semaforo.liberaciones == 0


def test_el_semaforo_es_acotado_y_una_liberacion_de_mas_se_detecta_como_error():
    limitador = LimitadorArgon2(cupos=1, espera_segundos=0.01)

    assert isinstance(limitador.semaforo, threading.BoundedSemaphore)
    with limitador.cupo():
        pass
    with pytest.raises(ValueError):
        limitador.semaforo.release()


def test_el_resultado_y_los_argumentos_se_pasan_al_verificador():
    limitador = LimitadorArgon2(espera_segundos=0.01)

    assert limitador.ejecutar(lambda a, b: a + b, 2, 3) == 5


class _SemaforoRealQueSeCancelaEsperando:
    """Semaforo acotado real; `acquire` se cancela durante la espera sin tomar el cupo."""

    def __init__(self, cupos: int) -> None:
        self.real = threading.BoundedSemaphore(cupos)
        self.cancelar = True
        self.liberaciones = 0

    def acquire(self, timeout: float | None = None) -> bool:
        if self.cancelar:
            raise asyncio.CancelledError
        return self.real.acquire(timeout=timeout if timeout is not None else -1)

    def release(self) -> None:
        self.liberaciones += 1
        self.real.release()


def test_cuatro_cancelaciones_durante_la_espera_dejan_4_cupos_y_ninguno_se_libera_dos_veces():
    semaforo = _SemaforoRealQueSeCancelaEsperando(CUPOS_POR_PROCESO)
    limitador = LimitadorArgon2(semaforo=semaforo, espera_segundos=0.01)

    for _ in range(4):
        with pytest.raises(asyncio.CancelledError):
            limitador.ejecutar(lambda: pytest.fail("no debe ejecutarse"))

    assert semaforo.liberaciones == 0  # nunca se libero un cupo que no se tomo
    semaforo.cancelar = False
    assert _cupos_libres(limitador) == 4
    # Con un BoundedSemaphore, una liberacion de mas habria lanzado ValueError; no ocurrio.
    assert semaforo.liberaciones == 4  # solo las de `_cupos_libres` (una por cupo tomado)
    with pytest.raises(ValueError):
        semaforo.real.release()  # el semaforo sigue acotado: no hay cupos de mas

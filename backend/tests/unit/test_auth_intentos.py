"""Pruebas de la politica pura de intentos `app.auth.intentos` (tarea 3.6; DD-09, DD-10, PC-04)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.auth.intentos import (
    POLITICA_CUENTA,
    POLITICA_IP,
    Intento,
    descartar_para_cuenta,
    evaluar_bloqueo,
    evaluar_cuenta,
    evaluar_ip,
)

AHORA = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)


def _fallos(n: int, *, ultimo: datetime = AHORA, separacion: timedelta = timedelta(seconds=10)):
    """`n` fallos terminando en `ultimo`, separados por `separacion` (el mas reciente al final)."""
    return [ultimo - separacion * (n - 1 - i) for i in range(n)]


def test_las_politicas_son_5_por_cuenta_y_30_por_ip_en_15_minutos():
    assert (POLITICA_CUENTA.umbral, POLITICA_IP.umbral) == (5, 30)
    assert POLITICA_CUENTA.ventana == POLITICA_IP.ventana == timedelta(minutes=15)
    assert POLITICA_CUENTA.duracion_bloqueo == POLITICA_IP.duracion_bloqueo == timedelta(minutes=15)


@pytest.mark.parametrize("cantidad", [0, 1, 4])
def test_menos_de_5_fallos_no_bloquean_la_cuenta(cantidad):
    assert evaluar_bloqueo(_fallos(cantidad), AHORA, POLITICA_CUENTA) is None


def test_cinco_fallos_en_la_ventana_bloquean_con_retry_after_desde_el_quinto():
    fallos = _fallos(5, ultimo=AHORA - timedelta(minutes=2))

    assert evaluar_bloqueo(fallos, AHORA, POLITICA_CUENTA) == 13 * 60


def test_el_bloqueo_termina_a_los_15_minutos_del_quinto_fallo():
    quinto = AHORA
    fallos = _fallos(5, ultimo=quinto)

    assert evaluar_bloqueo(fallos, quinto + timedelta(minutes=15) - timedelta(seconds=1), POLITICA_CUENTA) == 1
    assert evaluar_bloqueo(fallos, quinto + timedelta(minutes=15), POLITICA_CUENTA) is None
    assert evaluar_bloqueo(fallos, quinto + timedelta(minutes=16), POLITICA_CUENTA) is None


def test_cinco_fallos_distribuidos_en_mas_de_15_minutos_no_bloquean():
    fallos = [AHORA - timedelta(minutes=16), *_fallos(4, ultimo=AHORA - timedelta(seconds=1))]

    assert evaluar_bloqueo(fallos, AHORA, POLITICA_CUENTA) is None


def test_el_limite_de_exactamente_15_minutos_entre_el_primero_y_el_quinto_bloquea():
    fallos = [AHORA - timedelta(minutes=15), *_fallos(4, ultimo=AHORA)]

    assert evaluar_bloqueo(fallos, AHORA, POLITICA_CUENTA) == 15 * 60


def test_se_consideran_los_5_fallos_mas_recientes_y_un_sexto_antiguo_no_evita_el_bloqueo():
    fallos = [AHORA - timedelta(minutes=29), *_fallos(5, ultimo=AHORA)]

    assert evaluar_bloqueo(fallos, AHORA, POLITICA_CUENTA) == 15 * 60


def test_los_fallos_de_hace_mas_de_30_minutos_no_cuentan():
    antiguos = _fallos(5, ultimo=AHORA - timedelta(minutes=30, seconds=1))
    mezcla = [*antiguos[:3], *_fallos(2, ultimo=AHORA - timedelta(minutes=1))]

    assert evaluar_bloqueo(antiguos, AHORA, POLITICA_CUENTA) is None
    assert evaluar_bloqueo(mezcla, AHORA, POLITICA_CUENTA) is None


def test_el_orden_de_entrada_no_cambia_el_resultado():
    fallos = _fallos(5, ultimo=AHORA - timedelta(minutes=1))

    assert evaluar_bloqueo(list(reversed(fallos)), AHORA, POLITICA_CUENTA) == evaluar_bloqueo(
        fallos, AHORA, POLITICA_CUENTA
    )


@pytest.mark.parametrize(
    ("restante", "esperado"),
    [
        (timedelta(milliseconds=200), 1),
        (timedelta(seconds=1), 1),
        (timedelta(seconds=1, milliseconds=1), 2),
        (timedelta(seconds=899, milliseconds=500), 900),
        (timedelta(minutes=15), 900),
    ],
)
def test_retry_after_se_redondea_hacia_arriba_con_minimo_1(restante, esperado):
    ultimo = AHORA + restante - POLITICA_CUENTA.duracion_bloqueo
    fallos = _fallos(5, ultimo=ultimo, separacion=timedelta(seconds=1))

    assert evaluar_bloqueo(fallos, AHORA, POLITICA_CUENTA) == esperado


@pytest.mark.parametrize(("cantidad", "bloqueado"), [(29, False), (30, True), (31, True)])
def test_umbral_por_ip_de_30_con_los_limites_29_y_30(cantidad, bloqueado):
    fallos = _fallos(cantidad, separacion=timedelta(seconds=5))

    assert (evaluar_bloqueo(fallos, AHORA, POLITICA_IP) is not None) is bloqueado


def test_30_fallos_de_ip_repartidos_en_mas_de_15_minutos_no_bloquean():
    fallos = _fallos(30, separacion=timedelta(seconds=31))  # 29 * 31 s = 14,98 min -> bloquea

    assert evaluar_bloqueo(fallos, AHORA, POLITICA_IP) is not None
    fallos = _fallos(30, separacion=timedelta(seconds=32))  # 29 * 32 s = 15,47 min -> no

    assert evaluar_bloqueo(fallos, AHORA, POLITICA_IP) is None


def test_el_bloqueo_por_ip_no_se_prolonga_con_intentos_posteriores_al_quinto_registrado():
    fallos = _fallos(30, ultimo=AHORA - timedelta(minutes=5))

    assert evaluar_bloqueo(fallos, AHORA, POLITICA_IP) == 10 * 60


# --- contadores independientes (PC-04) -----------------------------------


def _intentos(fallos, descartado: bool = False):
    return [Intento(ocurrido_en=f, descartado_para_cuenta=descartado) for f in fallos]


def test_el_contador_de_cuenta_ignora_los_fallos_descartados_y_el_de_ip_no():
    registros = _intentos(_fallos(5))

    assert evaluar_cuenta(registros, AHORA) is not None
    descartados = descartar_para_cuenta(registros)

    assert evaluar_cuenta(descartados, AHORA) is None
    assert evaluar_ip(descartados, AHORA) is None  # solo 5 de 30
    ip = descartar_para_cuenta(_intentos(_fallos(30, separacion=timedelta(seconds=5))))
    assert evaluar_ip(ip, AHORA) is not None  # el exito no reinicia la IP


def test_descartar_para_cuenta_no_borra_ni_altera_otros_campos_y_no_muta_la_entrada():
    original = _intentos(_fallos(3))
    resultado = descartar_para_cuenta(original)

    assert [i.ocurrido_en for i in resultado] == [i.ocurrido_en for i in original]
    assert all(i.descartado_para_cuenta for i in resultado)
    assert not any(i.descartado_para_cuenta for i in original)


def test_fallos_nuevos_tras_un_exito_empiezan_a_contar_desde_cero_para_la_cuenta():
    anteriores = descartar_para_cuenta(_intentos(_fallos(4, ultimo=AHORA - timedelta(minutes=1))))
    nuevo = _intentos([AHORA])

    assert evaluar_cuenta([*anteriores, *nuevo], AHORA) is None  # 1 contable, no 5
    mas = _intentos(_fallos(4, ultimo=AHORA))
    assert evaluar_cuenta([*anteriores, *mas], AHORA) is None  # 4 contables
    assert evaluar_cuenta([*anteriores, *mas, *nuevo], AHORA) is not None  # 5 contables

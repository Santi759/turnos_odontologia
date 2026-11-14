"""Presupuesto de conexiones por proceso (5.7, condicion 9; R3-02, DD-33).

Los pools y el cupo de Argon2 son POR PROCESO: cada proceso adicional de la API suma
`POOL_LOGIN + POOL_APP` conexiones (30) y 4 cupos de verificacion. Con los valores de PostgreSQL
(`max_connections = 100`, `superuser_reserved_connections = 3`):

    (15 + 15) x procesos + comandos locales <= max_connections - superuser_reserved_connections - margen

El margen y los comandos locales son constantes nombradas y registradas en `tdd-evidencia.md`.
"""

from app.auth.concurrencia import CUPOS_POR_PROCESO
from app.core import database

MAX_CONNECTIONS = 100
SUPERUSER_RESERVED_CONNECTIONS = 3
MARGEN_DE_CONEXIONES = 10  # herramientas (psql, pg_dump, Alembic) y picos
COMANDOS_LOCALES_SIMULTANEOS = 3  # seed, credenciales y mantenimiento: una conexion cada uno
PROCESOS_EN_DESARROLLO = 1

POOL_LOGIN_MAXIMO = database.POOL_LOGIN_TAMANO + database.POOL_LOGIN_DESBORDE
POOL_APP_MAXIMO = database.POOL_APP_TAMANO + database.POOL_APP_DESBORDE
POR_PROCESO = POOL_LOGIN_MAXIMO + POOL_APP_MAXIMO


def disponibles() -> int:
    return MAX_CONNECTIONS - SUPERUSER_RESERVED_CONNECTIONS - MARGEN_DE_CONEXIONES


def necesarias(procesos: int) -> int:
    return POR_PROCESO * procesos + COMANDOS_LOCALES_SIMULTANEOS


def test_los_maximos_por_pool_salen_de_las_constantes_de_la_configuracion():
    assert (POOL_LOGIN_MAXIMO, POOL_APP_MAXIMO, POR_PROCESO) == (15, 15, 30)


def test_el_proceso_de_desarrollo_cabe_en_el_presupuesto():
    assert necesarias(PROCESOS_EN_DESARROLLO) == 33
    assert necesarias(PROCESOS_EN_DESARROLLO) <= disponibles()


def test_cada_proceso_adicional_suma_30_conexiones_y_el_limite_es_de_dos_procesos():
    assert necesarias(2) - necesarias(1) == 30
    assert necesarias(2) <= disponibles()  # 63 <= 87
    assert necesarias(3) > disponibles()  # 93 > 87: un tercer proceso exige revisar PD-04


def test_el_cupo_de_argon2_es_por_proceso_y_cabe_en_el_pool_de_login_de_ese_proceso():
    # Cada login retiene una conexion de login mientras verifica: los cupos nunca superan el pool.
    assert CUPOS_POR_PROCESO == 4
    assert CUPOS_POR_PROCESO <= POOL_LOGIN_MAXIMO

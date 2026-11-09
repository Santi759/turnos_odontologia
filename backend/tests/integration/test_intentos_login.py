"""Control de intentos integrado en el servicio de login (tarea 6.3; DD-09 a DD-12, DD-21, PC-04).

Contra db-test, con reloj inyectado y direcciones de documentacion (`203.0.113.0/24`, `2001:db8::/32`).
Los rechazos previos a la evaluacion de credenciales (Origin, direccion no determinable, Content-Type,
cuerpo) se prueban en las capas de dependencias y de API (grupos 7 y 8): aqui solo se prueba lo que el
servicio evalua.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.claves import clave_de_cuenta, clave_de_ip, normalizar_ip
from app.auth.servicio import LoginBloqueado, LoginRechazado
from tests.integration.app_auth import ORIGEN, crear_app_real
from tests.integration.datos_auth import (
    AHORA,
    CLAVE_HMAC,
    CONTRASENA_A,
    CONTRASENA_B,
    EMAIL,
    IP,
    Entorno,
    crear_usuario,
    hash_rapido,
    insertar_fallo,
)

OTRA_CONTRASENA = "otra-contrasena-ficticia"
PASO = timedelta(seconds=10)


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


def _fallar(e: Entorno, veces: int, *, codigo="ficticio-a", email=EMAIL, ip=IP, paso=PASO) -> None:
    """`veces` logins fallidos del mismo par, avanzando el reloj entre ellos (el ultimo no avanza)."""
    for i in range(veces):
        with pytest.raises(LoginRechazado):
            e.login(codigo=codigo, email=email, contrasena=OTRA_CONTRASENA, ip=ip)
        if i < veces - 1:
            e.reloj.avanzar(paso)


def _fallar_en_pares_distintos(e: Entorno, veces: int, *, ip=IP, paso=timedelta(seconds=20)) -> None:
    """Un fallo por par distinto (emails inexistentes) desde la misma direccion."""
    for i in range(veces):
        with pytest.raises(LoginRechazado):
            e.login(email=f"nadie{i}@example.test", contrasena=OTRA_CONTRASENA, ip=ip)
        e.reloj.avanzar(paso)


def _filas(e: Entorno):
    return e.db.execute(
        text("SELECT clave_cuenta, clave_ip, ocurrido_en, descartado_para_cuenta FROM intento_login ORDER BY id")
    ).all()


def _bloqueo(e: Entorno, **datos) -> int:
    with pytest.raises(LoginBloqueado) as bloqueo:
        e.login(**datos)
    return bloqueo.value.retry_after


# --- bloqueo por cuenta ----------------------------------------------------------------------


def test_sexto_intento_bloqueado_aun_con_la_contrasena_correcta_y_sin_verificar(entorno: Entorno):
    _fallar(entorno, 5, paso=timedelta(minutes=2))  # t5 = t0 + 8 min
    entorno.reloj.avanzar(timedelta(minutes=1))
    llamadas = entorno.verificador.llamadas

    assert _bloqueo(entorno) == 840
    assert entorno.verificador.llamadas == llamadas
    assert entorno.sesiones() == []


def test_fin_del_bloqueo_a_los_15_minutos_del_quinto_fallo(entorno: Entorno):
    _fallar(entorno, 5, paso=timedelta(minutes=2))
    entorno.reloj.avanzar(timedelta(minutes=15) - timedelta(seconds=1))
    assert _bloqueo(entorno) == 1

    entorno.reloj.avanzar(timedelta(seconds=1))
    assert entorno.login().nombre == "Persona A"


def test_fallos_fuera_de_la_ventana_no_bloquean(entorno: Entorno):
    _fallar(entorno, 4)
    entorno.reloj.avanzar(timedelta(minutes=20))
    _fallar(entorno, 1)
    entorno.reloj.avanzar(timedelta(minutes=1))

    assert entorno.login().nombre == "Persona A"


def test_los_intentos_bloqueados_no_se_registran_ni_prolongan_el_bloqueo(entorno: Entorno):
    _fallar(entorno, 5, paso=timedelta(minutes=1))  # t5 = t0 + 4 min
    quinto = entorno.reloj.ahora()

    for _ in range(3):
        entorno.reloj.avanzar(timedelta(minutes=1))
        _bloqueo(entorno)
    assert len(_filas(entorno)) == 5

    entorno.reloj.avanzar(quinto + timedelta(minutes=15) - entorno.reloj.ahora())
    assert entorno.login().nombre == "Persona A"


def test_el_exito_marca_los_fallos_del_par_sin_borrarlos_y_deja_los_de_otro_par(entorno: Entorno):
    _fallar(entorno, 3)
    for i in range(2):
        with pytest.raises(LoginRechazado):
            entorno.login(email=f"otro{i}@example.test", contrasena=OTRA_CONTRASENA)

    entorno.login()

    filas = _filas(entorno)
    clave_par = clave_de_cuenta(CLAVE_HMAC, "ficticio-a", EMAIL)
    assert len(filas) == 5
    assert [f.descartado_para_cuenta for f in filas if bytes(f.clave_cuenta) == clave_par] == [True] * 3
    assert [f.descartado_para_cuenta for f in filas if bytes(f.clave_cuenta) != clave_par] == [False] * 2


def test_el_exito_reinicia_el_contador_de_la_cuenta(entorno: Entorno):
    _fallar(entorno, 4)
    entorno.reloj.avanzar(PASO)
    entorno.login()
    entorno.reloj.avanzar(PASO)

    _fallar(entorno, 4)
    entorno.reloj.avanzar(PASO)

    assert entorno.login().nombre == "Persona A"


def test_el_exito_no_reinicia_el_contador_de_ip(entorno: Entorno):
    _fallar(entorno, 4, paso=timedelta(seconds=15))  # 4 del par
    entorno.reloj.avanzar(timedelta(seconds=15))
    _fallar_en_pares_distintos(entorno, 25, paso=timedelta(seconds=15))  # 29 desde la IP
    assert len(_filas(entorno)) == 29

    entorno.login()  # el par no esta bloqueado (4 < 5) ni la IP (29 < 30): 200
    entorno.reloj.avanzar(PASO)
    with pytest.raises(LoginRechazado):
        entorno.login(email="otro@example.test", contrasena=OTRA_CONTRASENA)  # el fallo 30 de la IP
    entorno.reloj.avanzar(PASO)

    assert len(_filas(entorno)) == 30
    _bloqueo(entorno)  # cualquier par, con la contrasena correcta: bloqueado por IP


# --- cuentas inexistentes y aislamiento del par --------------------------------------------------


@pytest.mark.parametrize(
    "datos",
    [{"email": "nadie@example.test"}, {"codigo": "no-existe"}],
    ids=["email-inexistente", "consultorio-inexistente"],
)
def test_las_cuentas_inexistentes_se_bloquean_igual_que_las_existentes(entorno: Entorno, datos):
    for _ in range(5):
        with pytest.raises(LoginRechazado):
            entorno.login(**datos)
    llamadas = entorno.verificador.llamadas

    with pytest.raises(LoginBloqueado):
        entorno.login(**datos)
    assert entorno.verificador.llamadas == llamadas
    assert len(_filas(entorno)) == 5


def test_el_bloqueo_afecta_solo_al_par_atacado(entorno: Entorno):
    crear_usuario(
        entorno.db, entorno.a, email="otra.persona@example.test", credencial=hash_rapido(CONTRASENA_A)
    )
    entorno.db.commit()
    _fallar(entorno, 5)
    _bloqueo(entorno)

    assert entorno.login(codigo="ficticio-b", contrasena=CONTRASENA_B).consultorio_nombre == (
        "Consultorio Ficticio B"
    )
    assert entorno.login(email="otra.persona@example.test").email == "otra.persona@example.test"


# --- limite por IP ----------------------------------------------------------------------------


def test_rociado_desde_una_ip_bloquea_logins_de_pares_sin_fallos(entorno: Entorno):
    _fallar_en_pares_distintos(entorno, 30)  # el ultimo fallo en t0 + 580 s; el reloj ya avanzo 20 s
    entorno.reloj.avanzar(timedelta(seconds=40))  # t30 + 1 min
    llamadas = entorno.verificador.llamadas

    assert _bloqueo(entorno) == 840
    assert entorno.verificador.llamadas == llamadas


def test_por_debajo_del_limite_por_ip_el_login_correcto_pasa(entorno: Entorno):
    _fallar_en_pares_distintos(entorno, 29)

    assert entorno.login().nombre == "Persona A"


def test_otra_direccion_no_queda_afectada_por_el_bloqueo_de_ip(entorno: Entorno):
    _fallar_en_pares_distintos(entorno, 30)
    _bloqueo(entorno)

    assert entorno.login(ip=normalizar_ip("203.0.113.8")).nombre == "Persona A"


def test_fin_del_bloqueo_por_ip_sin_prolongacion(entorno: Entorno):
    _fallar_en_pares_distintos(entorno, 30, paso=timedelta(seconds=10))
    t30 = entorno.reloj.ahora() - timedelta(seconds=10)
    for _ in range(5):
        entorno.reloj.avanzar(timedelta(minutes=1))
        _bloqueo(entorno)
    assert len(_filas(entorno)) == 30

    entorno.reloj.avanzar(t30 + timedelta(minutes=15) - entorno.reloj.ahora())
    assert entorno.login().nombre == "Persona A"


def test_red_compartida_dos_usuarios_legitimos_quedan_bloqueados_desde_esa_ip(entorno: Entorno):
    crear_usuario(
        entorno.db, entorno.a, email="otra.persona@example.test", credencial=hash_rapido(CONTRASENA_A)
    )
    entorno.db.commit()
    _fallar_en_pares_distintos(entorno, 30)

    _bloqueo(entorno)
    _bloqueo(entorno, email="otra.persona@example.test")
    assert entorno.login(ip=normalizar_ip("203.0.113.8")).nombre == "Persona A"


def test_ipv6_se_agrupa_por_prefijo_64(entorno: Entorno):
    for i in range(30):
        with pytest.raises(LoginRechazado):
            entorno.login(
                email=f"nadie{i}@example.test",
                contrasena=OTRA_CONTRASENA,
                ip=normalizar_ip(f"2001:db8:1:2::{i + 1:x}"),
            )
        entorno.reloj.avanzar(timedelta(seconds=20))

    _bloqueo(entorno, ip=normalizar_ip("2001:db8:1:2:ffff:ffff:ffff:ffff"))
    assert entorno.login(ip=normalizar_ip("2001:db8:1:3::1")).nombre == "Persona A"


def test_ipv4_mapeada_cuenta_como_la_ipv4(entorno: Entorno):
    _fallar_en_pares_distintos(entorno, 30, ip=normalizar_ip("::ffff:203.0.113.7"))

    _bloqueo(entorno, ip=normalizar_ip("203.0.113.7"))


def test_el_bloqueo_de_ip_no_afecta_a_las_sesiones_abiertas(entorno: Entorno):
    iniciada = entorno.login()
    _fallar_en_pares_distintos(entorno, 30)
    _bloqueo(entorno)

    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is not None
    assert entorno.servicio.cerrar_sesion(entorno.db, iniciada.sesion_id) is True


# --- filas sin datos en claro ---------------------------------------------------------------------


def test_la_fila_de_un_fallo_solo_tiene_claves_hmac_y_la_marca_en_falso(entorno: Entorno):
    _fallar(entorno, 1)

    (fila,) = _filas(entorno)
    assert bytes(fila.clave_cuenta) == clave_de_cuenta(CLAVE_HMAC, "ficticio-a", EMAIL)
    assert bytes(fila.clave_ip) == clave_de_ip(CLAVE_HMAC, IP)
    assert len(bytes(fila.clave_cuenta)) == len(bytes(fila.clave_ip)) == 32
    assert fila.descartado_para_cuenta is False
    en_claro = (EMAIL, "ficticio-a", "203.0.113.7", OTRA_CONTRASENA)
    assert not any(dato in str(tuple(fila)) for dato in en_claro)


# --- limpieza de intentos --------------------------------------------------------------------------


def _insertar_viejos(e: Entorno, cantidad: int) -> None:
    otra_cuenta, otra_ip = bytes(32), bytes([1]) * 32
    for _ in range(cantidad):
        insertar_fallo(e.db, otra_cuenta, otra_ip, AHORA - timedelta(hours=25))
    e.db.commit()


def test_un_login_fallido_borra_los_intentos_viejos_y_deja_los_recientes_y_el_propio(entorno: Entorno):
    _insertar_viejos(entorno, 30)
    for _ in range(2):
        insertar_fallo(entorno.db, bytes(32), bytes([1]) * 32, AHORA - timedelta(minutes=5))
    entorno.db.commit()

    _fallar(entorno, 1)

    assert len(_filas(entorno)) == 3


def test_un_login_exitoso_tambien_limpia_intentos_viejos(entorno: Entorno):
    _insertar_viejos(entorno, 30)

    entorno.login()

    assert _filas(entorno) == []


def test_la_limpieza_de_intentos_borra_como_maximo_100_por_login(entorno: Entorno):
    _insertar_viejos(entorno, 150)

    _fallar(entorno, 1)

    assert len(_filas(entorno)) == 150 - 100 + 1


def test_un_login_bloqueado_no_escribe_ni_limpia(entorno: Entorno):
    _fallar(entorno, 5)
    _insertar_viejos(entorno, 3)
    antes = len(_filas(entorno))

    _bloqueo(entorno)

    assert len(_filas(entorno)) == antes


# --- cabeceras de reenvio ignoradas, por la API real (tarea 11.2; DD-19, PC-05) -----------------------

CABECERAS_DE_REENVIO = {
    "x-forwarded-for": lambda i: f"198.51.100.{i + 1}",
    "x-real-ip": lambda i: f"198.51.100.{i + 1}",
    "forwarded": lambda i: f"for=198.51.100.{i + 1}",
}


@pytest.mark.parametrize("cabecera", list(CABECERAS_DE_REENVIO))
def test_las_cabeceras_de_reenvio_variables_no_evitan_el_limite_por_ip(entorno: Entorno, cabecera: str):
    """30 fallos de 30 pares desde la misma conexion, cada uno con una cabecera de reenvio distinta."""
    cliente = TestClient(
        crear_app_real(entorno), base_url="https://testserver", client=("203.0.113.7", 50000)
    )
    valor = CABECERAS_DE_REENVIO[cabecera]
    for i in range(30):
        respuesta = cliente.post(
            "/api/auth/login",
            json={
                "codigo_consultorio": "ficticio-a",
                "email": f"nadie{i}@example.test",
                "contrasena": OTRA_CONTRASENA,
            },
            headers={"Origin": ORIGEN, cabecera: valor(i)},
        )
        assert respuesta.status_code == 401

    # Un par sin fallos, con credenciales correctas y OTRA direccion de reenvio: igual queda bloqueado.
    siguiente = cliente.post(
        "/api/auth/login",
        json={"codigo_consultorio": "ficticio-a", "email": EMAIL, "contrasena": CONTRASENA_A},
        headers={"Origin": ORIGEN, cabecera: valor(99)},
    )

    assert siguiente.status_code == 429
    assert siguiente.headers["retry-after"] == "900"

"""Control de intentos por HTTP con la app REAL y `db-test` (cierre 12.2; spec `control-intentos-login`).

Refleja a nivel de endpoint los escenarios que las pruebas de servicio (`test_intentos_login.py`)
verifican sin pasar por la capa HTTP: estado, cuerpo exacto, `Retry-After`, ausencia de cookie y de
verificacion. El reloj es el inyectable de `Entorno`; las direcciones son de documentacion
(`203.0.113.0/24`, `2001:db8::/32`) y se inyectan siempre de forma explicita.
"""

from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.claves import clave_de_cuenta
from app.auth.cookies import NOMBRE_COOKIE
from tests.integration.app_auth import ORIGEN, crear_app_real
from tests.integration.datos_auth import (
    CLAVE_HMAC,
    CONTRASENA_A,
    CONTRASENA_B,
    EMAIL,
    Entorno,
    crear_usuario,
    hash_rapido,
)

RECHAZO_LOGIN = {"detail": "No se pudo iniciar sesión."}
BLOQUEADO = {"detail": "Demasiados intentos. Intente más tarde."}
OTRA_CONTRASENA = "otra-contrasena-ficticia"
IP = "203.0.113.7"
PASO = timedelta(seconds=10)


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


@pytest.fixture
def app(entorno: Entorno) -> FastAPI:
    return crear_app_real(entorno)


def _login(app: FastAPI, ip: str = IP, *, codigo="ficticio-a", email=EMAIL, contrasena=CONTRASENA_A):
    cliente = TestClient(app, base_url="https://testserver", client=(ip, 50000))
    return cliente.post(
        "/api/auth/login",
        json={"codigo_consultorio": codigo, "email": email, "contrasena": contrasena},
        headers={"Origin": ORIGEN},
    )


def _fallar(app: FastAPI, e: Entorno, veces: int, *, ip=IP, email=EMAIL, codigo="ficticio-a", paso=PASO):
    for i in range(veces):
        respuesta = _login(app, ip, codigo=codigo, email=email, contrasena=OTRA_CONTRASENA)
        assert respuesta.status_code == 401
        assert respuesta.json() == RECHAZO_LOGIN
        if i < veces - 1:
            e.reloj.avanzar(paso)


def _fallar_en_pares_distintos(app: FastAPI, e: Entorno, veces: int, *, ip=IP, direcciones=None):
    """Un fallo por par distinto (emails inexistentes), 20 s entre ellos (el ultimo no avanza)."""
    for i in range(veces):
        direccion = direcciones[i] if direcciones else ip
        respuesta = _login(app, direccion, email=f"nadie{i}@example.test", contrasena=OTRA_CONTRASENA)
        assert respuesta.status_code == 401
        if i < veces - 1:
            e.reloj.avanzar(timedelta(seconds=20))


def _bloqueada(respuesta, retry_after: int) -> None:
    assert respuesta.status_code == 429
    assert respuesta.json() == BLOQUEADO
    assert respuesta.headers["retry-after"] == str(retry_after)
    assert respuesta.headers["cache-control"] == "no-store"
    assert not any(NOMBRE_COOKIE in v for v in respuesta.headers.get_list("set-cookie"))


def _contar(e: Entorno, tabla: str) -> int:
    return e.db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


# --- bloqueo por cuenta -----------------------------------------------------------------------------


def test_sexto_intento_responde_429_con_retry_after_840_sin_verificar_ni_crear_sesion(
    app: FastAPI, entorno: Entorno
):
    _fallar(app, entorno, 5, paso=timedelta(minutes=2))  # t5 = t0 + 8 min
    entorno.reloj.avanzar(timedelta(minutes=1))
    llamadas = entorno.verificador.llamadas

    respuesta = _login(app)

    _bloqueada(respuesta, 840)
    assert entorno.verificador.llamadas == llamadas
    assert _contar(entorno, "sesion") == 0


def test_a_los_15_minutos_del_quinto_fallo_el_login_correcto_responde_200(app: FastAPI, entorno: Entorno):
    _fallar(app, entorno, 5, paso=timedelta(minutes=2))
    entorno.reloj.avanzar(timedelta(minutes=15) - timedelta(seconds=1))
    _bloqueada(_login(app), 1)

    entorno.reloj.avanzar(timedelta(seconds=1))

    assert _login(app).status_code == 200


def test_fallos_fuera_de_la_ventana_no_cuentan_y_el_login_correcto_responde_200(
    app: FastAPI, entorno: Entorno
):
    _fallar(app, entorno, 4)
    entorno.reloj.avanzar(timedelta(minutes=20))
    _fallar(app, entorno, 1)
    entorno.reloj.avanzar(timedelta(minutes=1))

    assert _login(app).status_code == 200


def test_los_logins_bloqueados_no_prolongan_el_bloqueo_y_a_los_15_minutos_responde_200(
    app: FastAPI, entorno: Entorno
):
    _fallar(app, entorno, 5, paso=timedelta(minutes=1))  # t5 = t0 + 4 min
    quinto = entorno.reloj.ahora()

    for _ in range(3):
        entorno.reloj.avanzar(timedelta(minutes=1))
        assert _login(app).status_code == 429
    assert _contar(entorno, "intento_login") == 5

    entorno.reloj.avanzar(quinto + timedelta(minutes=15) - entorno.reloj.ahora())
    assert _login(app).status_code == 200


# --- el exito reinicia la cuenta pero no la IP ----------------------------------------------------------


def test_fallos_previos_descartados_tras_un_exito_por_http(app: FastAPI, entorno: Entorno):
    _fallar(app, entorno, 4)
    entorno.reloj.avanzar(PASO)
    assert _login(app).status_code == 200
    entorno.reloj.avanzar(PASO)
    _fallar(app, entorno, 4)
    entorno.reloj.avanzar(PASO)

    assert _login(app).status_code == 200


def test_el_exito_responde_200_y_marca_los_fallos_del_par_sin_borrarlos(app: FastAPI, entorno: Entorno):
    _fallar(app, entorno, 3)
    for i in range(2):
        assert _login(app, email=f"otro{i}@example.test", contrasena=OTRA_CONTRASENA).status_code == 401

    assert _login(app).status_code == 200

    filas = entorno.db.execute(
        text("SELECT clave_cuenta, descartado_para_cuenta FROM intento_login ORDER BY id")
    ).all()
    clave_par = clave_de_cuenta(CLAVE_HMAC, "ficticio-a", EMAIL)
    assert len(filas) == 5
    assert [f.descartado_para_cuenta for f in filas if bytes(f.clave_cuenta) == clave_par] == [True] * 3
    assert [f.descartado_para_cuenta for f in filas if bytes(f.clave_cuenta) != clave_par] == [False] * 2


def test_el_exito_no_reinicia_el_contador_de_ip_y_el_siguiente_login_responde_429(
    app: FastAPI, entorno: Entorno
):
    _fallar(app, entorno, 4)  # 4 del par
    entorno.reloj.avanzar(PASO)
    for i in range(25):  # el resto, de otros pares
        assert _login(app, email=f"nadie{i}@example.test", contrasena=OTRA_CONTRASENA).status_code == 401
        entorno.reloj.avanzar(timedelta(seconds=10))
    assert _contar(entorno, "intento_login") == 29

    exito = _login(app)
    assert exito.status_code == 200
    assert _contar(entorno, "intento_login") == 29  # siguen registrados los 29 fallos previos
    assert _login(app, email="nadie-final@example.test", contrasena=OTRA_CONTRASENA).status_code == 401

    siguiente = _login(app, codigo="ficticio-b", email=EMAIL, contrasena=CONTRASENA_B)

    assert siguiente.status_code == 429
    assert siguiente.json() == BLOQUEADO


# --- cuentas inexistentes y aislamiento del par ----------------------------------------------------------


@pytest.mark.parametrize(
    "codigo,email",
    [("ficticio-a", "nadie@example.test"), ("no-existe", EMAIL)],
    ids=["email-inexistente", "consultorio-inexistente"],
)
def test_cuenta_inexistente_cinco_401_y_el_sexto_429(app: FastAPI, entorno: Entorno, codigo: str, email: str):
    primeras = [_login(app, codigo=codigo, email=email, contrasena=OTRA_CONTRASENA) for _ in range(5)]
    sexta = _login(app, codigo=codigo, email=email, contrasena=OTRA_CONTRASENA)

    assert [r.status_code for r in primeras] == [401] * 5
    assert all(r.json() == RECHAZO_LOGIN for r in primeras)
    _bloqueada(sexta, 900)


def test_el_bloqueo_de_un_par_no_afecta_al_mismo_email_en_otro_consultorio_ni_a_otro_usuario(
    app: FastAPI, entorno: Entorno
):
    crear_usuario(
        entorno.db,
        entorno.a,
        email="otra.ficticia@example.test",
        nombre="Otra",
        credencial=hash_rapido(CONTRASENA_A),
    )
    entorno.db.commit()
    _fallar(app, entorno, 5)
    assert _login(app).status_code == 429

    en_otro_consultorio = _login(app, codigo="ficticio-b", email=EMAIL, contrasena=CONTRASENA_B)
    otro_usuario = _login(app, email="otra.ficticia@example.test")

    assert en_otro_consultorio.status_code == 200
    assert otro_usuario.status_code == 200


# --- limite por IP -------------------------------------------------------------------------------------


def test_rociado_de_30_pares_desde_una_ip_responde_429_con_retry_after_840_sin_verificar(
    app: FastAPI, entorno: Entorno
):
    _fallar_en_pares_distintos(app, entorno, 30)
    entorno.reloj.avanzar(timedelta(minutes=1))
    llamadas = entorno.verificador.llamadas

    respuesta = _login(app)  # par sin fallos, contrasena correcta

    _bloqueada(respuesta, 840)
    assert entorno.verificador.llamadas == llamadas


def test_por_debajo_del_limite_por_ip_el_login_correcto_responde_200(app: FastAPI, entorno: Entorno):
    _fallar_en_pares_distintos(app, entorno, 29)
    entorno.reloj.avanzar(timedelta(minutes=1))

    assert _login(app).status_code == 200


def test_otra_direccion_no_queda_afectada_por_el_bloqueo_de_ip(app: FastAPI, entorno: Entorno):
    _fallar_en_pares_distintos(app, entorno, 30)
    entorno.reloj.avanzar(timedelta(minutes=1))
    assert _login(app).status_code == 429

    assert _login(app, "203.0.113.8").status_code == 200


def test_fin_del_bloqueo_por_ip_sin_prolongacion(app: FastAPI, entorno: Entorno):
    _fallar_en_pares_distintos(app, entorno, 30)
    t30 = entorno.reloj.ahora()
    for _ in range(5):
        entorno.reloj.avanzar(timedelta(minutes=1))
        assert _login(app).status_code == 429

    entorno.reloj.avanzar(t30 + timedelta(minutes=15) - entorno.reloj.ahora())

    assert _login(app).status_code == 200


def test_red_compartida_dos_usuarios_legitimos_reciben_429_y_desde_otra_direccion_200(
    app: FastAPI, entorno: Entorno
):
    crear_usuario(
        entorno.db,
        entorno.a,
        email="otra.ficticia@example.test",
        nombre="Otra",
        credencial=hash_rapido(CONTRASENA_A),
    )
    entorno.db.commit()
    _fallar_en_pares_distintos(app, entorno, 30)
    entorno.reloj.avanzar(timedelta(minutes=1))

    primero = _login(app)
    segundo = _login(app, email="otra.ficticia@example.test")

    assert (primero.status_code, segundo.status_code) == (429, 429)
    assert _login(app, "203.0.113.8").status_code == 200


def test_ipv6_se_agrupa_por_prefijo_64_por_http(app: FastAPI, entorno: Entorno):
    direcciones = [f"2001:db8:1:2::{n:x}" for n in range(1, 31)]
    assert direcciones[-1] == "2001:db8:1:2::1e"
    _fallar_en_pares_distintos(app, entorno, 30, direcciones=direcciones)
    entorno.reloj.avanzar(timedelta(minutes=1))

    mismo_prefijo = _login(app, "2001:db8:1:2:ffff:ffff:ffff:ffff")
    otro_prefijo = _login(app, "2001:db8:1:3::1")

    assert mismo_prefijo.status_code == 429
    assert otro_prefijo.status_code == 200


def test_ipv4_mapeada_cuenta_como_la_ipv4_por_http(app: FastAPI, entorno: Entorno):
    _fallar_en_pares_distintos(app, entorno, 30, ip="::ffff:203.0.113.7")
    entorno.reloj.avanzar(timedelta(minutes=1))

    assert _login(app, "203.0.113.7").status_code == 429

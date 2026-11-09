"""Endpoints de autenticacion con la app REAL y `db-test` (tarea 8.1; DD-23, DD-24, DD-30).

`TestClient` con `base_url="https://testserver"` (para que httpx envie la cookie `Secure`) y la
direccion del cliente inyectada de forma explicita (`203.0.113.7`); toda peticion `POST` lleva
`Origin` permitido y `Content-Type: application/json` salvo en los escenarios de rechazo.
"""

import re
from http.cookies import SimpleCookie

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.claves import token_csrf
from app.auth.cookies import NOMBRE_COOKIE
from tests.integration.app_auth import ORIGEN, crear_app_real, settings_de_prueba
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
CREDENCIALES = {"codigo_consultorio": "ficticio-a", "email": EMAIL, "contrasena": CONTRASENA_A}
CUERPO_A = {
    "usuario": {"nombre": "Persona A", "email": EMAIL, "rol": "secretaria"},
    "consultorio": {"nombre": "Consultorio Ficticio A"},
}
BASE64URL_43 = re.compile(r"^[A-Za-z0-9_-]{43}$")


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


@pytest.fixture
def cliente(entorno: Entorno) -> TestClient:
    return TestClient(
        crear_app_real(entorno), base_url="https://testserver", client=("203.0.113.7", 50000)
    )


def _login(cliente: TestClient, headers: dict | None = None, **cuerpo):
    datos = {**CREDENCIALES, **cuerpo}
    return cliente.post(
        "/api/auth/login", json=datos, headers={"Origin": ORIGEN, **(headers or {})}
    )


def _atributos(respuesta) -> SimpleCookie:
    cookies = SimpleCookie()
    for valor in respuesta.headers.get_list("set-cookie"):
        cookies.load(valor)
    return cookies


def _valor_cookie(respuesta) -> str:
    return _atributos(respuesta)[NOMBRE_COOKIE].value


def _contar(entorno: Entorno, tabla: str, where: str = "true") -> int:
    return entorno.db.execute(text(f"SELECT count(*) FROM {tabla} WHERE {where}")).scalar_one()


# --- Inicio de sesion exitoso ---------------------------------------------------------------------


def test_login_exitoso_responde_200_emite_la_cookie_y_crea_una_sesion(
    entorno: Entorno, cliente: TestClient
):
    respuesta = _login(cliente)

    assert respuesta.status_code == 200
    assert NOMBRE_COOKIE in _atributos(respuesta)
    assert _contar(entorno, "sesion", f"usuario_id = '{entorno.ua}' AND revocada_en IS NULL") == 1
    assert _contar(entorno, "sesion") == 1


def test_el_cuerpo_del_login_es_exactamente_la_identidad_minima(entorno: Entorno, cliente: TestClient):
    respuesta = _login(cliente)

    assert respuesta.json() == CUERPO_A
    texto = respuesta.text
    assert _valor_cookie(respuesta) not in texto
    assert "$argon2" not in texto
    for identificador in (entorno.ua, entorno.a, entorno.ub, entorno.b):
        assert str(identificador) not in texto


def test_la_cookie_de_sesion_tiene_los_atributos_por_defecto(cliente: TestClient):
    respuesta = _login(cliente)

    cookie = _atributos(respuesta)[NOMBRE_COOKIE]
    assert BASE64URL_43.match(cookie.value)
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"
    assert cookie["secure"]
    assert cookie["path"] == "/"
    assert cookie["max-age"] == "43200"
    assert cookie["domain"] == ""


def test_la_cookie_sin_secure_solo_se_emite_en_local_explicito(entorno: Entorno):
    app = crear_app_real(entorno, settings_de_prueba(APP_ENV="local", AUTH_COOKIE_SECURE=False))
    cliente = TestClient(app, base_url="https://testserver", client=("203.0.113.7", 50000))

    respuesta = _login(cliente)

    cookie = _atributos(respuesta)[NOMBRE_COOKIE]
    assert cookie["secure"] == ""
    assert cookie["httponly"] and cookie["samesite"] == "Lax" and cookie["path"] == "/"
    assert cookie["max-age"] == "43200"


def test_dos_logins_emiten_cookies_y_tokens_csrf_distintos(cliente: TestClient):
    primero = _login(cliente)
    cliente.cookies.clear()
    segundo = _login(cliente)

    assert _valor_cookie(primero) != _valor_cookie(segundo)
    assert BASE64URL_43.match(_valor_cookie(segundo))
    assert primero.headers["x-csrf-token"] != segundo.headers["x-csrf-token"]


def test_el_login_entrega_el_token_csrf_por_cabecera_derivado_de_la_sesion(
    entorno: Entorno, cliente: TestClient
):
    respuesta = _login(cliente)

    sesion_id = entorno.sesiones()[0].id
    csrf = respuesta.headers["x-csrf-token"]
    assert csrf == token_csrf(CLAVE_HMAC, sesion_id)
    assert csrf != _valor_cookie(respuesta)
    assert csrf not in respuesta.text


def test_las_respuestas_del_login_no_son_almacenables(cliente: TestClient):
    assert _login(cliente).headers["cache-control"] == "no-store"


def test_el_codigo_y_el_email_se_normalizan(cliente: TestClient):
    respuesta = _login(
        cliente, codigo_consultorio=" FICTICIO-A ", email=" Persona.Ficticia@Example.TEST "
    )

    assert respuesta.status_code == 200


def test_json_con_charset_utf8_se_acepta(cliente: TestClient):
    respuesta = cliente.post(
        "/api/auth/login",
        content=(
            b'{"codigo_consultorio": "ficticio-a", "email": "persona.ficticia@example.test",'
            b' "contrasena": "contrasena-ficticia-a1"}'
        ),
        headers={"Origin": ORIGEN, "Content-Type": "application/json; charset=utf-8"},
    )

    assert respuesta.status_code == 200


def test_la_contrasena_solo_se_normaliza_con_nfkc(cliente: TestClient):
    # Ni mayusculas ni un espacio final: la contrasena no se transforma mas alla de NFKC.
    assert _login(cliente, contrasena=CONTRASENA_A.upper()).status_code == 401
    assert _login(cliente, contrasena=CONTRASENA_A + " ").status_code == 401
    assert _login(cliente).status_code == 200


def test_nfkc_compuesta_y_descompuesta_son_equivalentes_al_verificar(
    entorno: Entorno, cliente: TestClient
):
    compuesta = "contraseña-de-prueba-ñ1"
    descompuesta = "contraseña-de-prueba-ñ1"
    crear_usuario(
        entorno.db,
        entorno.a,
        email="otra.ficticia@example.test",
        nombre="Otra",
        credencial=hash_rapido(compuesta),
    )
    entorno.db.commit()

    respuesta = _login(cliente, email="otra.ficticia@example.test", contrasena=descompuesta)

    assert respuesta.status_code == 200


def test_el_login_no_aplica_la_politica_de_contrasenas_nuevas(entorno: Entorno, cliente: TestClient):
    corta = "doce-ficticia"[:12]
    crear_usuario(
        entorno.db,
        entorno.a,
        email="corta.ficticia@example.test",
        nombre="Corta",
        credencial=hash_rapido(corta),
    )
    entorno.db.commit()

    assert _login(cliente, email="corta.ficticia@example.test", contrasena=corta).status_code == 200
    de_3 = _login(cliente, email="corta.ficticia@example.test", contrasena="abc")
    de_20 = _login(cliente, email="corta.ficticia@example.test", contrasena="x" * 20)
    assert (de_3.status_code, de_3.json()) == (401, RECHAZO_LOGIN)
    assert (de_20.status_code, de_20.json()) == (401, RECHAZO_LOGIN)


def test_la_cuenta_es_la_del_par_codigo_email_y_no_la_de_otro_consultorio(cliente: TestClient):
    cruzada = _login(cliente, codigo_consultorio="ficticio-a", contrasena=CONTRASENA_B)
    propia_de_b = _login(cliente, codigo_consultorio="ficticio-b", contrasena=CONTRASENA_B)

    assert (cruzada.status_code, cruzada.json()) == (401, RECHAZO_LOGIN)
    assert propia_de_b.status_code == 200
    assert propia_de_b.json()["consultorio"] == {"nombre": "Consultorio Ficticio B"}

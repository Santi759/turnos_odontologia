"""Pruebas de `app.auth.claves` (tarea 3.1; DD-02 y DD-19)."""

import re
import secrets
import uuid

import pytest

from app.auth import claves
from app.auth.claves import DireccionClienteNoDeterminable

CLAVE = secrets.token_bytes(48)
OTRA_CLAVE = secrets.token_bytes(48)
FORMATO_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")


# --- token de sesion -------------------------------------------------------


def test_el_token_tiene_43_caracteres_base64url_y_cambia_en_cada_llamada():
    tokens = {claves.generar_token() for _ in range(50)}

    assert len(tokens) == 50
    assert all(FORMATO_TOKEN.match(t) for t in tokens)


@pytest.mark.parametrize("token", ["A" * 43, "a-_" * 14 + "a", secrets.token_urlsafe(32)])
def test_formatos_de_token_validos(token):
    assert claves.token_valido(token)


@pytest.mark.parametrize(
    "token",
    ["", "A" * 42, "A" * 44, "A" * 42 + "+", "A" * 42 + "=", "A" * 42 + " ", "ñ" * 43, None, 43, "A" * 42 + "\n"],
)
def test_formatos_de_token_invalidos(token):
    assert not claves.token_valido(token)


# --- HMAC con etiquetas de dominio ----------------------------------------


def test_hmac_de_sesion_tiene_32_bytes_y_es_determinista():
    token = claves.generar_token()

    assert len(claves.hmac_de_token(CLAVE, token)) == 32
    assert claves.hmac_de_token(CLAVE, token) == claves.hmac_de_token(CLAVE, token)


def test_hmac_de_sesion_depende_del_token_y_de_la_clave():
    token = claves.generar_token()

    assert claves.hmac_de_token(CLAVE, token) != claves.hmac_de_token(CLAVE, claves.generar_token())
    assert claves.hmac_de_token(CLAVE, token) != claves.hmac_de_token(OTRA_CLAVE, token)


def test_las_etiquetas_de_dominio_separan_los_valores_derivados():
    # Mismos bytes de entrada, distinta etiqueta: nunca coinciden.
    texto = "c-aaaaaaaaaaaa"
    sesion = claves.hmac_de_token(CLAVE, texto)
    cuenta = claves.clave_de_cuenta(CLAVE, texto, "")
    ip = claves.clave_de_ip(CLAVE, texto)

    assert len({sesion, cuenta, ip}) == 3
    assert all(len(v) == 32 for v in (sesion, cuenta, ip))


# --- token CSRF ------------------------------------------------------------


def test_token_csrf_es_determinista_por_sesion_y_distinto_entre_sesiones():
    sesion_a, sesion_b = uuid.uuid4(), uuid.uuid4()

    assert claves.token_csrf(CLAVE, sesion_a) == claves.token_csrf(CLAVE, sesion_a)
    assert claves.token_csrf(CLAVE, sesion_a) != claves.token_csrf(CLAVE, sesion_b)
    assert claves.token_csrf(CLAVE, sesion_a) != claves.token_csrf(OTRA_CLAVE, sesion_a)
    assert FORMATO_TOKEN.match(claves.token_csrf(CLAVE, sesion_a))


def test_token_csrf_difiere_del_token_de_sesion_y_de_su_hmac():
    sesion = uuid.uuid4()
    csrf = claves.token_csrf(CLAVE, sesion)
    token = claves.generar_token()

    assert csrf != token
    assert csrf != claves.hmac_de_token(CLAVE, csrf).hex()
    assert csrf != claves.hmac_de_token(CLAVE, sesion.hex)


# --- claves de intentos ----------------------------------------------------


def test_clave_de_cuenta_normaliza_codigo_y_email():
    base = claves.clave_de_cuenta(CLAVE, "ficticio-a", "persona@example.test")

    assert claves.clave_de_cuenta(CLAVE, "  FICTICIO-A ", " Persona@Example.TEST  ") == base


def test_clave_de_cuenta_distingue_pares_y_no_confunde_la_frontera():
    base = claves.clave_de_cuenta(CLAVE, "ficticio-a", "x@example.test")

    assert claves.clave_de_cuenta(CLAVE, "ficticio-b", "x@example.test") != base
    assert claves.clave_de_cuenta(CLAVE, "ficticio-a", "y@example.test") != base
    # El separador impide que ("ab", "c") y ("a", "bc") produzcan la misma clave.
    assert claves.clave_de_cuenta(CLAVE, "ab", "c") != claves.clave_de_cuenta(CLAVE, "a", "bc")
    assert claves.clave_de_cuenta(OTRA_CLAVE, "ficticio-a", "x@example.test") != base


def test_clave_de_ip_depende_de_la_ip_normalizada():
    assert claves.clave_de_ip(CLAVE, "v4:203.0.113.7") == claves.clave_de_ip(CLAVE, "v4:203.0.113.7")
    assert claves.clave_de_ip(CLAVE, "v4:203.0.113.7") != claves.clave_de_ip(CLAVE, "v4:203.0.113.8")


# --- normalizacion de la direccion del cliente ----------------------------


@pytest.mark.parametrize(
    ("host", "esperado"),
    [
        ("203.0.113.7", "v4:203.0.113.7"),
        ("198.51.100.250", "v4:198.51.100.250"),
        ("::ffff:203.0.113.7", "v4:203.0.113.7"),
        ("::FFFF:198.51.100.9", "v4:198.51.100.9"),
        ("2001:db8:1:2::1", "v6:2001:db8:1:2::/64"),
        ("2001:db8:1:2:ffff:ffff:ffff:ffff", "v6:2001:db8:1:2::/64"),
        ("2001:DB8:1:3::1", "v6:2001:db8:1:3::/64"),
    ],
)
def test_normalizacion_de_direcciones(host, esperado):
    assert claves.normalizar_ip(host) == esperado


def test_dos_direcciones_del_mismo_prefijo_64_comparten_baldes_y_otro_prefijo_no():
    a = claves.normalizar_ip("2001:db8:1:2::1")
    b = claves.normalizar_ip("2001:db8:1:2:1234::99")
    c = claves.normalizar_ip("2001:db8:1:9::1")

    assert a == b
    assert a != c


@pytest.mark.parametrize(
    "host", [None, "", " ", "testclient", "localhost", "unix:/run/x.sock", "203.0.113.256", "2001:db8::g", "203.0.113.7/24"]
)
def test_direccion_no_determinable_lanza_error_sin_devolver_balde(host):
    with pytest.raises(DireccionClienteNoDeterminable):
        claves.normalizar_ip(host)


def test_el_error_de_direccion_no_incluye_el_valor_recibido():
    with pytest.raises(DireccionClienteNoDeterminable) as excinfo:
        claves.normalizar_ip("nombre-de-host-ficticio")

    assert "nombre-de-host-ficticio" not in str(excinfo.value)

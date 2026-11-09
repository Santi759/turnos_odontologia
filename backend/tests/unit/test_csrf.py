"""Reglas puras de Origin, Content-Type y token CSRF (tarea 7.2; DA-11, DD-08, DD-30)."""

import hmac
import secrets
import uuid

import pytest

from app.auth import dependencias
from app.auth.claves import token_csrf
from app.core.config import Settings

PERMITIDOS = ["http://localhost:5173", "http://127.0.0.1:5173"]


# --- Origin ---------------------------------------------------------------------------------


@pytest.mark.parametrize("origen", PERMITIDOS)
def test_cada_origen_configurado_se_acepta_con_igualdad_exacta(origen: str):
    assert dependencias.origen_permitido(origen, PERMITIDOS) is True


@pytest.mark.parametrize(
    "origen",
    [
        None,
        "",
        "null",
        "http://otro-origen.invalid",
        "http://localhost:5173/",
        "http://LOCALHOST:5173",
        "HTTP://localhost:5173",
        "http://localhost:5173 ",
        " http://localhost:5173",
        "https://localhost:5173",
        "http://localhost:5174",
        "http://localhost",
        "*",
    ],
)
def test_todo_origen_que_no_es_identico_se_rechaza(origen: str | None):
    assert dependencias.origen_permitido(origen, PERMITIDOS) is False


# --- Content-Type ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "valor",
    [
        "application/json",
        "Application/JSON",
        "APPLICATION/JSON",
        "application/json; charset=utf-8",
        "application/json;charset=utf-8",
        "application/json; charset=UTF-8",
        "application/json ; charset=\"utf-8\"",
    ],
)
def test_json_admitido_con_a_lo_sumo_charset_utf8(valor: str):
    assert dependencias.tipo_de_medio_json(valor) is True


@pytest.mark.parametrize(
    "valor",
    [
        None,
        "",
        "text/plain",
        "application/x-www-form-urlencoded",
        "multipart/form-data; boundary=x",
        "application/jsonx",
        "application/json-patch+json",
        "application/json; charset=latin-1",
        "application/json; boundary=x",
        "application/json; charset=utf-8; x=1",
        "application/json; charset=utf-8; charset=utf-8",
        "application/json,text/plain",
        "text/plain; application/json",
    ],
)
def test_todo_otro_tipo_de_medio_se_rechaza(valor: str | None):
    assert dependencias.tipo_de_medio_json(valor) is False


# --- token CSRF -----------------------------------------------------------------------------


def test_el_token_csrf_de_la_sesion_coincide_y_los_demas_no():
    clave = secrets.token_bytes(48)
    sesion, otra = uuid.uuid4(), uuid.uuid4()
    valido = token_csrf(clave, sesion)
    alterado = valido[:-1] + ("A" if valido[-1] != "A" else "B")

    assert dependencias.token_csrf_coincide(clave, sesion, valido) is True
    assert dependencias.token_csrf_coincide(clave, sesion, alterado) is False
    assert dependencias.token_csrf_coincide(clave, sesion, token_csrf(clave, otra)) is False
    assert dependencias.token_csrf_coincide(secrets.token_bytes(48), sesion, valido) is False
    assert dependencias.token_csrf_coincide(clave, sesion, None) is False
    assert dependencias.token_csrf_coincide(clave, sesion, "") is False


def test_la_comparacion_del_token_csrf_usa_compare_digest(monkeypatch: pytest.MonkeyPatch):
    llamadas: list[tuple[object, object]] = []
    original = hmac.compare_digest

    def espia(a, b):
        llamadas.append((a, b))
        return original(a, b)

    monkeypatch.setattr(hmac, "compare_digest", espia)
    clave, sesion = secrets.token_bytes(48), uuid.uuid4()

    assert dependencias.token_csrf_coincide(clave, sesion, token_csrf(clave, sesion)) is True
    assert len(llamadas) == 1


def test_un_token_con_caracteres_no_ascii_no_lanza_error():
    assert dependencias.token_csrf_coincide(secrets.token_bytes(48), uuid.uuid4(), "ñandú") is False


# --- sin interruptores ---------------------------------------------------------------------------


def test_ningun_campo_de_configuracion_desactiva_origin_csrf_ni_json():
    campos = set(Settings.model_fields)
    sospechosos = ("csrf", "bypass", "disable", "skip", "insecure", "debug", "permisivo", "testing")

    assert [c for c in campos if any(s in c.lower() for s in sospechosos)] == []
    booleanos = {c for c, f in Settings.model_fields.items() if f.annotation is bool}
    assert booleanos == {"auth_cookie_secure"}

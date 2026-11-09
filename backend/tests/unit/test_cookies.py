"""Cookie de sesion (tarea 7.1; DA-12): atributos de emision y de borrado."""

import secrets
from http.cookies import SimpleCookie

import pytest
from fastapi import Response

from app.auth.claves import generar_token
from app.auth.cookies import (
    NOMBRE_COOKIE,
    borrar_cookie,
    emitir_cookie,
    valor_cookie_borrada,
    valor_cookie_sesion,
)
from app.core.config import Settings


def _settings(monkeypatch: pytest.MonkeyPatch, *, secure: bool = True, horas: int = 12) -> Settings:
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true" if secure else "false")
    return Settings(
        DATABASE_URL="postgresql+psycopg://app:app@db:5432/turnos",
        CORS_ALLOWED_ORIGINS="http://localhost:5173",
        APP_ENV="local",
        AUTH_SECRET_KEY=secrets.token_urlsafe(48),
        AUTH_SESSION_MAX_HOURS=horas,
    )


def _atributos(valor: str) -> tuple[str, str, set[str], dict[str, str]]:
    """(nombre, valor, banderas, atributos clave=valor) de una cabecera Set-Cookie."""
    partes = [parte.strip() for parte in valor.split(";")]
    nombre, _, contenido = partes[0].partition("=")
    banderas = {p.lower() for p in partes[1:] if "=" not in p}
    pares = {p.split("=")[0].lower(): p.split("=", 1)[1] for p in partes[1:] if "=" in p}
    return nombre, contenido, banderas, pares


def test_cookie_de_sesion_con_los_atributos_por_defecto(monkeypatch: pytest.MonkeyPatch):
    token = generar_token()

    nombre, contenido, banderas, pares = _atributos(valor_cookie_sesion(token, _settings(monkeypatch)))

    assert (nombre, contenido) == (NOMBRE_COOKIE, token) == ("turnos_session", token)
    assert banderas == {"httponly", "secure"}
    assert pares == {"max-age": "43200", "path": "/", "samesite": "Lax"}
    assert "domain" not in pares


@pytest.mark.parametrize("horas", [1, 12, 24])
def test_max_age_es_el_maximo_absoluto_en_segundos(monkeypatch: pytest.MonkeyPatch, horas: int):
    valor = valor_cookie_sesion(generar_token(), _settings(monkeypatch, horas=horas))

    assert _atributos(valor)[3]["max-age"] == str(horas * 3600)


def test_cookie_sin_secure_solo_con_configuracion_explicita(monkeypatch: pytest.MonkeyPatch):
    valor = valor_cookie_sesion(generar_token(), _settings(monkeypatch, secure=False))

    _, _, banderas, pares = _atributos(valor)
    assert banderas == {"httponly"}
    assert pares == {"max-age": "43200", "path": "/", "samesite": "Lax"}


def test_el_borrado_conserva_los_atributos_y_pone_max_age_cero(monkeypatch: pytest.MonkeyPatch):
    for secure in (True, False):
        nombre, contenido, banderas, pares = _atributos(
            valor_cookie_borrada(_settings(monkeypatch, secure=secure))
        )

        assert (nombre, contenido) == (NOMBRE_COOKIE, "")
        assert pares == {"max-age": "0", "path": "/", "samesite": "Lax"}
        assert banderas == ({"httponly", "secure"} if secure else {"httponly"})


def test_emitir_y_borrar_agregan_cabeceras_set_cookie_analizables(monkeypatch: pytest.MonkeyPatch):
    settings = _settings(monkeypatch)
    token = generar_token()
    respuesta = Response()

    emitir_cookie(respuesta, token, settings)
    borrar_cookie(respuesta, settings)

    cabeceras = respuesta.headers.getlist("set-cookie")
    assert cabeceras == [valor_cookie_sesion(token, settings), valor_cookie_borrada(settings)]
    analizada = SimpleCookie()
    analizada.load(cabeceras[0])
    assert analizada[NOMBRE_COOKIE].value == token
    assert analizada[NOMBRE_COOKIE]["httponly"] is True
    assert analizada[NOMBRE_COOKIE]["samesite"] == "Lax"

"""Recorrido de TODAS las rutas registradas en la app real (tarea 8.3; RN-AU-01, DA-11, DD-18).

Una ruta nueva que no exija identidad, `Origin` o token CSRF rompe estas pruebas: no hay forma de
publicarla por descuido. La lista blanca es exacta y depende de `APP_ENV`.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.routing import Route

from app.auth.cookies import NOMBRE_COOKIE
from app.auth.dependencias import identidad_actual
from tests.integration.app_auth import ORIGEN, crear_app_real, settings_de_prueba
from tests.integration.datos_auth import CONTRASENA_A, EMAIL, Entorno
from tests.rutas import aplanar, depende_de

NO_AUTENTICADO = {"detail": "No autenticado."}
RECHAZADA = {"detail": "Solicitud rechazada."}
METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}
LISTA_BLANCA_TEST = {("GET", "/api/health"), ("POST", "/api/auth/login")}
LISTA_BLANCA_LOCAL = LISTA_BLANCA_TEST | {
    ("GET", "/docs"),
    ("GET", "/redoc"),
    ("GET", "/openapi.json"),
}
CREDENCIALES = {"codigo_consultorio": "ficticio-a", "email": EMAIL, "contrasena": CONTRASENA_A}


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


def _app(entorno: Entorno, app_env: str) -> FastAPI:
    return crear_app_real(entorno, settings_de_prueba(APP_ENV=app_env))


def _cliente(app: FastAPI) -> TestClient:
    return TestClient(app, base_url="https://testserver", client=("203.0.113.7", 50000))


def _depende_de_identidad(dependiente: Dependant) -> bool:
    return depende_de(dependiente, identidad_actual)


def _rutas(app: FastAPI) -> list[tuple[str, str, bool]]:
    """(metodo, ruta, requiere_identidad) de cada metodo de cada ruta; HEAD es implicito de GET."""
    rutas = []
    for ruta in aplanar(app.routes):
        dependiente = getattr(ruta, "dependant", None)
        assert dependiente is not None or isinstance(ruta, Route), f"ruta no contemplada: {ruta!r}"
        requiere = dependiente is not None and _depende_de_identidad(dependiente)
        for metodo in sorted(ruta.methods or ()):
            if metodo != "HEAD":
                rutas.append((metodo, ruta.path, requiere))
    return rutas


def _con_valores(ruta: str) -> str:
    """Reemplaza parametros de ruta (`{id}`) por un UUID: las rutas futuras con parametros se invocan igual."""
    partes = [str(uuid.uuid4()) if p.startswith("{") else p for p in ruta.split("/")]
    return "/".join(partes)


@pytest.mark.parametrize(
    "app_env,esperada", [("test", LISTA_BLANCA_TEST), ("local", LISTA_BLANCA_LOCAL)]
)
def test_la_lista_blanca_de_rutas_publicas_es_exacta(entorno: Entorno, app_env, esperada):
    app = _app(entorno, app_env)

    publicas = {(metodo, ruta) for metodo, ruta, requiere in _rutas(app) if not requiere}

    assert publicas == esperada
    assert "/docs/oauth2-redirect" not in {ruta for _, ruta, _ in _rutas(app)}


@pytest.mark.parametrize("app_env", ["test", "local"])
def test_toda_ruta_fuera_de_la_lista_blanca_responde_401_sin_cookie(entorno: Entorno, app_env):
    app = _app(entorno, app_env)
    cliente = _cliente(app)
    privadas = [(m, r) for m, r, requiere in _rutas(app) if requiere]
    assert privadas  # el recorrido no puede quedar vacio

    for metodo, ruta in privadas:
        respuesta = cliente.request(metodo, _con_valores(ruta), headers={"Origin": ORIGEN})

        assert respuesta.status_code == 401, (metodo, ruta)
        assert respuesta.json() == NO_AUTENTICADO, (metodo, ruta)


@pytest.mark.parametrize("app_env", ["test", "local"])
def test_toda_ruta_que_cambia_estado_responde_403_sin_origin(entorno: Entorno, app_env):
    app = _app(entorno, app_env)
    cliente = _cliente(app)
    cambian_estado = [(m, r) for m, r, _ in _rutas(app) if m not in METODOS_SEGUROS]
    assert ("POST", "/api/auth/login") in cambian_estado

    for metodo, ruta in cambian_estado:
        respuesta = cliente.request(metodo, _con_valores(ruta), headers={})

        assert respuesta.status_code == 403, (metodo, ruta)
        assert respuesta.json() == RECHAZADA, (metodo, ruta)


@pytest.mark.parametrize("app_env", ["test", "local"])
def test_toda_ruta_con_sesion_que_cambia_estado_responde_403_sin_token_csrf(entorno: Entorno, app_env):
    app = _app(entorno, app_env)
    cliente = _cliente(app)
    login = cliente.post("/api/auth/login", json=CREDENCIALES, headers={"Origin": ORIGEN})
    assert login.status_code == 200
    con_sesion = [
        (m, r) for m, r, requiere in _rutas(app) if requiere and m not in METODOS_SEGUROS
    ]
    assert ("POST", "/api/auth/logout") in con_sesion

    for metodo, ruta in con_sesion:
        respuesta = cliente.request(metodo, _con_valores(ruta), headers={"Origin": ORIGEN})

        assert respuesta.status_code == 403, (metodo, ruta)
        assert respuesta.json() == RECHAZADA, (metodo, ruta)
    # La sesion sigue valida: ninguna operacion se ejecuto.
    assert cliente.get("/api/auth/me").status_code == 200
    assert NOMBRE_COOKIE in cliente.cookies


def test_health_sigue_publico_y_una_ruta_inexistente_sigue_en_404(entorno: Entorno):
    cliente = _cliente(_app(entorno, "test"))

    assert cliente.get("/api/health").json() == {"status": "ok"}
    assert cliente.get("/api/no-existe").status_code == 404

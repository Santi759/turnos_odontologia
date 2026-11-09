"""Datos sensibles fuera de respuestas y registros (tarea 8.4; X1, DD-25).

`caplog` en DEBUG captura TODOS los registros del proceso durante un login fallido, uno exitoso, uno
bloqueado, uno saturado, rechazos previos, `/me` y logout. Solo pueden aparecer codigos de evento fijos.
"""

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.cookies import NOMBRE_COOKIE
from tests.integration.app_auth import ORIGEN, ORIGEN_AJENO, crear_app_real, settings_de_prueba
from tests.integration.datos_auth import CONTRASENA_A, EMAIL, Entorno

DIRECCION = "203.0.113.7"
CREDENCIALES = {"codigo_consultorio": "ficticio-a", "email": EMAIL, "contrasena": CONTRASENA_A}
INCORRECTA = {**CREDENCIALES, "contrasena": "otra-contrasena-ficticia", "email": "nadie@example.test"}


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


@pytest.fixture
def settings():
    return settings_de_prueba()


@pytest.fixture
def cliente(entorno: Entorno, settings) -> TestClient:
    app = crear_app_real(entorno, settings)
    return TestClient(app, base_url="https://testserver", client=(DIRECCION, 50000))


def _mensajes(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records]


def _post(cliente: TestClient, cuerpo: dict, **headers):
    return cliente.post("/api/auth/login", json=cuerpo, headers={"Origin": ORIGEN, **headers})


def test_un_login_rechazado_registra_solo_el_codigo_fijo_login_rechazado(
    cliente: TestClient, caplog: pytest.LogCaptureFixture
):
    caplog.set_level(logging.DEBUG)

    assert _post(cliente, INCORRECTA).status_code == 401

    assert "login_rechazado" in _mensajes(caplog)


def test_un_login_saturado_registra_solo_el_codigo_fijo_verificacion_saturada(
    entorno: Entorno, cliente: TestClient, caplog: pytest.LogCaptureFixture
):
    caplog.set_level(logging.DEBUG)
    for _ in range(4):
        assert entorno.limitador.semaforo.acquire(timeout=0)
    try:
        assert _post(cliente, CREDENCIALES).status_code == 503
    finally:
        for _ in range(4):
            entorno.limitador.semaforo.release()

    assert "verificacion_saturada" in _mensajes(caplog)


def test_ningun_registro_ni_respuesta_contiene_datos_sensibles(
    entorno: Entorno, cliente: TestClient, settings, caplog: pytest.LogCaptureFixture
):
    caplog.set_level(logging.DEBUG)
    respuestas = []

    respuestas.append(_post(cliente, INCORRECTA))  # fallido
    exitoso = _post(cliente, CREDENCIALES)  # exitoso
    respuestas.append(exitoso)
    token = exitoso.cookies[NOMBRE_COOKIE]
    csrf = exitoso.headers["x-csrf-token"]
    respuestas.append(cliente.get("/api/auth/me"))
    respuestas.append(_post(cliente, CREDENCIALES, Origin=ORIGEN_AJENO))  # 403
    respuestas.append(
        cliente.post("/api/auth/login", content=b"{}", headers={"Origin": ORIGEN})  # 415
    )
    respuestas.append(_post(cliente, {**CREDENCIALES, "consultorio_id": "x"}))  # 422
    respuestas.append(cliente.post("/api/auth/logout", headers={"Origin": ORIGEN, "X-CSRF-Token": csrf}))
    cliente.cookies.clear()
    for _ in range(5):  # hasta bloquear el par
        respuestas.append(_post(cliente, INCORRECTA))
    respuestas.append(_post(cliente, CREDENCIALES))  # 429 por la IP o por el par? (otro par: 401/200)
    for _ in range(4):
        assert entorno.limitador.semaforo.acquire(timeout=0)
    try:
        respuestas.append(_post(cliente, {**CREDENCIALES, "email": "otra@example.test"}))  # 503
    finally:
        for _ in range(4):
            entorno.limitador.semaforo.release()
    respuestas.append(_post(cliente, INCORRECTA))  # 429 del par bloqueado
    assert {429, 503} <= {r.status_code for r in respuestas}

    sensibles = [
        CONTRASENA_A,
        "otra-contrasena-ficticia",
        EMAIL,
        "nadie@example.test",
        "otra@example.test",
        "ficticio-a",
        token,
        csrf,
        "$argon2",
        settings.auth_secret_key.get_secret_value(),
        DIRECCION,
    ]
    registros = "\n".join(_mensajes(caplog) + [r.exc_text or "" for r in caplog.records])
    cuerpos_y_cabeceras = "\n".join(
        r.text + "\n".join(f"{k}: {v}" for k, v in r.headers.items() if k.lower() not in {"set-cookie", "x-csrf-token"})
        for r in respuestas
    )
    for valor in sensibles:
        assert valor not in registros, f"un registro contiene un dato sensible ({len(valor)} caracteres)"
    # Las respuestas nunca reflejan contrasena, hash, clave ni la direccion.
    for valor in (CONTRASENA_A, "otra-contrasena-ficticia", "$argon2", settings.auth_secret_key.get_secret_value(), DIRECCION):
        assert valor not in cuerpos_y_cabeceras

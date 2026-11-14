"""Consultorio enviado por el cliente con la app real (tarea 8.2; DD-18, PD-02, X1, spec `validacion-entrada`).

La app real (`crear_app`) sobre la transaccion revertible de la fixture `sesion`. Datos ficticios (D1).
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.cookies import NOMBRE_COOKIE
from tests.integration.app_auth import ORIGEN, crear_app_de_prueba, crear_app_real
from tests.integration.datos_auth import CONTRASENA_A, EMAIL, Entorno

CONSULTORIO_A = "Consultorio Ficticio A"


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


@pytest.fixture
def cliente(entorno: Entorno) -> TestClient:
    return TestClient(
        crear_app_real(entorno), base_url="https://testserver", client=("203.0.113.7", 50000)
    )


def _cookie(iniciada) -> dict[str, str]:
    return {"Cookie": f"{NOMBRE_COOKIE}={iniciada.token}"}


def _contar(entorno: Entorno, tabla: str) -> int:
    return entorno.db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


def test_me_con_consultorio_id_en_la_query_responde_422_sin_ejecutar_la_ruta(
    entorno: Entorno, cliente: TestClient
):
    iniciada = entorno.login()
    ultimo_uso = entorno.db.execute(text("SELECT ultimo_uso_en FROM sesion")).scalar_one()
    entorno.reloj.avanzar(timedelta(minutes=5))

    respuesta = cliente.get(
        "/api/auth/me", params={"consultorio_id": str(entorno.b)}, headers=_cookie(iniciada)
    )

    assert respuesta.status_code == 422
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json()["detail"][0]["loc"] == ["query", "consultorio_id"]
    assert str(entorno.b) not in respuesta.text
    assert "x-csrf-token" not in respuesta.headers  # la ruta no se ejecuto
    # Tampoco se resolvio la identidad: la sesion no se renovo.
    assert entorno.db.execute(text("SELECT ultimo_uso_en FROM sesion")).scalar_one() == ultimo_uso


@pytest.mark.parametrize("cabecera", ["X-Consultorio-Id", "x-consultorio-id", "X-CONSULTORIO-ID"])
def test_me_con_la_cabecera_x_consultorio_id_responde_422_sin_el_valor(
    entorno: Entorno, cliente: TestClient, cabecera
):
    iniciada = entorno.login()

    respuesta = cliente.get(
        "/api/auth/me", headers={**_cookie(iniciada), cabecera: str(entorno.b)}
    )

    assert respuesta.status_code == 422
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json()["detail"][0]["loc"] == ["header", "X-Consultorio-Id"]
    assert str(entorno.b) not in respuesta.text


@pytest.mark.parametrize("cabecera", ["X-Consultorio", "Consultorio-Id", "X-Tenant-Id", "X-Request-Id"])
def test_otras_cabeceras_se_ignoran_y_la_identidad_es_la_de_a(
    entorno: Entorno, cliente: TestClient, cabecera
):
    iniciada = entorno.login()

    respuesta = cliente.get(
        "/api/auth/me", headers={**_cookie(iniciada), cabecera: str(entorno.b)}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["consultorio"]["nombre"] == CONSULTORIO_A
    assert respuesta.json()["usuario"]["email"] == EMAIL


def test_health_con_un_parametro_cualquiera_responde_200_y_con_consultorio_id_422(
    cliente: TestClient,
):
    assert cliente.get("/api/health", params={"otro": "1"}).status_code == 200
    assert cliente.get("/api/health", params={"Consultorio_ID": "1"}).status_code == 422


@pytest.mark.parametrize("cabecera", ["x-consultorio-id", "X-CONSULTORIO-ID"])
def test_health_con_la_cabecera_en_cualquier_mayuscula_responde_422(cliente: TestClient, cabecera):
    assert cliente.get("/api/health", headers={cabecera: "1"}).status_code == 422


def test_login_correcto_con_la_cabecera_prohibida_responde_422_sin_sesion_ni_intento(
    entorno: Entorno, cliente: TestClient
):
    sesiones, intentos = _contar(entorno, "sesion"), _contar(entorno, "intento_login")
    verificaciones = entorno.verificador.llamadas

    respuesta = cliente.post(
        "/api/auth/login",
        json={"codigo_consultorio": "ficticio-a", "email": EMAIL, "contrasena": CONTRASENA_A},
        headers={"Origin": ORIGEN, "X-Consultorio-Id": str(entorno.b)},
    )

    assert respuesta.status_code == 422
    assert respuesta.headers["cache-control"] == "no-store"
    assert "set-cookie" not in respuesta.headers
    assert (_contar(entorno, "sesion"), _contar(entorno, "intento_login")) == (sesiones, intentos)
    assert entorno.verificador.llamadas == verificaciones


def test_el_422_del_consultorio_precede_al_403_de_origen_en_el_login(
    entorno: Entorno, cliente: TestClient
):
    respuesta = cliente.post(
        "/api/auth/login",
        json={},
        headers={"Origin": "http://otro-origen.invalid", "X-Consultorio-Id": str(entorno.b)},
    )

    assert respuesta.status_code == 422


def test_sin_los_datos_prohibidos_el_login_sigue_su_orden_de_c03(entorno: Entorno, cliente: TestClient):
    ajeno = cliente.post("/api/auth/login", json={}, headers={"Origin": "http://otro-origen.invalid"})
    correcto = cliente.post(
        "/api/auth/login",
        json={"codigo_consultorio": "ficticio-a", "email": EMAIL, "contrasena": CONTRASENA_A},
        headers={"Origin": ORIGEN},
    )

    assert ajeno.status_code == 403
    assert correcto.status_code == 200


def test_la_app_de_pruebas_tambien_registra_la_dependencia_global(entorno: Entorno):
    app_prueba = crear_app_de_prueba(entorno)
    cliente_prueba = TestClient(app_prueba.app, base_url="https://testserver")
    iniciada = entorno.login()

    respuesta = cliente_prueba.get(
        "/prueba/identidad", headers={**_cookie(iniciada), "X-Consultorio-Id": str(entorno.b)}
    )

    assert respuesta.status_code == 422

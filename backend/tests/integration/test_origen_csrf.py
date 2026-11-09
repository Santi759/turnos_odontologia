"""Origin, Content-Type JSON y token CSRF en las dependencias (tarea 7.2; DA-11, DD-07, DD-08, DD-30)."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.cookies import NOMBRE_COOKIE
from tests.integration.app_auth import ORIGEN, ORIGEN_AJENO, AppDePrueba, crear_app_de_prueba
from tests.integration.datos_auth import CONTRASENA_A, EMAIL, Entorno

RECHAZADA = {"detail": "Solicitud rechazada."}
TIPO_NO_ADMITIDO = {"detail": "Tipo de contenido no admitido."}
CREDENCIALES = {"codigo_consultorio": "ficticio-a", "email": EMAIL, "contrasena": CONTRASENA_A}
CUERPO = json.dumps(CREDENCIALES).encode()
JSON = {"Content-Type": "application/json"}


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


@pytest.fixture
def app_prueba(entorno: Entorno) -> AppDePrueba:
    return crear_app_de_prueba(entorno)


@pytest.fixture
def cliente(app_prueba: AppDePrueba) -> TestClient:
    return TestClient(app_prueba.app, base_url="https://testserver", client=("203.0.113.7", 50000))


def _cookie(token: str) -> dict[str, str]:
    return {"Cookie": f"{NOMBRE_COOKIE}={token}"}


def _contar(entorno: Entorno, tabla: str) -> int:
    return entorno.db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


def _sin_efectos(entorno: Entorno) -> None:
    assert _contar(entorno, "sesion") == 0
    assert _contar(entorno, "intento_login") == 0
    assert entorno.verificador.llamadas == 0


# --- Origin obligatorio y exacto ------------------------------------------------------------------


@pytest.mark.parametrize(
    "cabeceras",
    [
        {},
        {"Origin": "null"},
        {"Origin": ORIGEN_AJENO},
        {"Origin": ORIGEN + "/"},
        {"Origin": "http://LOCALHOST:5173"},
        {"Referer": ORIGEN + "/login"},
        {"Origin": ORIGEN_AJENO, "Content-Type": "application/x-www-form-urlencoded"},
    ],
    ids=["sin-origin", "null", "ajeno", "barra-final", "mayusculas", "solo-referer", "formulario-ajeno"],
)
def test_login_con_origin_ausente_o_no_permitido_responde_403_sin_efectos(
    entorno: Entorno, cliente: TestClient, cabeceras: dict[str, str]
):
    respuesta = cliente.post("/prueba/login", content=CUERPO, headers={**JSON, **cabeceras})

    assert respuesta.status_code == 403
    assert respuesta.json() == RECHAZADA
    assert respuesta.headers["cache-control"] == "no-store"
    assert "set-cookie" not in respuesta.headers
    _sin_efectos(entorno)


def test_login_con_origin_permitido_continua(entorno: Entorno, cliente: TestClient):
    respuesta = cliente.post("/prueba/login", content=CUERPO, headers={**JSON, "Origin": ORIGEN})

    assert respuesta.status_code == 200
    assert _contar(entorno, "sesion") == 1


def test_con_dos_cabeceras_origin_se_rechaza(entorno: Entorno, cliente: TestClient):
    respuesta = cliente.post(
        "/prueba/login", content=CUERPO, headers=[("Content-Type", "application/json"), ("Origin", ORIGEN), ("Origin", ORIGEN)]
    )

    assert respuesta.status_code == 403
    _sin_efectos(entorno)


# --- Content-Type JSON ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cabeceras",
    [
        {"Content-Type": "text/plain"},
        {"Content-Type": "application/x-www-form-urlencoded"},
        {"Content-Type": "multipart/form-data; boundary=x"},
        {},
    ],
    ids=["text-plain", "formulario", "multipart", "sin-content-type"],
)
def test_login_con_content_type_no_json_responde_415_sin_efectos(
    entorno: Entorno, cliente: TestClient, cabeceras: dict[str, str]
):
    respuesta = cliente.post("/prueba/login", content=CUERPO, headers={"Origin": ORIGEN, **cabeceras})

    assert respuesta.status_code == 415
    assert respuesta.json() == TIPO_NO_ADMITIDO
    assert respuesta.headers["cache-control"] == "no-store"
    _sin_efectos(entorno)


def test_json_con_charset_utf8_se_acepta(entorno: Entorno, cliente: TestClient):
    respuesta = cliente.post(
        "/prueba/login",
        content=CUERPO,
        headers={"Origin": ORIGEN, "Content-Type": "application/json; charset=utf-8"},
    )

    assert respuesta.status_code == 200


def test_origin_se_valida_antes_que_el_content_type(entorno: Entorno, cliente: TestClient):
    respuesta = cliente.post("/prueba/login", content=CUERPO, headers={"Content-Type": "text/plain"})

    assert respuesta.status_code == 403


# --- logout y token CSRF ----------------------------------------------------------------------------


def test_logout_sin_origin_responde_403_y_la_sesion_sigue_valida(entorno: Entorno, app_prueba: AppDePrueba, cliente: TestClient):
    iniciada = entorno.login()

    respuesta = cliente.post(
        "/prueba/cerrar",
        headers={**_cookie(iniciada.token), "X-CSRF-Token": app_prueba.token_csrf(iniciada.sesion_id)},
    )

    assert respuesta.status_code == 403
    assert respuesta.json() == RECHAZADA
    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is not None


def test_logout_con_origin_y_token_validos_cierra_la_sesion(entorno: Entorno, app_prueba: AppDePrueba, cliente: TestClient):
    iniciada = entorno.login()

    respuesta = cliente.post(
        "/prueba/cerrar",
        headers={
            **_cookie(iniciada.token),
            "Origin": ORIGEN,
            "X-CSRF-Token": app_prueba.token_csrf(iniciada.sesion_id),
        },
    )

    assert respuesta.status_code == 204
    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is None


def _alterar(token: str) -> str:
    return token[:-1] + ("A" if token[-1] != "A" else "B")


def test_cambiar_estado_sin_token_o_con_token_incorrecto_responde_403_sin_cambios(
    entorno: Entorno, app_prueba: AppDePrueba, cliente: TestClient
):
    s1, s2 = entorno.login(), entorno.login()
    revocada = entorno.login()
    entorno.servicio.cerrar_sesion(entorno.db, revocada.sesion_id)
    propio = app_prueba.token_csrf(s1.sesion_id)
    token_de_otra = app_prueba.token_csrf(s2.sesion_id)
    token_de_revocada = app_prueba.token_csrf(revocada.sesion_id)

    for token in (None, "", _alterar(propio), token_de_otra, token_de_revocada):
        cabeceras = {**_cookie(s1.token), "Origin": ORIGEN}
        if token is not None:
            cabeceras["X-CSRF-Token"] = token
        respuesta = cliente.post("/prueba/cambia", headers=cabeceras)
        assert respuesta.status_code == 403, token
        assert respuesta.json() == RECHAZADA

    assert app_prueba.cambios == []
    assert entorno.servicio.resolver_identidad(entorno.db, s1.token) is not None
    assert entorno.servicio.resolver_identidad(entorno.db, s2.token) is not None


def test_cambiar_estado_con_token_valido_pero_origin_ajeno_o_ausente_responde_403(
    entorno: Entorno, app_prueba: AppDePrueba, cliente: TestClient
):
    iniciada = entorno.login()
    base = {**_cookie(iniciada.token), "X-CSRF-Token": app_prueba.token_csrf(iniciada.sesion_id)}

    for extra in ({"Origin": ORIGEN_AJENO}, {}):
        respuesta = cliente.post("/prueba/cambia", headers={**base, **extra})
        assert respuesta.status_code == 403
        assert respuesta.json() == RECHAZADA

    assert app_prueba.cambios == []


def test_cambiar_estado_con_origin_y_token_de_su_sesion_funciona(
    entorno: Entorno, app_prueba: AppDePrueba, cliente: TestClient
):
    iniciada = entorno.login()

    respuesta = cliente.post(
        "/prueba/cambia",
        headers={
            **_cookie(iniciada.token),
            "Origin": ORIGEN,
            "X-CSRF-Token": app_prueba.token_csrf(iniciada.sesion_id),
        },
    )

    assert respuesta.status_code == 200
    assert app_prueba.cambios == ["cambio"]


def test_cambiar_estado_sin_sesion_responde_401_pero_sin_origin_responde_403(
    cliente: TestClient,
):
    assert cliente.post("/prueba/cambia", headers={"Origin": ORIGEN}).status_code == 401
    assert cliente.post("/prueba/cambia").status_code == 403


def test_los_metodos_seguros_no_exigen_origin_ni_token(entorno: Entorno, cliente: TestClient):
    iniciada = entorno.login()

    respuesta = cliente.get("/prueba/identidad", headers=_cookie(iniciada.token))

    assert respuesta.status_code == 200

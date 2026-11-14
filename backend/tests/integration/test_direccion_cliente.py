"""Direccion del cliente no determinable (tarea 7.3; DD-19, PC-05, PD-10).

Las pruebas inyectan SIEMPRE la direccion con el parametro `client` de `TestClient` (direcciones de
documentacion); solo los escenarios de direccion no determinable usan `testclient` o `None` a proposito.
"""

import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import acceso_login
from app.auth.cookies import NOMBRE_COOKIE
from tests.integration.app_auth import ORIGEN, AppDePrueba, crear_app_de_prueba
from tests.integration.datos_auth import CONTRASENA_A, EMAIL, Entorno

NO_PROCESABLE = {"detail": "No se pudo procesar la solicitud."}
CREDENCIALES = {"codigo_consultorio": "ficticio-a", "email": EMAIL, "contrasena": CONTRASENA_A}
CUERPO = json.dumps(CREDENCIALES).encode()
JSON = {"Content-Type": "application/json", "Origin": ORIGEN}


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


@pytest.fixture
def app_prueba(entorno: Entorno) -> AppDePrueba:
    return crear_app_de_prueba(entorno)


def _cliente(app: FastAPI, direccion: tuple[str, int] | None) -> TestClient:
    return TestClient(app, base_url="https://testserver", client=direccion)


def _contar(entorno: Entorno, tabla: str) -> int:
    return entorno.db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


SIN_DIRECCION_DETERMINABLE = [
    None,
    ("testclient", 50000),
    ("", 50000),
    ("localhost", 50000),
    ("no-es-una-ip", 50000),
    ("203.0.113.256", 50000),
]


@pytest.mark.parametrize(
    "direccion", SIN_DIRECCION_DETERMINABLE, ids=["cliente-nulo", "testclient", "vacio", "nombre", "texto", "ipv4-invalida"]
)
def test_sin_direccion_determinable_el_login_responde_400_sin_buscar_ni_verificar_ni_registrar(
    entorno: Entorno,
    app_prueba: AppDePrueba,
    monkeypatch: pytest.MonkeyPatch,
    direccion,
):
    busquedas: list[str] = []
    original = acceso_login.buscar_cuenta
    monkeypatch.setattr(
        acceso_login, "buscar_cuenta", lambda *a, **k: (busquedas.append("x"), original(*a, **k))[1]
    )

    respuesta = _cliente(app_prueba.app, direccion).post("/prueba/login", content=CUERPO, headers=JSON)

    assert respuesta.status_code == 400
    assert respuesta.json() == NO_PROCESABLE
    assert respuesta.headers["cache-control"] == "no-store"
    assert "set-cookie" not in respuesta.headers
    assert busquedas == []
    assert entorno.verificador.llamadas == 0
    assert _contar(entorno, "intento_login") == 0
    assert _contar(entorno, "sesion") == 0


def test_x_forwarded_for_no_se_usa_como_direccion(entorno: Entorno, app_prueba: AppDePrueba):
    cabeceras = {**JSON, "X-Forwarded-For": "198.51.100.9", "X-Real-IP": "198.51.100.9", "Forwarded": "for=198.51.100.9"}

    sin_cliente = _cliente(app_prueba.app, None).post("/prueba/login", content=CUERPO, headers=cabeceras)
    con_cliente = _cliente(app_prueba.app, ("203.0.113.7", 50000)).post(
        "/prueba/login", content=CUERPO, headers=cabeceras
    )

    assert sin_cliente.status_code == 400
    assert con_cliente.status_code == 200
    assert con_cliente.json() == {"ip": "v4:203.0.113.7"}


@pytest.mark.parametrize(
    ("direccion", "normalizada"),
    [
        ("203.0.113.7", "v4:203.0.113.7"),
        ("2001:db8:1:2::1", "v6:2001:db8:1:2::/64"),
        ("::ffff:203.0.113.7", "v4:203.0.113.7"),
    ],
)
def test_las_direcciones_ipv4_e_ipv6_validas_continuan(
    entorno: Entorno, app_prueba: AppDePrueba, direccion: str, normalizada: str
):
    respuesta = _cliente(app_prueba.app, (direccion, 50000)).post(
        "/prueba/login", content=CUERPO, headers=JSON
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ip": normalizada}
    assert entorno.verificador.llamadas == 1


def test_orden_de_rechazos_origin_antes_que_direccion_y_direccion_antes_que_content_type(
    entorno: Entorno, app_prueba: AppDePrueba
):
    sin_origin = _cliente(app_prueba.app, None).post(
        "/prueba/login", content=CUERPO, headers={"Content-Type": "application/json"}
    )
    sin_cliente_y_texto = _cliente(app_prueba.app, None).post(
        "/prueba/login", content=CUERPO, headers={"Origin": ORIGEN, "Content-Type": "text/plain"}
    )
    con_cliente_y_texto = _cliente(app_prueba.app, ("203.0.113.7", 50000)).post(
        "/prueba/login", content=CUERPO, headers={"Origin": ORIGEN, "Content-Type": "text/plain"}
    )

    assert (sin_origin.status_code, sin_cliente_y_texto.status_code, con_cliente_y_texto.status_code) == (
        403,
        400,
        415,
    )


def test_el_registro_tecnico_tiene_el_codigo_fijo_y_ningun_dato(
    entorno: Entorno, app_prueba: AppDePrueba, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.DEBUG):
        _cliente(app_prueba.app, ("no-es-una-ip", 50000)).post("/prueba/login", content=CUERPO, headers=JSON)

    mensajes = [registro.getMessage() for registro in caplog.records]
    assert any("direccion_cliente_no_determinable" in m for m in mensajes)
    texto = " ".join(mensajes) + " ".join(str(r.args) for r in caplog.records)
    for dato in (EMAIL, CONTRASENA_A, "ficticio-a", "no-es-una-ip"):
        assert dato not in texto


def test_me_y_logout_no_dependen_de_la_direccion(entorno: Entorno, app_prueba: AppDePrueba):
    iniciada = entorno.login()  # sesion obtenida desde 203.0.113.7
    cookie = {"Cookie": f"{NOMBRE_COOKIE}={iniciada.token}"}
    desde_testclient = _cliente(app_prueba.app, ("testclient", 50000))

    me = desde_testclient.get("/prueba/identidad", headers=cookie)
    salida = desde_testclient.post(
        "/prueba/cerrar",
        headers={**cookie, "Origin": ORIGEN, "X-CSRF-Token": app_prueba.token_csrf(iniciada.sesion_id)},
    )

    assert (me.status_code, salida.status_code) == (200, 204)


# --- 12.2: registro tecnico sin datos tambien cuando NO hay cliente (request.client es None) ---------


def _texto_de_los_registros(caplog: pytest.LogCaptureFixture) -> tuple[list[str], str]:
    mensajes = [registro.getMessage() for registro in caplog.records]
    texto = " ".join(mensajes) + " " + " ".join(
        f"{registro.args} {registro.exc_text}" for registro in caplog.records
    )
    return mensajes, texto


@pytest.mark.parametrize(
    "direccion",
    [None, ("testclient", 50000), ("", 50000), ("localhost", 50000)],
    ids=["sin-cliente", "testclient", "host-vacio", "localhost"],
)
def test_sin_direccion_el_registro_tecnico_es_el_codigo_fijo_y_no_contiene_datos(
    entorno: Entorno,
    app_prueba: AppDePrueba,
    caplog: pytest.LogCaptureFixture,
    direccion: tuple[str, int] | None,
):
    with caplog.at_level(logging.DEBUG):
        respuesta = _cliente(app_prueba.app, direccion).post(
            "/prueba/login", content=CUERPO, headers=JSON
        )

    assert respuesta.status_code == 400
    mensajes, texto = _texto_de_los_registros(caplog)
    assert sum("direccion_cliente_no_determinable" in m for m in mensajes) == 1
    datos = [EMAIL, CONTRASENA_A, "ficticio-a"] + ([direccion[0]] if direccion and direccion[0] else [])
    for dato in datos:
        assert dato not in texto
    assert entorno.verificador.llamadas == 0
    assert _contar(entorno, "intento_login") == 0


def test_login_real_sin_cliente_registra_solo_el_codigo_fijo(
    entorno: Entorno, caplog: pytest.LogCaptureFixture
):
    from tests.integration.app_auth import crear_app_real

    cliente = _cliente(crear_app_real(entorno), None)
    with caplog.at_level(logging.DEBUG):
        respuesta = cliente.post("/api/auth/login", content=CUERPO, headers=JSON)

    assert respuesta.status_code == 400
    assert respuesta.json() == NO_PROCESABLE
    mensajes, texto = _texto_de_los_registros(caplog)
    assert sum("direccion_cliente_no_determinable" in m for m in mensajes) == 1
    for dato in (EMAIL, CONTRASENA_A, "ficticio-a"):
        assert dato not in texto

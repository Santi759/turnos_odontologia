import pytest
from fastapi.testclient import TestClient

from app.main import crear_app


def test_origen_permitido_recibe_la_cabecera_cors(fabrica_settings):
    cliente = TestClient(crear_app(fabrica_settings(origenes="http://localhost:5173")))

    respuesta = cliente.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_origen_no_permitido_no_recibe_la_cabecera_cors(fabrica_settings):
    cliente = TestClient(crear_app(fabrica_settings(origenes="http://localhost:5173")))

    respuesta = cliente.get(
        "/api/health", headers={"Origin": "http://otro-origen.invalid"}
    )

    assert respuesta.status_code == 200
    assert "access-control-allow-origin" not in respuesta.headers


@pytest.mark.parametrize(
    "origen", ["http://localhost:5173", "http://127.0.0.1:5173"]
)
def test_cada_origen_configurado_es_permitido(fabrica_settings, origen):
    settings = fabrica_settings(
        origenes="http://localhost:5173,http://127.0.0.1:5173"
    )
    cliente = TestClient(crear_app(settings))

    respuesta = cliente.get("/api/health", headers={"Origin": origen})

    assert respuesta.headers["access-control-allow-origin"] == origen


def test_el_origen_permitido_recibe_credenciales(fabrica_settings):
    # Ajuste justificado por la delta `configuracion-backend` (autenticacion-sesion): antes
    # no se habilitaban credenciales; ahora la cookie de sesion exige `Allow-Credentials`.
    cliente = TestClient(crear_app(fabrica_settings()))

    respuesta = cliente.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert respuesta.headers["access-control-allow-credentials"] == "true"


def test_el_origen_ajeno_no_recibe_credenciales_ni_cabeceras_cors(fabrica_settings):
    cliente = TestClient(crear_app(fabrica_settings()))

    respuesta = cliente.get("/api/health", headers={"Origin": "http://otro-origen.invalid"})

    assert "access-control-allow-origin" not in respuesta.headers
    assert "access-control-allow-credentials" not in respuesta.headers


def _preflight(cliente, origen, metodo="POST", cabeceras="content-type, x-csrf-token"):
    return cliente.options(
        "/api/auth/login",
        headers={
            "Origin": origen,
            "Access-Control-Request-Method": metodo,
            "Access-Control-Request-Headers": cabeceras,
        },
    )


def _valores(respuesta, cabecera):
    return {v.strip().lower() for v in respuesta.headers.get(cabecera, "").split(",") if v.strip()}


def test_el_preflight_de_post_con_token_csrf_se_autoriza_con_credenciales(fabrica_settings):
    cliente = TestClient(crear_app(fabrica_settings()))

    respuesta = _preflight(cliente, "http://localhost:5173")

    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert respuesta.headers["access-control-allow-credentials"] == "true"
    assert {"x-csrf-token", "content-type"} <= _valores(respuesta, "access-control-allow-headers")


def test_los_metodos_autorizados_son_solo_get_y_post(fabrica_settings):
    cliente = TestClient(crear_app(fabrica_settings()))

    respuesta = _preflight(cliente, "http://localhost:5173")

    assert _valores(respuesta, "access-control-allow-methods") == {"get", "post"}


@pytest.mark.parametrize("metodo", ["PUT", "PATCH", "DELETE"])
def test_el_preflight_de_metodos_no_autorizados_se_rechaza(fabrica_settings, metodo):
    cliente = TestClient(crear_app(fabrica_settings()))

    respuesta = _preflight(cliente, "http://localhost:5173", metodo=metodo)

    assert respuesta.status_code == 400
    assert metodo.lower() not in _valores(respuesta, "access-control-allow-methods")


def test_el_preflight_desde_un_origen_ajeno_no_recibe_cabeceras_cors(fabrica_settings):
    cliente = TestClient(crear_app(fabrica_settings()))

    respuesta = _preflight(cliente, "http://otro-origen.invalid")

    assert "access-control-allow-origin" not in respuesta.headers
    assert "access-control-allow-credentials" not in respuesta.headers


def test_el_preflight_no_autoriza_cabeceras_no_declaradas(fabrica_settings):
    cliente = TestClient(crear_app(fabrica_settings()))

    respuesta = _preflight(cliente, "http://localhost:5173", cabeceras="x-consultorio-id")

    assert respuesta.status_code == 400
    assert "x-consultorio-id" not in _valores(respuesta, "access-control-allow-headers")


def test_se_exponen_x_csrf_token_y_retry_after(fabrica_settings):
    cliente = TestClient(crear_app(fabrica_settings()))

    respuesta = cliente.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert {"x-csrf-token", "retry-after"} <= _valores(respuesta, "access-control-expose-headers")

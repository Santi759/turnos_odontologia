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


def test_no_se_habilitan_credenciales(fabrica_settings):
    cliente = TestClient(crear_app(fabrica_settings()))

    respuesta = cliente.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert "access-control-allow-credentials" not in respuesta.headers

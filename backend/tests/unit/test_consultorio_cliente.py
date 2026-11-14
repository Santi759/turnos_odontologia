"""`rechazar_consultorio_del_cliente` (tarea 8.1; DD-18, PD-02, X1, spec `validacion-entrada`).

Sin base: una app minima con la dependencia global. El 422 nunca refleja el valor enviado.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencias import rechazar_consultorio_del_cliente

ID_AJENO = "5f0b0b0e-1111-7222-8333-444455556666"


@pytest.fixture
def cliente() -> TestClient:
    app = FastAPI(dependencies=[Depends(rechazar_consultorio_del_cliente)])
    llamadas: list[str] = []

    @app.get("/ruta")
    def ruta() -> dict:
        llamadas.append("ruta")
        return {"ok": True}

    cliente = TestClient(app)
    cliente.llamadas = llamadas  # type: ignore[attr-defined]
    return cliente


@pytest.mark.parametrize(
    "parametro", ["consultorio_id", "Consultorio_ID", "CONSULTORIO_ID", "cOnSuLtOrIo_Id"]
)
def test_la_query_consultorio_id_se_rechaza_con_422_en_cualquier_variante(cliente, parametro):
    respuesta = cliente.get("/ruta", params={parametro: ID_AJENO})

    assert respuesta.status_code == 422
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "detail": [
            {
                "type": "consultorio_no_admitido",
                "loc": ["query", "consultorio_id"],
                "msg": "El consultorio no se acepta del cliente.",
            }
        ]
    }
    assert ID_AJENO not in respuesta.text
    assert cliente.llamadas == []


def test_la_query_con_valor_vacio_o_repetida_tambien_se_rechaza(cliente):
    assert cliente.get("/ruta?consultorio_id=").status_code == 422
    assert cliente.get("/ruta?otro=1&consultorio_id=1&consultorio_id=2").status_code == 422


@pytest.mark.parametrize("cabecera", ["X-Consultorio-Id", "x-consultorio-id", "X-CONSULTORIO-ID"])
def test_la_cabecera_x_consultorio_id_se_rechaza_con_422_en_cualquier_variante(cliente, cabecera):
    respuesta = cliente.get("/ruta", headers={cabecera: ID_AJENO})

    assert respuesta.status_code == 422
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.json() == {
        "detail": [
            {
                "type": "consultorio_no_admitido",
                "loc": ["header", "X-Consultorio-Id"],
                "msg": "El consultorio no se acepta del cliente.",
            }
        ]
    }
    assert ID_AJENO not in respuesta.text
    assert cliente.llamadas == []


@pytest.mark.parametrize(
    ("cabeceras", "params"),
    [
        ({"X-Consultorio": ID_AJENO}, {}),
        ({"Consultorio-Id": ID_AJENO}, {}),
        ({"X-Tenant-Id": ID_AJENO}, {}),
        ({"X-Request-Id": "prueba"}, {}),
        ({}, {"otro": "1"}),
        ({}, {"consultorio": ID_AJENO}),
        ({}, {"consultorio_ids": ID_AJENO}),
    ],
)
def test_otras_cabeceras_y_parametros_no_se_rechazan(cliente, cabeceras, params):
    respuesta = cliente.get("/ruta", headers=cabeceras, params=params)

    assert respuesta.status_code == 200
    assert cliente.llamadas == ["ruta"]


def test_sin_nada_la_ruta_se_ejecuta(cliente):
    assert cliente.get("/ruta").status_code == 200

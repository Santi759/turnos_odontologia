from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from app.main import crear_app


def test_health_responde_ok(fabrica_settings):
    cliente = TestClient(crear_app(fabrica_settings()))

    respuesta = cliente.get("/api/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_health_responde_ok_con_la_base_inaccesible(fabrica_settings):
    conexiones = []

    def registrar_intento(dialect, conn_rec, cargs, cparams):
        conexiones.append(cparams.get("host"))

    event.listen(Engine, "do_connect", registrar_intento)
    try:
        settings = fabrica_settings(
            database_url="postgresql+psycopg://app:app@host-inexistente.invalid:5432/turnos"
        )
        respuesta = TestClient(crear_app(settings)).get("/api/health")
    finally:
        event.remove(Engine, "do_connect", registrar_intento)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}
    assert conexiones == []


def test_ruta_no_declarada_bajo_api_responde_404(fabrica_settings):
    cliente = TestClient(crear_app(fabrica_settings()))

    assert cliente.get("/api/no-existe").status_code == 404
    assert cliente.get("/api/health/otra").status_code == 404


def test_el_instrumento_detecta_intentos_de_conexion():
    intentos = []

    def registrar_intento(dialect, conn_rec, cargs, cparams):
        intentos.append(cparams.get("host"))

    event.listen(Engine, "do_connect", registrar_intento)
    try:
        motor = create_engine(
            "postgresql+psycopg://app:app@host-inexistente.invalid:5432/turnos",
            connect_args={"connect_timeout": 2},
        )
        with pytest.raises(OperationalError):
            motor.connect()
    finally:
        event.remove(Engine, "do_connect", registrar_intento)

    assert intentos == ["host-inexistente.invalid"]

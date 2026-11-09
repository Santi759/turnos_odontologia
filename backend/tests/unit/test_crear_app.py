"""`crear_app` deja motor, fabrica de sesiones y servicio de autenticacion en `app.state` (8.5, DD-20).

Sin conectar a la base al crear la app ni al arrancarla (el health no usa la base).
"""

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.auth.servicio import ServicioAuth
from app.main import crear_app


def test_la_app_guarda_configuracion_motor_fabrica_y_servicio_en_su_estado(fabrica_settings):
    settings = fabrica_settings()

    app = crear_app(settings)

    assert getattr(app.state, "settings", None) is settings
    assert isinstance(getattr(app.state, "engine", None), Engine)
    assert getattr(app.state, "fabrica_sesiones", None) is not None
    assert isinstance(getattr(app.state, "servicio_auth", None), ServicioAuth)


def test_el_servicio_usa_la_clave_y_los_tiempos_de_la_configuracion(fabrica_settings):
    settings = fabrica_settings()

    servicio = getattr(crear_app(settings).state, "servicio_auth", None)

    assert servicio is not None
    assert servicio.config.clave_hmac == settings.auth_hmac_key
    assert servicio.config.minutos_inactividad == settings.auth_session_minutes
    assert servicio.config.horas_maximas == settings.auth_session_max_hours


def test_la_fabrica_de_sesiones_usa_el_motor_de_la_app(fabrica_settings):
    app = crear_app(fabrica_settings())

    fabrica = getattr(app.state, "fabrica_sesiones", None)
    assert fabrica is not None
    with fabrica() as sesion:
        assert sesion.get_bind() is app.state.engine


def test_cada_app_tiene_su_propio_estado(fabrica_settings):
    una = crear_app(fabrica_settings())
    otra = crear_app(fabrica_settings())

    servicio_una = getattr(una.state, "servicio_auth", None)
    servicio_otra = getattr(otra.state, "servicio_auth", None)
    assert servicio_una is not None and servicio_otra is not None
    assert servicio_una is not servicio_otra
    assert servicio_una.limitador is not servicio_otra.limitador
    assert una.state.engine is not otra.state.engine


def test_no_se_conecta_a_la_base_al_crear_ni_al_arrancar_la_app(fabrica_settings):
    conexiones: list[object] = []

    def registrar(dialect, conn_rec, cargs, cparams):
        conexiones.append(cparams.get("host"))

    event.listen(Engine, "do_connect", registrar)
    try:
        settings = fabrica_settings(
            database_url="postgresql+psycopg://app:app@host-inexistente.invalid:5432/turnos"
        )
        app = crear_app(settings)
        with TestClient(app) as cliente:  # ejecuta el arranque (lifespan) de la app
            assert cliente.get("/api/health").status_code == 200
    finally:
        event.remove(Engine, "do_connect", registrar)

    assert conexiones == []

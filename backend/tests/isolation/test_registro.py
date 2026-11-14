"""Registro de aislamiento obligatorio (tarea 9.2; DD-22, spec `pruebas-aislamiento`).

No abre conexiones: la app se construye sin conectar. Una ruta protegida sin entrada, o una entrada sin
ruta, hace fallar la verificacion nombrando metodo y ruta.
"""

import pytest
from fastapi import Depends, FastAPI

from app.auth.dependencias import identidad_actual
from app.main import crear_app
from tests.integration.app_auth import settings_de_prueba
from tests.isolation.registro import REGISTRO, RecursoPorId, SesionPropia, verificar_registro
from tests.rutas import rutas_que_dependen_de


def test_el_registro_coincide_exactamente_con_las_rutas_protegidas_de_la_app_real():
    app = crear_app(settings_de_prueba())

    protegidas = rutas_que_dependen_de(app, identidad_actual)

    assert protegidas == set(REGISTRO)
    assert protegidas == {("GET", "/api/auth/me"), ("POST", "/api/auth/logout")}
    verificar_registro(app)  # no lanza


def test_toda_entrada_declara_su_caso_con_justificacion_o_parametro():
    for (metodo, ruta), caso in REGISTRO.items():
        assert metodo and ruta.startswith("/api/")
        assert isinstance(caso, SesionPropia | RecursoPorId)
        if isinstance(caso, SesionPropia):
            assert caso.justificacion.strip()
        else:
            assert caso.parametro.strip() and "{" + caso.parametro + "}" in ruta


def test_una_ruta_protegida_extra_no_registrada_hace_fallar_la_verificacion():
    app = crear_app(settings_de_prueba())

    @app.get("/api/pacientes/{paciente_id}", dependencies=[Depends(identidad_actual)])
    def paciente(paciente_id: str) -> dict:
        return {}

    with pytest.raises(AssertionError) as error:
        verificar_registro(app)

    assert "GET /api/pacientes/{paciente_id}" in str(error.value)


def test_una_entrada_sin_ruta_hace_fallar_la_verificacion():
    app = crear_app(settings_de_prueba())
    registro = {**REGISTRO, ("DELETE", "/api/fantasma"): SesionPropia("entrada sin ruta")}

    with pytest.raises(AssertionError) as error:
        verificar_registro(app, registro)

    assert "DELETE /api/fantasma" in str(error.value)


def test_una_app_sin_rutas_protegidas_falla_por_todas_las_entradas():
    with pytest.raises(AssertionError) as error:
        verificar_registro(FastAPI())

    mensaje = str(error.value)
    assert "GET /api/auth/me" in mensaje and "POST /api/auth/logout" in mensaje

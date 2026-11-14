"""La conexion del rol de login solo la usa `POST /api/auth/login` (5.5, DD-28).

Recorrido de rutas de la app real (sin conectar) y pruebas estaticas sobre `app/`.
"""

import ast
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI

from app.auth.dependencias import obtener_sesion_login
from app.main import crear_app
from tests.rutas import rutas_que_dependen_de

APP = Path(__file__).resolve().parents[2] / "app"


def rutas_con_sesion_de_login(app: FastAPI) -> set[tuple[str, str]]:
    return rutas_que_dependen_de(app, obtener_sesion_login)


def test_en_la_app_real_solo_el_login_declara_la_sesion_de_login(fabrica_settings):
    app = crear_app(fabrica_settings())

    assert rutas_con_sesion_de_login(app) == {("POST", "/api/auth/login")}


def test_una_ruta_extra_con_la_sesion_de_login_hace_fallar_la_verificacion(fabrica_settings):
    app = crear_app(fabrica_settings())
    extra = APIRouter()

    @extra.get("/prueba/extra")
    def extra_ruta(_db=Depends(obtener_sesion_login)) -> dict:
        return {}

    app.include_router(extra)

    assert rutas_con_sesion_de_login(app) == {("POST", "/api/auth/login"), ("GET", "/prueba/extra")}


# --- Estaticas ---------------------------------------------------------------------------------


def _fuentes() -> dict[str, str]:
    return {
        ruta.relative_to(APP).as_posix(): ruta.read_text(encoding="utf-8")
        for ruta in APP.rglob("*.py")
    }


def test_el_motor_y_la_fabrica_de_login_solo_se_mencionan_en_main_y_dependencias():
    menciones = {
        ruta
        for ruta, fuente in _fuentes().items()
        if "engine_login" in fuente or "fabrica_sesiones_login" in fuente
    }

    # `database.py` define `crear_engine_login` y `crear_fabrica_de_sesiones_login`.
    assert menciones == {"main.py", "auth/dependencias.py", "core/database.py"}
    for ruta, fuente in _fuentes().items():
        if ruta not in ("main.py", "auth/dependencias.py", "core/database.py"):
            assert "app.state.engine_login" not in fuente, ruta


def _llamadas(nombre: str) -> set[str]:
    encontrados = set()
    for ruta, fuente in _fuentes().items():
        for nodo in ast.walk(ast.parse(fuente)):
            if isinstance(nodo, ast.Call):
                funcion = nodo.func
                llamado = funcion.id if isinstance(funcion, ast.Name) else getattr(funcion, "attr", None)
                if llamado == nombre:
                    encontrados.add(ruta)
    return encontrados


def test_crear_engine_login_solo_se_llama_desde_main():
    assert _llamadas("crear_engine_login") == {"main.py"}


def test_obtener_sesion_login_solo_se_importa_en_la_ruta_de_login():
    importadores = set()
    for ruta, fuente in _fuentes().items():
        for nodo in ast.walk(ast.parse(fuente)):
            if isinstance(nodo, ast.ImportFrom) and any(
                alias.name == "obtener_sesion_login" for alias in nodo.names
            ):
                importadores.add(ruta)

    assert importadores == {"api/auth.py"}


def test_database_login_url_solo_la_leen_la_configuracion_y_el_motor_de_login():
    lectores = {
        ruta
        for ruta, fuente in _fuentes().items()
        if "database_login_url" in fuente or "DATABASE_LOGIN_URL" in fuente
    }

    # `main.py` pasa la configuracion a `crear_engine_login`; `migraciones.py` valida URLs distintas.
    assert lectores <= {"core/config.py", "core/database.py", "core/migraciones.py", "main.py"}
    assert "core/database.py" in lectores


def test_los_comandos_locales_no_usan_el_rol_de_login():
    for ruta, fuente in _fuentes().items():
        if ruta.startswith(("seed/", "credenciales/", "mantenimiento/", "roles_postgres/")):
            for prohibido in ("engine_login", "obtener_sesion_login", "acceso_login", "database_login_url"):
                assert prohibido not in fuente, (ruta, prohibido)

"""Pruebas estaticas de los modulos de acceso (5.4, DD-26, DD-28; spec `acceso-previo-al-contexto`).

Recorren `app/` con `ast` y texto, sin ejecutar nada: quien puede importar cada modulo, donde esta el
unico `UPDATE usuario SET credencial` y que ninguna ruta ni modulo de autenticacion escribe credenciales.
"""

import ast
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "app"


def _modulos() -> dict[str, Path]:
    return {
        ".".join(ruta.relative_to(RAIZ).with_suffix("").parts): ruta
        for ruta in APP.rglob("*.py")
    }


def _importa(ruta: Path, modulo: str) -> bool:
    """Si el archivo importa `modulo` (`import app.x.y`, `from app.x import y`, `from app.x.y import z`)."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    paquete, _, hoja = modulo.rpartition(".")
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            if any(alias.name == modulo for alias in nodo.names):
                return True
        elif isinstance(nodo, ast.ImportFrom) and nodo.module is not None:
            if nodo.module == modulo:
                return True
            if nodo.module == paquete and any(alias.name == hoja for alias in nodo.names):
                return True
    return False


def _importadores(modulo: str) -> set[str]:
    return {
        nombre
        for nombre, ruta in _modulos().items()
        if nombre != modulo and _importa(ruta, modulo)
    }


def test_acceso_admin_solo_lo_importan_los_comandos_locales():
    importadores = _importadores("app.auth.acceso_admin")

    assert importadores
    for nombre in importadores:
        assert nombre.startswith(
            ("app.credenciales.", "app.mantenimiento.", "app.seed.")
        ), nombre


def test_acceso_login_solo_lo_importan_servicio_e_intentos():
    assert _importadores("app.auth.acceso_login") == {"app.auth.servicio", "app.auth.intentos"}


def test_acceso_previo_solo_lo_importa_el_servicio():
    assert _importadores("app.auth.acceso_previo") == {"app.auth.servicio"}


@pytest.mark.parametrize("modulo", ["app.auth.acceso_admin", "app.auth.acceso_login", "app.auth.acceso_previo"])
def test_los_modulos_de_acceso_no_se_importan_entre_si(modulo):
    ruta = _modulos()[modulo]
    for otro in ("app.auth.acceso_admin", "app.auth.acceso_login", "app.auth.acceso_previo"):
        if otro != modulo:
            assert not _importa(ruta, otro), (modulo, otro)


_ESCRIBE_CREDENCIAL = re.compile(
    r"(UPDATE\s+usuario\s+SET[^;\"']*credencial|INSERT\s+INTO\s+usuario[^;\"']*credencial)",
    re.IGNORECASE,
)


def test_el_unico_update_de_credencial_de_la_aplicacion_esta_en_acceso_admin():
    escriben = {
        nombre
        for nombre, ruta in _modulos().items()
        if _ESCRIBE_CREDENCIAL.search(ruta.read_text(encoding="utf-8"))
    }

    assert escriben == {"app.auth.acceso_admin"}


def test_ninguna_ruta_ni_modulo_de_autenticacion_importa_acceso_admin():
    for nombre, ruta in _modulos().items():
        if nombre.startswith(("app.api.", "app.auth.")):
            assert not _importa(ruta, "app.auth.acceso_admin"), nombre


def test_el_login_no_hashea_ni_decide_rehash():
    servicio = (APP / "auth" / "servicio.py").read_text(encoding="utf-8")

    assert "hashear" not in servicio
    assert "necesita_rehash" not in servicio
    assert "escribir_credencial" not in servicio


def test_un_importador_inyectado_hace_fallar_la_verificacion(tmp_path):
    ajeno = tmp_path / "ajeno.py"
    ajeno.write_text("from app.auth import acceso_admin\n", encoding="utf-8")

    assert _importa(ajeno, "app.auth.acceso_admin") is True
    ajeno.write_text("import app.auth.acceso_admin\n", encoding="utf-8")
    assert _importa(ajeno, "app.auth.acceso_admin") is True
    ajeno.write_text("from app.auth import acceso_login\n", encoding="utf-8")
    assert _importa(ajeno, "app.auth.acceso_admin") is False

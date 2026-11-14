"""Sin comparaciones de rol dispersas (tarea 7.5; DD-16, spec `autorizacion-roles`).

Las decisiones de rol viven solo en `app/auth/autorizacion.py` (y la definicion del tipo en
`app/models/usuario.py`). Un detector AST busca comparaciones que involucren el rol de una identidad
o un valor de `Rol`; se valida contra codigo inyectado (control negativo) y contra el arbol real.
"""

import ast
from pathlib import Path

import pytest

RAIZ_APP = Path(__file__).resolve().parents[2] / "app"
PERMITIDOS = {RAIZ_APP / "auth" / "autorizacion.py", RAIZ_APP / "models" / "usuario.py"}
VALORES_DE_ROL = {"administrador", "secretaria", "odontologo"}


def _menciona_rol(nodo: ast.AST) -> bool:
    for sub in ast.walk(nodo):
        if isinstance(sub, ast.Attribute) and sub.attr == "rol":
            return True
        if isinstance(sub, ast.Name) and sub.id in {"rol", "Rol"}:
            return True
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value in VALORES_DE_ROL:
            return True
    return False


def comparaciones_de_rol(codigo: str) -> list[int]:
    """Numeros de linea de comparaciones (`==`, `!=`, `in`, `is`, ...) o `match` sobre un rol."""
    lineas: list[int] = []
    for nodo in ast.walk(ast.parse(codigo)):
        if isinstance(nodo, ast.Compare) and _menciona_rol(nodo):
            lineas.append(nodo.lineno)
        elif isinstance(nodo, ast.Match) and _menciona_rol(nodo.subject):
            lineas.append(nodo.lineno)
    return sorted(lineas)


@pytest.mark.parametrize(
    "codigo",
    [
        'if usuario.rol == "administrador":\n    pass',
        "if identidad.rol in (Rol.ADMINISTRADOR, Rol.SECRETARIA):\n    pass",
        "ok = identidad.rol is Rol.SECRETARIA",
        'ok = "odontologo" != actual',
        "if rol != otro:\n    pass",
        "match identidad.rol:\n    case _:\n        pass",
    ],
)
def test_el_detector_encuentra_comparaciones_de_rol(codigo):
    assert comparaciones_de_rol(codigo) != []


@pytest.mark.parametrize(
    "codigo",
    [
        "if total == 3:\n    pass",
        'if nombre == "administrador-de-consultorio-x" and False:\n    pass',
        "rol = Rol(valor)",
        "x = identidad.rol.value",
        "if estado in ('activo', 'inactivo'):\n    pass",
    ],
)
def test_el_detector_no_marca_codigo_sin_comparaciones_de_rol(codigo):
    assert comparaciones_de_rol(codigo) == []


def test_en_app_solo_el_mecanismo_de_autorizacion_compara_roles():
    hallazgos = {
        str(ruta.relative_to(RAIZ_APP)): lineas
        for ruta in sorted(RAIZ_APP.rglob("*.py"))
        if ruta not in PERMITIDOS and (lineas := comparaciones_de_rol(ruta.read_text(encoding="utf-8")))
    }

    assert hallazgos == {}


def test_el_mecanismo_de_autorizacion_si_compara_roles():
    # Control: el detector ve la comparacion que debe existir en el unico lugar permitido.
    assert comparaciones_de_rol((RAIZ_APP / "auth" / "autorizacion.py").read_text(encoding="utf-8")) != []

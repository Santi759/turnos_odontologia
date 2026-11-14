"""Lista blanca de lecturas de la peticion (tarea 8.3; DD-18, X1, spec `validacion-entrada`).

Un detector AST recorre `app/` y registra cada acceso a `request.headers`, `request.query_params` y
`request.cookies` (y a `scope["headers"]` / `scope["query_string"]`) como (modulo, coleccion, nombre
leido). El conjunto debe coincidir EXACTAMENTE con la lista blanca; ningun nombre que contenga
`consultorio` o `tenant` se lee fuera del rechazo. Un acceso nuevo (en un modulo inyectado) rompe la
verificacion. La identidad y el consultorio salen solo de la sesion (RN-MT-02).
"""

import ast
import importlib
from pathlib import Path

import pytest

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
RAIZ_APP = RAIZ_BACKEND / "app"
COLECCIONES = {"headers", "query_params", "cookies"}
BASES_DE_RESPUESTA = {"response", "respuesta", "mensaje"}
RECHAZO = "rechazar_consultorio_del_cliente"
DEPENDENCIAS = "app/auth/dependencias.py"

LISTA_BLANCA = {
    (DEPENDENCIAS, "headers", "'origin'"),
    (DEPENDENCIAS, "headers", "'content-type'"),
    (DEPENDENCIAS, "headers", "'x-csrf-token'"),
    (DEPENDENCIAS, "cookies", "NOMBRE_COOKIE"),
    (DEPENDENCIAS, "query_params", "<iteracion>"),
    (DEPENDENCIAS, "headers", "CABECERA_CONSULTORIO.casefold()"),
    ("app/api/auth.py", "cookies", "NOMBRE_COOKIE"),
}


def _padres(arbol: ast.AST) -> dict[ast.AST, ast.AST]:
    return {hijo: padre for padre in ast.walk(arbol) for hijo in ast.iter_child_nodes(padre)}


def _funcion_de(nodo: ast.AST, padres: dict[ast.AST, ast.AST]) -> str | None:
    while nodo in padres:
        nodo = padres[nodo]
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef):
            return nodo.name
    return None


def _nombre_leido(acceso: ast.Attribute, padres: dict[ast.AST, ast.AST]) -> str:
    padre = padres.get(acceso)
    if isinstance(padre, ast.Attribute) and isinstance(padres.get(padre), ast.Call):
        llamada = padres[padre]
        if llamada.func is padre and llamada.args:  # type: ignore[attr-defined]
            return ast.unparse(llamada.args[0])  # type: ignore[attr-defined]
        return "<llamada-sin-nombre>"
    if isinstance(padre, ast.Subscript):
        return ast.unparse(padre.slice)
    if isinstance(padre, ast.Compare) and acceso in padre.comparators:
        return ast.unparse(padre.left)
    if isinstance(padre, ast.comprehension | ast.For):
        return "<iteracion>"
    return "<otro>"


def lecturas(codigo: str, modulo: str) -> list[tuple[str, str, str, str | None]]:
    """(modulo, coleccion, nombre leido, funcion que lo lee) de cada acceso a la peticion."""
    arbol = ast.parse(codigo)
    padres = _padres(arbol)
    encontradas: list[tuple[str, str, str, str | None]] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Attribute) and nodo.attr in COLECCIONES:
            base = nodo.value
            if isinstance(base, ast.Name) and base.id in BASES_DE_RESPUESTA:
                continue  # cabeceras de la RESPUESTA, no de la peticion
            if isinstance(getattr(nodo, "ctx", None), ast.Store):
                continue
            encontradas.append(
                (modulo, nodo.attr, _nombre_leido(nodo, padres), _funcion_de(nodo, padres))
            )
        elif isinstance(nodo, ast.Subscript) and isinstance(nodo.slice, ast.Constant):
            if nodo.slice.value in {"headers", "query_string"} and _es_scope(nodo.value):
                encontradas.append((modulo, "scope", repr(nodo.slice.value), _funcion_de(nodo, padres)))
    return encontradas


def _es_scope(nodo: ast.AST) -> bool:
    return (isinstance(nodo, ast.Name) and nodo.id == "scope") or (
        isinstance(nodo, ast.Attribute) and nodo.attr == "scope"
    )


def lecturas_de_la_aplicacion() -> list[tuple[str, str, str, str | None]]:
    todas: list[tuple[str, str, str, str | None]] = []
    for ruta in sorted(RAIZ_APP.rglob("*.py")):
        relativa = ruta.relative_to(RAIZ_BACKEND).as_posix()
        todas.extend(lecturas(ruta.read_text(encoding="utf-8"), relativa))
    return todas


def _valor_resuelto(modulo: str, nombre_leido: str) -> str:
    """Si el nombre leido es un identificador, el valor de esa constante del modulo (o el mismo texto)."""
    if nombre_leido.isidentifier():
        importado = importlib.import_module(modulo.removesuffix(".py").replace("/", "."))
        return str(getattr(importado, nombre_leido, nombre_leido))
    return nombre_leido


def test_las_lecturas_de_la_peticion_coinciden_exactamente_con_la_lista_blanca():
    encontradas = {(m, c, n) for m, c, n, _f in lecturas_de_la_aplicacion()}

    assert encontradas == LISTA_BLANCA


def test_ninguna_lectura_fuera_del_rechazo_usa_un_nombre_de_consultorio_o_tenant():
    prohibidas = []
    for modulo, coleccion, nombre, funcion in lecturas_de_la_aplicacion():
        if funcion == RECHAZO:
            continue
        for texto in (nombre, _valor_resuelto(modulo, nombre)):
            if "consultorio" in texto.lower() or "tenant" in texto.lower():
                prohibidas.append((modulo, coleccion, nombre))

    assert prohibidas == []


def test_el_unico_lugar_que_toca_nombres_de_consultorio_es_el_rechazo():
    en_el_rechazo = [
        (m, c, n) for m, c, n, f in lecturas_de_la_aplicacion() if f == RECHAZO
    ]

    assert {m for m, _c, _n in en_el_rechazo} == {DEPENDENCIAS}
    assert {c for _m, c, _n in en_el_rechazo} == {"query_params", "headers"}


@pytest.mark.parametrize(
    "codigo",
    [
        'def f(request):\n    return request.headers.get("X-Consultorio")',
        'def f(request):\n    return request.headers["x-tenant-id"]',
        'def f(request):\n    return request.query_params.get("consultorio_id")',
        'def f(request):\n    return request.cookies.get("otra")',
        'def f(request):\n    return "x" in request.headers',
        'def f(request):\n    return dict(request.headers)',
        'def f(scope):\n    return scope["headers"]',
    ],
)
def test_un_acceso_nuevo_inyectado_en_un_modulo_rompe_la_verificacion(codigo):
    inyectadas = {(m, c, n) for m, c, n, _f in lecturas(codigo, "app/inyectado.py")}

    assert inyectadas != set()
    assert not inyectadas <= LISTA_BLANCA


def test_las_cabeceras_de_la_respuesta_no_cuentan_como_lecturas():
    codigo = 'def f(response):\n    response.headers["X-CSRF-Token"] = "x"\n    return response.headers'

    assert lecturas(codigo, "app/inyectado.py") == []


def test_un_nombre_inyectado_con_consultorio_fuera_del_rechazo_se_detecta():
    codigo = 'def f(request):\n    return request.headers.get("X-Consultorio")'

    inyectadas = lecturas(codigo, "app/inyectado.py")

    assert [(c, n) for _m, c, n, f in inyectadas if f != RECHAZO and "consultorio" in n.lower()]

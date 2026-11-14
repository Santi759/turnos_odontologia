"""Comando local de creacion de roles, tarea 6.1 (DD-15, spec `aislamiento-base-de-datos`).

Sin base: la sesion es un doble con lecturas guionadas y las contrasenas se inyectan. Ninguna
conexion real; las contrasenas son ficticias y nunca deben aparecer en la salida ni en el SQL.
"""

import secrets

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.core.roles_bd import ROL_ACCESO_LOGIN, ROL_ACCESO_PREVIO, ROL_APP, ROL_LOGIN
from app.roles_postgres.__main__ import main

URL_API = "postgresql+psycopg://turnos_app:clave-api-ficticia@host-api.invalid:5432/turnos"
URL_LOGIN = "postgresql+psycopg://turnos_login:clave-login-ficticia@host-login.invalid:5432/turnos"
URL_ADMIN = "postgresql+psycopg://app:clave-admin-ficticia@host-admin.invalid:5432/turnos"

CLAVE_A = "clave-ficticia-aaaaaaaa-1"
CLAVE_B = "clave-ficticia-bbbbbbbb-2"


def _entorno(monkeypatch, *, migracion: str | None = URL_ADMIN, app_env: str = "local") -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("DATABASE_URL", URL_API)
    monkeypatch.setenv("DATABASE_LOGIN_URL", URL_LOGIN)
    if migracion is None:
        monkeypatch.delenv("DATABASE_MIGRATION_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_MIGRATION_URL", migracion)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("AUTH_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")


class _Resultado:
    def __init__(self, filas):
        self._filas = filas

    def mappings(self):
        return self

    def one_or_none(self):
        return self._filas[0] if self._filas else None

    def scalar_one(self):
        return self._filas[0]


def _fila_de_rol(nombre: str, **cambios):
    base = {
        "rolname": nombre,
        "rolsuper": False,
        "rolbypassrls": False,
        "rolcreaterole": False,
        "rolcreatedb": False,
        "rolreplication": False,
        "rolcanlogin": nombre in (ROL_APP, ROL_LOGIN),
    }
    base.update(cambios)
    return base


class SesionDoble:
    """Doble de `Session`: lecturas guionadas, escrituras registradas."""

    def __init__(self, *, existentes=(), puede_crear=True, filas_a_medida=None, membresias=()):
        self.roles = {n: _fila_de_rol(n) for n in existentes}
        if filas_a_medida:
            self.roles.update(filas_a_medida)
        self.puede_crear = puede_crear
        self.membresias = set(membresias)
        self.escrituras: list[str] = []
        self.eventos: list[str] = []

    def execute(self, sentencia, parametros=None):
        sql = str(sentencia)
        if "puede_crear_roles" in sql:
            return _Resultado([self.puede_crear])
        if "pg_auth_members" in sql:
            return _Resultado([parametros["nombre"] in self.membresias])
        if "FROM pg_catalog.pg_roles" in sql:
            fila = self.roles.get(parametros["nombre"])
            return _Resultado([fila] if fila else [])
        raise AssertionError(f"lectura no prevista: {sql}")

    def connection(self):
        return self

    def exec_driver_sql(self, sentencia):
        self.escrituras.append(sentencia)

    def commit(self):
        self.eventos.append("commit")

    def rollback(self):
        self.eventos.append("rollback")

    def close(self):
        self.eventos.append("close")


def _cifrar(_sesion, rol: str, contrasena: str) -> str:
    return f"SCRAM-SHA-256$4096:c2FsdA==$c3RvcmVk{abs(hash(contrasena)) % 1000}:c2VydmVy"


def _terminal(*contrasenas: str):
    cola = list(contrasenas)
    pedidos: list[str] = []

    def leer_oculto(pedido: str = "") -> str:
        pedidos.append(pedido)
        return cola.pop(0)

    leer_oculto.pedidos = pedidos  # type: ignore[attr-defined]
    return leer_oculto


def _correr(argv, sesion, leer_oculto, *, es_interactivo=lambda: True):
    return main(
        argv,
        abrir_sesion=lambda settings: sesion,
        leer_oculto=leer_oculto,
        es_interactivo=es_interactivo,
        cifrar_contrasena=_cifrar,
    )


def _escuchar_conexiones():
    intentos: list[object] = []
    registrar = lambda dialect, rec, cargs, cparams: intentos.append(cparams.get("host"))  # noqa: E731
    event.listen(Engine, "do_connect", registrar)
    return intentos, lambda: event.remove(Engine, "do_connect", registrar)


# --- argumentos -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["borrar"],
        ["crear", "--rotar-contrasena", "otro_rol"],
        ["crear", "--rotar-contrasena", ROL_ACCESO_PREVIO],
        ["crear", "--contrasena", CLAVE_A],
        ["crear", CLAVE_A],
    ],
)
def test_argumentos_invalidos_fallan_sin_conectar_ni_repetir_lo_recibido(monkeypatch, capsys, argv):
    _entorno(monkeypatch)
    sesion = SesionDoble()
    leer = _terminal(CLAVE_A)

    codigo = _correr(argv, sesion, leer)

    salida = capsys.readouterr()
    texto = salida.out + salida.err
    assert codigo == 1
    assert sesion.escrituras == [] and leer.pedidos == []
    assert CLAVE_A not in texto and "otro_rol" not in texto


# --- guardias anteriores a la conexion ------------------------------------------------------------


def test_app_env_test_se_rechaza_sin_conectar_ni_pedir_contrasenas(monkeypatch, capsys):
    _entorno(monkeypatch, app_env="test")
    leer = _terminal(CLAVE_A)
    intentos, quitar = _escuchar_conexiones()
    try:
        codigo = main(["crear"], es_interactivo=lambda: True, leer_oculto=leer)
    finally:
        quitar()

    salida = capsys.readouterr()
    assert codigo == 1 and intentos == [] and leer.pedidos == []
    assert "APP_ENV" in salida.out + salida.err


def test_sin_terminal_se_rechaza_antes_de_pedir_contrasenas(monkeypatch, capsys):
    _entorno(monkeypatch)
    sesion = SesionDoble()
    leer = _terminal(CLAVE_A)

    codigo = _correr(["crear"], sesion, leer, es_interactivo=lambda: False)

    assert codigo == 1
    assert leer.pedidos == [] and sesion.escrituras == []
    assert "terminal" in capsys.readouterr().err


def test_sin_url_de_administracion_se_rechaza_sin_conectar(monkeypatch, capsys):
    _entorno(monkeypatch, migracion=None)
    leer = _terminal(CLAVE_A)
    intentos, quitar = _escuchar_conexiones()
    try:
        codigo = main(["crear"], es_interactivo=lambda: True, leer_oculto=leer)
    finally:
        quitar()

    salida = capsys.readouterr()
    texto = salida.out + salida.err
    assert codigo == 1 and intentos == [] and leer.pedidos == []
    assert "DATABASE_MIGRATION_URL" in texto
    for secreto in ("clave-api-ficticia", "host-api", "postgresql", "@"):
        assert secreto not in texto


def test_un_rol_conectado_que_no_puede_crear_roles_se_rechaza_sin_escribir(monkeypatch, capsys):
    _entorno(monkeypatch)
    sesion = SesionDoble(puede_crear=False)
    leer = _terminal(CLAVE_A, CLAVE_A, CLAVE_B, CLAVE_B)

    codigo = _correr(["crear"], sesion, leer)

    assert codigo == 1
    assert sesion.escrituras == [] and leer.pedidos == []
    assert "rollback" in sesion.eventos and "commit" not in sesion.eventos


# --- contrasenas ------------------------------------------------------------------------------


def test_doble_ingreso_distinto_se_rechaza_sin_crear_roles(monkeypatch, capsys):
    _entorno(monkeypatch)
    sesion = SesionDoble()

    codigo = _correr(["crear"], sesion, _terminal(CLAVE_A, CLAVE_B))

    salida = capsys.readouterr()
    texto = salida.out + salida.err
    assert codigo == 1
    assert sesion.escrituras == []
    assert "commit" not in sesion.eventos
    assert CLAVE_A not in texto and CLAVE_B not in texto


def test_la_misma_contrasena_para_ambos_roles_se_rechaza_sin_crear_ninguno(monkeypatch, capsys):
    _entorno(monkeypatch)
    sesion = SesionDoble()

    codigo = _correr(["crear"], sesion, _terminal(CLAVE_A, CLAVE_A, CLAVE_A, CLAVE_A))

    salida = capsys.readouterr()
    assert codigo == 1
    assert sesion.escrituras == []
    assert CLAVE_A not in salida.out + salida.err
    assert "commit" not in sesion.eventos


def test_contrasena_vacia_se_rechaza(monkeypatch, capsys):
    _entorno(monkeypatch)
    sesion = SesionDoble()

    codigo = _correr(["crear"], sesion, _terminal("", ""))

    assert codigo == 1 and sesion.escrituras == []


# --- salida y creacion ----------------------------------------------------------------------


def test_creacion_completa_imprime_solo_textos_fijos_y_confirma(monkeypatch, capsys):
    _entorno(monkeypatch)
    sesion = SesionDoble()

    codigo = _correr(["crear"], sesion, _terminal(CLAVE_A, CLAVE_A, CLAVE_B, CLAVE_B))

    salida = capsys.readouterr()
    assert codigo == 0
    assert salida.out.splitlines() == [
        f"rol creado: {ROL_ACCESO_PREVIO}",
        f"rol creado: {ROL_ACCESO_LOGIN}",
        f"rol creado: {ROL_APP}",
        f"rol creado: {ROL_LOGIN}",
    ]
    assert sesion.eventos[-2:] == ["commit", "close"]
    for texto in (CLAVE_A, CLAVE_B):
        assert texto not in salida.out + salida.err
        assert all(texto not in s for s in sesion.escrituras)
    con_clave = [s for s in sesion.escrituras if "PASSWORD" in s]
    assert len(con_clave) == 2
    assert all("PASSWORD 'SCRAM-SHA-256$" in s for s in con_clave)


def test_roles_existentes_correctos_no_cambian_nada_ni_piden_contrasenas(monkeypatch, capsys):
    _entorno(monkeypatch)
    sesion = SesionDoble(existentes=(ROL_APP, ROL_LOGIN, ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN))
    leer = _terminal()

    codigo = _correr(["crear"], sesion, leer)

    assert codigo == 0
    assert sesion.escrituras == [] and leer.pedidos == []
    assert capsys.readouterr().out.splitlines() == [
        f"rol existente verificado: {ROL_ACCESO_PREVIO}",
        f"rol existente verificado: {ROL_ACCESO_LOGIN}",
        f"rol existente verificado: {ROL_APP}",
        f"rol existente verificado: {ROL_LOGIN}",
    ]


def test_rol_existente_con_atributo_indebido_falla_sin_corregir(monkeypatch, capsys):
    _entorno(monkeypatch)
    sesion = SesionDoble(
        existentes=(ROL_APP, ROL_LOGIN, ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN),
        filas_a_medida={ROL_LOGIN: _fila_de_rol(ROL_LOGIN, rolbypassrls=True)},
    )

    codigo = _correr(["crear"], sesion, _terminal())

    salida = capsys.readouterr()
    assert codigo == 1
    assert sesion.escrituras == [] and "commit" not in sesion.eventos
    assert ROL_LOGIN in salida.err and "BYPASSRLS" in salida.err


def test_rol_existente_con_membresia_indebida_falla_sin_corregir(monkeypatch, capsys):
    _entorno(monkeypatch)
    sesion = SesionDoble(
        existentes=(ROL_APP, ROL_LOGIN, ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN),
        membresias=(ROL_ACCESO_LOGIN,),
    )

    codigo = _correr(["crear"], sesion, _terminal())

    salida = capsys.readouterr()
    assert codigo == 1
    assert sesion.escrituras == [] and "commit" not in sesion.eventos
    assert ROL_ACCESO_LOGIN in salida.err and "MEMBRESIAS" in salida.err


def test_rotar_pide_solo_la_contrasena_del_rol_indicado(monkeypatch, capsys):
    _entorno(monkeypatch)
    sesion = SesionDoble(existentes=(ROL_APP, ROL_LOGIN, ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN))
    leer = _terminal(CLAVE_A, CLAVE_A)

    codigo = _correr(["crear", "--rotar-contrasena", ROL_LOGIN], sesion, leer)

    salida = capsys.readouterr()
    assert codigo == 0
    assert len(leer.pedidos) == 2
    assert len(sesion.escrituras) == 1
    assert sesion.escrituras[0].startswith(f"ALTER ROLE {ROL_LOGIN} PASSWORD 'SCRAM-SHA-256$")
    assert f"contraseña rotada: {ROL_LOGIN}" in salida.out
    assert CLAVE_A not in salida.out + salida.err

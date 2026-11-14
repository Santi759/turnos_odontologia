"""Los comandos locales usan el motor de administracion (`DATABASE_MIGRATION_URL`), 1.4 (DD-02)."""

import secrets

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.core.config import Settings
from app.core.database import AdministracionNoConfigurada, crear_engine_admin
from app.credenciales import __main__ as credenciales
from app.mantenimiento import __main__ as mantenimiento
from app.seed import __main__ as seed

URL_API = "postgresql+psycopg://turnos_app:clave-api-ficticia@host-api.invalid:5432/turnos"
URL_LOGIN = "postgresql+psycopg://turnos_login:clave-login-ficticia@host-login.invalid:5432/turnos"
URL_ADMIN = "postgresql+psycopg://app:clave-admin-ficticia@host-admin.invalid:5432/turnos"


def _settings(*, migracion: str | None = URL_ADMIN, app_env: str = "local") -> Settings:
    return Settings(
        DATABASE_URL=URL_API,
        DATABASE_LOGIN_URL=URL_LOGIN,
        DATABASE_MIGRATION_URL=migracion,
        CORS_ALLOWED_ORIGINS="http://localhost:5173",
        APP_ENV=app_env,
        AUTH_SECRET_KEY=secrets.token_urlsafe(48),
    )


def _entorno(monkeypatch: pytest.MonkeyPatch, *, migracion: str | None, app_env: str = "local") -> None:
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


def _comando_seed() -> int:
    return seed.main()


def _comando_credenciales() -> int:
    return credenciales.main(
        [], es_interactivo=lambda: True, leer_visible=lambda _p: "ficticio", leer_oculto=lambda _p: "x"
    )


def _comando_mantenimiento() -> int:
    return mantenimiento.main(["limpiar"])


COMANDOS = [_comando_seed, _comando_credenciales, _comando_mantenimiento]
ABRIDORES = [seed, credenciales, mantenimiento]


def test_crear_engine_admin_apunta_a_la_url_de_administracion():
    motor = crear_engine_admin(_settings())

    assert motor.url.host == "host-admin.invalid"
    assert motor.url.username == "app"


def test_crear_engine_admin_sin_la_url_falla_con_mensaje_fijo_sin_valores():
    with pytest.raises(AdministracionNoConfigurada) as error:
        crear_engine_admin(_settings(migracion=None))

    texto = str(error.value)
    assert "DATABASE_MIGRATION_URL" in texto
    for secreto in ("clave-api-ficticia", "clave-login-ficticia", "host-api", "host-login"):
        assert secreto not in texto


@pytest.mark.parametrize("modulo", ABRIDORES, ids=["seed", "credenciales", "mantenimiento"])
def test_la_sesion_por_defecto_de_cada_comando_apunta_al_host_de_administracion(modulo):
    with modulo._abrir_sesion_por_defecto(_settings()) as sesion:
        url = sesion.get_bind().url

    assert url.host == "host-admin.invalid"
    assert url.username == "app"


@pytest.mark.parametrize("comando", COMANDOS, ids=["seed", "credenciales", "mantenimiento"])
def test_cada_comando_sin_la_url_de_administracion_la_menciona_sin_conectar(
    monkeypatch, capsys, comando
):
    _entorno(monkeypatch, migracion=None)
    intentos: list[object] = []
    registrar = lambda dialect, rec, cargs, cparams: intentos.append(cparams.get("host"))  # noqa: E731
    event.listen(Engine, "do_connect", registrar)
    try:
        codigo = comando()
    finally:
        event.remove(Engine, "do_connect", registrar)

    salida = capsys.readouterr()
    texto = salida.out + salida.err
    assert codigo == 1
    assert "DATABASE_MIGRATION_URL" in texto
    assert intentos == []
    for secreto in ("clave-api-ficticia", "host-api", "postgresql", "@"):
        assert secreto not in texto


@pytest.mark.parametrize("comando", COMANDOS, ids=["seed", "credenciales", "mantenimiento"])
def test_cada_comando_con_app_env_test_se_rechaza_sin_conectar(monkeypatch, capsys, comando):
    _entorno(monkeypatch, migracion=URL_ADMIN, app_env="test")
    intentos: list[object] = []
    registrar = lambda dialect, rec, cargs, cparams: intentos.append(cparams.get("host"))  # noqa: E731
    event.listen(Engine, "do_connect", registrar)
    try:
        codigo = comando()
    finally:
        event.remove(Engine, "do_connect", registrar)

    salida = capsys.readouterr()
    assert codigo == 1
    assert "APP_ENV" in salida.out + salida.err
    assert intentos == []

import dataclasses
import secrets
import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ProgrammingError

from app.core.config import Settings
from app.models.usuario import Rol
from app.seed.__main__ import main
from app.seed.aplicar import ResumenSeed
from app.seed.datos import CONSULTORIOS, USUARIOS, UsuarioSeed
from app.seed.entorno import validar_entorno_de_seed

URL_INEXISTENTE = "postgresql+psycopg://app:secreto@host-inexistente.invalid:5432/turnos"
# C-04: los comandos locales usan DATABASE_MIGRATION_URL (rol `app`); la de la API es otro rol.
URL_API_INEXISTENTE = "postgresql+psycopg://turnos_app:secreto@host-api-inexistente.invalid:5432/turnos"


def _configurar_entorno(monkeypatch: pytest.MonkeyPatch, app_env: str) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("DATABASE_URL", URL_API_INEXISTENTE)
    monkeypatch.setenv("DATABASE_MIGRATION_URL", URL_INEXISTENTE)
    monkeypatch.delenv("DATABASE_LOGIN_URL", raising=False)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("AUTH_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")


def _settings(app_env: str) -> Settings:
    return Settings(
        DATABASE_URL=URL_INEXISTENTE,
        CORS_ALLOWED_ORIGINS="http://localhost:5173",
        APP_ENV=app_env,
        AUTH_SECRET_KEY=secrets.token_urlsafe(48),
    )


# --- Datos del seed ------------------------------------------------------------


def test_dos_consultorios_demo_a_y_b():
    assert [c.nombre for c in CONSULTORIOS] == [
        "Consultorio Demo A",
        "Consultorio Demo B",
    ]


def test_seis_usuarios_uno_por_rol_en_cada_consultorio():
    assert len(USUARIOS) == 6
    for consultorio in CONSULTORIOS:
        roles = sorted(u.rol for u in USUARIOS if u.consultorio_id == consultorio.id)
        assert roles == sorted(rol.value for rol in Rol)


def test_emails_y_nombres_evidentemente_ficticios():
    assert all(u.email.endswith("@example.test") for u in USUARIOS)
    assert all("Demo" in u.nombre for u in USUARIOS)
    for consultorio in CONSULTORIOS:
        emails = [u.email for u in USUARIOS if u.consultorio_id == consultorio.id]
        assert len(set(emails)) == 3
    assert all(u.email == u.email.strip().lower() for u in USUARIOS)


def test_todos_los_ids_del_seed_son_uuid_v7_rfc4122_y_distintos():
    ids = [c.id for c in CONSULTORIOS] + [u.id for u in USUARIOS]

    assert len(ids) == 8
    assert len(set(ids)) == 8
    assert all(isinstance(i, uuid.UUID) for i in ids)
    assert all(i.version == 7 for i in ids)
    assert all(i.variant == uuid.RFC_4122 for i in ids)


def test_los_datos_del_seed_no_contienen_credenciales():
    campos = {campo.name for campo in dataclasses.fields(UsuarioSeed)}

    assert not any("credencial" in campo or "password" in campo for campo in campos)


# --- Guardia de entorno -----------------------------------------------------------


def test_entorno_local_admitido():
    validar_entorno_de_seed(_settings("local"))  # no lanza


def test_entorno_de_pruebas_rechazado_con_mensaje_que_menciona_app_env():
    with pytest.raises(RuntimeError) as excinfo:
        validar_entorno_de_seed(_settings("test"))

    assert "APP_ENV" in str(excinfo.value)
    assert "host-inexistente" not in str(excinfo.value)


def _escuchar_conexiones() -> tuple[list[object], object]:
    intentos: list[object] = []

    def registrar(dialect, conn_rec, cargs, cparams):
        intentos.append(cparams.get("host"))

    event.listen(Engine, "do_connect", registrar)
    return intentos, registrar


def test_main_con_app_env_test_no_abre_conexion_y_termina_con_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _configurar_entorno(monkeypatch, "test")
    intentos, registrar = _escuchar_conexiones()
    try:
        codigo = main()
    finally:
        event.remove(Engine, "do_connect", registrar)  # type: ignore[arg-type]

    salida = capsys.readouterr()
    texto = salida.out + salida.err
    assert codigo != 0
    assert "APP_ENV" in texto
    assert intentos == []
    for prohibido in ("host-inexistente", "postgresql", "secreto", "@"):
        assert prohibido not in texto


def test_el_listener_de_control_detecta_un_intento_de_conexion(
    monkeypatch: pytest.MonkeyPatch,
):
    # Control: con APP_ENV=local la guardia pasa y main SI intenta conectar,
    # de modo que el listener de la prueba anterior detecta lo que debe detectar.
    _configurar_entorno(monkeypatch, "local")
    intentos, registrar = _escuchar_conexiones()
    try:
        codigo = main()
    finally:
        event.remove(Engine, "do_connect", registrar)  # type: ignore[arg-type]

    assert codigo != 0
    assert "host-inexistente.invalid" in intentos


# --- Errores y resumen ----------------------------------------------------------------


class _Orig(Exception):
    def __init__(self, sqlstate: str) -> None:
        super().__init__("detalle interno con prueba@example.test")
        self.sqlstate = sqlstate


class _SesionQueFalla:
    def __init__(self, error: Exception) -> None:
        self._error = error
        self.revertida = False

    def execute(self, *args: object, **kwargs: object) -> None:
        raise self._error

    def rollback(self) -> None:
        self.revertida = True

    def commit(self) -> None:
        raise AssertionError("no debe confirmar tras un error")

    def close(self) -> None:
        pass

    def __enter__(self) -> "_SesionQueFalla":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_main_sin_migraciones_pide_aplicarlas_sin_detalles(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _configurar_entorno(monkeypatch, "local")
    sesion = _SesionQueFalla(ProgrammingError("SELECT 1", {}, _Orig("42P01")))

    codigo = main(abrir_sesion=lambda settings: sesion)  # type: ignore[arg-type,return-value]

    salida = capsys.readouterr()
    texto = salida.out + salida.err
    assert codigo == 1
    assert "migraciones" in texto
    assert "@" not in texto and "postgresql" not in texto
    assert sesion.revertida


def test_main_con_otro_error_informa_sin_detalles(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _configurar_entorno(monkeypatch, "local")
    sesion = _SesionQueFalla(RuntimeError("fallo con persona@example.test"))

    codigo = main(abrir_sesion=lambda settings: sesion)  # type: ignore[arg-type,return-value]

    salida = capsys.readouterr()
    texto = salida.out + salida.err
    assert codigo == 1
    assert "@" not in texto and "persona" not in texto
    assert sesion.revertida


def test_resumen_solo_informa_cantidades():
    resumen = ResumenSeed(
        consultorios_insertados=2,
        consultorios_omitidos=0,
        usuarios_insertados=5,
        usuarios_omitidos=1,
    )

    texto = resumen.texto()

    assert "2" in texto and "5" in texto and "1" in texto
    assert "@" not in texto and "postgresql" not in texto
    assert not any(u.nombre in texto for u in USUARIOS)
    assert not any(c.nombre in texto for c in CONSULTORIOS)


def test_resumen_con_otras_cantidades_cambia_el_texto():
    base = ResumenSeed(2, 0, 6, 0).texto()
    otro = ResumenSeed(0, 2, 0, 6).texto()

    assert base != otro


def test_el_codigo_del_seed_no_contiene_sentencias_de_actualizacion_ni_borrado():
    import re
    from pathlib import Path

    import app.seed

    patron = re.compile(r"update|delete|truncate|drop\s", re.IGNORECASE)
    hallazgos = [
        f"{archivo.name}:{numero}"
        for archivo in Path(app.seed.__file__).parent.glob("*.py")
        for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1)
        if patron.search(linea)
    ]

    assert hallazgos == []


def test_el_patron_de_busqueda_detecta_una_sentencia_prohibida():
    import re

    patron = re.compile(r"update|delete|truncate|drop\s", re.IGNORECASE)

    assert patron.search("sesion.execute(update(Usuario).values(activo=False))")
    assert not patron.search("insert(Usuario).on_conflict_do_nothing()")

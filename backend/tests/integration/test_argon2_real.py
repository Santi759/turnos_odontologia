"""Argon2id con los parametros REALES (m=65536, t=3, p=4) contra `db-test` (cierre 12.2).

Las demas pruebas usan un hasher rapido por costo; estas fijan los escenarios "Formato del hash" y
"Rehash al cambiar parametros" de la spec con el hasher de produccion (`crear_hasher`), sin tocar la
base de desarrollo. Todo ocurre dentro de la transaccion revertible de la fixture `sesion`.
"""

import secrets

import pytest
from argon2 import PasswordHasher, Type, extract_parameters
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.concurrencia import LimitadorArgon2
from app.auth.contrasenas import VerificadorContrasenas, crear_hasher
from app.auth.servicio import ServicioAuth
from app.credenciales.__main__ import main
from tests.integration.app_auth import ORIGEN, crear_app_real
from tests.integration.datos_auth import (
    CONTRASENA_A,
    EMAIL,
    Entorno,
)

# Literal de la spec (no importado de la aplicacion): si cambia un parametro, la prueba falla.
PREFIJO_DE_LA_SPEC = "$argon2id$v=19$m=65536,t=3,p=4$"
CODIGO_A = "ficticio-a"
CONTRASENA_NUEVA = "clave-de-prueba-real-a1"


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


@pytest.fixture(autouse=True)
def entorno_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://app:secreto@host-inexistente.invalid:5432/turnos"
    )
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("AUTH_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")


def _credencial(entorno: Entorno) -> str:
    return entorno.db.execute(
        text("SELECT credencial FROM usuario WHERE id = :u"), {"u": entorno.ua}
    ).scalar_one()


def _fijar_credencial(entorno: Entorno, valor: str) -> None:
    entorno.db.execute(
        text("UPDATE usuario SET credencial = :c WHERE id = :u"), {"c": valor, "u": entorno.ua}
    )
    entorno.db.commit()


def _hasher_real(time_cost: int = 3) -> PasswordHasher:
    return PasswordHasher(
        time_cost=time_cost, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID
    )


def _app_con_verificador_real(entorno: Entorno) -> TestClient:
    servicio = ServicioAuth(
        entorno.config, entorno.reloj, VerificadorContrasenas(), LimitadorArgon2(espera_segundos=10.0)
    )
    return TestClient(
        crear_app_real(entorno, servicio=servicio),
        base_url="https://testserver",
        client=("203.0.113.7", 50000),
    )


def _login(cliente: TestClient, contrasena: str = CONTRASENA_A):
    return cliente.post(
        "/api/auth/login",
        json={"codigo_consultorio": CODIGO_A, "email": EMAIL, "contrasena": contrasena},
        headers={"Origin": ORIGEN},
    )


# --- Formato del hash producido por el comando local ------------------------------------------------


class _Terminal:
    def __init__(self, visibles: list[str], ocultas: list[str]) -> None:
        self.visibles, self.ocultas = list(visibles), list(ocultas)

    def leer_visible(self, pedido: str = "") -> str:
        return self.visibles.pop(0)

    def leer_oculto(self, pedido: str = "") -> str:
        return self.ocultas.pop(0)


def test_el_comando_local_guarda_un_hash_con_los_parametros_reales_de_la_spec(entorno: Entorno):
    entorno.db.execute(
        text("UPDATE usuario SET credencial = NULL WHERE id = :u"), {"u": entorno.ua}
    )
    entorno.db.commit()
    terminal = _Terminal([CODIGO_A, EMAIL], [CONTRASENA_NUEVA, CONTRASENA_NUEVA])
    nueva = Session(
        bind=entorno.db.get_bind(), expire_on_commit=False, join_transaction_mode="create_savepoint"
    )

    # `hasher` omitido: el comando usa `crear_hasher()`, el hasher REAL de produccion.
    codigo = main(
        [],
        abrir_sesion=lambda settings: nueva,
        leer_visible=terminal.leer_visible,
        leer_oculto=terminal.leer_oculto,
        es_interactivo=lambda: True,
        reloj=entorno.reloj,
    )

    assert codigo == 0
    guardada = _credencial(entorno)
    assert guardada.startswith(PREFIJO_DE_LA_SPEC)
    parametros = extract_parameters(guardada)
    assert (parametros.type, parametros.version) == (Type.ID, 19)
    assert (parametros.memory_cost, parametros.time_cost, parametros.parallelism) == (65536, 3, 4)
    assert (parametros.hash_len, parametros.salt_len) == (32, 16)
    assert _hasher_real().verify(guardada, CONTRASENA_NUEVA)


def test_el_hasher_de_produccion_produce_el_prefijo_de_la_spec_con_sal_distinta():
    primero = crear_hasher().hash("contrasena-ficticia-real-1")
    segundo = crear_hasher().hash("contrasena-ficticia-real-1")

    assert primero.startswith(PREFIJO_DE_LA_SPEC) and segundo.startswith(PREFIJO_DE_LA_SPEC)
    assert primero != segundo


# --- Rehash por HTTP con parametros reales ----------------------------------------------------------


def test_login_http_con_hash_de_t2_responde_200_y_la_credencial_pasa_a_los_parametros_vigentes(
    entorno: Entorno,
):
    viejo = _hasher_real(time_cost=2).hash(CONTRASENA_A)
    assert viejo.startswith("$argon2id$v=19$m=65536,t=2,p=4$")
    _fijar_credencial(entorno, viejo)
    cliente = _app_con_verificador_real(entorno)

    respuesta = _login(cliente)

    assert respuesta.status_code == 200
    nuevo = _credencial(entorno)
    assert nuevo != viejo
    assert nuevo.startswith(PREFIJO_DE_LA_SPEC)
    assert not _hasher_real().check_needs_rehash(nuevo)
    assert _hasher_real().verify(nuevo, CONTRASENA_A)  # la contrasena sigue autenticando
    assert _login(cliente).status_code == 200
    assert _credencial(entorno) == nuevo  # y ya no se vuelve a reescribir


def test_login_http_con_hash_vigente_no_cambia_la_credencial(entorno: Entorno):
    vigente = _hasher_real().hash(CONTRASENA_A)
    _fijar_credencial(entorno, vigente)
    cliente = _app_con_verificador_real(entorno)

    assert _login(cliente).status_code == 200

    assert _credencial(entorno) == vigente


def test_login_http_fallido_con_hash_de_t2_no_reescribe_la_credencial(entorno: Entorno):
    viejo = _hasher_real(time_cost=2).hash(CONTRASENA_A)
    _fijar_credencial(entorno, viejo)
    cliente = _app_con_verificador_real(entorno)

    assert _login(cliente, contrasena="otra-contrasena-ficticia").status_code == 401

    assert _credencial(entorno) == viejo

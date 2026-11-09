"""Comando local de credenciales contra `db-test` (tarea 9.2; DD-22, spec `credenciales-locales`).

La sesion de base y las lecturas de terminal se inyectan: el comando usa una segunda `Session` sobre
la conexion y la transaccion revertible de la fixture `sesion`, de modo que todo se revierte al
terminar. `DATABASE_URL` apunta a un host inexistente: si el comando intentara abrir su propia
conexion, la prueba fallaria. Nunca se toca la base de desarrollo (X2, D1).
"""

import secrets
import unicodedata
from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.credenciales.__main__ import main
from tests.integration.app_auth import ORIGEN, crear_app_real
from tests.integration.datos_auth import (
    EMAIL,
    Entorno,
    RelojFijo,
    crear_usuario,
    hasher_rapido,
    hash_rapido,
    insertar_sesion,
)

CODIGO_A = "ficticio-a"
CODIGO_B = "ficticio-b"
CONTRASENA = "clave-de-prueba-a1"
OTRA_CONTRASENA = "clave-de-prueba-a2"
CONTRASENA_PREVIA = "contrasena-ficticia-a1"  # la de `Entorno` para A


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


class Terminal:
    def __init__(self, visibles: Sequence[str], ocultas: Sequence[str], al_leer_oculto=None) -> None:
        self.visibles = list(visibles)
        self.ocultas = list(ocultas)
        self.al_leer_oculto = al_leer_oculto

    def leer_visible(self, pedido: str = "") -> str:
        return self.visibles.pop(0)

    def leer_oculto(self, pedido: str = "") -> str:
        if self.al_leer_oculto is not None and len(self.ocultas) == 1:
            self.al_leer_oculto()  # ocurre entre la primera y la segunda lectura
        return self.ocultas.pop(0)


def _ejecutar(
    entorno: Entorno,
    terminal: Terminal,
    argv: Sequence[str] = (),
    reloj: RelojFijo | None = None,
) -> int:
    nueva = Session(
        bind=entorno.db.get_bind(), expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    return main(
        list(argv),
        abrir_sesion=lambda settings: nueva,
        leer_visible=terminal.leer_visible,
        leer_oculto=terminal.leer_oculto,
        es_interactivo=lambda: True,
        hasher=hasher_rapido(),
        reloj=reloj or entorno.reloj,
    )


def _credencial(entorno: Entorno, usuario_id) -> str | None:
    return entorno.db.execute(
        text("SELECT credencial FROM usuario WHERE id = :id"), {"id": usuario_id}
    ).scalar_one()


def _dejar_nula(entorno: Entorno, *usuarios) -> None:
    for usuario_id in usuarios:
        entorno.db.execute(
            text("UPDATE usuario SET credencial = NULL WHERE id = :id"), {"id": usuario_id}
        )
    entorno.db.commit()


def _cliente(entorno: Entorno) -> TestClient:
    return TestClient(
        crear_app_real(entorno), base_url="https://testserver", client=("203.0.113.7", 50000)
    )


def _login(cliente: TestClient, contrasena: str, codigo: str = CODIGO_A):
    return cliente.post(
        "/api/auth/login",
        json={"codigo_consultorio": codigo, "email": EMAIL, "contrasena": contrasena},
        headers={"Origin": ORIGEN},
    )


def _salida(capsys: pytest.CaptureFixture[str]) -> str:
    capturada = capsys.readouterr()
    return capturada.out + capturada.err


# --- Solo completa credenciales nulas ---------------------------------------------------------------


def test_un_usuario_sin_credencial_la_recibe_y_puede_iniciar_sesion(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    _dejar_nula(entorno, entorno.ua)

    codigo = _ejecutar(entorno, Terminal([CODIGO_A, EMAIL], [CONTRASENA, CONTRASENA]))

    assert codigo == 0, _salida(capsys)
    assert _credencial(entorno, entorno.ua).startswith("$argon2id$")
    assert _login(_cliente(entorno), CONTRASENA).status_code == 200


def test_con_credencial_y_sin_reemplazar_falla_y_no_cambia_nada(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    antes = _credencial(entorno, entorno.ua)

    codigo = _ejecutar(entorno, Terminal([CODIGO_A, EMAIL], [CONTRASENA, CONTRASENA]))

    assert codigo != 0
    assert "--reemplazar" in _salida(capsys)
    assert _credencial(entorno, entorno.ua) == antes
    cliente = _cliente(entorno)
    assert _login(cliente, CONTRASENA_PREVIA).status_code == 200
    assert _login(cliente, CONTRASENA).status_code == 401


def test_una_cuenta_inexistente_falla_sin_crear_filas(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    antes = entorno.db.execute(
        text(
            "SELECT (SELECT count(*) FROM consultorio), (SELECT count(*) FROM usuario), "
            "(SELECT md5(string_agg(u::text, '|' ORDER BY u.id)) FROM usuario u)"
        )
    ).one()

    codigo = _ejecutar(
        entorno, Terminal([CODIGO_A, "nadie@example.test"], [CONTRASENA, CONTRASENA])
    )

    despues = entorno.db.execute(
        text(
            "SELECT (SELECT count(*) FROM consultorio), (SELECT count(*) FROM usuario), "
            "(SELECT md5(string_agg(u::text, '|' ORDER BY u.id)) FROM usuario u)"
        )
    ).one()
    salida = _salida(capsys)
    assert codigo != 0
    assert "no se encontró la cuenta indicada" in salida
    assert "nadie" not in salida and "@" not in salida and CODIGO_A not in salida
    assert tuple(despues) == tuple(antes)


# --- Identificacion por codigo + email (aislamiento entre consultorios) -----------------------------


def test_con_el_mismo_email_en_dos_consultorios_solo_cambia_el_del_codigo_indicado(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    _dejar_nula(entorno, entorno.ua, entorno.ub)

    codigo = _ejecutar(entorno, Terminal([CODIGO_B, EMAIL], [CONTRASENA, CONTRASENA]))

    assert codigo == 0, _salida(capsys)
    assert _credencial(entorno, entorno.ua) is None
    assert _credencial(entorno, entorno.ub).startswith("$argon2id$")
    assert _login(_cliente(entorno), CONTRASENA, codigo=CODIGO_B).status_code == 200


def test_el_codigo_se_normaliza_y_un_email_de_otro_consultorio_no_se_encuentra(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    otro = crear_usuario(entorno.db, entorno.b, email="solo.en.b@example.test", nombre="Solo B")
    entorno.db.commit()

    codigo = _ejecutar(
        entorno, Terminal([CODIGO_A, "solo.en.b@example.test"], [CONTRASENA, CONTRASENA])
    )

    assert codigo != 0
    assert "no se encontró la cuenta indicada" in _salida(capsys)
    assert _credencial(entorno, otro) is None


# --- Reemplazo ----------------------------------------------------------------------------------------


def _sesiones_revocadas(entorno: Entorno, usuario_id) -> list[bool]:
    filas = entorno.db.execute(
        text("SELECT revocada_en IS NOT NULL FROM sesion WHERE usuario_id = :u ORDER BY id"),
        {"u": usuario_id},
    )
    return [fila[0] for fila in filas]


def test_el_reemplazo_confirmado_cambia_la_contrasena_y_revoca_solo_las_sesiones_del_usuario(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    for _ in range(2):
        insertar_sesion(entorno.db, entorno.a, entorno.ua)
    insertar_sesion(entorno.db, entorno.b, entorno.ub)
    colega = crear_usuario(entorno.db, entorno.a, email="colega@example.test", nombre="Colega A")
    insertar_sesion(entorno.db, entorno.a, colega)
    entorno.db.commit()

    codigo = _ejecutar(
        entorno,
        Terminal([CODIGO_A, EMAIL, "REEMPLAZAR"], [CONTRASENA, CONTRASENA]),
        ["--reemplazar"],
    )

    assert codigo == 0, _salida(capsys)
    # Antes de iniciar sesion: un login exitoso borra las sesiones revocadas (DD-21).
    assert _sesiones_revocadas(entorno, entorno.ua) == [True, True]
    assert _sesiones_revocadas(entorno, entorno.ub) == [False]
    assert _sesiones_revocadas(entorno, colega) == [False]  # mismo consultorio, otro usuario
    cliente = _cliente(entorno)
    assert _login(cliente, CONTRASENA_PREVIA).status_code == 401
    assert _login(cliente, CONTRASENA).status_code == 200


def test_el_reemplazo_informa_la_cantidad_de_sesiones_revocadas(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    for _ in range(2):
        insertar_sesion(entorno.db, entorno.a, entorno.ua)
    entorno.db.commit()

    _ejecutar(
        entorno,
        Terminal([CODIGO_A, EMAIL, "REEMPLAZAR"], [CONTRASENA, CONTRASENA]),
        ["--reemplazar"],
    )

    assert _salida(capsys).strip() == "credencial reemplazada; sesiones revocadas: 2"


def test_el_reemplazo_no_confirmado_deja_la_credencial_y_las_sesiones(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    antes = _credencial(entorno, entorno.ua)
    for _ in range(2):
        insertar_sesion(entorno.db, entorno.a, entorno.ua)
    entorno.db.commit()

    codigo = _ejecutar(
        entorno, Terminal([CODIGO_A, EMAIL, "no"], [CONTRASENA, CONTRASENA]), ["--reemplazar"]
    )

    assert codigo != 0
    assert _credencial(entorno, entorno.ua) == antes
    assert _sesiones_revocadas(entorno, entorno.ua) == [False, False]


def test_si_otra_escritura_cambia_la_credencial_durante_el_dialogo_no_se_pisa_ni_se_revoca(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    insertar_sesion(entorno.db, entorno.a, entorno.ua)
    entorno.db.commit()
    intermedia = hash_rapido("otra-contrasena-ficticia-9")

    def cambiar_a_mitad() -> None:
        entorno.db.execute(
            text("UPDATE usuario SET credencial = :c WHERE id = :id"),
            {"c": intermedia, "id": entorno.ua},
        )
        entorno.db.commit()

    codigo = _ejecutar(
        entorno,
        Terminal(
            [CODIGO_A, EMAIL, "REEMPLAZAR"], [CONTRASENA, CONTRASENA], al_leer_oculto=cambiar_a_mitad
        ),
        ["--reemplazar"],
    )

    assert codigo != 0
    assert "cambió" in _salida(capsys)
    # (la reversion del comando descarta tambien el cambio intermedio: comparten transaccion
    # exterior en la prueba; lo que importa es que la contrasena nueva NO quedo establecida)
    assert _sesiones_revocadas(entorno, entorno.ua) == [False]
    assert _login(_cliente(entorno), CONTRASENA).status_code == 401


# --- Normalizacion NFKC al establecer y al verificar ---------------------------------------------------


def test_una_contrasena_establecida_descompuesta_inicia_sesion_con_la_forma_compuesta(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    _dejar_nula(entorno, entorno.ua)
    descompuesta = unicodedata.normalize("NFD", "contraseña-de-prueba-ñ1")
    compuesta = unicodedata.normalize("NFC", descompuesta)
    assert descompuesta != compuesta

    codigo = _ejecutar(entorno, Terminal([CODIGO_A, EMAIL], [descompuesta, descompuesta]))

    assert codigo == 0, _salida(capsys)
    cliente = _cliente(entorno)
    assert _login(cliente, compuesta).status_code == 200
    assert _login(cliente, descompuesta).status_code == 200


# --- Salida sin datos sensibles --------------------------------------------------------------------------


def test_ninguna_salida_contiene_contrasena_hash_email_codigo_ni_url(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    _dejar_nula(entorno, entorno.ua)
    salidas = []

    exito = _ejecutar(entorno, Terminal([CODIGO_A, EMAIL], [CONTRASENA, CONTRASENA]))
    salidas.append(_salida(capsys))
    _dejar_nula(entorno, entorno.ua)
    distinta = _ejecutar(entorno, Terminal([CODIGO_A, EMAIL], [CONTRASENA, OTRA_CONTRASENA]))
    salidas.append(_salida(capsys))
    con_codigo = _ejecutar(
        entorno, Terminal([CODIGO_A, EMAIL], ["mi-clave-ficticio-a-2026"] * 2)
    )
    salidas.append(_salida(capsys))

    assert (exito, distinta != 0, con_codigo != 0) == (0, True, True)
    assert all(salidas)
    for salida in salidas:
        for prohibido in (
            CONTRASENA,
            OTRA_CONTRASENA,
            "mi-clave-ficticio-a-2026",
            "$argon2",
            "@",
            CODIGO_A,
            "postgresql",
        ):
            assert prohibido not in salida

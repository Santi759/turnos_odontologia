"""Identidad y contexto derivados de la sesion (tarea 7.1; RN-MT-02, DD-27).

Rutas de prueba registradas solo en la app de pruebas (`app_auth.py`); las sesiones de la app comparten
la transaccion revertible de la fixture `sesion`.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.cookies import NOMBRE_COOKIE
from tests.integration.app_auth import AppDePrueba, crear_app_de_prueba
from tests.integration.datos_auth import (
    CONTRASENA_A,
    CONTRASENA_B,
    EMAIL,
    Entorno,
    crear_usuario,
    hash_rapido,
)

NO_AUTENTICADO = {"detail": "No autenticado."}
OTRO_EMAIL_DE_A = "otra.persona@example.test"


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    e = Entorno(sesion)
    crear_usuario(
        sesion, e.a, email=OTRO_EMAIL_DE_A, nombre="Otra Persona A", credencial=hash_rapido(CONTRASENA_A)
    )
    sesion.commit()
    return e


@pytest.fixture
def app_prueba(entorno: Entorno) -> AppDePrueba:
    return crear_app_de_prueba(entorno)


@pytest.fixture
def cliente(app_prueba: AppDePrueba) -> TestClient:
    return TestClient(app_prueba.app, base_url="https://testserver", client=("203.0.113.7", 50000))


def _con_cookie(token: str) -> dict[str, str]:
    return {"Cookie": f"{NOMBRE_COOKIE}={token}"}


def _borra_la_cookie(respuesta) -> bool:
    cabeceras = respuesta.headers.get_list("set-cookie")
    return len(cabeceras) == 1 and cabeceras[0].startswith(f"{NOMBRE_COOKIE}=;") and "Max-Age=0" in cabeceras[0]


# --- identidad y contexto ----------------------------------------------------------------------


def test_la_identidad_sale_de_la_sesion_y_el_contexto_es_el_de_su_consultorio(
    entorno: Entorno, cliente: TestClient
):
    iniciada = entorno.login()

    respuesta = cliente.get("/prueba/identidad", headers=_con_cookie(iniciada.token))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "usuario_id": str(entorno.ua),
        "rol": "secretaria",
        "consultorio_id": str(entorno.a),
        "es_contexto": True,
    }


def test_el_consultorio_enviado_por_el_cliente_nunca_altera_el_contexto(
    entorno: Entorno, cliente: TestClient
):
    # C-04 (DD-18, PD-02): `consultorio_id` en la query y `X-Consultorio-Id` se rechazan con 422 ANTES de
    # resolver la identidad (antes el contexto seguia siendo el de A con esos datos). Las demas
    # cabeceras no se rechazan y se ignoran: el contexto sigue siendo el de la sesion.
    iniciada = entorno.login()

    rechazada = cliente.get(
        "/prueba/identidad",
        params={"consultorio_id": str(entorno.b)},
        headers={**_con_cookie(iniciada.token), "X-Consultorio-Id": str(entorno.b)},
    )
    ignoradas = [
        cliente.get(
            "/prueba/identidad", headers={**_con_cookie(iniciada.token), cabecera: str(entorno.b)}
        )
        for cabecera in ("X-Consultorio", "Consultorio-Id", "X-Tenant-Id")
    ]
    sin_ellos = cliente.get("/prueba/identidad", headers=_con_cookie(iniciada.token))

    assert rechazada.status_code == 422
    for respuesta in (*ignoradas, sin_ellos):
        assert respuesta.status_code == 200
        assert respuesta.json()["consultorio_id"] == str(entorno.a)


def test_cada_sesion_da_el_contexto_de_su_propio_consultorio(entorno: Entorno, cliente: TestClient):
    de_a = entorno.login()
    de_b = entorno.login(codigo="ficticio-b", contrasena=CONTRASENA_B)

    id_a = cliente.get("/prueba/identidad", headers=_con_cookie(de_a.token)).json()["consultorio_id"]
    # El intento de colar el consultorio de A usa una cabecera NO rechazada (con `consultorio_id` o
    # `X-Consultorio-Id` la respuesta seria 422, C-04): sigue probando que se ignora.
    id_b = cliente.get(
        "/prueba/identidad",
        headers={**_con_cookie(de_b.token), "X-Consultorio": str(entorno.a)},
    ).json()["consultorio_id"]

    assert (id_a, id_b) == (str(entorno.a), str(entorno.b))


def test_el_repositorio_de_usuarios_con_el_contexto_inyectado_lista_solo_a(
    entorno: Entorno, cliente: TestClient
):
    iniciada = entorno.login()

    # Carriles NO rechazados por C-04 (con `consultorio_id` o `X-Consultorio-Id` la respuesta es 422).
    respuesta = cliente.get(
        "/prueba/usuarios",
        params={"consultorio": str(entorno.b)},
        headers={**_con_cookie(iniciada.token), "X-Tenant-Id": str(entorno.b)},
    )

    assert respuesta.status_code == 200
    assert sorted(respuesta.json()) == sorted([EMAIL, OTRO_EMAIL_DE_A])


# --- 401 sin identidad -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cookie",
    [None, "", "x" * 10, "A" * 42 + "+", "A" * 43],
    ids=["sin-cookie", "vacia", "corta", "caracter-invalido", "desconocida"],
)
def test_sin_sesion_valida_responde_401_y_borra_la_cookie(cliente: TestClient, cookie):
    headers = {} if cookie is None else _con_cookie(cookie)

    respuesta = cliente.get("/prueba/identidad", headers=headers)

    assert respuesta.status_code == 401
    assert respuesta.json() == NO_AUTENTICADO
    assert respuesta.headers["cache-control"] == "no-store"
    assert _borra_la_cookie(respuesta)


def test_una_sesion_revocada_vencida_o_de_usuario_inactivo_responde_401(
    entorno: Entorno, cliente: TestClient
):
    revocada = entorno.login()
    entorno.servicio.cerrar_sesion(entorno.db, revocada.sesion_id)
    vencida = entorno.login()
    entorno.reloj.avanzar(timedelta(minutes=31))
    inactiva = entorno.login(email=OTRO_EMAIL_DE_A)
    entorno.db.execute(text("UPDATE usuario SET activo = false WHERE email = :e"), {"e": OTRO_EMAIL_DE_A})
    entorno.db.commit()

    for token in (revocada.token, vencida.token, inactiva.token):
        respuesta = cliente.get("/prueba/identidad", headers=_con_cookie(token))
        assert respuesta.status_code == 401, token
        assert respuesta.json() == NO_AUTENTICADO


def test_una_peticion_autenticada_renueva_el_ultimo_uso_como_maximo_una_vez_por_minuto(
    entorno: Entorno, cliente: TestClient
):
    iniciada = entorno.login()
    entorno.reloj.avanzar(timedelta(seconds=30))
    cliente.get("/prueba/identidad", headers=_con_cookie(iniciada.token))
    entorno.reloj.avanzar(timedelta(seconds=30))
    cliente.get("/prueba/identidad", headers=_con_cookie(iniciada.token))

    ultimo_uso = entorno.db.execute(
        text("SELECT ultimo_uso_en FROM sesion WHERE id = :s"), {"s": iniciada.sesion_id}
    ).scalar_one()

    assert ultimo_uso == entorno.reloj.ahora()


# --- 7.1 Rol tipado en la identidad autenticada (DD-16, spec `autorizacion-roles`) -----------------------

import logging  # noqa: E402
from dataclasses import replace  # noqa: E402

from app.models.usuario import Rol  # noqa: E402
from tests.integration.app_auth import crear_app_real  # noqa: E402

ROLES_EN_A = {
    Rol.ADMINISTRADOR: "admin.ficticio@example.test",
    Rol.SECRETARIA: EMAIL,
    Rol.ODONTOLOGO: "odontologo.ficticio@example.test",
}


def _usuarios_de_los_tres_roles(entorno: Entorno) -> dict[Rol, str]:
    for rol, email in ROLES_EN_A.items():
        if rol is not Rol.SECRETARIA:
            crear_usuario(
                entorno.db, entorno.a, email=email, nombre=f"Persona {rol.value}", rol=rol.value,
                credencial=hash_rapido(CONTRASENA_A),
            )
    entorno.db.commit()
    return ROLES_EN_A


def test_el_rol_de_la_identidad_es_el_tipo_cerrado_rol(entorno: Entorno, cliente: TestClient):
    iniciada = entorno.login()

    respuesta = cliente.get("/prueba/rol", headers=_con_cookie(iniciada.token))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"rol": "secretaria", "es_rol": True, "es_secretaria": True}


@pytest.mark.parametrize("rol", list(Rol), ids=[r.value for r in Rol])
def test_me_muestra_el_rol_como_texto_para_cada_rol(entorno: Entorno, rol: Rol):
    emails = _usuarios_de_los_tres_roles(entorno)
    iniciada = entorno.login(email=emails[rol], contrasena=CONTRASENA_A)
    cliente_real = TestClient(
        crear_app_real(entorno), base_url="https://testserver", client=("203.0.113.7", 50000)
    )

    respuesta = cliente_real.get("/api/auth/me", headers=_con_cookie(iniciada.token))

    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"]["rol"] == rol.value


def test_un_rol_desconocido_no_autentica_responde_401_y_registra_un_codigo_fijo(
    entorno: Entorno, caplog: pytest.LogCaptureFixture
):
    iniciada = entorno.login()
    original = entorno.servicio.resolver_identidad
    entorno.servicio.resolver_identidad = lambda db, token: replace(  # type: ignore[method-assign]
        original(db, token), rol="auditor"
    )
    cliente_real = TestClient(
        crear_app_real(entorno), base_url="https://testserver", client=("203.0.113.7", 50000)
    )

    with caplog.at_level(logging.WARNING):
        respuesta = cliente_real.get("/api/auth/me", headers=_con_cookie(iniciada.token))

    assert respuesta.status_code == 401
    assert respuesta.json() == NO_AUTENTICADO
    assert respuesta.headers["cache-control"] == "no-store"
    assert _borra_la_cookie(respuesta)
    mensajes = [r.getMessage() for r in caplog.records]
    assert "rol_desconocido" in mensajes
    for dato in ("auditor", EMAIL, str(entorno.ua), iniciada.token):
        assert all(dato not in m for m in mensajes)

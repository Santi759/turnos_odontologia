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
    iniciada = entorno.login()

    respuesta = cliente.get(
        "/prueba/identidad",
        params={"consultorio_id": str(entorno.b)},
        headers={**_con_cookie(iniciada.token), "X-Consultorio-Id": str(entorno.b)},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["consultorio_id"] == str(entorno.a)


def test_cada_sesion_da_el_contexto_de_su_propio_consultorio(entorno: Entorno, cliente: TestClient):
    de_a = entorno.login()
    de_b = entorno.login(codigo="ficticio-b", contrasena=CONTRASENA_B)

    id_a = cliente.get("/prueba/identidad", headers=_con_cookie(de_a.token)).json()["consultorio_id"]
    id_b = cliente.get(
        "/prueba/identidad", params={"consultorio_id": str(entorno.a)}, headers=_con_cookie(de_b.token)
    ).json()["consultorio_id"]

    assert (id_a, id_b) == (str(entorno.a), str(entorno.b))


def test_el_repositorio_de_usuarios_con_el_contexto_inyectado_lista_solo_a(
    entorno: Entorno, cliente: TestClient
):
    iniciada = entorno.login()

    respuesta = cliente.get(
        "/prueba/usuarios",
        params={"consultorio_id": str(entorno.b)},
        headers={**_con_cookie(iniciada.token), "X-Consultorio-Id": str(entorno.b)},
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

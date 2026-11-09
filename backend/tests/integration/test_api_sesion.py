"""`GET /api/auth/me` y `POST /api/auth/logout` con la app real y `db-test` (tarea 8.1; DD-04, DD-05, DD-07).

Todas las peticiones `POST` llevan `Origin` permitido; la direccion del cliente se inyecta siempre.
"""

from datetime import timedelta
from http.cookies import SimpleCookie

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.auth.cookies import NOMBRE_COOKIE
from app.auth.servicio import ConfigAuth, ServicioAuth
from tests.integration.app_auth import ORIGEN, ORIGEN_AJENO, crear_app_real
from tests.integration.datos_auth import CONTRASENA_A, EMAIL, Entorno

NO_AUTENTICADO = {"detail": "No autenticado."}
RECHAZADA = {"detail": "Solicitud rechazada."}
CREDENCIALES = {"codigo_consultorio": "ficticio-a", "email": EMAIL, "contrasena": CONTRASENA_A}
CUERPO_A = {
    "usuario": {"nombre": "Persona A", "email": EMAIL, "rol": "secretaria"},
    "consultorio": {"nombre": "Consultorio Ficticio A"},
}


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


@pytest.fixture
def app(entorno: Entorno):
    return crear_app_real(entorno)


def _cliente(app) -> TestClient:
    return TestClient(app, base_url="https://testserver", client=("203.0.113.7", 50000))


@pytest.fixture
def cliente(app) -> TestClient:
    return _cliente(app)


def _login(cliente: TestClient):
    respuesta = cliente.post("/api/auth/login", json=CREDENCIALES, headers={"Origin": ORIGEN})
    assert respuesta.status_code == 200
    return respuesta


def _logout(cliente: TestClient, csrf: str | None, origen: str | None = ORIGEN, cookie: str | None = None):
    headers = {}
    if origen is not None:
        headers["Origin"] = origen
    if csrf is not None:
        headers["X-CSRF-Token"] = csrf
    if cookie is not None:
        headers["Cookie"] = f"{NOMBRE_COOKIE}={cookie}"
    return cliente.post("/api/auth/logout", headers=headers)


def _con_cookie(token: str) -> dict[str, str]:
    return {"Cookie": f"{NOMBRE_COOKIE}={token}"}


def _borra_la_cookie(respuesta) -> bool:
    cookies = SimpleCookie()
    for valor in respuesta.headers.get_list("set-cookie"):
        cookies.load(valor)
    cookie = cookies.get(NOMBRE_COOKIE)
    return (
        cookie is not None
        and cookie.value == ""
        and cookie["max-age"] == "0"
        and cookie["path"] == "/"
        and cookie["samesite"] == "Lax"
        and bool(cookie["httponly"])
        and bool(cookie["secure"])
    )


def _revocada(entorno: Entorno, sesion_id) -> bool:
    return entorno.db.execute(
        text("SELECT revocada_en IS NOT NULL FROM sesion WHERE id = :i"), {"i": sesion_id}
    ).scalar_one()


# --- GET /api/auth/me ---------------------------------------------------------------------------------


def test_me_con_sesion_valida_responde_la_identidad_minima_y_el_token_csrf(cliente: TestClient):
    login = _login(cliente)

    respuesta = cliente.get("/api/auth/me")

    assert respuesta.status_code == 200
    assert respuesta.json() == CUERPO_A
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["x-csrf-token"] == login.headers["x-csrf-token"]
    assert respuesta.headers["x-csrf-token"] != login.cookies[NOMBRE_COOKIE]
    assert respuesta.headers["x-csrf-token"] not in respuesta.text


def test_me_sin_cookie_responde_401_no_store_y_borra_la_cookie(cliente: TestClient):
    respuesta = cliente.get("/api/auth/me")

    assert respuesta.status_code == 401
    assert respuesta.json() == NO_AUTENTICADO
    assert respuesta.headers["cache-control"] == "no-store"
    assert _borra_la_cookie(respuesta)


def test_me_con_cookie_desconocida_responde_401_y_borra_la_cookie(cliente: TestClient):
    respuesta = cliente.get("/api/auth/me", headers=_con_cookie("A" * 43))

    assert respuesta.status_code == 401
    assert respuesta.json() == NO_AUTENTICADO
    assert _borra_la_cookie(respuesta)


@pytest.mark.parametrize("valor", ["", "a" * 10, "a+" + "b" * 41, "a" * 44], ids=["vacia", "corta", "caracter", "larga"])
def test_me_con_cookie_de_formato_invalido_responde_401_sin_consultar_sesiones(
    entorno: Entorno, cliente: TestClient, valor: str
):
    consultas: list[str] = []
    conexion = entorno.db.get_bind()

    def registrar(conn, cursor, sentencia, parametros, contexto, many):
        consultas.append(sentencia)

    event.listen(conexion, "before_cursor_execute", registrar)
    try:
        respuesta = cliente.get("/api/auth/me", headers=_con_cookie(valor))
    finally:
        event.remove(conexion, "before_cursor_execute", registrar)

    assert respuesta.status_code == 401
    assert respuesta.json() == NO_AUTENTICADO
    assert not [c for c in consultas if "sesion" in c.lower()]


def test_me_no_exige_origin_ni_token_csrf(cliente: TestClient):
    _login(cliente)

    respuesta = cliente.get("/api/auth/me")  # sin Origin y sin X-CSRF-Token

    assert respuesta.status_code == 200


def test_el_token_csrf_es_legible_desde_un_origen_permitido(cliente: TestClient):
    _login(cliente)

    respuesta = cliente.get("/api/auth/me", headers={"Origin": ORIGEN})

    assert respuesta.status_code == 200
    assert respuesta.headers["x-csrf-token"]
    assert respuesta.headers["access-control-allow-origin"] == ORIGEN
    assert respuesta.headers["access-control-allow-credentials"] == "true"
    assert "x-csrf-token" in respuesta.headers["access-control-expose-headers"].lower()


def test_un_origen_ajeno_no_puede_leer_el_token_csrf(cliente: TestClient):
    _login(cliente)

    respuesta = cliente.get("/api/auth/me", headers={"Origin": ORIGEN_AJENO})

    assert "access-control-allow-origin" not in respuesta.headers
    assert "access-control-allow-credentials" not in respuesta.headers


def test_cambiar_la_clave_de_autenticacion_invalida_las_sesiones(entorno: Entorno, cliente: TestClient):
    _login(cliente)
    otra = ServicioAuth(
        ConfigAuth(clave_hmac=bytes(reversed(entorno.config.clave_hmac)), minutos_inactividad=30, horas_maximas=12),
        entorno.reloj,
        entorno.verificador,
        entorno.limitador,
    )
    cliente_otra_clave = _cliente(crear_app_real(entorno, servicio=otra))
    cookie = cliente.cookies[NOMBRE_COOKIE]

    respuesta = cliente_otra_clave.get("/api/auth/me", headers=_con_cookie(cookie))

    assert respuesta.status_code == 401
    assert respuesta.json() == NO_AUTENTICADO


def test_una_sesion_inactiva_mas_de_30_minutos_pierde_la_validez(entorno: Entorno, cliente: TestClient):
    _login(cliente)
    entorno.reloj.avanzar(timedelta(minutes=31))

    respuesta = cliente.get("/api/auth/me")

    assert respuesta.status_code == 401
    assert respuesta.json() == NO_AUTENTICADO


def test_la_actividad_renueva_la_sesion(entorno: Entorno, cliente: TestClient):
    _login(cliente)

    entorno.reloj.avanzar(timedelta(minutes=20))
    primera = cliente.get("/api/auth/me")
    entorno.reloj.avanzar(timedelta(minutes=25))  # t0 + 45 min
    segunda = cliente.get("/api/auth/me")

    assert (primera.status_code, segunda.status_code) == (200, 200)


def test_la_renovacion_se_acota_a_una_por_minuto(entorno: Entorno, cliente: TestClient):
    _login(cliente)
    antes = entorno.sesiones()[0].ultimo_uso_en
    entorno.reloj.avanzar(timedelta(seconds=30))

    respuesta = cliente.get("/api/auth/me")

    assert respuesta.status_code == 200
    assert entorno.sesiones()[0].ultimo_uso_en == antes


def test_una_sesion_activa_vence_a_las_12_horas_sin_extenderse(entorno: Entorno, cliente: TestClient):
    _login(cliente)
    inicio = entorno.sesiones()[0]

    for _ in range(71):  # uso cada 10 minutos hasta t0 + 11 h 50 min
        entorno.reloj.avanzar(timedelta(minutes=10))
        assert cliente.get("/api/auth/me").status_code == 200
    entorno.reloj.avanzar(timedelta(minutes=10))  # t0 + 12 h

    assert cliente.get("/api/auth/me").status_code == 401
    assert entorno.sesiones()[0].vence_absoluto_en == inicio.vence_absoluto_en


@pytest.mark.parametrize(
    "sentencia",
    ["UPDATE usuario SET activo = false WHERE id = :u", "UPDATE consultorio SET activo = false WHERE id = :c"],
    ids=["usuario-desactivado", "consultorio-desactivado"],
)
def test_la_desactivacion_con_sesion_abierta_corta_el_acceso(
    entorno: Entorno, cliente: TestClient, sentencia: str
):
    _login(cliente)
    entorno.db.execute(text(sentencia), {"u": entorno.ua, "c": entorno.a})

    respuesta = cliente.get("/api/auth/me")

    assert respuesta.status_code == 401
    assert respuesta.json() == NO_AUTENTICADO


# --- POST /api/auth/logout --------------------------------------------------------------------------------


def test_logout_valido_revoca_la_sesion_borra_la_cookie_y_el_token_anterior_deja_de_servir(
    entorno: Entorno, app, cliente: TestClient
):
    login = _login(cliente)
    token = login.cookies[NOMBRE_COOKIE]
    sesion_id = entorno.sesiones()[0].id

    respuesta = _logout(cliente, login.headers["x-csrf-token"])

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    assert respuesta.headers["cache-control"] == "no-store"
    assert _borra_la_cookie(respuesta)
    assert _revocada(entorno, sesion_id)
    posterior = _cliente(app).get("/api/auth/me", headers=_con_cookie(token))
    assert posterior.status_code == 401


@pytest.mark.parametrize(
    "origen,csrf",
    [(ORIGEN, None), (None, "valido"), (ORIGEN_AJENO, "valido"), (ORIGEN, "alterado"), ("null", "valido")],
    ids=["sin-token", "sin-origin", "origen-ajeno", "token-alterado", "origin-null"],
)
def test_logout_rechazado_responde_403_no_store_y_la_sesion_sigue_valida(
    entorno: Entorno, cliente: TestClient, origen: str | None, csrf: str | None
):
    login = _login(cliente)
    valido = login.headers["x-csrf-token"]
    presentado = {None: None, "valido": valido, "alterado": valido[:-1] + ("A" if valido[-1] != "A" else "B")}[csrf]

    respuesta = _logout(cliente, presentado, origen)

    assert respuesta.status_code == 403
    assert respuesta.json() == RECHAZADA
    assert respuesta.headers["cache-control"] == "no-store"
    assert not _revocada(entorno, entorno.sesiones()[0].id)
    assert cliente.get("/api/auth/me").status_code == 200


def test_logout_con_el_token_csrf_de_otra_sesion_responde_403_y_ambas_siguen_validas(
    entorno: Entorno, app
):
    uno, dos = _cliente(app), _cliente(app)
    _login(uno)
    login_dos = _login(dos)

    respuesta = _logout(uno, login_dos.headers["x-csrf-token"])

    assert respuesta.status_code == 403
    assert uno.get("/api/auth/me").status_code == 200
    assert dos.get("/api/auth/me").status_code == 200


def test_logout_revoca_solo_su_sesion(entorno: Entorno, app):
    uno, dos = _cliente(app), _cliente(app)
    login_uno = _login(uno)
    _login(dos)

    assert _logout(uno, login_uno.headers["x-csrf-token"]).status_code == 204

    assert dos.get("/api/auth/me").status_code == 200


def test_el_segundo_logout_con_la_misma_cookie_responde_401_y_no_cambia_otras_sesiones(
    entorno: Entorno, app
):
    uno, dos = _cliente(app), _cliente(app)
    login_uno = _login(uno)
    _login(dos)
    token = login_uno.cookies[NOMBRE_COOKIE]
    csrf = login_uno.headers["x-csrf-token"]
    assert _logout(uno, csrf).status_code == 204
    revocadas = entorno.db.execute(text("SELECT count(*) FROM sesion WHERE revocada_en IS NOT NULL")).scalar_one()

    repetido = _logout(_cliente(app), csrf, cookie=token)

    assert repetido.status_code == 401
    assert repetido.json() == NO_AUTENTICADO
    assert repetido.headers["cache-control"] == "no-store"
    assert _borra_la_cookie(repetido)
    assert entorno.db.execute(text("SELECT count(*) FROM sesion WHERE revocada_en IS NOT NULL")).scalar_one() == revocadas == 1


def test_logout_sin_sesion_responde_401_pero_sin_origin_responde_403(cliente: TestClient):
    sin_sesion = _logout(cliente, "cualquiera")
    sin_origin = _logout(cliente, "cualquiera", origen=None)

    assert (sin_sesion.status_code, sin_sesion.json()) == (401, NO_AUTENTICADO)
    assert (sin_origin.status_code, sin_origin.json()) == (403, RECHAZADA)


def test_el_token_csrf_de_una_sesion_revocada_no_sirve_con_la_cookie_de_otra(entorno: Entorno, app):
    uno, dos = _cliente(app), _cliente(app)
    login_uno = _login(uno)
    _login(dos)
    assert _logout(uno, login_uno.headers["x-csrf-token"]).status_code == 204

    respuesta = _logout(dos, login_uno.headers["x-csrf-token"])

    assert respuesta.status_code == 403
    assert dos.get("/api/auth/me").status_code == 200

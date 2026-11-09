"""Rechazos del login real: genericos, orden de validacion, 429, 503 y no-store (tarea 8.1).

Orden: 403 (`Origin`) -> 400 (direccion) -> 415 (`Content-Type`) -> 422 (cuerpo) -> 429 -> 503 -> 401.
Cuerpos exactos de DD-23. La app es la real (`crear_app`) con `db-test`.
"""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.cookies import NOMBRE_COOKIE
from tests.integration.app_auth import ORIGEN, ORIGEN_AJENO, crear_app_real
from tests.integration.datos_auth import (
    CONTRASENA_A,
    EMAIL,
    Entorno,
)

RECHAZO_LOGIN = {"detail": "No se pudo iniciar sesión."}
RECHAZADA = {"detail": "Solicitud rechazada."}
NO_PROCESABLE = {"detail": "No se pudo procesar la solicitud."}
TIPO_NO_ADMITIDO = {"detail": "Tipo de contenido no admitido."}
BLOQUEADO = {"detail": "Demasiados intentos. Intente más tarde."}
OCUPADO = {"detail": "Servicio ocupado. Intente más tarde."}
CREDENCIALES = {"codigo_consultorio": "ficticio-a", "email": EMAIL, "contrasena": CONTRASENA_A}
CUERPO = json.dumps(CREDENCIALES).encode()
URL = "/api/auth/login"


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


@pytest.fixture
def app(entorno: Entorno):
    return crear_app_real(entorno)


def _cliente(app, direccion=("203.0.113.7", 50000), **opciones) -> TestClient:
    return TestClient(app, base_url="https://testserver", client=direccion, **opciones)


@pytest.fixture
def cliente(app) -> TestClient:
    return _cliente(app)


def _login(cliente: TestClient, headers: dict | None = None, **cuerpo):
    return cliente.post(
        URL, json={**CREDENCIALES, **cuerpo}, headers={"Origin": ORIGEN, **(headers or {})}
    )


def _contar(entorno: Entorno, tabla: str) -> int:
    return entorno.db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


def _sin_efectos(entorno: Entorno) -> None:
    assert _contar(entorno, "sesion") == 0
    assert _contar(entorno, "intento_login") == 0
    assert entorno.verificador.llamadas == 0


def _sin_cookie_de_sesion(respuesta) -> bool:
    return not any(NOMBRE_COOKIE in v for v in respuesta.headers.get_list("set-cookie"))


def _fallar(cliente: TestClient, veces: int) -> None:
    for _ in range(veces):
        assert _login(cliente, contrasena="otra-contrasena-ficticia").status_code == 401


# --- 401 generico -----------------------------------------------------------------------------------


def _desactivar_usuario(e: Entorno) -> dict:
    e.db.execute(text("UPDATE usuario SET activo = false WHERE id = :u"), {"u": e.ua})
    return {}


def _desactivar_consultorio(e: Entorno) -> dict:
    e.db.execute(text("UPDATE consultorio SET activo = false WHERE id = :c"), {"c": e.a})
    return {}


def _sin_credencial(e: Entorno) -> dict:
    e.db.execute(text("UPDATE usuario SET credencial = NULL WHERE id = :u"), {"u": e.ua})
    return {"contrasena": "null"}


def _credencial_argon2i(e: Entorno) -> dict:
    valor = "$argon2i$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$RdescudvJCsgt3ub+b+dWRWJTmaaJObG"
    e.db.execute(text("UPDATE usuario SET credencial = :c WHERE id = :u"), {"c": valor, "u": e.ua})
    return {}


def _credencial_texto(e: Entorno) -> dict:
    e.db.execute(
        text("UPDATE usuario SET credencial = 'no-es-un-hash' WHERE id = :u"), {"u": e.ua}
    )
    return {}


CASOS_401 = {
    "contrasena-incorrecta": lambda e: {"contrasena": "otra-contrasena-ficticia"},
    "email-inexistente": lambda e: {"email": "nadie@example.test"},
    "codigo-inexistente": lambda e: {"codigo_consultorio": "no-existe"},
    "usuario-inactivo": _desactivar_usuario,
    "consultorio-inactivo": _desactivar_consultorio,
    "sin-credencial": _sin_credencial,
    "argon2i": _credencial_argon2i,
    "texto": _credencial_texto,
}


@pytest.mark.parametrize("caso", list(CASOS_401))
def test_todo_rechazo_de_credenciales_es_identico_y_no_emite_cookie(
    entorno: Entorno, cliente: TestClient, caso: str
):
    cuerpo = CASOS_401[caso](entorno)

    respuesta = _login(cliente, **cuerpo)

    assert respuesta.status_code == 401
    assert respuesta.json() == RECHAZO_LOGIN
    assert respuesta.headers["cache-control"] == "no-store"
    assert _sin_cookie_de_sesion(respuesta)
    assert _contar(entorno, "sesion") == 0
    assert _contar(entorno, "intento_login") == 1  # un fallo registrado, nada mas
    assert entorno.verificador.llamadas == 1  # una verificacion, real o ficticia


# --- 403, 400, 415 con el login real -------------------------------------------------------------


@pytest.mark.parametrize(
    "cabeceras",
    [
        {},
        {"Origin": "null"},
        {"Origin": ORIGEN_AJENO},
        {"Origin": ORIGEN + "/"},
        {"Origin": "http://LOCALHOST:5173"},
        {"Referer": ORIGEN + "/login"},
        {"Origin": ORIGEN_AJENO, "Content-Type": "application/x-www-form-urlencoded"},
    ],
    ids=["sin-origin", "null", "ajeno", "barra-final", "mayusculas", "solo-referer", "formulario-ajeno"],
)
def test_origin_ausente_o_no_permitido_responde_403_sin_efectos(
    entorno: Entorno, cliente: TestClient, cabeceras: dict[str, str]
):
    respuesta = cliente.post(
        URL, content=CUERPO, headers={"Content-Type": "application/json", **cabeceras}
    )

    assert respuesta.status_code == 403
    assert respuesta.json() == RECHAZADA
    assert respuesta.headers["cache-control"] == "no-store"
    assert _sin_cookie_de_sesion(respuesta)
    _sin_efectos(entorno)


@pytest.mark.parametrize("direccion", [None, ("testclient", 50000)], ids=["nulo", "testclient"])
def test_direccion_no_determinable_responde_400_sin_efectos(
    entorno: Entorno, app, direccion
):
    respuesta = _login(_cliente(app, direccion))

    assert respuesta.status_code == 400
    assert respuesta.json() == NO_PROCESABLE
    assert respuesta.headers["cache-control"] == "no-store"
    assert _sin_cookie_de_sesion(respuesta)
    _sin_efectos(entorno)


@pytest.mark.parametrize(
    "tipo",
    ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x", None],
    ids=["text-plain", "formulario", "multipart", "sin-content-type"],
)
def test_content_type_distinto_de_json_responde_415_sin_efectos(
    entorno: Entorno, cliente: TestClient, tipo: str | None
):
    headers = {"Origin": ORIGEN}
    if tipo is not None:
        headers["Content-Type"] = tipo

    respuesta = cliente.post(URL, content=CUERPO, headers=headers)

    assert respuesta.status_code == 415
    assert respuesta.json() == TIPO_NO_ADMITIDO
    assert respuesta.headers["cache-control"] == "no-store"
    assert _sin_cookie_de_sesion(respuesta)
    _sin_efectos(entorno)


# --- 422: cuerpo estricto --------------------------------------------------------------------------


def test_un_campo_no_declarado_responde_422_e_identifica_el_campo_sin_efectos(
    entorno: Entorno, cliente: TestClient
):
    respuesta = _login(cliente, consultorio_id=str(entorno.b))

    assert respuesta.status_code == 422
    assert ["body", "consultorio_id"] in [e["loc"] for e in respuesta.json()["detail"]]
    assert respuesta.headers["cache-control"] == "no-store"
    assert str(entorno.b) not in respuesta.text
    _sin_efectos(entorno)


def test_un_campo_faltante_responde_422_sin_efectos(entorno: Entorno, cliente: TestClient):
    cuerpo = {k: v for k, v in CREDENCIALES.items() if k != "codigo_consultorio"}

    respuesta = cliente.post(URL, json=cuerpo, headers={"Origin": ORIGEN})

    assert respuesta.status_code == 422
    assert ["body", "codigo_consultorio"] in [e["loc"] for e in respuesta.json()["detail"]]
    _sin_efectos(entorno)


def test_una_contrasena_de_129_caracteres_responde_422_sin_reflejarla_ni_verificar(
    entorno: Entorno, cliente: TestClient
):
    larga = "contrasena-ficticia-" + "x" * (129 - len("contrasena-ficticia-"))

    respuesta = _login(cliente, contrasena=larga)

    assert respuesta.status_code == 422
    assert larga not in respuesta.text
    assert "input" not in respuesta.text
    _sin_efectos(entorno)


def test_el_maximo_de_128_se_mide_sobre_la_entrada_sin_normalizar(
    entorno: Entorno, cliente: TestClient
):
    # 128 ligaduras U+FB01 ocupan 256 puntos de codigo tras NFKC, pero la entrada mide 128.
    respuesta = _login(cliente, contrasena="ﬁ" * 128)

    assert respuesta.status_code == 401
    assert respuesta.json() == RECHAZO_LOGIN


@pytest.mark.parametrize(
    "campo,largo", [("codigo_consultorio", 65), ("email", 255)], ids=["codigo", "email"]
)
def test_codigo_y_email_desmedidos_responden_422_sin_efectos(
    entorno: Entorno, cliente: TestClient, campo: str, largo: int
):
    respuesta = _login(cliente, **{campo: "a" * largo})

    assert respuesta.status_code == 422
    _sin_efectos(entorno)


def test_un_json_malformado_con_origin_valido_responde_422_sin_efectos(
    entorno: Entorno, cliente: TestClient
):
    respuesta = cliente.post(
        URL, content=b"{no es json", headers={"Origin": ORIGEN, "Content-Type": "application/json"}
    )

    assert respuesta.status_code == 422
    assert respuesta.headers["cache-control"] == "no-store"
    _sin_efectos(entorno)


# --- orden de rechazos ---------------------------------------------------------------------------------


def test_el_orden_de_los_rechazos_es_403_400_415_422(entorno: Entorno, app):
    sin_direccion = _cliente(app, None)
    con_direccion = _cliente(app)
    malo = b'{"codigo_consultorio": "ficticio-a", "consultorio_id": "x"}'

    sin_origin_ni_direccion = sin_direccion.post(
        URL, content=CUERPO, headers={"Content-Type": "text/plain"}
    )
    sin_direccion_y_texto = sin_direccion.post(
        URL, content=CUERPO, headers={"Origin": ORIGEN, "Content-Type": "text/plain"}
    )
    texto_y_cuerpo_malo = con_direccion.post(
        URL, content=malo, headers={"Origin": ORIGEN, "Content-Type": "text/plain"}
    )
    cuerpo_malo = con_direccion.post(
        URL, content=malo, headers={"Origin": ORIGEN, "Content-Type": "application/json"}
    )

    assert [
        sin_origin_ni_direccion.status_code,
        sin_direccion_y_texto.status_code,
        texto_y_cuerpo_malo.status_code,
        cuerpo_malo.status_code,
    ] == [403, 400, 415, 422]
    _sin_efectos(entorno)


def test_un_json_malformado_con_origin_ajeno_responde_403_antes_de_analizar_el_cuerpo(
    entorno: Entorno, cliente: TestClient
):
    respuesta = cliente.post(
        URL,
        content=b"{no es json",
        headers={"Origin": ORIGEN_AJENO, "Content-Type": "application/json"},
    )

    assert respuesta.status_code == 403
    _sin_efectos(entorno)


def test_el_422_va_antes_que_el_429(entorno: Entorno, cliente: TestClient):
    _fallar(cliente, 5)

    con_campo_extra = _login(cliente, consultorio_id="x")
    correcto = _login(cliente)

    assert (con_campo_extra.status_code, correcto.status_code) == (422, 429)


# --- 429 ---------------------------------------------------------------------------------------------------


def test_el_sexto_intento_responde_429_aun_con_la_contrasena_correcta_sin_verificar(
    entorno: Entorno, cliente: TestClient
):
    _fallar(cliente, 5)
    verificaciones = entorno.verificador.llamadas

    respuesta = _login(cliente)

    assert respuesta.status_code == 429
    assert respuesta.json() == BLOQUEADO
    assert respuesta.headers["retry-after"] == "900"
    assert respuesta.headers["cache-control"] == "no-store"
    assert _sin_cookie_de_sesion(respuesta)
    assert entorno.verificador.llamadas == verificaciones
    assert _contar(entorno, "sesion") == 0
    assert _contar(entorno, "intento_login") == 5


def test_el_retry_after_decrece_con_el_tiempo(entorno: Entorno, cliente: TestClient):
    from datetime import timedelta

    _fallar(cliente, 5)
    entorno.reloj.avanzar(timedelta(minutes=14, seconds=59, milliseconds=500))

    respuesta = _login(cliente)

    assert respuesta.status_code == 429
    assert respuesta.headers["retry-after"] == "1"


# --- 503 por saturacion de Argon2 ----------------------------------------------------------------------


def _ocupar_cupos(entorno: Entorno) -> None:
    for _ in range(4):
        assert entorno.limitador.semaforo.acquire(timeout=0)


def _liberar_cupos(entorno: Entorno) -> None:
    for _ in range(4):
        entorno.limitador.semaforo.release()


@pytest.mark.parametrize(
    "cuerpo",
    [{}, {"email": "nadie@example.test"}],
    ids=["cuenta-existente", "cuenta-inexistente"],
)
def test_sin_cupo_de_argon2_el_login_responde_503_sin_fallo_ni_sesion(
    entorno: Entorno, cliente: TestClient, cuerpo: dict
):
    _ocupar_cupos(entorno)
    try:
        respuesta = _login(cliente, **cuerpo)
    finally:
        _liberar_cupos(entorno)

    assert respuesta.status_code == 503
    assert respuesta.json() == OCUPADO
    assert respuesta.headers["retry-after"] == "5"
    assert respuesta.headers["cache-control"] == "no-store"
    assert _sin_cookie_de_sesion(respuesta)
    _sin_efectos(entorno)


def test_el_bloqueo_429_se_evalua_antes_que_la_saturacion_503(entorno: Entorno, cliente: TestClient):
    _fallar(cliente, 5)
    _ocupar_cupos(entorno)
    try:
        respuesta = _login(cliente)
    finally:
        _liberar_cupos(entorno)

    assert respuesta.status_code == 429


def _disponibles(entorno: Entorno) -> int:
    tomados = 0
    while entorno.limitador.semaforo.acquire(timeout=0):
        tomados += 1
    for _ in range(tomados):
        entorno.limitador.semaforo.release()
    return tomados


def test_el_cupo_se_libera_ante_errores_del_verificador(
    entorno: Entorno, app, monkeypatch: pytest.MonkeyPatch
):
    def explotar(contrasena, almacenado):
        raise RuntimeError("falla ficticia del verificador")

    monkeypatch.setattr(entorno.verificador, "verificar", explotar)
    cliente = _cliente(app, raise_server_exceptions=False)

    estados = [_login(cliente).status_code for _ in range(4)]
    monkeypatch.undo()

    assert estados == [500, 500, 500, 500]
    assert _disponibles(entorno) == 4
    assert _login(cliente).status_code == 200


def test_el_cupo_se_libera_ante_cancelaciones_del_verificador(
    entorno: Entorno, app, monkeypatch: pytest.MonkeyPatch
):
    def cancelar(contrasena, almacenado):
        raise asyncio.CancelledError

    monkeypatch.setattr(entorno.verificador, "verificar", cancelar)
    cliente = _cliente(app, raise_server_exceptions=False)

    for _ in range(4):
        try:
            _login(cliente)
        except BaseException:  # noqa: BLE001 - la cancelacion puede propagarse hasta el cliente
            pass
    monkeypatch.undo()

    assert _disponibles(entorno) == 4


# --- no-store en todas las respuestas del login ------------------------------------------------------------


def test_todas_las_respuestas_del_login_son_no_store(entorno: Entorno, cliente: TestClient):
    exitosa = _login(cliente)
    cliente.cookies.clear()
    rechazada = _login(cliente, contrasena="otra-contrasena-ficticia")
    sin_origin = cliente.post(URL, content=CUERPO, headers={"Content-Type": "application/json"})
    texto_plano = cliente.post(
        URL, content=CUERPO, headers={"Origin": ORIGEN, "Content-Type": "text/plain"}
    )
    campo_no_declarado = _login(cliente, consultorio_id="x")

    estados = [
        r.status_code for r in (exitosa, rechazada, sin_origin, texto_plano, campo_no_declarado)
    ]
    assert estados == [200, 401, 403, 415, 422]
    for respuesta in (exitosa, rechazada, sin_origin, texto_plano, campo_no_declarado):
        assert respuesta.headers["cache-control"] == "no-store"


# --- rotacion de sesion y limpieza ---------------------------------------------------------------------------


def test_un_login_con_cookie_de_sesion_valida_la_revoca_y_emite_otra(
    entorno: Entorno, cliente: TestClient
):
    primera = _login(cliente)  # el cliente conserva la cookie en su jar
    token_anterior = primera.cookies[NOMBRE_COOKIE]

    segunda = _login(cliente)

    assert segunda.status_code == 200
    assert segunda.cookies[NOMBRE_COOKIE] != token_anterior
    estados = entorno.db.execute(text("SELECT revocada_en IS NOT NULL FROM sesion")).scalars().all()
    assert sorted(estados) == [False, True]


# --- 12.2: la contrasena no se normaliza (respuesta HTTP completa) ------------------------------------


@pytest.mark.parametrize(
    "variante",
    [str.upper, lambda c: c + " "],
    ids=["mayusculas", "espacio-final"],
)
def test_la_contrasena_correcta_en_mayusculas_o_con_espacio_final_responde_el_rechazo_generico(
    entorno: Entorno, cliente: TestClient, variante
):
    contrasena = variante(CONTRASENA_A)
    assert contrasena != CONTRASENA_A

    respuesta = _login(cliente, contrasena=contrasena)

    assert respuesta.status_code == 401
    assert respuesta.json() == RECHAZO_LOGIN
    assert respuesta.headers["cache-control"] == "no-store"
    assert _sin_cookie_de_sesion(respuesta)
    assert _contar(entorno, "sesion") == 0
    assert _contar(entorno, "intento_login") == 1
    # La contrasena exacta, enviada despues, si inicia sesion.
    assert _login(cliente).status_code == 200


# --- 12.2: el bloqueo de IP no afecta sesiones abiertas (por HTTP) ----------------------------------------


def test_el_bloqueo_de_ip_deja_intactas_las_sesiones_abiertas_me_200_y_logout_204(
    entorno: Entorno, app
):
    sesion_abierta = _cliente(app)
    login = _login(sesion_abierta)
    assert login.status_code == 200
    token = login.cookies[NOMBRE_COOKIE]
    csrf = login.headers["x-csrf-token"]
    # 30 fallos desde la MISMA direccion sobre 30 pares distintos: la IP queda bloqueada.
    otro_cliente = _cliente(app)
    for numero in range(30):
        respuesta = _login(otro_cliente, email=f"nadie{numero}@example.test")
        assert respuesta.status_code == 401
    bloqueada = _login(otro_cliente)  # credenciales correctas, par sin fallos, IP bloqueada
    assert bloqueada.status_code == 429
    assert bloqueada.json() == BLOQUEADO

    me = _cliente(app).get("/api/auth/me", headers={"Cookie": f"{NOMBRE_COOKIE}={token}"})
    cierre = _cliente(app).post(
        "/api/auth/logout",
        headers={
            "Cookie": f"{NOMBRE_COOKIE}={token}",
            "Origin": ORIGEN,
            "X-CSRF-Token": csrf,
        },
    )

    assert me.status_code == 200
    assert me.json()["usuario"]["email"] == EMAIL
    assert cierre.status_code == 204
    assert cierre.content == b""
    revocadas = entorno.db.execute(
        text("SELECT count(*) FROM sesion WHERE revocada_en IS NOT NULL")
    ).scalar_one()
    assert revocadas == 1


# --- 12.2: rechazos previos no cuentan (10 por tipo, como en la spec) --------------------------------------


def test_diez_rechazos_previos_de_cada_tipo_no_registran_fallos_y_el_login_correcto_responde_200(
    entorno: Entorno, app
):
    cliente = _cliente(app)
    sin_direccion = _cliente(app, None)
    esperados = {"sin Origin": 403, "sin direccion": 400, "text/plain": 415, "campo no declarado": 422}
    obtenidos: dict[str, set[int]] = {nombre: set() for nombre in esperados}

    for _ in range(10):
        obtenidos["sin Origin"].add(
            cliente.post(URL, content=CUERPO, headers={"Content-Type": "application/json"}).status_code
        )
        obtenidos["sin direccion"].add(_login(sin_direccion).status_code)
        obtenidos["text/plain"].add(
            cliente.post(
                URL, content=CUERPO, headers={"Origin": ORIGEN, "Content-Type": "text/plain"}
            ).status_code
        )
        obtenidos["campo no declarado"].add(_login(cliente, consultorio_id=str(entorno.b)).status_code)

    assert obtenidos == {nombre: {codigo} for nombre, codigo in esperados.items()}
    # 40 rechazos previos con las mismas credenciales: superan el limite del par (5) y el de la IP (30)
    # si se hubieran contado; no hay fallos, ni verificaciones, ni sesiones.
    _sin_efectos(entorno)

    correcto = _login(cliente)

    assert correcto.status_code == 200
    assert _contar(entorno, "sesion") == 1
    assert _contar(entorno, "intento_login") == 0

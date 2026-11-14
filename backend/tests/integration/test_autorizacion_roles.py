"""Autorizacion por rol y respuestas 401/403/404 (tareas 7.3 y 7.4; DD-16 a DD-18, spec `autorizacion-roles`).

Rutas de prueba solo en la app de pruebas (`app_auth.py`); la app real se usa para `/me` y logout. Las
sesiones comparten la transaccion revertible de la fixture `sesion`. Datos ficticios (D1).
"""

import re
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.auth.cookies import NOMBRE_COOKIE
from app.models.usuario import Rol
from tests.integration.app_auth import ORIGEN, AppDePrueba, crear_app_de_prueba, crear_app_real
from tests.integration.datos_auth import (
    CONTRASENA_A,
    CONTRASENA_B,
    EMAIL,
    Entorno,
    crear_usuario,
    hash_rapido,
)

DENEGADO = {"detail": "Acceso denegado."}
NO_ENCONTRADO = {"detail": "No encontrado."}
NO_AUTENTICADO = {"detail": "No autenticado."}
RECHAZADA = {"detail": "Solicitud rechazada."}
EMAIL_POR_ROL = {
    Rol.ADMINISTRADOR: "administrador.ficticio@example.test",
    Rol.SECRETARIA: EMAIL,
    Rol.ODONTOLOGO: "odontologo.ficticio@example.test",
}
SENTENCIA_SOBRE_USUARIO = re.compile(r"\busuario\b", re.IGNORECASE)


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    e = Entorno(sesion)
    for rol, email in EMAIL_POR_ROL.items():
        if rol is not Rol.SECRETARIA:
            crear_usuario(
                sesion, e.a, email=email, nombre=f"Persona {rol.value}", rol=rol.value,
                credencial=hash_rapido(CONTRASENA_A),
            )
    sesion.commit()
    return e


@pytest.fixture
def app_prueba(entorno: Entorno) -> AppDePrueba:
    return crear_app_de_prueba(entorno)


@pytest.fixture
def cliente(app_prueba: AppDePrueba) -> TestClient:
    return TestClient(app_prueba.app, base_url="https://testserver", client=("203.0.113.7", 50000))


def _sesion_de(entorno: Entorno, rol: Rol):
    return entorno.login(email=EMAIL_POR_ROL[rol], contrasena=CONTRASENA_A)


def _cookie(iniciada) -> dict[str, str]:
    return {"Cookie": f"{NOMBRE_COOKIE}={iniciada.token}"}


def _con_csrf(app_prueba: AppDePrueba, iniciada, origen: str | None = ORIGEN) -> dict[str, str]:
    cabeceras = {**_cookie(iniciada), "X-CSRF-Token": app_prueba.token_csrf(iniciada.sesion_id)}
    if origen is not None:
        cabeceras["Origin"] = origen
    return cabeceras


def _sentencias(entorno: Entorno):
    capturadas: list[str] = []

    def capturar(conexion, cursor, sentencia, parametros, contexto, many):
        capturadas.append(sentencia)

    conexion = entorno.db.get_bind()
    event.listen(conexion, "before_cursor_execute", capturar)
    return capturadas, lambda: event.remove(conexion, "before_cursor_execute", capturar)


# --- 7.3 Matriz de roles ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ruta", "esperados"),
    [
        ("/prueba/solo-admin", {Rol.ADMINISTRADOR: 200, Rol.SECRETARIA: 403, Rol.ODONTOLOGO: 403}),
        ("/prueba/admin-o-secretaria", {Rol.ADMINISTRADOR: 200, Rol.SECRETARIA: 200, Rol.ODONTOLOGO: 403}),
    ],
)
def test_matriz_de_los_tres_roles(entorno: Entorno, cliente: TestClient, ruta, esperados):
    for rol, estado in esperados.items():
        iniciada = _sesion_de(entorno, rol)

        respuesta = cliente.get(ruta, headers=_cookie(iniciada))

        assert respuesta.status_code == estado, (ruta, rol)
        if estado == 403:
            assert respuesta.json() == DENEGADO
            assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("ruta", ["/prueba/solo-admin", "/prueba/admin-o-secretaria"])
def test_sin_sesion_responde_401_antes_de_evaluar_el_rol(cliente: TestClient, ruta):
    respuesta = cliente.get(ruta)

    assert respuesta.status_code == 401 and respuesta.json() == NO_AUTENTICADO


def test_sin_token_csrf_la_secretaria_recibe_el_403_de_csrf_antes_que_el_del_rol(
    entorno: Entorno, cliente: TestClient
):
    iniciada = _sesion_de(entorno, Rol.SECRETARIA)

    respuesta = cliente.post("/prueba/cambia-admin", headers={**_cookie(iniciada), "Origin": ORIGEN})

    assert respuesta.status_code == 403 and respuesta.json() == RECHAZADA


def test_orden_origen_identidad_csrf_rol_en_una_operacion_que_cambia_estado(
    entorno: Entorno, app_prueba: AppDePrueba, cliente: TestClient
):
    secretaria = _sesion_de(entorno, Rol.SECRETARIA)
    administrador = _sesion_de(entorno, Rol.ADMINISTRADOR)

    sin_sesion = cliente.post("/prueba/cambia-admin", headers={"Origin": ORIGEN})
    origen_ajeno = cliente.post(
        "/prueba/cambia-admin", headers=_con_csrf(app_prueba, secretaria, "http://otro-origen.invalid")
    )
    por_rol = cliente.post("/prueba/cambia-admin", headers=_con_csrf(app_prueba, secretaria))
    permitida = cliente.post("/prueba/cambia-admin", headers=_con_csrf(app_prueba, administrador))

    assert (sin_sesion.status_code, sin_sesion.json()) == (401, NO_AUTENTICADO)
    assert (origen_ajeno.status_code, origen_ajeno.json()) == (403, RECHAZADA)
    assert (por_rol.status_code, por_rol.json()) == (403, DENEGADO)
    assert permitida.status_code == 200
    assert app_prueba.cambios == ["cambio-admin"]  # solo la permitida ejecuto la ruta


def test_el_403_por_rol_es_identico_para_propio_ajeno_e_inexistente_y_no_toca_usuario(
    entorno: Entorno, cliente: TestClient
):
    secretaria = _sesion_de(entorno, Rol.SECRETARIA)
    administrador = _sesion_de(entorno, Rol.ADMINISTRADOR)
    propio, ajeno, inexistente = entorno.ua, entorno.ub, uuid.uuid4()

    capturadas, quitar = _sentencias(entorno)
    try:
        respuestas = [
            cliente.get(f"/prueba/admin/usuarios/{u}", headers=_cookie(secretaria))
            for u in (propio, ajeno, inexistente)
        ]
        denegadas = list(capturadas)
        cliente.get(f"/prueba/admin/usuarios/{propio}", headers=_cookie(administrador))
        control = [s for s in capturadas[len(denegadas):] if SENTENCIA_SOBRE_USUARIO.search(s)]
    finally:
        quitar()

    assert {r.status_code for r in respuestas} == {403}
    assert all(r.json() == DENEGADO for r in respuestas)
    assert len({tuple(sorted(r.headers.items())) for r in respuestas}) == 1
    assert [s for s in denegadas if SENTENCIA_SOBRE_USUARIO.search(s)] == []
    # Control: el detector ve la consulta cuando el administrador si llega al recurso.
    assert control, "el detector de sentencias sobre usuario no detecto la consulta permitida"


# --- Sesion propia accesible para los tres roles (app real) ------------------------------------------


@pytest.mark.parametrize("rol", list(Rol), ids=[r.value for r in Rol])
def test_me_y_logout_estan_disponibles_para_cada_rol(entorno: Entorno, rol: Rol):
    sesiones = {r: _sesion_de(entorno, r) for r in Rol}
    cliente_real = TestClient(
        crear_app_real(entorno), base_url="https://testserver", client=("203.0.113.7", 50000)
    )
    propia = sesiones[rol]

    me = cliente_real.get("/api/auth/me", headers=_cookie(propia))
    assert me.status_code == 200 and me.json()["usuario"]["rol"] == rol.value

    logout = cliente_real.post(
        "/api/auth/logout",
        headers={**_cookie(propia), "Origin": ORIGEN, "X-CSRF-Token": me.headers["x-csrf-token"]},
    )
    assert logout.status_code == 204
    assert cliente_real.get("/api/auth/me", headers=_cookie(propia)).status_code == 401
    for otro, sesion_ajena in sesiones.items():
        if otro is not rol:
            assert cliente_real.get("/api/auth/me", headers=_cookie(sesion_ajena)).status_code == 200


# --- 7.4 404 identico para recurso ajeno o inexistente -----------------------------------------------


def test_usuario_de_b_y_uuid_inexistente_responden_404_identicos_y_el_propio_200(
    entorno: Entorno, cliente: TestClient
):
    secretaria = _sesion_de(entorno, Rol.SECRETARIA)

    ajeno = cliente.get(f"/prueba/usuarios/{entorno.ub}", headers=_cookie(secretaria))
    inexistente = cliente.get(f"/prueba/usuarios/{uuid.uuid4()}", headers=_cookie(secretaria))
    propio = cliente.get(f"/prueba/usuarios/{entorno.ua}", headers=_cookie(secretaria))

    assert ajeno.status_code == inexistente.status_code == 404
    assert ajeno.json() == inexistente.json() == NO_ENCONTRADO
    assert dict(ajeno.headers) == dict(inexistente.headers)
    assert ajeno.headers["cache-control"] == "no-store"
    assert propio.status_code == 200
    assert propio.json() == {"id": str(entorno.ua), "email": EMAIL}


def test_el_404_no_depende_del_rol(entorno: Entorno, cliente: TestClient):
    for rol in Rol:
        iniciada = _sesion_de(entorno, rol)
        respuesta = cliente.get(f"/prueba/usuarios/{entorno.ub}", headers=_cookie(iniciada))
        assert (respuesta.status_code, respuesta.json()) == (404, NO_ENCONTRADO)


def test_un_identificador_mal_formado_no_revela_nada_del_recurso(
    entorno: Entorno, cliente: TestClient
):
    secretaria = _sesion_de(entorno, Rol.SECRETARIA)

    respuesta = cliente.get("/prueba/usuarios/no-es-un-uuid", headers=_cookie(secretaria))

    assert respuesta.status_code == 422
    assert CONTRASENA_B not in respuesta.text

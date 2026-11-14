"""Regresion de C-03 con los roles de conexion efectivos (5.6 y 9.4; DD-24, DD-27).

App real sobre `db-test` con conexiones reales de `turnos_app` y `turnos_login`. El servicio usa el
reloj y el verificador de prueba (como las pruebas de concurrencia de C-03).
"""

import pytest
from sqlalchemy import event, text

from app.models.usuario import Rol


def _de(datos, consultorio: str = "a", rol: Rol = Rol.SECRETARIA):
    c = getattr(datos, consultorio)
    return c, c.usuarios[rol]


def _escalar(motor_admin, sql: str, **params):
    with motor_admin.connect() as conexion:
        return conexion.execute(text(sql), params).scalar_one()


# --- 5.6 ---------------------------------------------------------------------------------------


def test_sesion_creada_en_el_consultorio_de_la_cuenta(api_real, datos_ab, motor_admin):
    for letra in ("a", "b"):
        c, u = _de(datos_ab, letra)
        assert api_real.login(api_real.cliente(), c.codigo, u.email, u.contrasena).status_code == 200
        assert (
            _escalar(motor_admin, "SELECT consultorio_id FROM sesion WHERE usuario_id = :u", u=u.id)
            == c.id
        )


def test_login_rechazado_sin_contexto_y_sin_abrir_la_transaccion_de_sesion(api_real, datos_ab):
    sentencias: list[tuple[str, str]] = []
    for etiqueta, motor in (("app", api_real.app.state.engine), ("login", api_real.app.state.engine_login)):

        def grabar(conexion, cursor, sentencia, parametros, contexto, many, etiqueta=etiqueta):  # noqa: ANN001
            sentencias.append((etiqueta, sentencia))

        event.listen(motor, "before_cursor_execute", grabar)
    c, u = _de(datos_ab)

    respuesta = api_real.login(api_real.cliente(), c.codigo, u.email, "contrasena-incorrecta")

    assert respuesta.status_code == 401
    assert [s for etiqueta, s in sentencias if etiqueta == "app"] == []  # T2 nunca se abrio
    assert not any("app.consultorio_id" in s for _etiqueta, s in sentencias)
    assert any(etiqueta == "login" for etiqueta, _ in sentencias)


def test_revocacion_de_la_sesion_entrante_de_otro_consultorio(api_real, datos_ab, motor_admin):
    b, ub = _de(datos_ab, "b")
    cliente = api_real.cliente()
    assert api_real.login(cliente, b.codigo, ub.email, ub.contrasena).status_code == 200
    assert _escalar(motor_admin, "SELECT revocada_en FROM sesion WHERE usuario_id = :u", u=ub.id) is None
    a, ua = _de(datos_ab, "a")

    # Login exitoso en A con la cookie de la sesion valida de B en la peticion.
    assert api_real.login(cliente, a.codigo, ua.email, ua.contrasena).status_code == 200

    assert _escalar(motor_admin, "SELECT revocada_en FROM sesion WHERE usuario_id = :u", u=ub.id) is not None
    assert _escalar(motor_admin, "SELECT revocada_en FROM sesion WHERE usuario_id = :u", u=ua.id) is None


@pytest.mark.parametrize("letra", ["a", "b"])
def test_la_cookie_de_un_consultorio_nunca_da_la_identidad_del_otro(api_real, datos_ab, letra):
    c, u = _de(datos_ab, letra)
    cliente = api_real.cliente()
    assert api_real.login(cliente, c.codigo, u.email, u.contrasena).status_code == 200

    me = cliente.get("/api/auth/me")

    assert me.status_code == 200
    assert me.json()["consultorio"]["nombre"] == c.nombre
    assert me.json()["usuario"]["email"] == u.email


# --- 9.4 Regresion de C-03 con los roles efectivos (DD-24, spec `pruebas-aislamiento`) ---------------------

from datetime import timedelta  # noqa: E402

from app.api.auth import DETALLE_LOGIN_RECHAZADO  # noqa: E402
from app.auth.cookies import NOMBRE_COOKIE  # noqa: E402
from tests.integration.app_auth import ORIGEN  # noqa: E402
from tests.isolation.conftest import construir_api  # noqa: E402

RECHAZO_DE_LOGIN = {"detail": DETALLE_LOGIN_RECHAZADO}
INCORRECTA = "contrasena-incorrecta-ficticia"


def _admin(motor_admin, sql: str, **params) -> None:
    with motor_admin.begin() as conexion:
        conexion.execute(text(sql), params)


def _fila_de_usuario(motor_admin, usuario_id):
    with motor_admin.connect() as conexion:
        return conexion.execute(
            text("SELECT credencial, xmin::text FROM usuario WHERE id = :u"), {"u": usuario_id}
        ).one()


def _logout(cliente, csrf: str | None):
    cabeceras = {"Origin": ORIGEN}
    if csrf is not None:
        cabeceras["X-CSRF-Token"] = csrf
    return cliente.post("/api/auth/logout", headers=cabeceras)


def test_flujo_login_me_renovacion_tras_61_segundos_y_logout(api_real, datos_ab, motor_admin):
    a, u = _de(datos_ab)
    cliente = api_real.cliente()

    login = api_real.login(cliente, a.codigo, u.email, u.contrasena)
    me = cliente.get("/api/auth/me")
    api_real.reloj.avanzar(timedelta(seconds=61))
    renovada = cliente.get("/api/auth/me")
    ultimo_uso = _escalar(motor_admin, "SELECT ultimo_uso_en FROM sesion WHERE usuario_id = :u", u=u.id)
    cerrar = _logout(cliente, renovada.headers["x-csrf-token"])

    assert (login.status_code, me.status_code, renovada.status_code, cerrar.status_code) == (200, 200, 200, 204)
    assert ultimo_uso == api_real.reloj.ahora()
    assert _escalar(motor_admin, "SELECT revocada_en FROM sesion WHERE usuario_id = :u", u=u.id) is not None
    assert cliente.get("/api/auth/me").status_code == 401


def test_rechazos_genericos_con_el_mismo_cuerpo_y_sin_cookie(api_real, datos_ab, motor_admin):
    a, secretaria = _de(datos_ab)
    _, odontologo = _de(datos_ab, "a", Rol.ODONTOLOGO)
    _, administrador = _de(datos_ab, "a", Rol.ADMINISTRADOR)
    b, de_b = _de(datos_ab, "b")
    _admin(motor_admin, "UPDATE usuario SET activo = false WHERE id = :u", u=administrador.id)
    _admin(motor_admin, "UPDATE consultorio SET activo = false WHERE id = :c", c=b.id)
    with motor_admin.begin() as conexion:  # sin credencial: solo el rol de administracion puede escribirla
        conexion.execute(text("UPDATE usuario SET credencial = NULL WHERE id = :u"), {"u": odontologo.id})
    casos = [
        (a.codigo, secretaria.email, INCORRECTA),
        (a.codigo, "no.existe@example.test", secretaria.contrasena),
        ("consultorio-inexistente", secretaria.email, secretaria.contrasena),
        (a.codigo, administrador.email, administrador.contrasena),
        (b.codigo, de_b.email, de_b.contrasena),
        (a.codigo, odontologo.email, odontologo.contrasena),
    ]

    respuestas = [
        api_real.login(api_real.cliente(ip=f"203.0.113.{10 + i}"), codigo, email, clave)
        for i, (codigo, email, clave) in enumerate(casos)
    ]

    assert [r.status_code for r in respuestas] == [401] * 6
    assert all(r.json() == RECHAZO_DE_LOGIN for r in respuestas)
    assert all("set-cookie" not in r.headers for r in respuestas)


def test_login_con_credencial_de_parametros_anteriores_responde_200_sin_cambiar_la_fila(
    api_real, datos_ab, motor_admin
):
    a, u = _de(datos_ab)  # el arnes crea los hashes con t=2 (parametros anteriores a la politica)
    antes = _fila_de_usuario(motor_admin, u.id)
    assert "t=2" in antes[0]

    respuesta = api_real.login(api_real.cliente(), a.codigo, u.email, u.contrasena)

    assert respuesta.status_code == 200
    assert _fila_de_usuario(motor_admin, u.id) == antes  # credencial y xmin sin cambios (R2-01)


def test_cinco_fallos_del_mismo_par_dan_401_y_el_sexto_429_con_retry_after(api_real, datos_ab):
    a, u = _de(datos_ab)
    cliente = api_real.cliente()

    respuestas = [api_real.login(cliente, a.codigo, u.email, INCORRECTA) for _ in range(6)]

    assert [r.status_code for r in respuestas] == [401] * 5 + [429]
    assert int(respuestas[5].headers["retry-after"]) > 0
    assert respuestas[5].headers["cache-control"] == "no-store"


def test_el_limite_por_direccion_bloquea_al_fallo_31_aunque_cambien_las_cuentas(api_real, datos_ab):
    a, _ = _de(datos_ab)
    cliente = api_real.cliente(ip="203.0.113.99")

    respuestas = [
        api_real.login(cliente, a.codigo, f"inexistente{i}@example.test", INCORRECTA) for i in range(31)
    ]

    assert [r.status_code for r in respuestas] == [401] * 30 + [429]
    assert "retry-after" in respuestas[30].headers


def test_un_exito_descarta_los_fallos_previos_de_la_cuenta(api_real, datos_ab):
    a, u = _de(datos_ab)
    cliente = api_real.cliente()
    previos = [api_real.login(cliente, a.codigo, u.email, INCORRECTA).status_code for _ in range(4)]

    exito = api_real.login(cliente, a.codigo, u.email, u.contrasena)
    posteriores = [api_real.login(cliente, a.codigo, u.email, INCORRECTA).status_code for _ in range(4)]

    assert previos == [401] * 4 and exito.status_code == 200
    assert posteriores == [401] * 4  # ninguno 429: los cuatro previos ya no cuentan


def test_logout_sin_token_csrf_responde_403_y_la_sesion_sigue_valida(api_real, datos_ab, motor_admin):
    a, u = _de(datos_ab)
    cliente = api_real.cliente()
    assert api_real.login(cliente, a.codigo, u.email, u.contrasena).status_code == 200

    respuesta = _logout(cliente, None)

    assert respuesta.status_code == 403
    assert _escalar(motor_admin, "SELECT revocada_en FROM sesion WHERE usuario_id = :u", u=u.id) is None
    assert cliente.get("/api/auth/me").status_code == 200


def test_un_usuario_desactivado_con_sesion_abierta_recibe_401(api_real, datos_ab, motor_admin):
    a, u = _de(datos_ab)
    cliente = api_real.cliente()
    assert api_real.login(cliente, a.codigo, u.email, u.contrasena).status_code == 200
    assert cliente.get("/api/auth/me").status_code == 200

    _admin(motor_admin, "UPDATE usuario SET activo = false WHERE id = :u", u=u.id)

    assert cliente.get("/api/auth/me").status_code == 401


def test_cambiar_auth_secret_key_invalida_las_sesiones_existentes(api_real, datos_ab, url_app, url_login):
    a, u = _de(datos_ab)
    cliente = api_real.cliente()
    assert api_real.login(cliente, a.codigo, u.email, u.contrasena).status_code == 200
    token = cliente.cookies.get(NOMBRE_COOKIE)
    otra = construir_api(url_app, url_login)  # AUTH_SECRET_KEY distinta (se genera por llamada)
    try:
        assert otra.settings.auth_secret_key.get_secret_value() != api_real.settings.auth_secret_key.get_secret_value()
        con_otra_clave = otra.cliente().get("/api/auth/me", headers={"Cookie": f"{NOMBRE_COOKIE}={token}"})
        con_la_original = api_real.cliente().get("/api/auth/me", headers={"Cookie": f"{NOMBRE_COOKIE}={token}"})
    finally:
        otra.app.state.engine.dispose()
        otra.app.state.engine_login.dispose()

    assert con_otra_clave.status_code == 401
    assert con_la_original.status_code == 200


def test_credencial_reemplazada_durante_el_login_queda_la_del_comando_y_el_login_no_la_modifica(
    datos_ab, motor_admin, url_app, url_login
):
    # Spec `autenticacion-sesion`, "Credencial reemplazada durante el login": el login ya leyo la
    # credencial (T1) cuando el comando local (rol de administracion) confirma otra; sin rehash, el
    # login nunca escribe `usuario`.
    from tests.integration.datos_auth import VerificadorEspia, hash_rapido

    a, u = _de(datos_ab)
    nueva = hash_rapido("contrasena-del-comando-ficticia-1", time_cost=3)

    class VerificadorQueReemplaza(VerificadorEspia):
        def verificar(self, contrasena, almacenado):
            if self.llamadas == 0:  # una sola vez, ya con la credencial leida por el login
                with motor_admin.begin() as conexion:
                    conexion.execute(
                        text("UPDATE usuario SET credencial = :n WHERE id = :u"), {"n": nueva, "u": u.id}
                    )
            return super().verificar(contrasena, almacenado)

    api = construir_api(url_app, url_login, verificador=VerificadorQueReemplaza())
    try:
        respuesta = api.login(api.cliente(), a.codigo, u.email, u.contrasena)
    finally:
        api.app.state.engine.dispose()
        api.app.state.engine_login.dispose()

    assert respuesta.status_code == 200  # autentico con la credencial que ya habia leido
    assert _fila_de_usuario(motor_admin, u.id)[0] == nueva  # la final es la del comando

"""Servicio de autenticacion con reloj inyectado (tarea 6.2; DD-03, DD-04, DD-06, DD-09, DD-29).

Contra db-test. Cada prueba confirma (`commit`) sus datos de preparacion en el SAVEPOINT de la
fixture `sesion`: el servicio hace `commit`/`rollback` propios y la transaccion exterior se revierte.
"""

import asyncio
import unicodedata
from datetime import timedelta

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.auth.claves import hmac_de_token, token_valido
from app.auth.concurrencia import CUPOS_POR_PROCESO, LimitadorArgon2, ServicioOcupado
from app.auth.servicio import (
    ConfigAuth,
    LoginRechazado,
    ServicioAuth,
)
from tests.integration.datos_auth import (
    AHORA,
    CLAVE_HMAC,
    CONTRASENA_A,
    CONTRASENA_B,
    EMAIL,
    Entorno,
    hash_rapido,
    hasher_rapido,
    insertar_sesion,
)

@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


# --- login exitoso -----------------------------------------------------------------------


def test_login_exitoso_crea_una_sesion_con_solo_el_hmac_del_token(entorno: Entorno):
    iniciada = entorno.login()

    assert token_valido(iniciada.token)
    assert (iniciada.nombre, iniciada.email, iniciada.rol) == ("Persona A", EMAIL, "secretaria")
    assert iniciada.consultorio_nombre == "Consultorio Ficticio A"
    (fila,) = entorno.sesiones()
    assert fila.id == iniciada.sesion_id
    assert (fila.consultorio_id, fila.usuario_id) == (entorno.a, entorno.ua)
    assert bytes(fila.token_hmac) == hmac_de_token(CLAVE_HMAC, iniciada.token)
    assert len(bytes(fila.token_hmac)) == 32
    assert (fila.creada_en, fila.ultimo_uso_en) == (AHORA, AHORA)
    assert fila.vence_absoluto_en == AHORA + timedelta(hours=12)
    assert fila.revocada_en is None
    assert iniciada.token not in " ".join(str(columna) for columna in fila)
    assert entorno.intentos() == 0


def test_dos_logins_dan_tokens_y_sesiones_distintos(entorno: Entorno):
    primero, segundo = entorno.login(), entorno.login()

    assert primero.token != segundo.token
    assert primero.sesion_id != segundo.sesion_id
    assert len(entorno.sesiones()) == 2


def test_codigo_y_email_se_normalizan(entorno: Entorno):
    iniciada = entorno.login(codigo=" FICTICIO-A ", email=" Persona.Ficticia@Example.TEST ")

    assert iniciada.email == EMAIL


def test_la_contrasena_no_se_normaliza_salvo_nfkc(entorno: Entorno):
    for incorrecta in (CONTRASENA_A.upper(), CONTRASENA_A + " "):
        with pytest.raises(LoginRechazado):
            entorno.login(contrasena=incorrecta)
    assert entorno.sesiones() == []


def test_nfkc_al_verificar_equivale_compuesta_y_descompuesta(entorno: Entorno):
    compuesta = "contraseña-de-prueba-ñ1"
    descompuesta = unicodedata.normalize("NFD", compuesta)
    assert compuesta != descompuesta
    entorno.db.execute(
        text("UPDATE usuario SET credencial = :c WHERE id = :u"),
        {"c": hash_rapido(compuesta), "u": entorno.ua},
    )
    entorno.db.commit()

    assert entorno.login(contrasena=descompuesta).nombre == "Persona A"


def test_el_login_no_aplica_la_politica_de_contrasenas_nuevas(entorno: Entorno):
    corta = "doce-chars-1"
    assert len(corta) == 12
    entorno.db.execute(
        text("UPDATE usuario SET credencial = :c WHERE id = :u"),
        {"c": hash_rapido(corta), "u": entorno.ua},
    )
    entorno.db.commit()

    assert entorno.login(contrasena=corta).nombre == "Persona A"
    for incorrecta in ("abc", "x" * 20):
        with pytest.raises(LoginRechazado) as error:
            entorno.login(contrasena=incorrecta)
        assert str(error.value) == ""


def test_aislamiento_de_cuentas_la_contrasena_de_b_no_autentica_en_a(entorno: Entorno):
    with pytest.raises(LoginRechazado):
        entorno.login(codigo="ficticio-a", contrasena=CONTRASENA_B)

    iniciada = entorno.login(codigo="ficticio-b", contrasena=CONTRASENA_B)

    assert iniciada.consultorio_nombre == "Consultorio Ficticio B"
    (fila,) = entorno.sesiones()
    assert (fila.consultorio_id, fila.usuario_id) == (entorno.b, entorno.ub)


# --- rechazos genericos ------------------------------------------------------------------


def _desactivar_usuario(e: Entorno):
    e.db.execute(text("UPDATE usuario SET activo = false WHERE id = :u"), {"u": e.ua})


def _desactivar_consultorio(e: Entorno):
    e.db.execute(text("UPDATE consultorio SET activo = false WHERE id = :c"), {"c": e.a})


def _credencial_nula(e: Entorno):
    e.db.execute(text("UPDATE usuario SET credencial = NULL WHERE id = :u"), {"u": e.ua})


def _credencial_argon2i(e: Entorno):
    e.db.execute(
        text("UPDATE usuario SET credencial = :c WHERE id = :u"),
        {"c": "$argon2i$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$aGFzaGhhc2hoYXNo", "u": e.ua},
    )


def _credencial_texto(e: Entorno):
    e.db.execute(
        text("UPDATE usuario SET credencial = 'esto-no-es-un-hash' WHERE id = :u"), {"u": e.ua}
    )


@pytest.mark.parametrize(
    ("preparar", "datos"),
    [
        (None, {"contrasena": "otra-contrasena-ficticia"}),
        (None, {"email": "nadie@example.test"}),
        (None, {"codigo": "no-existe"}),
        (_desactivar_usuario, {}),
        (_desactivar_consultorio, {}),
        (_credencial_nula, {"contrasena": "null"}),
        (_credencial_nula, {"contrasena": CONTRASENA_A}),
        (_credencial_argon2i, {"contrasena": CONTRASENA_A}),
        (_credencial_texto, {"contrasena": CONTRASENA_A}),
    ],
    ids=[
        "contrasena-incorrecta",
        "email-inexistente",
        "codigo-inexistente",
        "usuario-inactivo",
        "consultorio-inactivo",
        "credencial-nula-null",
        "credencial-nula",
        "formato-argon2i",
        "texto-no-hash",
    ],
)
def test_todo_rechazo_es_generico_ejecuta_una_verificacion_y_registra_un_fallo(
    entorno: Entorno, preparar, datos
):
    if preparar is not None:
        preparar(entorno)
        entorno.db.commit()

    with pytest.raises(LoginRechazado) as error:
        entorno.login(**datos)

    assert str(error.value) == ""
    assert entorno.verificador.llamadas == 1
    assert entorno.sesiones() == []
    assert entorno.intentos() == 1


def test_un_login_exitoso_ejecuta_una_sola_verificacion(entorno: Entorno):
    entorno.login()

    assert entorno.verificador.llamadas == 1


def test_un_rechazo_no_modifica_ningun_usuario(entorno: Entorno):
    consulta = text("SELECT md5(string_agg(u::text, '|' ORDER BY id)) FROM usuario u")
    antes = entorno.db.execute(consulta).scalar_one()

    with pytest.raises(LoginRechazado):
        entorno.login(email="nadie@example.test")

    assert entorno.db.execute(consulta).scalar_one() == antes


# --- rehash --------------------------------------------------------------------------------


def _credencial(e: Entorno) -> str:
    return e.db.execute(text("SELECT credencial FROM usuario WHERE id = :u"), {"u": e.ua}).scalar_one()


def test_rehash_al_iniciar_sesion_con_parametros_desactualizados(entorno: Entorno):
    viejo = hash_rapido(CONTRASENA_A, time_cost=1)
    entorno.db.execute(
        text("UPDATE usuario SET credencial = :c WHERE id = :u"), {"c": viejo, "u": entorno.ua}
    )
    entorno.db.commit()

    entorno.login()

    nuevo = _credencial(entorno)
    assert nuevo != viejo
    assert not hasher_rapido(2).check_needs_rehash(nuevo)
    assert hasher_rapido(2).verify(nuevo, CONTRASENA_A)
    entorno.login()  # la contrasena sigue autenticando


def test_sin_rehash_si_los_parametros_son_vigentes_o_si_el_login_falla(entorno: Entorno):
    vigente = _credencial(entorno)
    entorno.login()
    assert _credencial(entorno) == vigente

    viejo = hash_rapido(CONTRASENA_A, time_cost=1)
    entorno.db.execute(
        text("UPDATE usuario SET credencial = :c WHERE id = :u"), {"c": viejo, "u": entorno.ua}
    )
    entorno.db.commit()
    with pytest.raises(LoginRechazado):
        entorno.login(contrasena="otra-contrasena-ficticia")
    assert _credencial(entorno) == viejo


# --- rotacion de sesion ----------------------------------------------------------------------


def _revocada_en(e: Entorno, sesion_id):
    return e.db.execute(
        text("SELECT revocada_en FROM sesion WHERE id = :s"), {"s": sesion_id}
    ).scalar_one()


def test_login_con_cookie_de_sesion_valida_la_revoca_y_emite_un_token_distinto(entorno: Entorno):
    previa = entorno.login()
    entorno.reloj.avanzar(timedelta(minutes=5))

    nueva = entorno.login(token=previa.token)

    assert nueva.token != previa.token
    assert _revocada_en(entorno, previa.sesion_id) == AHORA + timedelta(minutes=5)
    assert _revocada_en(entorno, nueva.sesion_id) is None


def test_login_sin_cookie_o_con_cookie_desconocida_no_revoca_otras_sesiones(entorno: Entorno):
    otra = entorno.login()

    entorno.login()
    entorno.login(token="A" * 43)

    assert _revocada_en(entorno, otra.sesion_id) is None


def test_un_login_fallido_no_revoca_la_sesion_previa(entorno: Entorno):
    previa = entorno.login()

    with pytest.raises(LoginRechazado):
        entorno.login(contrasena="otra-contrasena-ficticia", token=previa.token)

    assert _revocada_en(entorno, previa.sesion_id) is None


# --- identidad, vencimientos y renovacion ------------------------------------------------------


def _ultimo_uso(e: Entorno, sesion_id):
    return e.db.execute(
        text("SELECT ultimo_uso_en FROM sesion WHERE id = :s"), {"s": sesion_id}
    ).scalar_one()


def test_resolver_identidad_devuelve_los_datos_de_la_sesion_valida(entorno: Entorno):
    iniciada = entorno.login()

    identidad = entorno.servicio.resolver_identidad(entorno.db, iniciada.token)

    assert identidad is not None
    assert (identidad.sesion_id, identidad.usuario_id, identidad.consultorio_id) == (
        iniciada.sesion_id,
        entorno.ua,
        entorno.a,
    )
    assert (identidad.nombre, identidad.email, identidad.rol) == ("Persona A", EMAIL, "secretaria")
    assert identidad.consultorio_nombre == "Consultorio Ficticio A"


def test_token_desconocido_o_de_otra_clave_no_resuelve(entorno: Entorno):
    iniciada = entorno.login()
    otra_clave = ServicioAuth(
        ConfigAuth(clave_hmac=bytes(48), minutos_inactividad=30, horas_maximas=12),
        entorno.reloj,
        entorno.verificador,
        entorno.limitador,
    )

    assert entorno.servicio.resolver_identidad(entorno.db, "A" * 43) is None
    assert otra_clave.resolver_identidad(entorno.db, iniciada.token) is None
    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is not None


@pytest.mark.parametrize(
    "token", [None, "", "x" * 10, "A" * 42, "A" * 44, "A" * 42 + "+", "A" * 42 + " ", 123]
)
def test_token_con_formato_invalido_no_consulta_la_tabla_de_sesiones(entorno: Entorno, token):
    sentencias: list[str] = []

    def registrar(conexion, cursor, sentencia, parametros, contexto, muchos):
        sentencias.append(sentencia)

    event.listen(entorno.db.get_bind(), "before_cursor_execute", registrar)
    try:
        assert entorno.servicio.resolver_identidad(entorno.db, token) is None
    finally:
        event.remove(entorno.db.get_bind(), "before_cursor_execute", registrar)

    assert [s for s in sentencias if "sesion" in s.lower()] == []


def test_inactividad_vence_al_cumplirse_el_limite(entorno: Entorno):
    iniciada = entorno.login()

    entorno.reloj.avanzar(timedelta(minutes=29, seconds=59))
    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is not None
    # El uso anterior renovo la sesion (>= 60 s): medimos otra vez desde ese uso.
    entorno.reloj.avanzar(timedelta(minutes=30))
    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is None


def test_sesion_inactiva_31_minutos_vencida(entorno: Entorno):
    iniciada = entorno.login()
    entorno.reloj.avanzar(timedelta(minutes=31))

    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is None


def test_la_actividad_renueva_la_sesion(entorno: Entorno):
    iniciada = entorno.login()

    entorno.reloj.avanzar(timedelta(minutes=20))
    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is not None
    entorno.reloj.avanzar(timedelta(minutes=25))  # t0 + 45 min
    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is not None


def test_la_renovacion_se_acota_a_una_por_minuto(entorno: Entorno):
    iniciada = entorno.login()

    entorno.reloj.avanzar(timedelta(seconds=30))
    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is not None
    assert _ultimo_uso(entorno, iniciada.sesion_id) == AHORA

    entorno.reloj.avanzar(timedelta(seconds=30))
    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is not None
    assert _ultimo_uso(entorno, iniciada.sesion_id) == AHORA + timedelta(seconds=60)


def test_sesion_activa_vence_a_las_12_horas_aunque_se_use_cada_10_minutos(entorno: Entorno):
    iniciada = entorno.login()

    for _ in range(71):  # hasta t0 + 11 h 50 min
        entorno.reloj.avanzar(timedelta(minutes=10))
        assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is not None
    vence = entorno.db.execute(
        text("SELECT vence_absoluto_en FROM sesion WHERE id = :s"), {"s": iniciada.sesion_id}
    ).scalar_one()
    assert vence == AHORA + timedelta(hours=12)

    entorno.reloj.avanzar(timedelta(minutes=10))  # t0 + 12 h
    assert entorno.servicio.resolver_identidad(entorno.db, iniciada.token) is None
    assert _ultimo_uso(entorno, iniciada.sesion_id) <= vence


def test_usuario_o_consultorio_desactivado_pierde_la_sesion_abierta(entorno: Entorno):
    de_a = entorno.login()
    de_b = entorno.login(codigo="ficticio-b", contrasena=CONTRASENA_B)

    entorno.db.execute(text("UPDATE usuario SET activo = false WHERE id = :u"), {"u": entorno.ua})
    entorno.db.execute(text("UPDATE consultorio SET activo = false WHERE id = :c"), {"c": entorno.b})
    entorno.db.commit()

    assert entorno.servicio.resolver_identidad(entorno.db, de_a.token) is None
    assert entorno.servicio.resolver_identidad(entorno.db, de_b.token) is None


def test_cerrar_sesion_revoca_solo_esa_sesion_y_es_idempotente(entorno: Entorno):
    primera, segunda = entorno.login(), entorno.login()
    entorno.reloj.avanzar(timedelta(minutes=1))

    assert entorno.servicio.cerrar_sesion(entorno.db, primera.sesion_id) is True
    assert entorno.servicio.cerrar_sesion(entorno.db, primera.sesion_id) is False

    assert entorno.servicio.resolver_identidad(entorno.db, primera.token) is None
    assert entorno.servicio.resolver_identidad(entorno.db, segunda.token) is not None
    assert _revocada_en(entorno, primera.sesion_id) == AHORA + timedelta(minutes=1)


# --- saturacion de Argon2 y liberacion del cupo -----------------------------------------------


@pytest.fixture
def entorno_saturado(entorno: Entorno):
    for _ in range(CUPOS_POR_PROCESO):
        assert entorno.limitador.semaforo.acquire(timeout=0)
    yield entorno
    for _ in range(CUPOS_POR_PROCESO):
        entorno.limitador.semaforo.release()


@pytest.mark.parametrize(
    "email", [EMAIL, "nadie@example.test"], ids=["cuenta-existente", "cuenta-inexistente"]
)
def test_sin_cupo_el_login_falla_como_servicio_ocupado_sin_efectos(entorno_saturado: Entorno, email):
    with pytest.raises(ServicioOcupado):
        entorno_saturado.login(email=email)

    assert entorno_saturado.verificador.llamadas == 0
    assert entorno_saturado.intentos() == 0
    assert entorno_saturado.sesiones() == []


def _cupos_libres(limitador: LimitadorArgon2) -> int:
    tomados = 0
    while limitador.semaforo.acquire(timeout=0):
        tomados += 1
    for _ in range(tomados):
        limitador.semaforo.release()
    return tomados


@pytest.mark.parametrize(
    "error", [RuntimeError("falla"), asyncio.CancelledError()], ids=["excepcion", "cancelacion"]
)
def test_el_cupo_se_libera_ante_errores_y_cancelacion_del_verificador(entorno: Entorno, error):
    def verificador_que_falla(contrasena, almacenado):
        raise error

    entorno.verificador.verificar = verificador_que_falla  # type: ignore[method-assign]

    for _ in range(CUPOS_POR_PROCESO):
        with pytest.raises(type(error)):
            entorno.login()

    assert _cupos_libres(entorno.limitador) == CUPOS_POR_PROCESO
    assert entorno.intentos() == 0 and entorno.sesiones() == []


# --- limpieza oportunista de sesiones ------------------------------------------------------------


def _total_sesiones(e: Entorno) -> int:
    return e.db.execute(text("SELECT count(*) FROM sesion")).scalar_one()


def test_login_exitoso_borra_sesiones_revocadas_y_vencidas_sin_tocar_las_validas(entorno: Entorno):
    creada = AHORA - timedelta(hours=3)
    for _ in range(3):
        insertar_sesion(entorno.db, entorno.a, entorno.ua, creada_en=creada, revocada_en=AHORA)
    insertar_sesion(
        entorno.db, entorno.a, entorno.ua, creada_en=creada, ultimo_uso_en=AHORA - timedelta(minutes=31)
    )
    insertar_sesion(
        entorno.db,
        entorno.a,
        entorno.ua,
        creada_en=AHORA - timedelta(hours=13),
        ultimo_uso_en=AHORA - timedelta(minutes=10),
        vence_absoluto_en=AHORA - timedelta(minutes=1),
    )
    valida = insertar_sesion(
        entorno.db, entorno.a, entorno.ua, creada_en=creada, ultimo_uso_en=AHORA - timedelta(minutes=5)
    )
    entorno.db.commit()

    nueva = entorno.login()

    restantes = set(entorno.db.execute(text("SELECT id FROM sesion")).scalars())
    assert restantes == {valida, nueva.sesion_id}


def test_la_limpieza_de_sesiones_borra_como_maximo_100_y_solo_en_login_exitoso(entorno: Entorno):
    for _ in range(150):
        insertar_sesion(
            entorno.db, entorno.a, entorno.ua, creada_en=AHORA - timedelta(hours=3), revocada_en=AHORA
        )
    entorno.db.commit()

    with pytest.raises(LoginRechazado):
        entorno.login(contrasena="otra-contrasena-ficticia")
    assert _total_sesiones(entorno) == 150

    entorno.login()
    assert _total_sesiones(entorno) == 150 - 100 + 1


@pytest.mark.parametrize("tipo", ["inactividad", "absoluto"])
def test_la_limpieza_de_sesiones_borra_exactamente_100_de_150_sesiones_vencidas(
    entorno: Entorno, tipo: str
):
    """Escenario "Limite por ejecucion" con sesiones VENCIDAS (no revocadas), por ambos vencimientos."""
    for _ in range(150):
        if tipo == "inactividad":
            insertar_sesion(
                entorno.db,
                entorno.a,
                entorno.ua,
                creada_en=AHORA - timedelta(hours=3),
                ultimo_uso_en=AHORA - timedelta(minutes=31),
            )
        else:
            insertar_sesion(
                entorno.db,
                entorno.a,
                entorno.ua,
                creada_en=AHORA - timedelta(hours=13),
                ultimo_uso_en=AHORA - timedelta(minutes=10),
                vence_absoluto_en=AHORA - timedelta(minutes=1),
            )
    entorno.db.commit()
    assert _total_sesiones(entorno) == 150

    nueva = entorno.login()

    # Se borran exactamente 100; quedan 50 vencidas mas la nueva.
    assert _total_sesiones(entorno) == 150 - 100 + 1
    assert nueva.sesion_id in set(entorno.db.execute(text("SELECT id FROM sesion")).scalars())

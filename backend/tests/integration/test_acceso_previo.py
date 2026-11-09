"""Acceso previo al contexto (tarea 6.1; DD-01, DD-27). Solo contra db-test, en transaccion revertible."""

import secrets
import uuid
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import acceso_previo
from tests.integration.datos_auth import (
    AHORA,
    EMAIL,
    crear_consultorio,
    crear_usuario,
    insertar_fallo,
    insertar_sesion,
)

CREDENCIAL_A = "credencial-ficticia-a"
CREDENCIAL_B = "credencial-ficticia-b"


def _dos_consultorios(sesion: Session):
    a = crear_consultorio(sesion, "ficticio-a", "Consultorio Ficticio A")
    b = crear_consultorio(sesion, "ficticio-b", "Consultorio Ficticio B")
    ua = crear_usuario(sesion, a, credencial=CREDENCIAL_A, nombre="Persona A")
    ub = crear_usuario(sesion, b, credencial=CREDENCIAL_B, nombre="Persona B", rol="administrador")
    return a, b, ua, ub


# --- buscar_cuenta ----------------------------------------------------------------------


def test_buscar_cuenta_devuelve_la_del_consultorio_indicado(sesion: Session):
    a, b, ua, ub = _dos_consultorios(sesion)

    cuenta_a = acceso_previo.buscar_cuenta(sesion, "ficticio-a", EMAIL)
    cuenta_b = acceso_previo.buscar_cuenta(sesion, "ficticio-b", EMAIL)

    assert cuenta_a is not None and cuenta_b is not None
    assert (cuenta_a.usuario_id, cuenta_a.consultorio_id) == (ua, a)
    assert (cuenta_b.usuario_id, cuenta_b.consultorio_id) == (ub, b)
    assert (cuenta_a.credencial, cuenta_b.credencial) == (CREDENCIAL_A, CREDENCIAL_B)
    assert (cuenta_a.consultorio_nombre, cuenta_a.nombre, cuenta_a.rol, cuenta_a.email) == (
        "Consultorio Ficticio A",
        "Persona A",
        "secretaria",
        EMAIL,
    )
    assert cuenta_b.rol == "administrador"
    assert cuenta_a.usuario_activo and cuenta_a.consultorio_activo


def test_buscar_cuenta_inexistente_devuelve_none(sesion: Session):
    _dos_consultorios(sesion)

    assert acceso_previo.buscar_cuenta(sesion, "no-existe", EMAIL) is None
    assert acceso_previo.buscar_cuenta(sesion, "ficticio-a", "nadie@example.test") is None


def test_buscar_cuenta_normaliza_codigo_y_email(sesion: Session):
    _, _, ua, _ = _dos_consultorios(sesion)

    cuenta = acceso_previo.buscar_cuenta(sesion, " FICTICIO-A ", " Persona.Ficticia@Example.TEST ")

    assert cuenta is not None and cuenta.usuario_id == ua


def test_buscar_cuenta_informa_la_credencial_nula_y_los_estados_inactivos(sesion: Session):
    a = crear_consultorio(sesion, "ficticio-a", activo=False)
    crear_usuario(sesion, a, credencial=None, activo=False)

    cuenta = acceso_previo.buscar_cuenta(sesion, "ficticio-a", EMAIL)

    assert cuenta is not None
    assert cuenta.credencial is None
    assert (cuenta.usuario_activo, cuenta.consultorio_activo) == (False, False)


# --- resolver_sesion --------------------------------------------------------------------


def test_resolver_sesion_por_hmac_con_usuario_y_consultorio(sesion: Session):
    a, _, ua, _ = _dos_consultorios(sesion)
    hmac_a = secrets.token_bytes(32)
    sesion_id = insertar_sesion(sesion, a, ua, token_hmac=hmac_a, ultimo_uso_en=AHORA + timedelta(minutes=1))

    resuelta = acceso_previo.resolver_sesion(sesion, hmac_a)

    assert resuelta is not None
    assert (resuelta.sesion_id, resuelta.usuario_id, resuelta.consultorio_id) == (sesion_id, ua, a)
    assert (resuelta.email, resuelta.nombre, resuelta.rol) == (EMAIL, "Persona A", "secretaria")
    assert resuelta.consultorio_nombre == "Consultorio Ficticio A"
    assert resuelta.usuario_activo and resuelta.consultorio_activo
    assert resuelta.creada_en == AHORA
    assert resuelta.ultimo_uso_en == AHORA + timedelta(minutes=1)
    assert resuelta.vence_absoluto_en == AHORA + timedelta(hours=12)
    assert resuelta.revocada_en is None


def test_resolver_sesion_con_hmac_desconocido_devuelve_none(sesion: Session):
    a, _, ua, _ = _dos_consultorios(sesion)
    insertar_sesion(sesion, a, ua)

    assert acceso_previo.resolver_sesion(sesion, secrets.token_bytes(32)) is None


def test_resolver_sesion_no_mezcla_consultorios_y_expone_revocada_e_inactivos(sesion: Session):
    a, b, ua, ub = _dos_consultorios(sesion)
    hmac_b = secrets.token_bytes(32)
    insertar_sesion(sesion, b, ub, token_hmac=hmac_b, revocada_en=AHORA + timedelta(minutes=5))
    sesion.execute(text("UPDATE usuario SET activo = false WHERE id = :u"), {"u": ub})
    sesion.execute(text("UPDATE consultorio SET activo = false WHERE id = :c"), {"c": b})

    resuelta = acceso_previo.resolver_sesion(sesion, hmac_b)

    assert resuelta is not None
    assert (resuelta.consultorio_id, resuelta.usuario_id) == (b, ub)
    assert resuelta.consultorio_nombre == "Consultorio Ficticio B"
    assert resuelta.revocada_en == AHORA + timedelta(minutes=5)
    assert (resuelta.usuario_activo, resuelta.consultorio_activo) == (False, False)
    assert isinstance(resuelta.sesion_id, uuid.UUID) and resuelta.consultorio_id != a


# --- crear, renovar y revocar sesiones ---------------------------------------------------


def _fila_sesion(sesion: Session, sesion_id: uuid.UUID):
    return sesion.execute(
        text("SELECT * FROM sesion WHERE id = :id"), {"id": sesion_id}
    ).one_or_none()


def test_crear_sesion_guarda_solo_el_hmac_y_los_instantes(sesion: Session):
    a, _, ua, _ = _dos_consultorios(sesion)
    hmac_a = secrets.token_bytes(32)

    sesion_id = acceso_previo.crear_sesion(sesion, a, ua, hmac_a, AHORA, AHORA + timedelta(hours=12))

    fila = _fila_sesion(sesion, sesion_id)
    assert fila is not None
    assert (fila.consultorio_id, fila.usuario_id, bytes(fila.token_hmac)) == (a, ua, hmac_a)
    assert (fila.creada_en, fila.ultimo_uso_en) == (AHORA, AHORA)
    assert fila.vence_absoluto_en == AHORA + timedelta(hours=12)
    assert fila.revocada_en is None


def test_renovar_sesion_solo_si_pasaron_al_menos_60_segundos(sesion: Session):
    a, _, ua, _ = _dos_consultorios(sesion)
    sesion_id = insertar_sesion(sesion, a, ua)

    assert acceso_previo.renovar_sesion(sesion, sesion_id, AHORA + timedelta(seconds=59)) is False
    assert _fila_sesion(sesion, sesion_id).ultimo_uso_en == AHORA

    assert acceso_previo.renovar_sesion(sesion, sesion_id, AHORA + timedelta(seconds=60)) is True
    fila = _fila_sesion(sesion, sesion_id)
    assert fila.ultimo_uso_en == AHORA + timedelta(seconds=60)
    assert fila.vence_absoluto_en == AHORA + timedelta(hours=12)


def test_renovar_no_toca_una_sesion_revocada_ni_supera_el_vencimiento_absoluto(sesion: Session):
    a, _, ua, _ = _dos_consultorios(sesion)
    revocada = insertar_sesion(sesion, a, ua, revocada_en=AHORA + timedelta(minutes=1))
    vencida = insertar_sesion(sesion, a, ua)

    assert acceso_previo.renovar_sesion(sesion, revocada, AHORA + timedelta(minutes=5)) is False
    assert acceso_previo.renovar_sesion(sesion, vencida, AHORA + timedelta(hours=12)) is False
    assert _fila_sesion(sesion, revocada).ultimo_uso_en == AHORA
    assert _fila_sesion(sesion, vencida).ultimo_uso_en == AHORA


def test_revocar_sesion_marca_solo_esa_y_es_idempotente(sesion: Session):
    a, _, ua, _ = _dos_consultorios(sesion)
    s1 = insertar_sesion(sesion, a, ua)
    s2 = insertar_sesion(sesion, a, ua)
    primer_instante = AHORA + timedelta(minutes=2)

    assert acceso_previo.revocar_sesion(sesion, s1, primer_instante) is True
    assert acceso_previo.revocar_sesion(sesion, s1, primer_instante + timedelta(minutes=1)) is False

    assert _fila_sesion(sesion, s1).revocada_en == primer_instante
    assert _fila_sesion(sesion, s2).revocada_en is None


def test_revocar_todas_las_sesiones_de_un_usuario_conserva_las_ya_revocadas_y_las_ajenas(sesion: Session):
    a, b, ua, ub = _dos_consultorios(sesion)
    otro_de_a = crear_usuario(sesion, a, email="otra.persona@example.test", credencial=CREDENCIAL_A)
    activa1 = insertar_sesion(sesion, a, ua)
    activa2 = insertar_sesion(sesion, a, ua)
    previa = AHORA + timedelta(minutes=1)
    ya_revocada = insertar_sesion(sesion, a, ua, revocada_en=previa)
    ajena_mismo_consultorio = insertar_sesion(sesion, a, otro_de_a)
    ajena_otro_consultorio = insertar_sesion(sesion, b, ub)
    ahora = AHORA + timedelta(minutes=9)

    revocadas = acceso_previo.revocar_sesiones_de_usuario(sesion, a, ua, ahora)

    assert revocadas == 2
    assert _fila_sesion(sesion, activa1).revocada_en == ahora
    assert _fila_sesion(sesion, activa2).revocada_en == ahora
    assert _fila_sesion(sesion, ya_revocada).revocada_en == previa
    assert _fila_sesion(sesion, ajena_mismo_consultorio).revocada_en is None
    assert _fila_sesion(sesion, ajena_otro_consultorio).revocada_en is None


# --- intentos de login -------------------------------------------------------------------

CUENTA_1 = secrets.token_bytes(32)
CUENTA_2 = secrets.token_bytes(32)
IP_1 = secrets.token_bytes(32)
IP_2 = secrets.token_bytes(32)


def _intentos(sesion: Session):
    return sesion.execute(
        text(
            "SELECT clave_cuenta, clave_ip, ocurrido_en, descartado_para_cuenta "
            "FROM intento_login ORDER BY id"
        )
    ).all()


def test_registrar_fallo_guarda_solo_claves_instante_y_marca_falsa(sesion: Session):
    acceso_previo.registrar_fallo(sesion, CUENTA_1, IP_1, AHORA)

    (fila,) = _intentos(sesion)
    assert (bytes(fila.clave_cuenta), bytes(fila.clave_ip)) == (CUENTA_1, IP_1)
    assert fila.ocurrido_en == AHORA
    assert fila.descartado_para_cuenta is False
    columnas = sesion.execute(text("SELECT * FROM intento_login")).keys()
    assert set(columnas) == {"id", "clave_cuenta", "clave_ip", "ocurrido_en", "descartado_para_cuenta"}


def test_fallos_de_cuenta_filtra_por_clave_horizonte_y_descartados_y_ordena(sesion: Session):
    desde = AHORA - timedelta(minutes=30)
    for minutos in (5, 3, 1):
        acceso_previo.registrar_fallo(sesion, CUENTA_1, IP_1, AHORA - timedelta(minutes=minutos))
    acceso_previo.registrar_fallo(sesion, CUENTA_1, IP_1, AHORA - timedelta(minutes=31))  # fuera
    acceso_previo.registrar_fallo(sesion, CUENTA_2, IP_1, AHORA - timedelta(minutes=2))  # otra cuenta
    insertar_fallo(sesion, CUENTA_1, IP_1, AHORA - timedelta(minutes=4), descartado=True)

    assert acceso_previo.fallos_de_cuenta(sesion, CUENTA_1, desde, 5) == [
        AHORA - timedelta(minutes=5),
        AHORA - timedelta(minutes=3),
        AHORA - timedelta(minutes=1),
    ]
    # El limite conserva los mas recientes.
    assert acceso_previo.fallos_de_cuenta(sesion, CUENTA_1, desde, 2) == [
        AHORA - timedelta(minutes=3),
        AHORA - timedelta(minutes=1),
    ]


def test_fallos_de_ip_cuenta_todos_incluidos_los_descartados(sesion: Session):
    desde = AHORA - timedelta(minutes=30)
    insertar_fallo(sesion, CUENTA_1, IP_1, AHORA - timedelta(minutes=4), descartado=True)
    insertar_fallo(sesion, CUENTA_2, IP_1, AHORA - timedelta(minutes=2))
    insertar_fallo(sesion, CUENTA_2, IP_2, AHORA - timedelta(minutes=1))  # otra IP
    insertar_fallo(sesion, CUENTA_2, IP_1, AHORA - timedelta(minutes=40))  # fuera del horizonte

    assert acceso_previo.fallos_de_ip(sesion, IP_1, desde, 30) == [
        AHORA - timedelta(minutes=4),
        AHORA - timedelta(minutes=2),
    ]
    assert acceso_previo.fallos_de_ip(sesion, IP_1, desde, 1) == [AHORA - timedelta(minutes=2)]


def test_descartar_fallos_de_cuenta_marca_solo_las_filas_del_par_sin_borrarlas(sesion: Session):
    for _ in range(3):
        acceso_previo.registrar_fallo(sesion, CUENTA_1, IP_1, AHORA)
    for _ in range(2):
        acceso_previo.registrar_fallo(sesion, CUENTA_2, IP_1, AHORA)
    desde = AHORA - timedelta(minutes=30)

    assert acceso_previo.descartar_fallos_de_cuenta(sesion, CUENTA_1) == 3

    filas = _intentos(sesion)
    assert len(filas) == 5
    assert [bool(f.descartado_para_cuenta) for f in filas if bytes(f.clave_cuenta) == CUENTA_1] == [True] * 3
    assert [bool(f.descartado_para_cuenta) for f in filas if bytes(f.clave_cuenta) == CUENTA_2] == [False] * 2
    assert acceso_previo.fallos_de_cuenta(sesion, CUENTA_1, desde, 5) == []
    assert len(acceso_previo.fallos_de_ip(sesion, IP_1, desde, 30)) == 5
    assert acceso_previo.descartar_fallos_de_cuenta(sesion, CUENTA_1) == 0


def test_limpiar_intentos_borra_solo_los_de_mas_de_24_horas(sesion: Session):
    for _ in range(30):
        insertar_fallo(sesion, CUENTA_1, IP_1, AHORA - timedelta(hours=25))
    insertar_fallo(sesion, CUENTA_1, IP_1, AHORA - timedelta(hours=24))  # borde: no se borra
    for _ in range(2):
        insertar_fallo(sesion, CUENTA_1, IP_1, AHORA - timedelta(minutes=5))

    assert acceso_previo.limpiar_intentos(sesion, AHORA) == 30
    assert len(_intentos(sesion)) == 3


def test_limpiar_intentos_respeta_el_limite_de_100_por_ejecucion(sesion: Session):
    for _ in range(150):
        insertar_fallo(sesion, CUENTA_1, IP_1, AHORA - timedelta(hours=25))

    assert acceso_previo.limpiar_intentos(sesion, AHORA) == 100
    assert len(_intentos(sesion)) == 50
    assert acceso_previo.limpiar_intentos(sesion, AHORA, limite=10) == 10
    assert len(_intentos(sesion)) == 40


# --- credencial con control optimista -----------------------------------------------------


def _credencial(sesion: Session, usuario_id: uuid.UUID):
    return sesion.execute(
        text("SELECT credencial FROM usuario WHERE id = :id"), {"id": usuario_id}
    ).scalar_one()


def test_escribir_credencial_solo_si_la_actual_es_la_esperada(sesion: Session):
    a, _, ua, _ = _dos_consultorios(sesion)

    assert acceso_previo.escribir_credencial(sesion, a, ua, "hash-nuevo", CREDENCIAL_A) is True
    assert _credencial(sesion, ua) == "hash-nuevo"

    # Otro proceso ya la cambio: la escritura basada en la lectura vieja no pisa nada.
    assert acceso_previo.escribir_credencial(sesion, a, ua, "hash-tardio", CREDENCIAL_A) is False
    assert _credencial(sesion, ua) == "hash-nuevo"


def test_escribir_credencial_esperando_nula_solo_completa_las_nulas(sesion: Session):
    a = crear_consultorio(sesion, "ficticio-a")
    sin = crear_usuario(sesion, a, email="sin@example.test", credencial=None)
    con = crear_usuario(sesion, a, email="con@example.test", credencial=CREDENCIAL_A)

    assert acceso_previo.escribir_credencial(sesion, a, sin, "hash-nuevo", None) is True
    assert acceso_previo.escribir_credencial(sesion, a, con, "hash-nuevo", None) is False
    assert (_credencial(sesion, sin), _credencial(sesion, con)) == ("hash-nuevo", CREDENCIAL_A)


def test_escribir_credencial_con_consultorio_ajeno_no_escribe(sesion: Session):
    a, b, ua, _ = _dos_consultorios(sesion)

    assert acceso_previo.escribir_credencial(sesion, b, ua, "hash-nuevo", CREDENCIAL_A) is False
    assert _credencial(sesion, ua) == CREDENCIAL_A


# --- limpieza de sesiones ----------------------------------------------------------------


def _cantidad_de_sesiones(sesion: Session) -> int:
    return sesion.execute(text("SELECT count(*) FROM sesion")).scalar_one()


def test_limpiar_sesiones_borra_revocadas_y_vencidas_y_conserva_la_valida(sesion: Session):
    a, _, ua, _ = _dos_consultorios(sesion)
    creada = AHORA - timedelta(hours=3)
    for _ in range(3):
        insertar_sesion(sesion, a, ua, creada_en=creada, ultimo_uso_en=AHORA, revocada_en=AHORA)
    insertar_sesion(  # vencida por inactividad (31 min sin uso)
        sesion, a, ua, creada_en=creada, ultimo_uso_en=AHORA - timedelta(minutes=31)
    )
    insertar_sesion(  # vencida por tiempo absoluto, con uso reciente (10 min)
        sesion, a, ua, creada_en=AHORA - timedelta(hours=13), ultimo_uso_en=AHORA - timedelta(minutes=10),
        vence_absoluto_en=AHORA - timedelta(minutes=1),
    )
    valida = insertar_sesion(sesion, a, ua, creada_en=creada, ultimo_uso_en=AHORA - timedelta(minutes=29))

    assert acceso_previo.limpiar_sesiones(sesion, AHORA, 30) == 5
    restantes = sesion.execute(text("SELECT id FROM sesion")).scalars().all()
    assert restantes == [valida]


def test_limpiar_sesiones_trata_el_limite_de_inactividad_como_vencido(sesion: Session):
    a, _, ua, _ = _dos_consultorios(sesion)
    creada = AHORA - timedelta(hours=3)
    insertar_sesion(sesion, a, ua, creada_en=creada, ultimo_uso_en=AHORA - timedelta(minutes=30))
    insertar_sesion(sesion, a, ua, creada_en=creada, ultimo_uso_en=AHORA - timedelta(minutes=29, seconds=59))

    assert acceso_previo.limpiar_sesiones(sesion, AHORA, 30) == 1
    assert _cantidad_de_sesiones(sesion) == 1


def test_limpiar_sesiones_respeta_el_limite_de_100_por_ejecucion(sesion: Session):
    a, _, ua, _ = _dos_consultorios(sesion)
    for _ in range(150):
        insertar_sesion(sesion, a, ua, creada_en=AHORA - timedelta(hours=3), revocada_en=AHORA)

    assert acceso_previo.limpiar_sesiones(sesion, AHORA, 30) == 100
    assert _cantidad_de_sesiones(sesion) == 50

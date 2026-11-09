"""Restricciones de `sesion` e `intento_login` (C-03) contra PostgreSQL real (db-test)."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NOT_NULL = "23502"
FOREIGN_KEY = "23503"
UNIQUE = "23505"
CHECK = "23514"

AHORA = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)

INSERTAR_SESION = (
    "INSERT INTO sesion (consultorio_id, usuario_id, token_hmac, creada_en, "
    "ultimo_uso_en, vence_absoluto_en, revocada_en) "
    "VALUES (:consultorio_id, :usuario_id, :token_hmac, :creada_en, :ultimo_uso_en, "
    ":vence_absoluto_en, :revocada_en)"
)


def _consultorio(sesion: Session, codigo: str) -> uuid.UUID:
    return sesion.execute(
        text(
            "INSERT INTO consultorio (nombre, codigo) VALUES ('Consultorio Ficticio', :c) "
            "RETURNING id"
        ),
        {"c": codigo},
    ).scalar_one()


def _usuario(sesion: Session, consultorio_id: uuid.UUID) -> uuid.UUID:
    return sesion.execute(
        text(
            "INSERT INTO usuario (consultorio_id, email, nombre, rol) VALUES "
            "(:c, 'persona.ficticia@example.test', 'Persona Ficticia', 'secretaria') "
            "RETURNING id"
        ),
        {"c": consultorio_id},
    ).scalar_one()


def _parametros(
    consultorio_id: uuid.UUID, usuario_id: uuid.UUID, **cambios: object
) -> dict[str, object]:
    base: dict[str, object] = {
        "consultorio_id": consultorio_id,
        "usuario_id": usuario_id,
        "token_hmac": secrets.token_bytes(32),
        "creada_en": AHORA,
        "ultimo_uso_en": AHORA,
        "vence_absoluto_en": AHORA + timedelta(hours=12),
        "revocada_en": None,
    }
    base.update(cambios)
    return base


def _diagnostico(sesion: Session, sentencia: str, parametros: dict[str, object]):
    with pytest.raises(IntegrityError) as excinfo:
        with sesion.begin_nested():
            sesion.execute(text(sentencia), parametros)
    origen = excinfo.value.orig
    return getattr(origen, "sqlstate", None), origen.diag.constraint_name


@pytest.fixture
def cuenta(sesion: Session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """(consultorio A, usuario de A, consultorio B)."""
    consultorio_a = _consultorio(sesion, "ficticio-a")
    consultorio_b = _consultorio(sesion, "ficticio-b")
    return consultorio_a, _usuario(sesion, consultorio_a), consultorio_b


# --- Tabla de sesiones ligada al usuario de su consultorio ------------------------


def test_sesion_valida_con_valores_por_defecto(sesion: Session, cuenta):
    consultorio_a, usuario_a, _ = cuenta

    fila = sesion.execute(
        text(INSERTAR_SESION + " RETURNING id, revocada_en"),
        _parametros(consultorio_a, usuario_a),
    ).one()

    assert fila.id.version == 7
    assert fila.revocada_en is None


def test_sesion_con_consultorio_distinto_del_usuario_rechazada(sesion: Session, cuenta):
    _, usuario_a, consultorio_b = cuenta

    sqlstate, restriccion = _diagnostico(
        sesion, INSERTAR_SESION, _parametros(consultorio_b, usuario_a)
    )

    assert (sqlstate, restriccion) == (
        FOREIGN_KEY,
        "fk_sesion_consultorio_id_usuario",
    )


def test_hmac_duplicado_rechazado(sesion: Session, cuenta):
    consultorio_a, usuario_a, _ = cuenta
    token = secrets.token_bytes(32)
    sesion.execute(text(INSERTAR_SESION), _parametros(consultorio_a, usuario_a, token_hmac=token))

    sqlstate, restriccion = _diagnostico(
        sesion, INSERTAR_SESION, _parametros(consultorio_a, usuario_a, token_hmac=token)
    )

    assert (sqlstate, restriccion) == (UNIQUE, "uq_sesion_token_hmac")


def test_borrar_el_usuario_borra_sus_sesiones(sesion: Session, cuenta):
    consultorio_a, usuario_a, _ = cuenta
    sesion.execute(text(INSERTAR_SESION), _parametros(consultorio_a, usuario_a))

    sesion.execute(text("DELETE FROM usuario WHERE id = :id"), {"id": usuario_a})

    assert sesion.execute(text("SELECT count(*) FROM sesion")).scalar_one() == 0


# --- Restricciones CHECK de la sesion --------------------------------------------

VENCIMIENTOS_INCOHERENTES = {
    "vencimiento igual a la creacion": {"vence_absoluto_en": AHORA},
    "vencimiento anterior a la creacion": {"vence_absoluto_en": AHORA - timedelta(hours=1)},
    "ultimo uso anterior a la creacion": {"ultimo_uso_en": AHORA - timedelta(seconds=1)},
    "ultimo uso posterior al vencimiento": {
        "ultimo_uso_en": AHORA + timedelta(hours=12, seconds=1)
    },
}


@pytest.mark.parametrize("cambios", VENCIMIENTOS_INCOHERENTES.values(), ids=list(VENCIMIENTOS_INCOHERENTES))
def test_vencimientos_incoherentes_rechazados(sesion: Session, cuenta, cambios):
    consultorio_a, usuario_a, _ = cuenta

    sqlstate, restriccion = _diagnostico(
        sesion, INSERTAR_SESION, _parametros(consultorio_a, usuario_a, **cambios)
    )

    assert (sqlstate, restriccion) == (CHECK, "ck_sesion_vencimientos_coherentes")


def test_ultimo_uso_igual_al_vencimiento_aceptado(sesion: Session, cuenta):
    consultorio_a, usuario_a, _ = cuenta
    vence = AHORA + timedelta(hours=12)

    sesion.execute(
        text(INSERTAR_SESION),
        _parametros(consultorio_a, usuario_a, ultimo_uso_en=vence, vence_absoluto_en=vence),
    )

    assert sesion.execute(text("SELECT count(*) FROM sesion")).scalar_one() == 1


@pytest.mark.parametrize("longitud", [0, 31, 33, 64])
def test_hmac_de_longitud_distinta_de_32_rechazado(sesion: Session, cuenta, longitud: int):
    consultorio_a, usuario_a, _ = cuenta

    sqlstate, restriccion = _diagnostico(
        sesion,
        INSERTAR_SESION,
        _parametros(consultorio_a, usuario_a, token_hmac=secrets.token_bytes(longitud)),
    )

    assert (sqlstate, restriccion) == (CHECK, "ck_sesion_token_hmac_longitud")


def test_revocacion_anterior_a_la_creacion_rechazada_y_posterior_aceptada(
    sesion: Session, cuenta
):
    consultorio_a, usuario_a, _ = cuenta

    sqlstate, restriccion = _diagnostico(
        sesion,
        INSERTAR_SESION,
        _parametros(consultorio_a, usuario_a, revocada_en=AHORA - timedelta(seconds=1)),
    )
    sesion.execute(
        text(INSERTAR_SESION),
        _parametros(consultorio_a, usuario_a, revocada_en=AHORA + timedelta(minutes=5)),
    )

    assert (sqlstate, restriccion) == (CHECK, "ck_sesion_revocacion_posterior")
    assert sesion.execute(text("SELECT count(*) FROM sesion")).scalar_one() == 1


# --- Indices ------------------------------------------------------------------------


def _indices_ix(sesion: Session, tabla: str) -> dict[str, str]:
    filas = sesion.execute(
        text(
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname = 'public' AND tablename = :t AND indexname LIKE 'ix%'"
        ),
        {"t": tabla},
    ).all()
    return {fila.indexname: fila.indexdef for fila in filas}


def _columnas_indexadas(definicion: str) -> str:
    return definicion[definicion.index("(") :]


def test_indices_de_sesion(sesion: Session):
    indices = _indices_ix(sesion, "sesion")

    assert {nombre: _columnas_indexadas(d) for nombre, d in indices.items()} == {
        "ix_sesion_consultorio_id_usuario_id": "(consultorio_id, usuario_id)",
        "ix_sesion_vence_absoluto_en": "(vence_absoluto_en)",
        "ix_sesion_ultimo_uso_en": "(ultimo_uso_en)",
        "ix_sesion_revocada_en": "(revocada_en)",
    }


def test_indices_de_intento_login(sesion: Session):
    indices = _indices_ix(sesion, "intento_login")

    assert {nombre: _columnas_indexadas(d) for nombre, d in indices.items()} == {
        "ix_intento_login_clave_cuenta_ocurrido_en": "(clave_cuenta, ocurrido_en)",
        "ix_intento_login_clave_ip_ocurrido_en": "(clave_ip, ocurrido_en)",
        "ix_intento_login_ocurrido_en": "(ocurrido_en)",
    }


# --- intento_login -------------------------------------------------------------------

INSERTAR_INTENTO = (
    "INSERT INTO intento_login (clave_cuenta, clave_ip, ocurrido_en) "
    "VALUES (:cuenta, :ip, :ocurrido_en)"
)


def _intento(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "cuenta": secrets.token_bytes(32),
        "ip": secrets.token_bytes(32),
        "ocurrido_en": AHORA,
    }
    base.update(cambios)
    return base


def test_intento_login_solo_guarda_claves_instante_y_marca(sesion: Session):
    columnas = sesion.execute(
        text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'intento_login'"
        )
    ).all()

    assert {c.column_name: c.data_type for c in columnas} == {
        "id": "bigint",
        "clave_cuenta": "bytea",
        "clave_ip": "bytea",
        "ocurrido_en": "timestamp with time zone",
        "descartado_para_cuenta": "boolean",
    }


def test_intento_login_valores_por_defecto_e_identidad(sesion: Session):
    primero = sesion.execute(
        text(INSERTAR_INTENTO + " RETURNING id, descartado_para_cuenta"), _intento()
    ).one()
    segundo = sesion.execute(
        text(INSERTAR_INTENTO + " RETURNING id"), _intento()
    ).scalar_one()

    assert primero.descartado_para_cuenta is False
    assert segundo == primero.id + 1
    generacion = sesion.execute(
        text(
            "SELECT identity_generation FROM information_schema.columns "
            "WHERE table_name = 'intento_login' AND column_name = 'id'"
        )
    ).scalar_one()
    assert generacion == "ALWAYS"


@pytest.mark.parametrize("columna", ["cuenta", "ip"])
@pytest.mark.parametrize("longitud", [0, 31, 33])
def test_clave_de_intento_de_longitud_distinta_de_32_rechazada(
    sesion: Session, columna: str, longitud: int
):
    sqlstate, restriccion = _diagnostico(
        sesion, INSERTAR_INTENTO, _intento(**{columna: secrets.token_bytes(longitud)})
    )

    assert (sqlstate, restriccion) == (CHECK, "ck_intento_login_claves_longitud")


# --- Sin restriccion de prefijo en la base --------------------------------------------


def test_ninguna_restriccion_check_de_usuario_menciona_argon2(sesion: Session):
    definiciones = sesion.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = 'usuario'::regclass AND contype = 'c'"
        )
    ).scalars().all()

    assert definiciones  # hay restricciones CHECK que revisar
    assert not any("argon2" in definicion.lower() for definicion in definiciones)

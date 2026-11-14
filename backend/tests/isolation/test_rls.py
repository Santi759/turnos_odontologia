"""RLS forzada con conexiones reales de `turnos_app` (3.5, DD-03; delta `aislamiento-base-de-datos`).

Falla cerrado: sin contexto, con contexto vacio o con un contexto de otro consultorio no hay
filas ni escritura. Solo contra `db-test`.
"""

import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models.usuario import Rol

TABLAS_CON_RLS = ("consultorio", "usuario", "sesion", "intento_login")


def _sesion_de(motor_admin, consultorio, usuario) -> uuid.UUID:
    with motor_admin.begin() as conexion:
        return conexion.execute(
            text(
                "INSERT INTO sesion (consultorio_id, usuario_id, token_hmac, creada_en, "
                "ultimo_uso_en, vence_absoluto_en) VALUES (:c, :u, :t, now(), now(), "
                "now() + interval '1 hour') RETURNING id"
            ),
            {"c": consultorio.id, "u": usuario.id, "t": os.urandom(32)},
        ).scalar_one()


@pytest.fixture
def sesiones_ab(motor_admin, datos_ab):
    return (
        _sesion_de(motor_admin, datos_ab.a, datos_ab.a.usuarios[Rol.ADMINISTRADOR]),
        _sesion_de(motor_admin, datos_ab.b, datos_ab.b.usuarios[Rol.ADMINISTRADOR]),
    )


def _contar(motor, contexto: str | None, tabla: str) -> int:
    with motor.begin() as conexion:
        if contexto is not None:
            conexion.execute(
                text("SELECT set_config('app.consultorio_id', :c, true)"), {"c": contexto}
            )
        return conexion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


@pytest.mark.parametrize("tabla", ["consultorio", "usuario", "sesion"])
def test_sin_contexto_cero_filas(motor_app, sesiones_ab, tabla):
    assert _contar(motor_app, None, tabla) == 0


@pytest.mark.parametrize("tabla", ["consultorio", "usuario", "sesion"])
def test_contexto_vacio_cero_filas(motor_app, sesiones_ab, tabla):
    assert _contar(motor_app, "", tabla) == 0


@pytest.mark.parametrize("valor", ["abc", "no-es-uuid", "0"])
def test_contexto_no_uuid_falla_cerrado_con_error_de_conversion(motor_app, sesiones_ab, valor):
    with pytest.raises(DBAPIError) as info:
        _contar(motor_app, valor, "usuario")

    assert getattr(info.value.orig, "sqlstate", "") == "22P02"


def test_contexto_a_solo_ve_a(motor_app, datos_ab, sesiones_ab):
    contexto = str(datos_ab.a.id)

    assert _contar(motor_app, contexto, "consultorio") == 1
    assert _contar(motor_app, contexto, "usuario") == 3
    assert _contar(motor_app, contexto, "sesion") == 1


def test_contexto_b_solo_ve_b_y_a_la_inversa(motor_app, datos_ab, sesiones_ab):
    with motor_app.begin() as conexion:
        conexion.execute(
            text("SELECT set_config('app.consultorio_id', :c, true)"), {"c": str(datos_ab.b.id)}
        )
        consultorios = conexion.execute(text("SELECT id FROM consultorio")).scalars().all()
        usuarios = conexion.execute(text("SELECT consultorio_id FROM usuario")).scalars().all()

    assert consultorios == [datos_ab.b.id]
    assert set(usuarios) == {datos_ab.b.id}


def test_contexto_de_consultorio_inexistente_cero_filas(motor_app, sesiones_ab):
    assert _contar(motor_app, str(uuid.uuid4()), "usuario") == 0


def test_revocar_la_sesion_de_b_por_id_con_contexto_a_afecta_cero_filas(
    motor_app, motor_admin, datos_ab, sesiones_ab
):
    _sesion_a, sesion_b = sesiones_ab

    with motor_app.begin() as conexion:
        conexion.execute(
            text("SELECT set_config('app.consultorio_id', :c, true)"), {"c": str(datos_ab.a.id)}
        )
        resultado = conexion.execute(
            text("UPDATE sesion SET revocada_en = now() WHERE id = :i"), {"i": sesion_b}
        )

    assert resultado.rowcount == 0
    with motor_admin.connect() as conexion:
        assert (
            conexion.execute(
                text("SELECT revocada_en FROM sesion WHERE id = :i"), {"i": sesion_b}
            ).scalar_one()
            is None
        )


def test_revocar_la_propia_sesion_con_contexto_afecta_una_fila(
    motor_app, motor_admin, datos_ab, sesiones_ab
):
    sesion_a, _sesion_b = sesiones_ab

    with motor_app.begin() as conexion:
        conexion.execute(
            text("SELECT set_config('app.consultorio_id', :c, true)"), {"c": str(datos_ab.a.id)}
        )
        resultado = conexion.execute(
            text("UPDATE sesion SET revocada_en = now() WHERE id = :i"), {"i": sesion_a}
        )

    assert resultado.rowcount == 1


def test_insertar_una_sesion_de_b_con_contexto_a_es_rechazado(motor_app, datos_ab):
    with pytest.raises(DBAPIError) as info:
        with motor_app.begin() as conexion:
            conexion.execute(
                text("SELECT set_config('app.consultorio_id', :c, true)"),
                {"c": str(datos_ab.a.id)},
            )
            conexion.execute(
                text(
                    "INSERT INTO sesion (consultorio_id, usuario_id, token_hmac, creada_en, "
                    "ultimo_uso_en, vence_absoluto_en) VALUES (:c, :u, :t, now(), now(), "
                    "now() + interval '1 hour')"
                ),
                {
                    "c": datos_ab.b.id,
                    "u": datos_ab.b.usuarios[Rol.ADMINISTRADOR].id,
                    "t": os.urandom(32),
                },
            )

    assert getattr(info.value.orig, "sqlstate", "") == "42501"


def test_insertar_una_sesion_sin_contexto_es_rechazado(motor_app, datos_ab):
    with pytest.raises(DBAPIError) as info:
        with motor_app.begin() as conexion:
            conexion.execute(
                text(
                    "INSERT INTO sesion (consultorio_id, usuario_id, token_hmac, creada_en, "
                    "ultimo_uso_en, vence_absoluto_en) VALUES (:c, :u, :t, now(), now(), "
                    "now() + interval '1 hour')"
                ),
                {
                    "c": datos_ab.a.id,
                    "u": datos_ab.a.usuarios[Rol.ADMINISTRADOR].id,
                    "t": os.urandom(32),
                },
            )

    assert getattr(info.value.orig, "sqlstate", "") == "42501"


def test_insertar_una_sesion_propia_con_contexto_funciona(motor_app, motor_admin, datos_ab):
    with motor_app.begin() as conexion:
        conexion.execute(
            text("SELECT set_config('app.consultorio_id', :c, true)"), {"c": str(datos_ab.a.id)}
        )
        conexion.execute(
            text(
                "INSERT INTO sesion (consultorio_id, usuario_id, token_hmac, creada_en, "
                "ultimo_uso_en, vence_absoluto_en) VALUES (:c, :u, :t, now(), now(), "
                "now() + interval '1 hour')"
            ),
            {
                "c": datos_ab.a.id,
                "u": datos_ab.a.usuarios[Rol.ADMINISTRADOR].id,
                "t": os.urandom(32),
            },
        )

    with motor_admin.connect() as conexion:
        assert (
            conexion.execute(
                text("SELECT count(*) FROM sesion WHERE consultorio_id = :c"), {"c": datos_ab.a.id}
            ).scalar_one()
            == 1
        )


def test_rls_habilitada_y_forzada_en_las_cuatro_tablas(motor_admin):
    with motor_admin.connect() as conexion:
        filas = conexion.execute(
            text(
                "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE relnamespace = 'public'::regnamespace AND relname = ANY(:t)"
            ),
            {"t": list(TABLAS_CON_RLS)},
        ).all()

    assert {fila[0] for fila in filas} == set(TABLAS_CON_RLS)
    assert all(fila[1] and fila[2] for fila in filas)


def test_complemento_con_set_role_sin_contexto_cero_filas(motor_admin, datos_ab, sesiones_ab):
    """Complemento desde administracion: SET LOCAL ROLE turnos_app respeta RLS (transaccion revertida)."""
    with motor_admin.connect() as conexion:
        transaccion = conexion.begin()
        try:
            conexion.execute(text("SET LOCAL ROLE turnos_app"))
            sin = conexion.execute(text("SELECT count(*) FROM usuario")).scalar_one()
            conexion.execute(
                text("SELECT set_config('app.consultorio_id', :c, true)"),
                {"c": str(datos_ab.a.id)},
            )
            con = conexion.execute(text("SELECT count(*) FROM usuario")).scalar_one()
        finally:
            transaccion.rollback()

    assert sin == 0
    assert con == 3


def test_select_de_usuario_del_orm_funciona_como_turnos_app_con_contexto(motor_app, datos_ab):
    """4.5: las columnas diferidas permiten `select(Usuario)` aun sin privilegio sobre `credencial`."""
    from sqlalchemy import select
    from sqlalchemy.exc import InvalidRequestError
    from app.core.contexto_bd import aplicar_contexto, crear_fabrica_de_sesiones
    from app.models.usuario import Usuario
    from app.repositories.contexto import ContextoConsultorio

    with crear_fabrica_de_sesiones(motor_app)() as db:
        aplicar_contexto(db, ContextoConsultorio(datos_ab.a.id))
        usuarios = db.scalars(select(Usuario)).all()

        assert {u.consultorio_id for u in usuarios} == {datos_ab.a.id}
        assert len(usuarios) == 3
        with pytest.raises(InvalidRequestError):
            usuarios[0].credencial

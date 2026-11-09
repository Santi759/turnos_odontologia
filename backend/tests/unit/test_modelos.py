from app.models.base import Base
from app.models.consultorio import Consultorio
from app.models.usuario import Rol, Usuario, normalizar_email


def test_los_modelos_del_modelo_base_estan_registrados():
    assert {"consultorio", "usuario"} <= set(Base.metadata.tables)


def test_rol_tiene_exactamente_los_tres_valores_admitidos():
    assert sorted(rol.value for rol in Rol) == [
        "administrador",
        "odontologo",
        "secretaria",
    ]


def test_normalizar_email_quita_espacios_y_pasa_a_minusculas():
    assert (
        normalizar_email(" Persona.Ficticia@Example.TEST ")
        == "persona.ficticia@example.test"
    )


def test_normalizar_email_deja_igual_un_email_ya_normalizado():
    assert (
        normalizar_email("persona.ficticia@example.test")
        == "persona.ficticia@example.test"
    )


def test_normalizar_email_no_toca_espacios_internos():
    assert normalizar_email("Persona Ficticia@Example.test") == "persona ficticia@example.test"


def test_usuario_declara_las_restricciones_con_nombre_de_la_convencion():
    nombres = {restriccion.name for restriccion in Usuario.__table__.constraints}

    assert {
        "pk_usuario",
        "fk_usuario_consultorio_id_consultorio",
        "uq_usuario_consultorio_id_id",
        "uq_usuario_consultorio_id_email",
        "ck_usuario_rol_valido",
        "ck_usuario_email_normalizado",
        "ck_usuario_credencial_no_vacia",
    } <= nombres


# --- C-03: codigo de consultorio, sesion e intento_login ---------------------------


def test_consultorio_codigo_obligatorio_y_sin_valor_por_defecto_de_servidor():
    columna = Consultorio.__table__.c.codigo

    assert columna.nullable is False
    assert columna.server_default is None
    assert columna.default is None


def test_consultorio_declara_unicidad_y_formato_del_codigo_con_nombre_de_la_convencion():
    nombres = {restriccion.name for restriccion in Consultorio.__table__.constraints}

    assert {"uq_consultorio_codigo", "ck_consultorio_codigo_formato"} <= nombres


def test_sesion_e_intento_login_estan_registrados():
    import app.models  # noqa: F401  (registra los modelos en los metadatos)

    assert {"sesion", "intento_login"} <= set(Base.metadata.tables)


def test_sesion_declara_restricciones_e_indices_con_nombre_de_la_convencion():
    from app.models.sesion import Sesion

    tabla = Sesion.__table__

    assert {restriccion.name for restriccion in tabla.constraints} >= {
        "pk_sesion",
        "uq_sesion_token_hmac",
        "fk_sesion_consultorio_id_usuario",
        "ck_sesion_token_hmac_longitud",
        "ck_sesion_vencimientos_coherentes",
        "ck_sesion_revocacion_posterior",
    }
    assert {indice.name for indice in tabla.indexes} == {
        "ix_sesion_consultorio_id_usuario_id",
        "ix_sesion_vence_absoluto_en",
        "ix_sesion_ultimo_uso_en",
        "ix_sesion_revocada_en",
    }


def test_intento_login_declara_la_marca_con_valor_por_defecto_falso():
    from app.models.intento_login import IntentoLogin

    columna = IntentoLogin.__table__.c.descartado_para_cuenta

    assert columna.nullable is False
    assert str(columna.server_default.arg) == "false"
    assert {indice.name for indice in IntentoLogin.__table__.indexes} == {
        "ix_intento_login_clave_cuenta_ocurrido_en",
        "ix_intento_login_clave_ip_ocurrido_en",
        "ix_intento_login_ocurrido_en",
    }

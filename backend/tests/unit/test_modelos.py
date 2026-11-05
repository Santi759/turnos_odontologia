from app.models.base import Base
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

import dataclasses
import uuid

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.models.usuario import Rol
from app.repositories.consultorios import ConsultorioRepositorio
from app.repositories.contexto import ContextoConsultorio
from app.repositories.usuarios import NuevoUsuario, UsuarioRepositorio

ID_A = uuid.UUID("0199a000-0000-7000-8000-00000000000a")
ID_B = uuid.UUID("0199a000-0000-7000-8000-00000000000b")


def _sesion_sin_base() -> Session:
    # Una sesion sin conexion: solo se usa para compilar SQL, nunca se ejecuta.
    return Session()


def _sql(consulta) -> str:
    return str(
        consulta.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


# --- Contexto ---------------------------------------------------------------


def test_contexto_expone_el_identificador_y_es_inmutable():
    contexto = ContextoConsultorio(ID_A)

    assert contexto.consultorio_id == ID_A
    with pytest.raises(dataclasses.FrozenInstanceError):
        contexto.consultorio_id = ID_B  # type: ignore[misc]


@pytest.mark.parametrize("invalido", ["1", 1, str(ID_A), None])
def test_contexto_con_identificador_no_uuid_rechazado(invalido):
    with pytest.raises(TypeError):
        ContextoConsultorio(invalido)  # type: ignore[arg-type]


@pytest.mark.parametrize("repositorio", [UsuarioRepositorio, ConsultorioRepositorio])
def test_repositorio_sin_contexto_rechazado(repositorio):
    with pytest.raises(TypeError):
        repositorio(_sesion_sin_base(), ID_A)  # type: ignore[arg-type]


def test_repositorio_acepta_un_contexto_valido():
    repositorio = UsuarioRepositorio(_sesion_sin_base(), ContextoConsultorio(ID_B))

    assert repositorio.contexto.consultorio_id == ID_B


# --- Datos de alta de usuario -------------------------------------------------


def test_datos_de_alta_de_usuario_sin_consultorio_id():
    with pytest.raises(TypeError):
        NuevoUsuario(  # type: ignore[call-arg]
            email="a@example.test",
            nombre="Persona Ficticia",
            rol=Rol.SECRETARIA,
            consultorio_id=ID_A,
        )
    assert "consultorio_id" not in {c.name for c in dataclasses.fields(NuevoUsuario)}


# --- SQL generado ---------------------------------------------------------------


@pytest.mark.parametrize("contexto_id", [ID_A, ID_B])
def test_toda_consulta_generada_incluye_el_filtro_por_consultorio(contexto_id):
    repositorio = UsuarioRepositorio(
        _sesion_sin_base(), ContextoConsultorio(contexto_id)
    )
    consultas = [
        repositorio._consulta_listar(),
        repositorio._consulta_obtener_por_id(uuid.uuid4()),
        repositorio._consulta_buscar_por_email("Persona.Ficticia@Example.TEST"),
    ]

    for consulta in consultas:
        sql = _sql(consulta)
        assert f"usuario.consultorio_id = '{contexto_id}'" in sql


def test_el_acotamiento_del_repositorio_cambia_con_el_contexto():
    sql_a = _sql(
        UsuarioRepositorio(
            _sesion_sin_base(), ContextoConsultorio(ID_A)
        )._consulta_listar()
    )

    assert str(ID_B) not in sql_a


def test_buscar_por_email_normaliza_antes_de_consultar():
    sql = _sql(
        UsuarioRepositorio(
            _sesion_sin_base(), ContextoConsultorio(ID_A)
        )._consulta_buscar_por_email("  Persona.Ficticia@Example.TEST ")
    )

    assert "usuario.email = 'persona.ficticia@example.test'" in sql


# --- Consultorios: sin operaciones sobre otros consultorios -------------------------


def test_consultorio_repositorio_solo_expone_obtener_actual():
    publicas = {
        nombre
        for nombre in dir(ConsultorioRepositorio)
        if not nombre.startswith("_") and callable(getattr(ConsultorioRepositorio, nombre))
    }

    assert publicas == {"obtener_actual"}


def test_obtener_actual_se_acota_por_el_id_del_contexto():
    sql = _sql(
        ConsultorioRepositorio(
            _sesion_sin_base(), ContextoConsultorio(ID_A)
        )._consulta_actual()
    )

    assert f"consultorio.id = '{ID_A}'" in sql

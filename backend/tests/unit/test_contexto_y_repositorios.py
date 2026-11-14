import ast
import re
import dataclasses
import uuid
from pathlib import Path

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


# --- Un unico punto de construccion en la aplicacion (C-03, tarea 5.2) ------------------

RAIZ_APP = Path(__file__).resolve().parents[2] / "app"
MODULO_DE_IDENTIDAD = "auth/dependencias.py"


def _construyen_contexto(fuente: str) -> bool:
    """Verdadero si el codigo contiene una llamada a `ContextoConsultorio(...)`."""
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Call):
            funcion = nodo.func
            nombre = getattr(funcion, "id", None) or getattr(funcion, "attr", None)
            if nombre == "ContextoConsultorio":
                return True
    return False


def _archivos_de_la_app_que_construyen_contexto() -> set[str]:
    return {
        archivo.relative_to(RAIZ_APP).as_posix()
        for archivo in RAIZ_APP.rglob("*.py")
        if _construyen_contexto(archivo.read_text(encoding="utf-8"))
    }


def test_el_detector_encuentra_construcciones_directas_y_con_prefijo_de_modulo():
    assert _construyen_contexto("c = ContextoConsultorio(sesion.consultorio_id)")
    assert _construyen_contexto("c = contexto.ContextoConsultorio(uuid.uuid4())")
    assert not _construyen_contexto("def f(c: ContextoConsultorio) -> None: ...")
    assert not _construyen_contexto("class ContextoConsultorio: ...")


def test_las_construcciones_de_contexto_fuera_de_pruebas_solo_estan_en_la_dependencia_de_identidad():
    # Igualdad (tarea 5.2): la dependencia de identidad existe y es el UNICO lugar de la app
    # que construye el contexto; ni cero construcciones ni una adicional en otro archivo.
    construcciones = _archivos_de_la_app_que_construyen_contexto()

    assert construcciones == {MODULO_DE_IDENTIDAD}


# --- Contexto transaccional: usos permitidos (C-04, 4.6, DD-04) ----------------------------------------


def _fuentes_de_app() -> dict[str, str]:
    raiz = Path(__file__).resolve().parents[2] / "app"
    return {
        ruta.relative_to(raiz).as_posix(): ruta.read_text(encoding="utf-8")
        for ruta in raiz.rglob("*.py")
    }


def _llamadas(nombre: str) -> set[str]:
    """Archivos de `app/` que LLAMAN a `nombre` (la definicion no cuenta)."""
    encontrados = set()
    for ruta, fuente in _fuentes_de_app().items():
        for nodo in ast.walk(ast.parse(fuente)):
            if isinstance(nodo, ast.Call):
                funcion = nodo.func
                llamado = funcion.id if isinstance(funcion, ast.Name) else getattr(funcion, "attr", None)
                if llamado == nombre:
                    encontrados.add(ruta)
    return encontrados


def test_la_unica_aparicion_del_parametro_de_contexto_esta_en_contexto_bd():
    con_parametro = {
        ruta for ruta, fuente in _fuentes_de_app().items() if "app.consultorio_id" in fuente
    }

    assert con_parametro == {"core/contexto_bd.py"}


def test_aplicar_contexto_solo_se_llama_desde_dependencias():
    assert _llamadas("aplicar_contexto") == {"auth/dependencias.py"}


def test_fijar_consultorio_de_login_solo_se_llama_desde_el_servicio():
    assert _llamadas("fijar_consultorio_de_login") == {"auth/servicio.py"}


def test_nunca_se_fija_el_contexto_con_set_de_sesion():
    for ruta, fuente in _fuentes_de_app().items():
        assert "set_config('app.consultorio_id', :valor, false)" not in fuente, ruta
        assert not re.search(r"SET\s+(SESSION\s+)?app\.consultorio_id", fuente, re.IGNORECASE), ruta

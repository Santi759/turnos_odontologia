import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.consultorio import Consultorio
from app.models.usuario import Rol
from app.repositories.consultorios import ConsultorioRepositorio
from app.repositories.contexto import ContextoConsultorio
from app.repositories.usuarios import NuevoUsuario, UsuarioRepositorio

EMAIL = "persona.ficticia@example.test"


@dataclass
class Escenario:
    sesion: Session
    consultorio_a: uuid.UUID
    consultorio_b: uuid.UUID
    usuarios_a: list[uuid.UUID]
    usuarios_b: list[uuid.UUID]

    def repo_a(self) -> UsuarioRepositorio:
        return UsuarioRepositorio(self.sesion, ContextoConsultorio(self.consultorio_a))

    def repo_b(self) -> UsuarioRepositorio:
        return UsuarioRepositorio(self.sesion, ContextoConsultorio(self.consultorio_b))


def _consultorio(sesion: Session, nombre: str) -> uuid.UUID:
    return sesion.execute(
        text("INSERT INTO consultorio (nombre) VALUES (:n) RETURNING id"), {"n": nombre}
    ).scalar_one()


def _usuario(sesion: Session, consultorio_id: uuid.UUID, email: str) -> uuid.UUID:
    return sesion.execute(
        text(
            "INSERT INTO usuario (consultorio_id, email, nombre, rol) "
            "VALUES (:c, :e, 'Persona Ficticia', 'secretaria') RETURNING id"
        ),
        {"c": consultorio_id, "e": email},
    ).scalar_one()


@pytest.fixture
def escenario(sesion: Session) -> Escenario:
    a = _consultorio(sesion, "Consultorio Ficticio A")
    b = _consultorio(sesion, "Consultorio Ficticio B")
    usuarios_a = [
        _usuario(sesion, a, email)
        for email in (EMAIL, "dos.a@example.test", "tres.a@example.test")
    ]
    usuarios_b = [
        _usuario(sesion, b, email)
        for email in (EMAIL, "dos.b@example.test", "solo.b@example.test")
    ]
    return Escenario(sesion, a, b, usuarios_a, usuarios_b)


def _activo(sesion: Session, usuario_id: uuid.UUID) -> bool:
    return sesion.execute(
        text("SELECT activo FROM usuario WHERE id = :id"), {"id": usuario_id}
    ).scalar_one()


# --- Lecturas acotadas ----------------------------------------------------------


def test_listado_solo_del_consultorio_propio(escenario: Escenario):
    ids_a = {u.id for u in escenario.repo_a().listar()}
    ids_b = {u.id for u in escenario.repo_b().listar()}

    assert ids_a == set(escenario.usuarios_a)
    assert ids_b == set(escenario.usuarios_b)


def test_obtener_por_id_propio_devuelve_el_usuario(escenario: Escenario):
    usuario = escenario.repo_a().obtener_por_id(escenario.usuarios_a[1])

    assert usuario is not None
    assert usuario.email == "dos.a@example.test"
    assert usuario.consultorio_id == escenario.consultorio_a


def test_obtener_por_id_de_otro_consultorio_igual_que_inexistente(
    escenario: Escenario,
):
    ajeno = escenario.repo_a().obtener_por_id(escenario.usuarios_b[1])
    inexistente = escenario.repo_a().obtener_por_id(uuid.uuid4())

    assert ajeno is None
    assert ajeno == inexistente


def test_buscar_por_email_dentro_del_consultorio_sin_distinguir_mayusculas(
    escenario: Escenario,
):
    en_a = escenario.repo_a().buscar_por_email("Persona.Ficticia@Example.TEST")
    en_b = escenario.repo_b().buscar_por_email("Persona.Ficticia@Example.TEST")

    assert en_a is not None and en_b is not None
    assert en_a.id == escenario.usuarios_a[0]
    assert en_b.id == escenario.usuarios_b[0]


def test_buscar_por_email_de_otro_consultorio_igual_que_inexistente(
    escenario: Escenario,
):
    ajeno = escenario.repo_a().buscar_por_email("solo.b@example.test")
    inexistente = escenario.repo_a().buscar_por_email("nadie@example.test")

    assert ajeno is None
    assert ajeno == inexistente


# --- Escrituras acotadas ---------------------------------------------------------


def test_alta_con_el_consultorio_del_contexto(escenario: Escenario):
    usuario = escenario.repo_a().crear(
        NuevoUsuario(
            email=" Nueva.Persona@Example.test ",
            nombre="Nueva Persona Ficticia",
            rol=Rol.SECRETARIA,
        )
    )

    assert usuario.consultorio_id == escenario.consultorio_a
    assert usuario.email == "nueva.persona@example.test"
    assert usuario.credencial is None
    assert usuario.activo is True
    assert usuario.id.version == 7
    assert escenario.repo_b().buscar_por_email("nueva.persona@example.test") is None


def test_alta_en_b_queda_en_b(escenario: Escenario):
    usuario = escenario.repo_b().crear(
        NuevoUsuario(email="nuevo.b@example.test", nombre="Nuevo B", rol=Rol.ODONTOLOGO)
    )

    assert usuario.consultorio_id == escenario.consultorio_b
    assert usuario.rol == "odontologo"


def test_alta_con_email_repetido_sin_distinguir_mayusculas_rechazada(
    escenario: Escenario,
):
    with pytest.raises(IntegrityError) as excinfo:
        with escenario.sesion.begin_nested():
            escenario.repo_a().crear(
                NuevoUsuario(
                    email="PERSONA.FICTICIA@example.test",
                    nombre="Otra Persona Ficticia",
                    rol=Rol.ODONTOLOGO,
                )
            )

    assert getattr(excinfo.value.orig, "sqlstate", None) == "23505"
    assert len(escenario.repo_a().listar()) == 3


def test_mismo_email_en_otro_consultorio_se_permite(escenario: Escenario):
    usuario = escenario.repo_b().crear(
        NuevoUsuario(email="TRES.A@example.test", nombre="Cuenta B", rol=Rol.SECRETARIA)
    )

    assert usuario.consultorio_id == escenario.consultorio_b


def test_desactivar_un_usuario_propio(escenario: Escenario):
    objetivo = escenario.usuarios_a[2]

    resultado = escenario.repo_a().desactivar(objetivo)

    assert resultado is True
    assert _activo(escenario.sesion, objetivo) is False


def test_desactivar_un_usuario_de_otro_consultorio_igual_que_inexistente(
    escenario: Escenario,
):
    ajeno = escenario.repo_a().desactivar(escenario.usuarios_b[0])
    inexistente = escenario.repo_a().desactivar(uuid.uuid4())

    assert ajeno is False
    assert ajeno == inexistente
    assert all(_activo(escenario.sesion, u) for u in escenario.usuarios_b)
    assert all(_activo(escenario.sesion, u) for u in escenario.usuarios_a)


def test_desactivar_no_cambia_filas_ajenas_ni_otros_propios(escenario: Escenario):
    escenario.repo_a().desactivar(escenario.usuarios_a[0])

    assert _activo(escenario.sesion, escenario.usuarios_a[1]) is True
    assert _activo(escenario.sesion, escenario.usuarios_b[0]) is True


# --- Consultorio actual -----------------------------------------------------------


def test_obtener_el_consultorio_actual(escenario: Escenario):
    repo = ConsultorioRepositorio(
        escenario.sesion, ContextoConsultorio(escenario.consultorio_a)
    )

    consultorio = repo.obtener_actual()

    assert isinstance(consultorio, Consultorio)
    assert consultorio.id == escenario.consultorio_a
    assert consultorio.nombre == "Consultorio Ficticio A"
    assert consultorio.zona_horaria == "America/Argentina/Buenos_Aires"
    assert consultorio.anticipacion_cancelacion_horas == 24


def test_contexto_de_un_consultorio_inexistente_no_devuelve_resultado(
    escenario: Escenario,
):
    repo = ConsultorioRepositorio(escenario.sesion, ContextoConsultorio(uuid.uuid4()))

    assert repo.obtener_actual() is None

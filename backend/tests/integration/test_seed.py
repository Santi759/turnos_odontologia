import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.usuario import Rol
from app.seed.__main__ import main
from app.seed.aplicar import aplicar_seed
from app.seed.datos import CONSULTORIOS, USUARIOS


def _consultorios(sesion: Session) -> list:
    return sesion.execute(
        text(
            "SELECT id, nombre, activo, zona_horaria, anticipacion_cancelacion_horas "
            "FROM consultorio ORDER BY nombre"
        )
    ).all()


def _usuarios(sesion: Session) -> list:
    return sesion.execute(
        text(
            "SELECT id, consultorio_id, email, nombre, rol, credencial "
            "FROM usuario ORDER BY email"
        )
    ).all()


def test_dos_consultorios_y_seis_usuarios(sesion: Session):
    resumen = aplicar_seed(sesion)

    assert (resumen.consultorios_insertados, resumen.usuarios_insertados) == (2, 6)
    assert (resumen.consultorios_omitidos, resumen.usuarios_omitidos) == (0, 0)
    consultorios = _consultorios(sesion)
    assert [c.nombre for c in consultorios] == ["Consultorio Demo A", "Consultorio Demo B"]
    usuarios = _usuarios(sesion)
    assert len(usuarios) == 6
    for consultorio in consultorios:
        roles = sorted(u.rol for u in usuarios if u.consultorio_id == consultorio.id)
        assert roles == sorted(rol.value for rol in Rol)


def test_datos_evidentemente_ficticios(sesion: Session):
    aplicar_seed(sesion)

    usuarios = _usuarios(sesion)
    assert all(u.email.endswith("@example.test") for u in usuarios)
    assert all("Demo" in u.nombre for u in usuarios)


def test_valores_de_consultorio_del_seed(sesion: Session):
    aplicar_seed(sesion)

    for consultorio in _consultorios(sesion):
        assert consultorio.activo is True
        assert consultorio.zona_horaria == "America/Argentina/Buenos_Aires"
        assert consultorio.anticipacion_cancelacion_horas == 24


def test_seis_usuarios_sin_credencial(sesion: Session):
    aplicar_seed(sesion)

    usuarios = _usuarios(sesion)
    assert len(usuarios) == 6
    assert all(u.credencial is None for u in usuarios)


def test_dos_ejecuciones_no_duplican(sesion: Session):
    aplicar_seed(sesion)

    segunda = aplicar_seed(sesion)

    assert (segunda.consultorios_insertados, segunda.usuarios_insertados) == (0, 0)
    assert (segunda.consultorios_omitidos, segunda.usuarios_omitidos) == (2, 6)
    assert len(_consultorios(sesion)) == 2
    assert len(_usuarios(sesion)) == 6


def test_identificadores_fijos_entre_aplicaciones(sesion: Session):
    punto = sesion.begin_nested()
    aplicar_seed(sesion)
    ids_primera = sorted(str(f.id) for f in _consultorios(sesion) + _usuarios(sesion))
    punto.rollback()
    assert _consultorios(sesion) == []

    aplicar_seed(sesion)
    ids_segunda = sorted(str(f.id) for f in _consultorios(sesion) + _usuarios(sesion))

    assert ids_primera == ids_segunda
    assert ids_segunda == sorted(str(x.id) for x in (*CONSULTORIOS, *USUARIOS))


def test_una_fila_del_seed_modificada_no_se_sobrescribe(sesion: Session):
    aplicar_seed(sesion)
    sesion.execute(
        text("UPDATE consultorio SET nombre = 'Consultorio Ficticio Renombrado' WHERE id = :id"),
        {"id": CONSULTORIOS[0].id},
    )
    sesion.execute(
        text("UPDATE usuario SET nombre = 'Nombre Ficticio Cambiado' WHERE id = :id"),
        {"id": USUARIOS[0].id},
    )

    resumen = aplicar_seed(sesion)

    nombres = {c.id: c.nombre for c in _consultorios(sesion)}
    assert nombres[CONSULTORIOS[0].id] == "Consultorio Ficticio Renombrado"
    assert len(nombres) == 2
    usuarios = {u.id: u.nombre for u in _usuarios(sesion)}
    assert usuarios[USUARIOS[0].id] == "Nombre Ficticio Cambiado"
    assert (resumen.consultorios_insertados, resumen.usuarios_insertados) == (0, 0)


def test_una_fila_ajena_con_el_mismo_email_se_respeta(sesion: Session):
    aplicar_seed(sesion)
    administrador = USUARIOS[0]
    sesion.execute(text("DELETE FROM usuario WHERE id = :id"), {"id": administrador.id})
    ajeno = sesion.execute(
        text(
            "INSERT INTO usuario (consultorio_id, email, nombre, rol) "
            "VALUES (:c, :e, 'Persona Ficticia Previa', 'secretaria') RETURNING id"
        ),
        {"c": administrador.consultorio_id, "e": administrador.email},
    ).scalar_one()

    resumen = aplicar_seed(sesion)

    fila = sesion.execute(
        text("SELECT id, nombre, rol FROM usuario WHERE consultorio_id = :c AND email = :e"),
        {"c": administrador.consultorio_id, "e": administrador.email},
    ).one()
    assert fila.id == ajeno
    assert fila.nombre == "Persona Ficticia Previa"
    assert fila.rol == "secretaria"
    assert resumen.usuarios_omitidos >= 1
    assert resumen.usuarios_insertados == 0
    assert len(_usuarios(sesion)) == 6


def test_el_comando_principal_informa_solo_cantidades_y_carga_el_seed(
    sesion: Session,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    # Solo con una sesion inyectada (transaccion revertida de db-test): el comando
    # real nunca se ejecuta contra db-test.
    monkeypatch.setenv("APP_ENV", "local")

    codigo = main(abrir_sesion=lambda settings: sesion)

    salida = capsys.readouterr()
    assert codigo == 0
    assert "2 insertados" in salida.out and "6 insertados" in salida.out
    texto = salida.out + salida.err
    assert "@" not in texto and "postgresql" not in texto
    assert not any(u.nombre in texto for u in USUARIOS)
    assert len(_usuarios(sesion)) == 6

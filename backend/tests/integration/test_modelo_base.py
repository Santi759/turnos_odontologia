import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NOT_NULL = "23502"
FOREIGN_KEY = "23503"
RESTRICT = "23001"  # ON DELETE RESTRICT falla de inmediato con restrict_violation
UNIQUE = "23505"
CHECK = "23514"

EMAIL = "persona.ficticia@example.test"


def _consultorio(sesion: Session, nombre: str = "Consultorio Ficticio A") -> uuid.UUID:
    return sesion.execute(
        text("INSERT INTO consultorio (nombre) VALUES (:nombre) RETURNING id"),
        {"nombre": nombre},
    ).scalar_one()


def _usuario(
    sesion: Session,
    consultorio_id: uuid.UUID,
    email: str = EMAIL,
    rol: str = "secretaria",
) -> uuid.UUID:
    return sesion.execute(
        text(
            "INSERT INTO usuario (consultorio_id, email, nombre, rol) "
            "VALUES (:consultorio_id, :email, 'Persona Ficticia', :rol) RETURNING id"
        ),
        {"consultorio_id": consultorio_id, "email": email, "rol": rol},
    ).scalar_one()


def _sqlstate_de_la_falla(sesion: Session, sentencia: str, parametros: dict) -> str | None:
    with pytest.raises(IntegrityError) as excinfo:
        with sesion.begin_nested():
            sesion.execute(text(sentencia), parametros)
    return getattr(excinfo.value.orig, "sqlstate", None)


def _tipo_de_columna(sesion: Session, tabla: str, columna: str) -> str:
    return sesion.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :tabla "
            "AND column_name = :columna"
        ),
        {"tabla": tabla, "columna": columna},
    ).scalar_one()


# --- Consultorio con valores por defecto -------------------------------------


def test_valores_por_defecto_al_insertar_solo_el_nombre(sesion: Session):
    fila = sesion.execute(
        text(
            "INSERT INTO consultorio (nombre) VALUES ('Consultorio Ficticio A') "
            "RETURNING zona_horaria, anticipacion_cancelacion_horas, activo, creado_en"
        )
    ).one()

    assert fila.zona_horaria == "America/Argentina/Buenos_Aires"
    assert fila.anticipacion_cancelacion_horas == 24
    assert fila.activo is True
    assert fila.creado_en is not None
    assert _tipo_de_columna(sesion, "consultorio", "creado_en") == (
        "timestamp with time zone"
    )


def test_la_zona_horaria_por_defecto_existe_una_vez_en_pg_timezone_names(
    sesion: Session,
):
    zona = sesion.execute(
        text(
            "INSERT INTO consultorio (nombre) VALUES ('Consultorio Ficticio A') "
            "RETURNING zona_horaria"
        )
    ).scalar_one()

    cantidad = sesion.execute(
        text("SELECT count(*) FROM pg_timezone_names WHERE name = :zona"),
        {"zona": zona},
    ).scalar_one()

    assert cantidad == 1


def test_nombre_de_consultorio_obligatorio(sesion: Session):
    sqlstate = _sqlstate_de_la_falla(
        sesion, "INSERT INTO consultorio (activo) VALUES (true)", {}
    )

    assert sqlstate == NOT_NULL


# --- Anticipacion de cancelacion no negativa ---------------------------------


def test_anticipacion_negativa_rechazada(sesion: Session):
    sqlstate = _sqlstate_de_la_falla(
        sesion,
        "INSERT INTO consultorio (nombre, anticipacion_cancelacion_horas) "
        "VALUES ('Consultorio Ficticio A', -1)",
        {},
    )

    assert sqlstate == CHECK


def test_anticipacion_cero_aceptada(sesion: Session):
    horas = sesion.execute(
        text(
            "INSERT INTO consultorio (nombre, anticipacion_cancelacion_horas) "
            "VALUES ('Consultorio Ficticio A', 0) "
            "RETURNING anticipacion_cancelacion_horas"
        )
    ).scalar_one()

    assert horas == 0


# --- Identificadores UUIDv7 generados por la base ----------------------------


def test_id_de_consultorio_generado_como_uuid_v7(sesion: Session):
    consultorio_id = _consultorio(sesion)

    assert isinstance(consultorio_id, uuid.UUID)
    assert consultorio_id.version == 7


def test_id_de_usuario_generado_como_uuid_v7_y_distinto_del_consultorio(
    sesion: Session,
):
    consultorio_id = _consultorio(sesion)

    usuario_id = _usuario(sesion, consultorio_id)

    assert usuario_id.version == 7
    assert usuario_id != consultorio_id


# --- Usuario perteneciente a un unico consultorio ----------------------------


def test_usuario_con_consultorio_inexistente_rechazado(sesion: Session):
    sqlstate = _sqlstate_de_la_falla(
        sesion,
        "INSERT INTO usuario (consultorio_id, email, nombre, rol) "
        "VALUES (:inexistente, :email, 'Persona Ficticia', 'secretaria')",
        {"inexistente": uuid.uuid4(), "email": EMAIL},
    )

    assert sqlstate == FOREIGN_KEY


def test_usuario_sin_consultorio_rechazado(sesion: Session):
    sqlstate = _sqlstate_de_la_falla(
        sesion,
        "INSERT INTO usuario (email, nombre, rol) "
        "VALUES (:email, 'Persona Ficticia', 'secretaria')",
        {"email": EMAIL},
    )

    assert sqlstate == NOT_NULL


def test_borrado_de_consultorio_con_usuarios_restringido(sesion: Session):
    consultorio_id = _consultorio(sesion)
    _usuario(sesion, consultorio_id)

    sqlstate = _sqlstate_de_la_falla(
        sesion, "DELETE FROM consultorio WHERE id = :id", {"id": consultorio_id}
    )

    assert sqlstate == RESTRICT
    consultorios = sesion.execute(
        text("SELECT count(*) FROM consultorio WHERE id = :id"), {"id": consultorio_id}
    ).scalar_one()
    usuarios = sesion.execute(
        text("SELECT count(*) FROM usuario WHERE consultorio_id = :id"),
        {"id": consultorio_id},
    ).scalar_one()
    assert (consultorios, usuarios) == (1, 1)


def test_valores_por_defecto_del_usuario(sesion: Session):
    consultorio_id = _consultorio(sesion)

    fila = sesion.execute(
        text(
            "INSERT INTO usuario (consultorio_id, email, nombre, rol) "
            "VALUES (:consultorio_id, :email, 'Persona Ficticia', 'secretaria') "
            "RETURNING activo, credencial, creado_en"
        ),
        {"consultorio_id": consultorio_id, "email": EMAIL},
    ).one()

    assert fila.activo is True
    assert fila.credencial is None
    assert fila.creado_en is not None
    assert _tipo_de_columna(sesion, "usuario", "creado_en") == (
        "timestamp with time zone"
    )


# --- Ancla compuesta de consultorio e identificador --------------------------


def test_restriccion_unica_compuesta_consultorio_id_e_id_presente(sesion: Session):
    filas = sesion.execute(
        text(
            "SELECT c.conname, array_agg(a.attname ORDER BY k.ord) AS columnas "
            "FROM pg_constraint c "
            "CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) "
            "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum "
            "WHERE c.conrelid = 'usuario'::regclass AND c.contype = 'u' "
            "GROUP BY c.conname"
        )
    ).all()

    assert ["consultorio_id", "id"] in [list(fila.columnas) for fila in filas]


# --- Rol restringido ----------------------------------------------------------


def test_roles_admitidos_aceptados(sesion: Session):
    consultorio_id = _consultorio(sesion)

    for numero, rol in enumerate(["administrador", "secretaria", "odontologo"]):
        _usuario(sesion, consultorio_id, email=f"rol{numero}@example.test", rol=rol)

    cantidad = sesion.execute(
        text("SELECT count(*) FROM usuario WHERE consultorio_id = :id"),
        {"id": consultorio_id},
    ).scalar_one()
    assert cantidad == 3


@pytest.mark.parametrize("rol", ["secretaría", "Administrador", "paciente"])
def test_rol_no_admitido_rechazado(sesion: Session, rol: str):
    consultorio_id = _consultorio(sesion)

    sqlstate = _sqlstate_de_la_falla(
        sesion,
        "INSERT INTO usuario (consultorio_id, email, nombre, rol) "
        "VALUES (:consultorio_id, :email, 'Persona Ficticia', :rol)",
        {"consultorio_id": consultorio_id, "email": EMAIL, "rol": rol},
    )

    assert sqlstate == CHECK


# --- Email unico por consultorio y normalizado --------------------------------


def test_mismo_email_en_dos_consultorios_aceptado(sesion: Session):
    consultorio_a = _consultorio(sesion, "Consultorio Ficticio A")
    consultorio_b = _consultorio(sesion, "Consultorio Ficticio B")

    id_a = _usuario(sesion, consultorio_a)
    id_b = _usuario(sesion, consultorio_b)

    assert id_a != id_b


def test_email_repetido_en_el_mismo_consultorio_rechazado(sesion: Session):
    consultorio_a = _consultorio(sesion)
    _usuario(sesion, consultorio_a)

    sqlstate = _sqlstate_de_la_falla(
        sesion,
        "INSERT INTO usuario (consultorio_id, email, nombre, rol) "
        "VALUES (:consultorio_id, :email, 'Otra Persona Ficticia', 'odontologo')",
        {"consultorio_id": consultorio_a, "email": EMAIL},
    )

    assert sqlstate == UNIQUE


@pytest.mark.parametrize(
    "email",
    ["Persona.Ficticia@Example.test", " persona.ficticia@example.test", ""],
)
def test_email_no_normalizado_rechazado_por_la_base(sesion: Session, email: str):
    consultorio_id = _consultorio(sesion)

    sqlstate = _sqlstate_de_la_falla(
        sesion,
        "INSERT INTO usuario (consultorio_id, email, nombre, rol) "
        "VALUES (:consultorio_id, :email, 'Persona Ficticia', 'secretaria')",
        {"consultorio_id": consultorio_id, "email": email},
    )

    assert sqlstate == CHECK


# --- Usuario sin credencial utilizable ----------------------------------------


def test_usuario_sin_credencial_aceptado(sesion: Session):
    consultorio_id = _consultorio(sesion)

    credencial = sesion.execute(
        text(
            "INSERT INTO usuario (consultorio_id, email, nombre, rol) "
            "VALUES (:consultorio_id, :email, 'Persona Ficticia', 'secretaria') "
            "RETURNING credencial"
        ),
        {"consultorio_id": consultorio_id, "email": EMAIL},
    ).scalar_one()

    assert credencial is None


def test_credencial_vacia_rechazada(sesion: Session):
    consultorio_id = _consultorio(sesion)

    sqlstate = _sqlstate_de_la_falla(
        sesion,
        "INSERT INTO usuario (consultorio_id, email, nombre, rol, credencial) "
        "VALUES (:consultorio_id, :email, 'Persona Ficticia', 'secretaria', '')",
        {"consultorio_id": consultorio_id, "email": EMAIL},
    )

    assert sqlstate == CHECK

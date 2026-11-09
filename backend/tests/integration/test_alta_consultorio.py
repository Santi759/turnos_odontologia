"""Alta de consultorio con codigo derivado y reintento ante colision (DD-13).

Todo contra la base de PRUEBAS (db-test), dentro de la transaccion revertible de `sesion`.
"""

import secrets
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.acceso_previo import CodigoConsultorioNoDisponible, insertar_consultorio
from app.models.codigo import codigo_corto, codigo_largo

ID_EXISTENTE = uuid.UUID("01a1a95a-dd90-73e7-9496-c7d08d776d19")
ID_COLISION = uuid.UUID("01a1a95a-dd90-7000-8000-c7d08d776d19")
CODIGO_CORTO_COLISION = "c-c7d08d776d19"
CODIGO_LARGO_COLISION = "c-01a1a95add9070008000c7d08d776d19"


def _insertar_con_codigo(
    sesion: Session, codigo: str, consultorio_id: uuid.UUID | None = None
) -> uuid.UUID:
    return sesion.execute(
        text(
            "INSERT INTO consultorio (id, nombre, codigo) "
            "VALUES (COALESCE(:id, uuidv7()), 'Consultorio Ficticio Previo', :codigo) "
            "RETURNING id"
        ),
        {"id": consultorio_id, "codigo": codigo},
    ).scalar_one()


def _fila(sesion: Session, consultorio_id: uuid.UUID):
    return sesion.execute(
        text("SELECT * FROM consultorio WHERE id = :id"), {"id": consultorio_id}
    ).one_or_none()


def _total(sesion: Session) -> int:
    return sesion.execute(text("SELECT count(*) FROM consultorio")).scalar_one()


def _contar_inserciones(sesion: Session) -> list[str]:
    inserciones: list[str] = []

    def registrar(conexion, cursor, sentencia, parametros, contexto, ejecutar_muchos):
        if sentencia.lstrip().upper().startswith("INSERT INTO CONSULTORIO"):
            inserciones.append(str(parametros))

    event.listen(sesion.get_bind(), "before_cursor_execute", registrar)
    return inserciones


# --- Alta asigna el codigo corto ---------------------------------------------------


def test_alta_asigna_id_uuid_v7_de_la_base_y_el_codigo_corto_derivado(sesion: Session):
    creado = insertar_consultorio(sesion, "Consultorio Ficticio A")

    assert creado.id.version == 7
    assert creado.codigo == codigo_corto(creado.id)
    fila = _fila(sesion, creado.id)
    assert (fila.nombre, fila.codigo) == ("Consultorio Ficticio A", creado.codigo)


def test_el_nombre_no_influye_en_el_codigo(sesion: Session):
    primero = insertar_consultorio(sesion, "Consultorio Ficticio A")
    segundo = insertar_consultorio(sesion, "Consultorio Ficticio A")

    assert primero.codigo == codigo_corto(primero.id)
    assert segundo.codigo == codigo_corto(segundo.id)
    assert primero.codigo != segundo.codigo
    assert primero.codigo.startswith("c-") and "ficticio" not in primero.codigo


# --- Colision: reintento con el codigo largo ----------------------------------------


def test_alta_con_colision_reintenta_con_el_codigo_largo(sesion: Session):
    existente = _insertar_con_codigo(sesion, CODIGO_CORTO_COLISION)
    antes = _fila(sesion, existente)

    creado = insertar_consultorio(
        sesion, "Consultorio Ficticio B", generar_id=lambda _sesion: ID_COLISION
    )

    assert creado.id == ID_COLISION
    assert creado.codigo == CODIGO_LARGO_COLISION == codigo_largo(ID_COLISION)
    assert _fila(sesion, ID_COLISION).codigo == CODIGO_LARGO_COLISION
    assert _fila(sesion, existente) == antes
    assert _total(sesion) == 2  # la consulta posterior corre sin error en la misma transaccion


def test_colision_tambien_del_codigo_largo_falla_con_error_controlado(sesion: Session):
    corto = _insertar_con_codigo(sesion, CODIGO_CORTO_COLISION)
    largo = _insertar_con_codigo(sesion, CODIGO_LARGO_COLISION)
    antes = (_fila(sesion, corto), _fila(sesion, largo))

    with pytest.raises(CodigoConsultorioNoDisponible):
        insertar_consultorio(
            sesion, "Consultorio Ficticio B", generar_id=lambda _sesion: ID_COLISION
        )

    assert _fila(sesion, ID_COLISION) is None
    assert (_fila(sesion, corto), _fila(sesion, largo)) == antes
    assert _total(sesion) == 2  # la transaccion del llamador sigue utilizable


# --- Solo la colision del codigo provoca el reintento -------------------------------


def test_violacion_de_la_clave_primaria_se_propaga_sin_reintento(sesion: Session):
    _insertar_con_codigo(sesion, "ficticio-a", consultorio_id=ID_EXISTENTE)
    inserciones = _contar_inserciones(sesion)

    with pytest.raises(IntegrityError) as excinfo:
        insertar_consultorio(
            sesion, "Consultorio Ficticio B", generar_id=lambda _sesion: ID_EXISTENTE
        )

    assert excinfo.value.orig.diag.constraint_name == "pk_consultorio"
    assert len(inserciones) == 1  # no se intento con el codigo largo
    assert _total(sesion) == 1


def test_nombre_nulo_se_propaga_como_violacion_not_null_sin_reintento(sesion: Session):
    inserciones = _contar_inserciones(sesion)

    with pytest.raises(IntegrityError) as excinfo:
        insertar_consultorio(sesion, None)  # type: ignore[arg-type]

    assert getattr(excinfo.value.orig, "sqlstate", None) == "23502"
    assert excinfo.value.orig.diag.column_name == "nombre"
    assert len(inserciones) == 1
    assert _total(sesion) == 0


# --- Equivalencia SQL/Python -------------------------------------------------------


def test_equivalencia_entre_la_regla_de_python_y_el_backfill_de_sql(
    base_en_0002: Engine, config_alembic: Config
):
    ids = [uuid.uuid4() for _ in range(500)] + [uuid.uuid7() for _ in range(500)]
    assert len(set(ids)) == 1000
    assert {i.version for i in ids} == {4, 7}
    with base_en_0002.begin() as conexion:
        conexion.execute(
            text("INSERT INTO consultorio (id, nombre) VALUES (:id, 'Consultorio Ficticio')"),
            [{"id": i} for i in ids],
        )

    command.upgrade(config_alembic, "0003")

    with base_en_0002.connect() as conexion:
        filas = conexion.execute(
            text(
                "SELECT id, codigo, "
                "'c-' || right(replace(id::text, '-', ''), 12) AS corto_sql, "
                "'c-' || replace(id::text, '-', '') AS largo_sql FROM consultorio"
            )
        ).all()
    assert len(filas) == 1000
    for fila in filas:
        assert fila.corto_sql == codigo_corto(fila.id)
        assert fila.largo_sql == codigo_largo(fila.id)
        assert fila.codigo == codigo_corto(fila.id)  # sin colisiones entre estos 1000


def test_equivalencia_del_codigo_largo_con_la_expresion_real_de_la_migracion_0003(
    base_en_0002: Engine, config_alembic: Config
):
    """Escenario "Equivalencia SQL/Python", parte del codigo LARGO, con el SQL REAL de `0003`.

    La expresion larga de la migracion solo se aplica ante una colision del codigo corto. Para cada
    uno de 1000 UUID (v4 y v7) se inserta un "gemelo" con los mismos 12 ultimos digitos hexadecimales
    y otro prefijo: la migracion real conserva el corto en el de menor `id` y asigna el largo al otro.
    No se copia ninguna expresion en la prueba: se compara el resultado de la migracion con Python.
    """
    originales = [uuid.uuid4() for _ in range(500)] + [uuid.uuid7() for _ in range(500)]
    gemelos = [
        uuid.UUID(secrets.token_hex(10) + original.hex[-12:]) for original in originales
    ]
    ids = originales + gemelos
    assert len(set(ids)) == 2000
    assert all(a.hex[-12:] == b.hex[-12:] for a, b in zip(originales, gemelos, strict=True))
    with base_en_0002.begin() as conexion:
        conexion.execute(
            text("INSERT INTO consultorio (id, nombre) VALUES (:id, 'Consultorio Ficticio')"),
            [{"id": i} for i in ids],
        )

    command.upgrade(config_alembic, "0003")

    with base_en_0002.connect() as conexion:
        codigos = {fila.id: fila.codigo for fila in conexion.execute(text("SELECT id, codigo FROM consultorio"))}
    assert len(codigos) == 2000
    largos = 0
    for original, gemelo in zip(originales, gemelos, strict=True):
        menor, mayor = sorted((original, gemelo))
        assert codigos[menor] == codigo_corto(menor)
        assert codigos[mayor] == codigo_largo(mayor)
        assert len(codigos[mayor]) == len("c-") + 32
        largos += 1
    assert largos == 1000
    assert len(set(codigos.values())) == 2000

"""Codigo de consultorio en el seed (C-03, delta `seed-ficticio`). Sin base de datos."""

from pathlib import Path

from sqlalchemy.dialects import postgresql

import app.seed.datos
from app.models.codigo import codigo_corto
from app.seed.aplicar import aplicar_seed
from app.seed.datos import CONSULTORIOS

CODIGOS_DEL_SEED = {
    "Consultorio Demo A": "c-c7d08d776d19",
    "Consultorio Demo B": "c-c7d1647cab52",
}


def test_cada_consultorio_del_seed_declara_su_codigo_literal():
    assert {c.nombre: c.codigo for c in CONSULTORIOS} == CODIGOS_DEL_SEED


def test_los_literales_son_iguales_al_codigo_corto_derivado_del_id():
    for consultorio in CONSULTORIOS:
        assert consultorio.codigo == codigo_corto(consultorio.id)


def test_los_codigos_estan_escritos_como_literales_en_los_datos_del_seed():
    fuente = Path(app.seed.datos.__file__).read_text(encoding="utf-8")

    for codigo in CODIGOS_DEL_SEED.values():
        assert f'"{codigo}"' in fuente
    assert "codigo_corto" not in fuente  # no se calculan: el literal es el dato


class _Resultado:
    def all(self) -> list[object]:
        return []


class _SesionGrabadora:
    def __init__(self) -> None:
        self.sentencias: list[object] = []

    def execute(self, sentencia: object) -> _Resultado:
        self.sentencias.append(sentencia)
        return _Resultado()


def _compilar(sentencia: object):
    return sentencia.compile(dialect=postgresql.dialect())  # type: ignore[attr-defined]


def test_las_sentencias_de_consultorios_incluyen_el_codigo_y_solo_insertan():
    sesion = _SesionGrabadora()

    aplicar_seed(sesion)  # type: ignore[arg-type]

    compiladas = [_compilar(s) for s in sesion.sentencias]
    consultorios = [c for c in compiladas if c.statement.table.name == "consultorio"]
    assert [c.params["codigo"] for c in consultorios] == list(CODIGOS_DEL_SEED.values())
    assert len(compiladas) == 8
    for compilada in compiladas:
        texto = str(compilada).upper()
        assert texto.startswith("INSERT INTO")
        assert "ON CONFLICT DO NOTHING" in texto
        assert "UPDATE" not in texto and "DELETE" not in texto
        assert "CREDENCIAL" not in texto

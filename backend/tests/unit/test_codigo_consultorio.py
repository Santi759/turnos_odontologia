"""Pruebas de `app.models.codigo` (tarea 3.7; DD-13)."""

import re
import uuid

import pytest

from app.models.codigo import codigo_corto, codigo_largo

FORMATO = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")
ID_DE_REFERENCIA = uuid.UUID("01a1a95a-dd90-73e7-9496-c7d08d776d19")


def test_codigos_del_id_de_referencia():
    assert codigo_corto(ID_DE_REFERENCIA) == "c-c7d08d776d19"
    assert codigo_largo(ID_DE_REFERENCIA) == "c-01a1a95add9073e79496c7d08d776d19"


@pytest.mark.parametrize(
    ("texto", "corto", "largo"),
    [
        ("00000000-0000-0000-0000-000000000000", "c-000000000000", "c-" + "0" * 32),
        ("ffffffff-ffff-ffff-ffff-ffffffffffff", "c-ffffffffffff", "c-" + "f" * 32),
        ("0190a1b2-c3d4-7e5f-8a9b-0c1d2e3f4a5b", "c-0c1d2e3f4a5b", "c-0190a1b2c3d47e5f8a9b0c1d2e3f4a5b"),
        ("A1B2C3D4-E5F6-4789-ABCD-EF0123456789", "c-ef0123456789", "c-a1b2c3d4e5f64789abcdef0123456789"),
    ],
)
def test_otros_uuid_incluidos_los_extremos_y_las_mayusculas(texto, corto, largo):
    identificador = uuid.UUID(texto)

    assert codigo_corto(identificador) == corto
    assert codigo_largo(identificador) == largo


def test_formato_valido_longitudes_distintas_y_prefijo_comun_para_cualquier_uuid():
    for _ in range(300):
        identificador = uuid.uuid4() if _ % 2 else uuid.uuid7()
        corto, largo = codigo_corto(identificador), codigo_largo(identificador)

        assert FORMATO.match(corto) and FORMATO.match(largo)
        assert (len(corto), len(largo)) == (14, 34)
        assert largo.endswith(corto[2:])
        assert corto != largo

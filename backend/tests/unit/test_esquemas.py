import pytest
from pydantic import ValidationError

from app.schemas.base import EsquemaEntrada


class EsquemaDePrueba(EsquemaEntrada):
    nombre: str


def test_campo_no_declarado_es_rechazado():
    with pytest.raises(ValidationError) as excinfo:
        EsquemaDePrueba.model_validate(
            {"nombre": "Consultorio Ficticio", "consultorio_id": 1}
        )

    errores = excinfo.value.errors()
    assert [(e["type"], e["loc"]) for e in errores] == [
        ("extra_forbidden", ("consultorio_id",))
    ]


def test_solo_campos_declarados_se_validan():
    esquema = EsquemaDePrueba.model_validate({"nombre": "Consultorio Ficticio"})

    assert esquema.nombre == "Consultorio Ficticio"


def test_cualquier_campo_extra_se_rechaza_no_solo_consultorio_id():
    with pytest.raises(ValidationError) as excinfo:
        EsquemaDePrueba.model_validate({"nombre": "Otro Ficticio", "rol": "admin"})

    assert excinfo.value.errors()[0]["loc"] == ("rol",)

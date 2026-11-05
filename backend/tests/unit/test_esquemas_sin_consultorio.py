import importlib
import pkgutil

import app.schemas
from app.schemas.base import EsquemaEntrada


def _subclases(base: type) -> set[type]:
    encontradas: set[type] = set()
    for subclase in base.__subclasses__():
        encontradas.add(subclase)
        encontradas |= _subclases(subclase)
    return encontradas


def _esquemas_de_entrada_de_la_aplicacion() -> list[type[EsquemaEntrada]]:
    for modulo in pkgutil.iter_modules(app.schemas.__path__):
        importlib.import_module(f"app.schemas.{modulo.name}")
    return sorted(
        (
            clase
            for clase in _subclases(EsquemaEntrada)
            if clase.__module__.startswith("app.schemas")
        ),
        key=lambda clase: clase.__qualname__,
    )


def test_ningun_esquema_de_entrada_declara_consultorio_id():
    con_consultorio = [
        clase.__qualname__
        for clase in _esquemas_de_entrada_de_la_aplicacion()
        if "consultorio_id" in clase.model_fields
    ]

    assert con_consultorio == []


def test_todo_esquema_de_entrada_rechaza_campos_no_declarados():
    permisivos = [
        clase.__qualname__
        for clase in _esquemas_de_entrada_de_la_aplicacion()
        if clase.model_config.get("extra") != "forbid"
    ]

    assert permisivos == []


def test_la_base_comun_de_entrada_prohibe_campos_extra():
    # Control del recorrido anterior (hoy no hay esquemas de dominio): la herencia
    # de esta configuracion es lo que impide colar `consultorio_id` (S1, D5).
    assert EsquemaEntrada.model_config.get("extra") == "forbid"

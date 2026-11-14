"""`require_rol` (tarea 7.2; DD-16, DD-17, spec `autorizacion-roles`).

Sin base: la identidad se sustituye con `dependency_overrides`. Datos ficticios.
"""

import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.autorizacion import DETALLE_ACCESO_DENEGADO, require_rol
from app.auth.dependencias import IdentidadAutenticada, identidad_actual
from app.models.usuario import Rol
from app.repositories.contexto import ContextoConsultorio

DENEGADO = {"detail": "Acceso denegado."}


def _identidad(rol: Rol) -> IdentidadAutenticada:
    consultorio = uuid.uuid4()
    return IdentidadAutenticada(
        sesion_id=uuid.uuid4(),
        usuario_id=uuid.uuid4(),
        rol=rol,
        nombre="Persona Ficticia",
        email="persona.ficticia@example.test",
        consultorio_nombre="Consultorio Ficticio",
        contexto=ContextoConsultorio(consultorio),
    )


def _app(*roles: Rol) -> tuple[FastAPI, dict[str, Rol]]:
    """App con una ruta restringida a `roles`; el rol de la identidad lo fija la prueba."""
    actual: dict[str, Rol] = {"rol": Rol.ADMINISTRADOR}
    app = FastAPI()
    app.dependency_overrides[identidad_actual] = lambda: _identidad(actual["rol"])

    @app.get("/restringida", dependencies=[Depends(require_rol(*roles))])
    def restringida() -> dict:
        return {"ok": True}

    return app, actual


def test_sin_roles_falla_al_declararse():
    with pytest.raises(ValueError):
        require_rol()


@pytest.mark.parametrize("invalido", ["administrador", "auditor", None, 1])
def test_un_valor_que_no_es_rol_falla_al_declararse(invalido):
    with pytest.raises(TypeError):
        require_rol(invalido)


def test_un_valor_invalido_junto_a_roles_validos_tambien_falla():
    with pytest.raises(TypeError):
        require_rol(Rol.ADMINISTRADOR, "secretaria")


def test_el_rol_admitido_pasa():
    app, actual = _app(Rol.ADMINISTRADOR)
    actual["rol"] = Rol.ADMINISTRADOR

    respuesta = TestClient(app).get("/restringida")

    assert respuesta.status_code == 200 and respuesta.json() == {"ok": True}


@pytest.mark.parametrize("rol", [Rol.SECRETARIA, Rol.ODONTOLOGO])
def test_el_rol_no_admitido_recibe_403_sin_cache(rol):
    app, actual = _app(Rol.ADMINISTRADOR)
    actual["rol"] = rol

    respuesta = TestClient(app).get("/restringida")

    assert respuesta.status_code == 403
    assert respuesta.json() == DENEGADO == {"detail": DETALLE_ACCESO_DENEGADO}
    assert respuesta.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    ("rol", "esperado"),
    [(Rol.ADMINISTRADOR, 200), (Rol.SECRETARIA, 200), (Rol.ODONTOLOGO, 403)],
)
def test_varios_roles_admitidos(rol, esperado):
    app, actual = _app(Rol.ADMINISTRADOR, Rol.SECRETARIA)
    actual["rol"] = rol

    assert TestClient(app).get("/restringida").status_code == esperado

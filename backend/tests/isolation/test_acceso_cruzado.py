"""Acceso cruzado entre consultorios con la API real y `turnos_app` (7.4; luego 9.3; DD-18, RN-MT-05, RN-MT-06).

Se agregan rutas de prueba a la app real (que usa `turnos_login` y `turnos_app` reales sobre `db-test`):
el recurso ajeno responde 404 identico al inexistente, tanto con el repositorio acotado como con una
consulta SIN filtro de consultorio (la barrera es la RLS de la base, no el filtro de la aplicacion).
"""

import uuid

import pytest
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errores import no_encontrado
from app.auth.dependencias import contexto_consultorio, obtener_sesion_db
from app.models.usuario import Rol, Usuario
from app.repositories.contexto import ContextoConsultorio
from app.repositories.usuarios import UsuarioRepositorio

NO_ENCONTRADO = {"detail": "No encontrado."}


@pytest.fixture
def api_con_rutas(api_real):
    app = api_real.app

    @app.get("/prueba/usuarios/{usuario_id}")
    def con_repositorio(
        usuario_id: uuid.UUID,
        contexto: ContextoConsultorio = Depends(contexto_consultorio),
        db: Session = Depends(obtener_sesion_db),
    ) -> dict:
        usuario = UsuarioRepositorio(db, contexto).obtener_por_id(usuario_id)
        if usuario is None:
            raise no_encontrado()
        return {"id": str(usuario.id), "email": usuario.email}

    @app.get("/prueba/sin-filtro/usuarios/{usuario_id}")
    def sin_filtro_de_consultorio(
        usuario_id: uuid.UUID,
        _contexto: ContextoConsultorio = Depends(contexto_consultorio),
        db: Session = Depends(obtener_sesion_db),
    ) -> dict:
        usuario = db.scalars(select(Usuario).where(Usuario.id == usuario_id)).first()
        if usuario is None:
            raise no_encontrado()
        return {"id": str(usuario.id), "email": usuario.email}

    return api_real


def _iniciar(api, datos, letra="a", rol=Rol.SECRETARIA):
    consultorio = getattr(datos, letra)
    usuario = consultorio.usuarios[rol]
    cliente = api.cliente()
    assert api.login(cliente, consultorio.codigo, usuario.email, usuario.contrasena).status_code == 200
    return cliente


@pytest.mark.parametrize("ruta", ["/prueba/usuarios", "/prueba/sin-filtro/usuarios"])
def test_usuario_de_b_y_uuid_inexistente_dan_404_identicos_con_turnos_app(
    api_con_rutas, datos_ab, ruta
):
    cliente = _iniciar(api_con_rutas, datos_ab)
    de_b = datos_ab.b.usuarios[Rol.SECRETARIA]
    de_a = datos_ab.a.usuarios[Rol.SECRETARIA]

    ajeno = cliente.get(f"{ruta}/{de_b.id}")
    inexistente = cliente.get(f"{ruta}/{uuid.uuid4()}")
    propio = cliente.get(f"{ruta}/{de_a.id}")

    assert ajeno.status_code == inexistente.status_code == 404
    assert ajeno.json() == inexistente.json() == NO_ENCONTRADO
    assert dict(ajeno.headers) == dict(inexistente.headers)
    assert propio.status_code == 200 and propio.json() == {"id": str(de_a.id), "email": de_a.email}


@pytest.mark.parametrize("letra", ["a", "b"])
def test_cada_consultorio_ve_solo_los_suyos_y_el_otro_le_da_404(api_con_rutas, datos_ab, letra):
    otra = "b" if letra == "a" else "a"
    cliente = _iniciar(api_con_rutas, datos_ab, letra)

    propios = [
        cliente.get(f"/prueba/sin-filtro/usuarios/{u.id}").status_code
        for u in getattr(datos_ab, letra).usuarios.values()
    ]
    ajenos = [
        cliente.get(f"/prueba/sin-filtro/usuarios/{u.id}").status_code
        for u in getattr(datos_ab, otra).usuarios.values()
    ]

    assert propios == [200, 200, 200]
    assert ajenos == [404, 404, 404]


# --- 9.3 Una prueba de acceso cruzado por cada entrada del registro (DD-22) ------------------------------

from sqlalchemy import text  # noqa: E402

from tests.isolation.registro import REGISTRO  # noqa: E402


def _sesiones(motor_admin, consultorio_id) -> list[bool]:
    """`revocada_en IS NOT NULL` de cada sesion del consultorio, en orden estable."""
    with motor_admin.connect() as conexion:
        filas = conexion.execute(
            text("SELECT revocada_en IS NOT NULL FROM sesion WHERE consultorio_id = :c ORDER BY id"),
            {"c": consultorio_id},
        )
        return [f[0] for f in filas]


def _iniciar_a_y_b(api, datos):
    cliente_a = _iniciar(api, datos, "a")
    cliente_b = _iniciar(api, datos, "b")
    return cliente_a, cliente_b


def _caso_me(api, datos, motor_admin) -> None:
    cliente_a, cliente_b = _iniciar_a_y_b(api, datos)
    de_b = datos.b.usuarios[Rol.SECRETARIA]

    respuesta = cliente_b.get("/api/auth/me")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo == {
        "usuario": {"nombre": f"Persona Ficticia secretaria B", "email": de_b.email, "rol": "secretaria"},
        "consultorio": {"nombre": datos.b.nombre},
    }
    assert datos.a.nombre not in respuesta.text
    assert cliente_a.get("/api/auth/me").json()["consultorio"] == {"nombre": datos.a.nombre}


def _caso_logout(api, datos, motor_admin) -> None:
    cliente_a, cliente_b = _iniciar_a_y_b(api, datos)
    me_b = cliente_b.get("/api/auth/me")
    from tests.integration.app_auth import ORIGEN

    respuesta = cliente_b.post(
        "/api/auth/logout",
        headers={"Origin": ORIGEN, "X-CSRF-Token": me_b.headers["x-csrf-token"]},
    )

    assert respuesta.status_code == 204
    assert _sesiones(motor_admin, datos.b.id) == [True]
    assert _sesiones(motor_admin, datos.a.id) == [False]
    assert cliente_a.get("/api/auth/me").status_code == 200
    assert cliente_b.get("/api/auth/me").status_code == 401


EJECUTORES = {
    ("GET", "/api/auth/me"): _caso_me,
    ("POST", "/api/auth/logout"): _caso_logout,
}


def test_cada_entrada_del_registro_tiene_su_ejecutor_de_acceso_cruzado():
    assert set(EJECUTORES) == set(REGISTRO)


@pytest.mark.parametrize("entrada", sorted(REGISTRO), ids=lambda e: f"{e[0]} {e[1]}")
def test_acceso_cruzado_por_entrada_del_registro(api_real, datos_ab, motor_admin, entrada):
    EJECUTORES[entrada](api_real, datos_ab, motor_admin)

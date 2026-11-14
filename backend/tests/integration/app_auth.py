"""App FastAPI de PRUEBAS con rutas de prueba para las dependencias de autenticacion (grupo 7).

Las rutas de prueba existen solo aqui (nunca en `crear_app`). Las sesiones de base de la app comparten
la conexion y la transaccion revertible de la fixture `sesion` (con SAVEPOINT), de modo que ven los datos
de la prueba y todo se revierte al terminar.
"""

import secrets
import uuid
from dataclasses import dataclass

from fastapi import Body, Depends, FastAPI, HTTPException, Response
from sqlalchemy.orm import Session, sessionmaker

from app.api.errores import no_encontrado
from app.auth.autorizacion import require_rol
from app.auth.claves import token_csrf
from app.auth.dependencias import (
    IdentidadAutenticada,
    contexto_consultorio,
    exigir_csrf,
    exigir_direccion_cliente,
    exigir_json,
    identidad_actual,
    obtener_servicio,
    obtener_sesion_db,
    obtener_sesion_login,
    rechazar_consultorio_del_cliente,
    verificar_origen,
)
from app.auth.servicio import LoginRechazado, ServicioAuth
from app.core.config import Settings
from app.core.contexto_bd import crear_fabrica_de_sesiones
from app.models.usuario import Rol
from app.repositories.contexto import ContextoConsultorio
from app.repositories.usuarios import UsuarioRepositorio
from tests.integration.datos_auth import Entorno

ORIGEN = "http://localhost:5173"
ORIGEN_AJENO = "http://otro-origen.invalid"


def settings_de_prueba(**cambios: object) -> Settings:
    datos = {
        "DATABASE_URL": "postgresql+psycopg://app:app@db:5432/turnos",
        "DATABASE_LOGIN_URL": "postgresql+psycopg://turnos_login:login@db:5432/turnos",
        "CORS_ALLOWED_ORIGINS": ORIGEN,
        "APP_ENV": "test",
        "AUTH_SECRET_KEY": secrets.token_urlsafe(48),
        # Valores explicitos: el entorno del contenedor puede traer los del .env del autor.
        "AUTH_COOKIE_SECURE": True,
        "AUTH_SESSION_MINUTES": 30,
        "AUTH_SESSION_MAX_HOURS": 12,
    }
    datos.update(cambios)
    return Settings(**datos)  # type: ignore[arg-type]


@dataclass
class AppDePrueba:
    app: FastAPI
    entorno: Entorno
    settings: Settings
    cambios: list[str]

    def token_csrf(self, sesion_id) -> str:
        return token_csrf(self.entorno.config.clave_hmac, sesion_id)


def crear_app_de_prueba(entorno: Entorno, settings: Settings | None = None) -> AppDePrueba:
    conexion = entorno.db.get_bind()
    app = FastAPI(dependencies=[Depends(rechazar_consultorio_del_cliente)])
    app.state.settings = settings or settings_de_prueba()
    app.state.fabrica_sesiones = crear_fabrica_de_sesiones(
        conexion, join_transaction_mode="create_savepoint"
    )
    app.state.fabrica_sesiones_login = sessionmaker(
        bind=conexion, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    app.state.servicio_auth = entorno.servicio
    cambios: list[str] = []

    @app.get("/prueba/identidad")
    def identidad(actual: IdentidadAutenticada = Depends(identidad_actual)) -> dict:
        return {
            "usuario_id": str(actual.usuario_id),
            "rol": actual.rol,
            "consultorio_id": str(actual.contexto.consultorio_id),
            "es_contexto": isinstance(actual.contexto, ContextoConsultorio),
        }

    @app.get("/prueba/rol")
    def rol(actual: IdentidadAutenticada = Depends(identidad_actual)) -> dict:
        return {
            "rol": str(actual.rol),
            "es_rol": isinstance(actual.rol, Rol),
            "es_secretaria": actual.rol is Rol.SECRETARIA,
        }

    @app.get("/prueba/solo-admin", dependencies=[Depends(require_rol(Rol.ADMINISTRADOR))])
    def solo_admin() -> dict:
        return {"ok": True}

    @app.get(
        "/prueba/admin-o-secretaria",
        dependencies=[Depends(require_rol(Rol.ADMINISTRADOR, Rol.SECRETARIA))],
    )
    def admin_o_secretaria() -> dict:
        return {"ok": True}

    @app.post(
        "/prueba/cambia-admin",
        dependencies=[
            Depends(verificar_origen),
            Depends(exigir_csrf),
            Depends(require_rol(Rol.ADMINISTRADOR)),
        ],
    )
    def cambia_admin() -> dict:
        cambios.append("cambio-admin")
        return {"ok": True}

    def _usuario_por_id(usuario_id: uuid.UUID, contexto: ContextoConsultorio, db: Session) -> dict:
        usuario = UsuarioRepositorio(db, contexto).obtener_por_id(usuario_id)
        if usuario is None:
            raise no_encontrado()
        return {"id": str(usuario.id), "email": usuario.email}

    @app.get("/prueba/admin/usuarios/{usuario_id}", dependencies=[Depends(require_rol(Rol.ADMINISTRADOR))])
    def usuario_solo_admin(
        usuario_id: uuid.UUID,
        contexto: ContextoConsultorio = Depends(contexto_consultorio),
        db: Session = Depends(obtener_sesion_db),
    ) -> dict:
        return _usuario_por_id(usuario_id, contexto, db)

    @app.get("/prueba/usuarios/{usuario_id}")
    def usuario_por_id(
        usuario_id: uuid.UUID,
        contexto: ContextoConsultorio = Depends(contexto_consultorio),
        db: Session = Depends(obtener_sesion_db),
    ) -> dict:
        return _usuario_por_id(usuario_id, contexto, db)

    @app.get("/prueba/usuarios")
    def usuarios(
        contexto: ContextoConsultorio = Depends(contexto_consultorio),
        db: Session = Depends(obtener_sesion_db),
    ) -> list[str]:
        return [u.email for u in UsuarioRepositorio(db, contexto).listar()]

    @app.post("/prueba/cambia", dependencies=[Depends(verificar_origen), Depends(exigir_csrf)])
    def cambia() -> dict:
        cambios.append("cambio")
        return {"ok": True}

    @app.post("/prueba/cerrar", dependencies=[Depends(verificar_origen)])
    def cerrar(
        actual: IdentidadAutenticada = Depends(identidad_actual),
        servicio: ServicioAuth = Depends(obtener_servicio),
        db: Session = Depends(obtener_sesion_db),
        _csrf: None = Depends(exigir_csrf),
    ) -> Response:
        servicio.cerrar_sesion(db, actual.sesion_id)
        return Response(status_code=204)

    @app.post("/prueba/login", dependencies=[Depends(verificar_origen)])
    def login(
        ip: str = Depends(exigir_direccion_cliente),
        _json: None = Depends(exigir_json),
        datos: dict = Body(...),
        servicio: ServicioAuth = Depends(obtener_servicio),
        db_login: Session = Depends(obtener_sesion_login),
        db: Session = Depends(obtener_sesion_db),
    ) -> dict:
        try:
            servicio.iniciar_sesion(
                db_login,
                db,
                codigo=datos["codigo_consultorio"],
                email=datos["email"],
                contrasena=datos["contrasena"],
                ip_normalizada=ip,
            )
        except LoginRechazado:
            raise HTTPException(status_code=401, detail="No se pudo iniciar sesion.") from None
        return {"ip": ip}

    return AppDePrueba(app, entorno, app.state.settings, cambios)


def crear_app_real(
    entorno: Entorno, settings: Settings | None = None, servicio: ServicioAuth | None = None
) -> FastAPI:
    """La app REAL (`crear_app`) con la base de `db-test` y el servicio de la prueba.

    Se sustituyen solo el motor/fabrica de sesiones y el servicio (reloj, verificador y limitador
    inyectados); rutas, dependencias, CORS y manejadores son los de produccion (DD-20, DD-24).
    """
    from app.main import crear_app

    app = crear_app(settings or settings_de_prueba())
    conexion = entorno.db.get_bind()
    app.state.fabrica_sesiones = crear_fabrica_de_sesiones(
        conexion, join_transaction_mode="create_savepoint"
    )
    app.state.fabrica_sesiones_login = sessionmaker(
        bind=conexion, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    app.state.servicio_auth = servicio or entorno.servicio
    return app

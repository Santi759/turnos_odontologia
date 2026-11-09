from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, salud
from app.auth.concurrencia import LimitadorArgon2
from app.auth.contrasenas import VerificadorContrasenas
from app.auth.reloj import RelojSistema
from app.auth.servicio import ConfigAuth, ServicioAuth
from app.core.config import Settings, cargar_configuracion
from app.core.cors import CredencialesSoloConOrigenPermitido
from app.core.database import crear_engine, crear_fabrica_de_sesiones


def crear_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or cargar_configuracion()
    # Documentacion solo con APP_ENV=local, denegada por defecto (DD-18); sin /docs/oauth2-redirect.
    en_local = settings.app_env == "local"
    app = FastAPI(
        title="turnos_odontologia",
        docs_url="/docs" if en_local else None,
        redoc_url="/redoc" if en_local else None,
        openapi_url="/openapi.json" if en_local else None,
        swagger_ui_oauth2_redirect_url=None,
    )
    # Motor y fabrica de sesiones sin conectar (DD-20): la conexion se abre en el primer uso.
    engine = crear_engine(settings)
    app.state.settings = settings
    app.state.engine = engine
    app.state.fabrica_sesiones = crear_fabrica_de_sesiones(engine)
    app.state.servicio_auth = ServicioAuth(
        ConfigAuth.desde_settings(settings),
        RelojSistema(),
        VerificadorContrasenas(),
        LimitadorArgon2(),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
        expose_headers=["X-CSRF-Token", "Retry-After"],
        allow_credentials=True,
    )
    # Agregado despues del CORS: es la capa externa y ve su respuesta final.
    app.add_middleware(CredencialesSoloConOrigenPermitido)
    app.include_router(salud.router)
    app.include_router(auth.router)
    return app

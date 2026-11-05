from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import salud
from app.core.config import Settings, cargar_configuracion


def crear_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or cargar_configuracion()
    app = FastAPI(title="turnos_odontologia")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
    app.include_router(salud.router)
    return app

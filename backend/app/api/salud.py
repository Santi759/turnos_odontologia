from fastapi import APIRouter

from app.schemas.salud import RespuestaSalud

router = APIRouter(prefix="/api")


@router.get("/health", response_model=RespuestaSalud)
def salud() -> RespuestaSalud:
    return RespuestaSalud(status="ok")

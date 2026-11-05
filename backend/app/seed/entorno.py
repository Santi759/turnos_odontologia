from app.core.config import Settings


def validar_entorno_de_seed(settings: Settings) -> None:
    """Guardia (DM-08): el seed solo corre con APP_ENV=local.

    Es pura: no abre conexiones. El mensaje nombra APP_ENV y nada mas (sin URLs).
    """
    if settings.app_env != "local":
        raise RuntimeError("el seed solo se ejecuta con APP_ENV=local")

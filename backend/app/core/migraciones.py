from app.core.config import Settings
from app.core.database import validar_url_de_pruebas

DESTINO_DESARROLLO = "desarrollo"
DESTINO_PRUEBAS = "test"
_DESTINOS_ADMITIDOS = (DESTINO_DESARROLLO, DESTINO_PRUEBAS)


def resolver_url_de_migracion(
    settings: Settings, destino: str | None, url_explicita: str | None
) -> str:
    """Resuelve contra que base se ejecuta una migracion de Alembic.

    - Sin destino (o "desarrollo") y sin URL explicita: `DATABASE_URL`.
    - Destino "test" (`-x target=test`): `TEST_DATABASE_URL`, validada con la guardia.
    - URL explicita (`sqlalchemy.url` fijada por codigo, como hacen las pruebas de
      migraciones): se trata siempre como destino de pruebas y se valida con la
      guardia; junto a "desarrollo" es ambigua y se rechaza.

    Los mensajes de error nunca incluyen URLs ni credenciales.
    """
    if destino is not None and destino not in _DESTINOS_ADMITIDOS:
        raise ValueError(
            "destino de migracion no admitido (-x target=...): "
            f"los valores admitidos son {' o '.join(_DESTINOS_ADMITIDOS)}"
        )

    url_desarrollo = settings.database_url.get_secret_value()

    if url_explicita:
        if destino == DESTINO_DESARROLLO:
            raise ValueError(
                "destino ambiguo: una URL explicita de migracion solo se admite "
                "como destino de pruebas, no junto a target=desarrollo"
            )
        validar_url_de_pruebas(url_explicita, url_desarrollo)
        return url_explicita

    if destino == DESTINO_PRUEBAS:
        url_pruebas = (
            settings.test_database_url.get_secret_value()
            if settings.test_database_url is not None
            else None
        )
        validar_url_de_pruebas(url_pruebas, url_desarrollo)
        assert url_pruebas is not None
        return url_pruebas

    return url_desarrollo

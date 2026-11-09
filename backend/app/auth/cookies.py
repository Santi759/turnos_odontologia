"""Cookie de sesion `turnos_session` (DA-12, DD-04).

La sesion viaja solo en esta cookie: HttpOnly, SameSite=Lax, Path=/, sin Domain, Secure salvo
configuracion local explicita (`AUTH_COOKIE_SECURE=false`, solo con APP_ENV=local).
"""

from fastapi import Response

from app.core.config import Settings

NOMBRE_COOKIE = "turnos_session"
SEGUNDOS_POR_HORA = 3600


def _valor(contenido: str, max_age: int, settings: Settings) -> str:
    atributos = [f"{NOMBRE_COOKIE}={contenido}", f"Max-Age={max_age}", "Path=/", "HttpOnly", "SameSite=Lax"]
    if settings.auth_cookie_secure:
        atributos.append("Secure")
    return "; ".join(atributos)


def valor_cookie_sesion(token: str, settings: Settings) -> str:
    """Cabecera `Set-Cookie` de la sesion: `Max-Age` = vencimiento absoluto en segundos."""
    return _valor(token, settings.auth_session_max_hours * SEGUNDOS_POR_HORA, settings)


def valor_cookie_borrada(settings: Settings) -> str:
    """Borrado: mismos Path, SameSite, HttpOnly y Secure, con `Max-Age=0`."""
    return _valor("", 0, settings)


def emitir_cookie(response: Response, token: str, settings: Settings) -> None:
    response.headers.append("set-cookie", valor_cookie_sesion(token, settings))


def borrar_cookie(response: Response, settings: Settings) -> None:
    response.headers.append("set-cookie", valor_cookie_borrada(settings))

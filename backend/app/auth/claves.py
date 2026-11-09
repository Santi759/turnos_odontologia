"""Primitivas puras de claves, tokens y direcciones (DD-02, DD-07, DD-19).

Sin I/O: reciben la clave HMAC (`Settings.auth_hmac_key`, bytes decodificados de
`AUTH_SECRET_KEY`) como argumento. Una sola clave sirve para todos los valores
derivados gracias a las etiquetas de dominio.
"""

import base64
import hashlib
import hmac
import ipaddress
import re
import secrets
import uuid

ETIQUETA_SESION = b"turnos:sesion:v1\x00"
ETIQUETA_CSRF = b"turnos:csrf:v1\x00"
ETIQUETA_INTENTO_CUENTA = b"turnos:intento-cuenta:v1\x00"
ETIQUETA_INTENTO_IP = b"turnos:intento-ip:v1\x00"
SEPARADOR = b"\x00"
BYTES_DEL_TOKEN = 32
PREFIJO_IPV6 = 64
_FORMATO_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")


class DireccionClienteNoDeterminable(Exception):
    """La direccion de la conexion no es una IP analizable (DD-19, PC-05).

    No devuelve ningun balde sustituto y no incluye el valor recibido.
    """


def generar_token() -> str:
    """Token de sesion: 256 bits en base64url (43 caracteres)."""
    return secrets.token_urlsafe(BYTES_DEL_TOKEN)


def token_valido(token: object) -> bool:
    """Valida el formato antes de consultar la base."""
    return isinstance(token, str) and _FORMATO_TOKEN.fullmatch(token) is not None


def _hmac(clave: bytes, etiqueta: bytes, *partes: bytes) -> bytes:
    return hmac.new(clave, etiqueta + SEPARADOR.join(partes), hashlib.sha256).digest()


def hmac_de_token(clave: bytes, token: str) -> bytes:
    return _hmac(clave, ETIQUETA_SESION, token.encode("utf-8"))


def token_csrf(clave: bytes, sesion_id: uuid.UUID) -> str:
    digest = _hmac(clave, ETIQUETA_CSRF, sesion_id.bytes)
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def clave_de_cuenta(clave: bytes, codigo: str, email: str) -> bytes:
    """HMAC del par (codigo, email) normalizados (sin espacios en los extremos y en minusculas)."""
    return _hmac(
        clave,
        ETIQUETA_INTENTO_CUENTA,
        codigo.strip().lower().encode("utf-8"),
        email.strip().lower().encode("utf-8"),
    )


def clave_de_ip(clave: bytes, ip_normalizada: str) -> bytes:
    return _hmac(clave, ETIQUETA_INTENTO_IP, ip_normalizada.encode("utf-8"))


def normalizar_ip(host: str | None) -> str:
    """IPv4 -> `v4:<ip>`; IPv4 mapeada -> la misma IPv4; IPv6 -> `v6:<prefijo /64>`."""
    if not isinstance(host, str):
        raise DireccionClienteNoDeterminable()
    try:
        direccion = ipaddress.ip_address(host.strip())
    except ValueError:
        raise DireccionClienteNoDeterminable() from None
    if isinstance(direccion, ipaddress.IPv6Address):
        if direccion.ipv4_mapped is not None:
            return f"v4:{direccion.ipv4_mapped}"
        mascara = ((1 << PREFIJO_IPV6) - 1) << (128 - PREFIJO_IPV6)
        red = ipaddress.IPv6Network((int(direccion) & mascara, PREFIJO_IPV6))
        return f"v6:{red}"
    return f"v4:{direccion}"

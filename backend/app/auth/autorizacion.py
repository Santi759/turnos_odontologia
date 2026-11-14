"""Autorizacion por rol: unico lugar de la aplicacion con decisiones de rol (DD-16, DD-17, DA-04).

`require_rol(*roles)` devuelve una dependencia de FastAPI que exige una identidad valida (401 si falta,
por `identidad_actual`) y responde 403 `{"detail": "Acceso denegado."}` (siempre `no-store`) si el rol
no esta permitido. Decide solo con la identidad: nunca consulta el recurso pedido, de modo que el 403
es identico para un recurso propio, ajeno o inexistente. Orden en operaciones que cambian estado:
`verificar_origen` -> `identidad_actual` -> `exigir_csrf` -> `require_rol` (declarar las dependencias en
ese orden). C-04 no aprueba la matriz de permisos: solo ofrece el mecanismo.
"""

from collections.abc import Callable

from fastapi import Depends

from app.auth.dependencias import IdentidadAutenticada, identidad_actual, rechazo
from app.models.usuario import Rol

DETALLE_ACCESO_DENEGADO = "Acceso denegado."


def require_rol(*roles: Rol) -> Callable[..., IdentidadAutenticada]:
    """Dependencia que admite solo los roles indicados.

    Falla al declararse (antes de atender peticiones): `ValueError` sin roles y `TypeError` si algun
    valor no es un `Rol` (un texto como `"administrador"` no se acepta).
    """
    if not roles:
        raise ValueError("require_rol requiere al menos un rol")
    if not all(isinstance(rol, Rol) for rol in roles):
        raise TypeError("require_rol solo acepta valores del tipo Rol")
    permitidos = frozenset(roles)

    def exigir(identidad: IdentidadAutenticada = Depends(identidad_actual)) -> IdentidadAutenticada:
        if identidad.rol not in permitidos:
            raise rechazo(403, DETALLE_ACCESO_DENEGADO)
        return identidad

    return exigir

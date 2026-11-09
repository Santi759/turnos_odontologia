"""Ajuste de CORS: `Access-Control-Allow-Credentials` solo acompana a un origen autorizado.

`CORSMiddleware` de Starlette agrega `Allow-Credentials: true` a toda respuesta con `Origin`,
aunque el origen no este permitido. Los navegadores la ignoran sin `Allow-Origin`, pero la
especificacion del Change exige que un origen ajeno no reciba ninguna cabecera CORS.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_ORIGEN = b"access-control-allow-origin"
_CREDENCIALES = b"access-control-allow-credentials"


class CredencialesSoloConOrigenPermitido:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def enviar(mensaje: Message) -> None:
            if mensaje["type"] == "http.response.start":
                cabeceras = list(mensaje.get("headers", []))
                if not any(nombre.lower() == _ORIGEN for nombre, _ in cabeceras):
                    mensaje = {
                        **mensaje,
                        "headers": [(n, v) for n, v in cabeceras if n.lower() != _CREDENCIALES],
                    }
            await send(mensaje)

        await self.app(scope, receive, enviar)

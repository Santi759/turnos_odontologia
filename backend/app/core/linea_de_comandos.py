"""Analizador de argumentos de los comandos locales que nunca repite lo recibido (X1).

`argparse` incluye en sus errores los argumentos que no reconoce; si alguien escribe una
contrasena como argumento, el error la imprimiria. Este analizador responde siempre con un
texto fijo y lanza `ArgumentosInvalidos` en lugar de terminar el proceso.
"""

import argparse
from typing import NoReturn

MENSAJE_ARGUMENTOS_INVALIDOS = "argumentos no validos (argumento no reconocido o valor fuera de rango)"


class ArgumentosInvalidos(Exception):
    """Los argumentos no son validos; el mensaje es fijo y no contiene lo recibido."""


class AnalizadorSinEco(argparse.ArgumentParser):
    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    def error(self, message: str) -> NoReturn:
        raise ArgumentosInvalidos(MENSAJE_ARGUMENTOS_INVALIDOS)

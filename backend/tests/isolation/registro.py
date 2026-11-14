"""Registro de aislamiento: toda ruta protegida declara su prueba de acceso cruzado (DD-22, RN-MT-06).

Cada ruta de la app real que depende de `identidad_actual` DEBE figurar aqui, con un recurso por
identificador (`RecursoPorId`: un usuario de B pide un recurso de A y recibe lo mismo que para un UUID
inexistente) o como operacion sobre la sesion propia (`SesionPropia`: devuelve o afecta solo datos de la
sesion del llamador). Una ruta nueva sin entrada, o una entrada sin ruta, hace fallar la suite.
"""

from dataclasses import dataclass

from fastapi import FastAPI

from app.auth.dependencias import identidad_actual
from tests.rutas import rutas_que_dependen_de


@dataclass(frozen=True)
class RecursoPorId:
    parametro: str  # nombre del parametro de ruta que lleva el identificador
    descripcion: str


@dataclass(frozen=True)
class SesionPropia:
    justificacion: str


Caso = RecursoPorId | SesionPropia

REGISTRO: dict[tuple[str, str], Caso] = {
    ("GET", "/api/auth/me"): SesionPropia(
        "devuelve la identidad y el consultorio de la sesion que presenta la cookie; no recibe ids"
    ),
    ("POST", "/api/auth/logout"): SesionPropia(
        "revoca solo la sesion del llamador (por su id de sesion); no recibe ids ajenos"
    ),
}


def verificar_registro(app: FastAPI, registro: dict[tuple[str, str], Caso] = REGISTRO) -> None:
    """Igualdad exacta entre las rutas protegidas de `app` y las claves de `registro`."""
    protegidas = rutas_que_dependen_de(app, identidad_actual)
    sin_entrada = sorted(protegidas - set(registro))
    sin_ruta = sorted(set(registro) - protegidas)
    problemas = [f"ruta protegida sin entrada en el registro: {m} {r}" for m, r in sin_entrada]
    problemas += [f"entrada del registro sin ruta protegida: {m} {r}" for m, r in sin_ruta]
    if problemas:
        raise AssertionError("; ".join(problemas))

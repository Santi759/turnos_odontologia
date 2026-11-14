"""Recorrido de las rutas de una app FastAPI, compartido por las pruebas (9.1, 5.5, DD-22, DD-28).

Una sola implementacion de "rutas efectivas" y de "dependencias de una ruta": la usan la lista
blanca de rutas publicas, el registro de aislamiento y la restriccion de la sesion de login.
"""

from collections.abc import Callable, Iterable

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant


def aplanar(rutas: Iterable) -> list:
    """Rutas efectivas: FastAPI reciente deja los routers incluidos como nodos perezosos."""
    planas = []
    for ruta in rutas:
        if hasattr(ruta, "effective_candidates"):  # _IncludedRouter (API interna de FastAPI)
            planas.extend(aplanar(ruta.effective_candidates()))
        else:
            planas.append(ruta)
    return planas


def depende_de(dependiente: Dependant, funcion: Callable) -> bool:
    """Si `funcion` aparece en cualquier nivel del arbol de dependencias."""
    return any(
        sub.call is funcion or depende_de(sub, funcion) for sub in dependiente.dependencies
    )


def rutas_que_dependen_de(app: FastAPI, funcion: Callable) -> set[tuple[str, str]]:
    """(metodo, ruta) de cada ruta cuyo arbol de dependencias contiene `funcion` (sin HEAD implicito)."""
    return {
        (metodo, ruta.path)
        for ruta in aplanar(app.routes)
        if getattr(ruta, "dependant", None) is not None and depende_de(ruta.dependant, funcion)
        for metodo in ruta.methods or ()
        if metodo != "HEAD"
    }

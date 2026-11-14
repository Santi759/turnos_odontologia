"""Respuestas de error compartidas por las rutas protegidas (DD-18, RN-MT-05)."""

from fastapi import HTTPException

from app.auth.dependencias import rechazo

DETALLE_NO_ENCONTRADO = "No encontrado."


def no_encontrado() -> HTTPException:
    """404 unico para un recurso ajeno o inexistente: mismo estado, cuerpo y cabeceras (RN-MT-05)."""
    return rechazo(404, DETALLE_NO_ENCONTRADO)

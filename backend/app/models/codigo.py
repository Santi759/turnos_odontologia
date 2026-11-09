"""Codigo de consultorio derivado del `id` (DD-13).

Reglas unicas en funciones puras; el backfill de la migracion 0003 y el alta de
consultorios las usan (equivalentes en SQL y Python).
"""

import uuid

PREFIJO = "c-"
DIGITOS_DEL_CODIGO_CORTO = 12


def codigo_corto(consultorio_id: uuid.UUID) -> str:
    return PREFIJO + consultorio_id.hex[-DIGITOS_DEL_CODIGO_CORTO:]


def codigo_largo(consultorio_id: uuid.UUID) -> str:
    return PREFIJO + consultorio_id.hex

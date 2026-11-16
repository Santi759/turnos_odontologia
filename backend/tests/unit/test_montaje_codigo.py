"""El codigo del backend se monta de solo lectura en `/app` (DD-34, RT3-05).

Un compromiso del proceso de la API no debe poder modificar el codigo que despues ejecuta el servicio
`admin` con la credencial de administracion. La prueba intenta crear un archivo ficticio UNICO en
`/app` y espera `EROFS`; si la creacion tuviera exito, borra solo ese archivo y falla.
"""

import errno
import os
import uuid
from pathlib import Path

import pytest

RAIZ_DEL_CODIGO = Path("/app")


def test_el_codigo_montado_en_app_es_de_solo_lectura():
    assert Path(__file__).resolve().is_relative_to(RAIZ_DEL_CODIGO), "la prueba exige el montaje real en /app"
    ficticio = RAIZ_DEL_CODIGO / f".prueba-solo-lectura-{uuid.uuid4().hex}"

    try:
        descriptor = os.open(ficticio, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as error:
        assert error.errno == errno.EROFS
        assert not ficticio.exists()
        return

    # Solo se elimina el archivo que la propia prueba acaba de crear (O_EXCL garantiza que es nuevo).
    os.close(descriptor)
    ficticio.unlink()
    pytest.fail("se pudo crear un archivo en /app: el codigo no esta montado de solo lectura")

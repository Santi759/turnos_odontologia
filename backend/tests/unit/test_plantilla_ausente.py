"""Escenario "Plantilla ausente" (ejecucion-de-pruebas): sin `/repo/.env.example` las pruebas fallan.

Se ejecutan de verdad las pruebas del modulo de la plantilla en un SUBPROCESO de pytest cuya
ruta de plantilla apunta a un archivo inexistente (equivale a que el montaje no exista en el
contenedor). No se toca ni se lee `.env.example`.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
# Pruebas del modulo que dependen del archivo (las demas usan texto sintetico y no lo leen).
PRUEBAS_QUE_DEPENDEN_DE_LA_PLANTILLA = (
    "test_la_plantilla_existe_y_la_lectura_falla_si_falta",
    "test_la_plantilla_declara_las_variables_de_autenticacion_con_valores_ficticios",
    "test_la_plantilla_documenta_la_generacion_de_la_clave_y_el_uso_local_de_cookie_insegura",
    "test_la_constante_de_plantilla_coincide_con_el_valor_de_env_example",
    "test_los_valores_de_la_plantilla_se_rechazan_por_auth_secret_key",
    "test_la_plantilla_es_valida_reemplazando_solo_auth_secret_key",
    "test_el_valor_de_plantilla_de_la_clave_no_se_acepta_con_otros_valores_validos",
    "test_el_montaje_de_la_plantilla_en_el_contenedor_rechaza_la_escritura",
)


def _ejecutar_pruebas_de_plantilla(ruta: str) -> subprocess.CompletedProcess[str]:
    entorno = {**os.environ, "RUTA_PLANTILLA_PARA_PRUEBAS": ruta}
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-q",
            "--no-header",
            "tests/unit/test_plantilla_env.py",
        ],
        cwd=RAIZ_BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_con_la_plantilla_ausente_las_pruebas_de_la_plantilla_fallan_y_no_se_omiten(tmp_path):
    resultado = _ejecutar_pruebas_de_plantilla(str(tmp_path / "plantilla-inexistente.env"))
    salida = resultado.stdout

    assert resultado.returncode != 0
    assert "FileNotFoundError" in salida
    for nombre in PRUEBAS_QUE_DEPENDEN_DE_LA_PLANTILLA:
        assert re.search(rf"^(FAILED|ERROR) tests/unit/test_plantilla_env.py::{nombre}", salida, re.M), nombre
    assert "skipped" not in salida


def test_con_la_plantilla_presente_el_mismo_subproceso_pasa(tmp_path):
    """Control: el mecanismo del subproceso solo falla por la ausencia (la ruta real existe)."""
    resultado = _ejecutar_pruebas_de_plantilla("/repo/.env.example")

    assert resultado.returncode == 0, resultado.stdout[-800:]
    assert "failed" not in resultado.stdout

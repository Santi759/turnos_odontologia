"""Aislamiento de las pruebas unitarias frente al entorno heredado (D2, 2026-11-06).

El contenedor `api` carga el `.env` del autor con `env_file`; si ese archivo define
`AUTH_COOKIE_SECURE=false`, el proceso de pytest lo hereda. Las pruebas configuradas
con `APP_ENV=test` no deben depender de ese valor.
"""

import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.config import cargar_configuracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
ARCHIVOS_AFECTADOS = ("tests/unit/test_migraciones.py", "tests/unit/test_seed.py")
VARIABLES_AUTH = (
    "AUTH_SECRET_KEY",
    "AUTH_SESSION_MINUTES",
    "AUTH_SESSION_MAX_HOURS",
    "AUTH_COOKIE_SECURE",
)


def _ejecutar_pytest_con_entorno_heredado(heredado: dict[str, str]) -> subprocess.CompletedProcess[str]:
    entorno = {k: v for k, v in os.environ.items() if k not in VARIABLES_AUTH}
    entorno.update(heredado)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *ARCHIVOS_AFECTADOS],
        cwd=RAIZ_BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


@pytest.mark.parametrize(
    "heredado",
    [
        {"AUTH_COOKIE_SECURE": "false"},
        {"AUTH_COOKIE_SECURE": "false", "AUTH_SESSION_MINUTES": "999", "AUTH_SESSION_MAX_HOURS": "999"},
    ],
    ids=["cookie_insegura_heredada", "valores_invalidos_heredados"],
)
def test_pruebas_con_app_env_test_no_dependen_de_auth_heredado(heredado):
    resultado = _ejecutar_pytest_con_entorno_heredado(heredado)

    assert resultado.returncode == 0, resultado.stdout[-1500:]


def test_la_configuracion_real_rechaza_cookie_insegura_fuera_de_local(monkeypatch):
    for nombre in VARIABLES_AUTH:
        monkeypatch.delenv(nombre, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app:app@db:5432/turnos")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("AUTH_SECRET_KEY", secrets.token_urlsafe(48))

    with pytest.raises(Exception) as excinfo:
        cargar_configuracion()

    assert "AUTH_COOKIE_SECURE" in str(excinfo.value)

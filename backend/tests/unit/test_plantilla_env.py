"""Pruebas de la plantilla .env.example (tarea 2.4).

La plantilla se monta de solo lectura en el contenedor `api` en `/repo/.env.example`
(docker-compose.yml). Si el archivo no existe, las pruebas FALLAN: nunca se omiten.
"""

import errno
import os
import re
import secrets
import unicodedata
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core import config as modulo_config
from app.core.config import cargar_configuracion

# La variable solo la usa la prueba de "plantilla ausente" (test_plantilla_ausente.py) para ejecutar
# este modulo en un subproceso con una ruta inexistente; sin ella la ruta es la del montaje real.
RUTA_PLANTILLA = Path(os.environ.get("RUTA_PLANTILLA_PARA_PRUEBAS", "/repo/.env.example"))
VARIABLES_DE_CONFIGURACION = (
    "DATABASE_URL",
    "TEST_DATABASE_URL",
    "CORS_ALLOWED_ORIGINS",
    "APP_ENV",
    "AUTH_SECRET_KEY",
    "AUTH_SESSION_MINUTES",
    "AUTH_SESSION_MAX_HOURS",
    "AUTH_COOKIE_SECURE",
)
_LINEA_VARIABLE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)=(.*)$")
_COOKIE_INSEGURA = re.compile(r"AUTH_COOKIE_SECURE\s*=\s*false", re.IGNORECASE)
_PALABRA_HTTP = re.compile(r"\bhttp\b")


def leer_plantilla(ruta: Path = RUTA_PLANTILLA) -> str:
    """Lee la plantilla; si falta lanza FileNotFoundError (la prueba falla, no se omite)."""
    return ruta.read_text(encoding="utf-8")


def valores_de_plantilla(texto: str) -> dict[str, str]:
    valores: dict[str, str] = {}
    for linea in texto.splitlines():
        coincidencia = _LINEA_VARIABLE.match(linea)
        if coincidencia:
            valores[coincidencia.group(1)] = coincidencia.group(2).strip()
    return valores


def _sin_acentos_en_minusculas(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def grupos_de_comentarios(texto: str) -> list[list[str]]:
    """Grupos de lineas de comentario contiguas (sin el `#` inicial)."""
    grupos: list[list[str]] = []
    actual: list[str] = []
    for linea in texto.splitlines():
        if linea.lstrip().startswith("#"):
            actual.append(linea.lstrip()[1:].strip())
        elif actual:
            grupos.append(actual)
            actual = []
    if actual:
        grupos.append(actual)
    return grupos


def cookie_insegura_bien_documentada(texto: str) -> bool:
    """`AUTH_COOKIE_SECURE=false` solo comentado y con su uso local por HTTP documentado.

    La explicacion puede repartirse en lineas de comentario contiguas; no se exige
    una frase literal. Un `false` activo (sin comentar) nunca es valido.
    """
    activas = (linea for linea in texto.splitlines() if not linea.lstrip().startswith("#"))
    if any(_COOKIE_INSEGURA.match(linea.strip()) for linea in activas):
        return False
    for grupo in grupos_de_comentarios(texto):
        if not any(_COOKIE_INSEGURA.search(linea) for linea in grupo):
            continue
        normalizado = _sin_acentos_en_minusculas(" ".join(grupo))
        if "local" in normalizado and _PALABRA_HTTP.search(normalizado):
            return True
    return False


@pytest.fixture
def entorno_de_plantilla(monkeypatch):
    for nombre in VARIABLES_DE_CONFIGURACION:
        monkeypatch.delenv(nombre, raising=False)
    valores = valores_de_plantilla(leer_plantilla())
    for nombre in VARIABLES_DE_CONFIGURACION:
        monkeypatch.setenv(nombre, valores[nombre])
    return monkeypatch


def test_la_plantilla_existe_y_la_lectura_falla_si_falta(tmp_path):
    assert leer_plantilla().strip()
    with pytest.raises(FileNotFoundError):
        leer_plantilla(tmp_path / "no-existe.env")


def test_la_plantilla_declara_las_variables_de_autenticacion_con_valores_ficticios():
    valores = valores_de_plantilla(leer_plantilla())

    assert valores["AUTH_SESSION_MINUTES"] == "30"
    assert valores["AUTH_SESSION_MAX_HOURS"] == "12"
    assert valores["AUTH_COOKIE_SECURE"] == "true"
    assert not [nombre for nombre in valores if nombre.startswith("EMAIL_")]


def test_la_plantilla_documenta_la_generacion_de_la_clave_y_el_uso_local_de_cookie_insegura():
    texto = leer_plantilla()
    comentarios = [linea for linea in texto.splitlines() if linea.lstrip().startswith("#")]

    assert any("secrets.token_urlsafe(48)" in linea for linea in comentarios)
    assert cookie_insegura_bien_documentada(texto)
    # El valor activo es el seguro; la variante insegura nunca es un valor activo.
    assert valores_de_plantilla(texto)["AUTH_COOKIE_SECURE"] == "true"


_BASE_SINTETICA = "AUTH_SESSION_MINUTES=30\n"


@pytest.mark.parametrize(
    "plantilla",
    [
        "# AUTH_COOKIE_SECURE=false solo se permite en desarrollo local por HTTP.\n"
        "AUTH_COOKIE_SECURE=true\n",
        "# Uso inseguro (solo con APP_ENV=local):\n# AUTH_COOKIE_SECURE=false\n"
        "# unicamente en desarrollo local, con HTTP sin TLS.\nAUTH_COOKIE_SECURE=true\n",
        "# AUTH_COOKIE_SECURE=false\n#\n# Solo en desarrollo LOCAL; sirve la API por Http.\n"
        "AUTH_COOKIE_SECURE=true\n",
        "#AUTH_COOKIE_SECURE = false -> solo en entorno locál (HTTP)\nAUTH_COOKIE_SECURE=true\n",
    ],
    ids=["una_linea", "repartida_en_contiguas", "contiguas_con_comentario_vacio", "espacios_y_acentos"],
)
def test_documentacion_de_cookie_insegura_se_acepta(plantilla):
    assert cookie_insegura_bien_documentada(_BASE_SINTETICA + plantilla)


@pytest.mark.parametrize(
    "plantilla",
    [
        # La explicacion queda separada por una linea activa: no es contigua.
        "# AUTH_COOKIE_SECURE=false\nAUTH_SESSION_MAX_HOURS=12\n# solo local por HTTP\n"
        "AUTH_COOKIE_SECURE=true\n",
        # Comentario contiguo sin relacion con la variante insegura.
        "# Generar con: secrets.token_urlsafe(48)\n# usar local y HTTP en otro contexto\n"
        "AUTH_COOKIE_SECURE=true\n",
        # Valor activo inseguro, aunque el comentario este completo.
        "# AUTH_COOKIE_SECURE=false solo local por HTTP\nAUTH_COOKIE_SECURE=false\n",
        # Falta "local".
        "# AUTH_COOKIE_SECURE=false solo por HTTP\nAUTH_COOKIE_SECURE=true\n",
        # Falta HTTP (https no cuenta).
        "# AUTH_COOKIE_SECURE=false solo en desarrollo local con https\nAUTH_COOKIE_SECURE=true\n",
        # No hay variante insegura comentada.
        "# Cookie solo para uso local por HTTP\nAUTH_COOKIE_SECURE=true\n",
    ],
    ids=[
        "no_contigua",
        "comentario_ajeno",
        "false_activo",
        "sin_local",
        "sin_http",
        "sin_variante_insegura",
    ],
)
def test_documentacion_de_cookie_insegura_se_rechaza(plantilla):
    assert not cookie_insegura_bien_documentada(_BASE_SINTETICA + plantilla)


def test_la_constante_de_plantilla_coincide_con_el_valor_de_env_example():
    valores = valores_de_plantilla(leer_plantilla())

    assert valores["AUTH_SECRET_KEY"] == modulo_config.VALOR_PLANTILLA_AUTH_SECRET_KEY


def test_los_valores_de_la_plantilla_se_rechazan_por_auth_secret_key(entorno_de_plantilla):
    with pytest.raises(ValidationError) as excinfo:
        cargar_configuracion()

    mensaje = str(excinfo.value)
    assert "AUTH_SECRET_KEY" in mensaje
    assert modulo_config.VALOR_PLANTILLA_AUTH_SECRET_KEY not in mensaje
    # Es el unico motivo del rechazo: el resto de la plantilla es valido.
    assert "1 validation error" in mensaje


def test_la_plantilla_es_valida_reemplazando_solo_auth_secret_key(entorno_de_plantilla):
    entorno_de_plantilla.setenv("AUTH_SECRET_KEY", secrets.token_urlsafe(48))

    configuracion = cargar_configuracion()

    assert configuracion.auth_session_minutes == 30
    assert configuracion.auth_session_max_hours == 12
    assert configuracion.auth_cookie_secure is True


def test_el_valor_de_plantilla_de_la_clave_no_se_acepta_con_otros_valores_validos(
    entorno_de_plantilla,
):
    entorno_de_plantilla.setenv("AUTH_SESSION_MINUTES", "60")

    with pytest.raises(ValidationError) as excinfo:
        cargar_configuracion()

    assert "AUTH_SECRET_KEY" in str(excinfo.value)


def test_el_montaje_de_la_plantilla_en_el_contenedor_rechaza_la_escritura():
    """Escenario "Escritura rechazada": abrir para anexar sin escribir nada falla por solo lectura.

    Se abre con modo "a" (nunca "w"): no trunca ni escribe un byte ni se lee el contenido; con un
    montaje de lectura y escritura la apertura tendria exito y la prueba fallaria.
    """
    assert RUTA_PLANTILLA == Path("/repo/.env.example"), "la prueba exige la ruta real del montaje"

    with pytest.raises(OSError) as excinfo:
        with open(RUTA_PLANTILLA, "a", encoding="utf-8"):
            pass

    assert excinfo.value.errno == errno.EROFS

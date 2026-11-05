import pytest
from sqlalchemy.exc import OperationalError

from app.core.database import crear_engine, validar_url_de_pruebas, verificar_conexion

URL_DESARROLLO = "postgresql+psycopg://app:app@db:5432/turnos"
URL_PRUEBAS = "postgresql+psycopg://app:app@db-test:5432/turnos_test"


def test_verificar_conexion_falla_con_error_de_conexion_si_la_base_es_inaccesible(
    fabrica_settings,
):
    settings = fabrica_settings(
        database_url="postgresql+psycopg://app:app@host-inexistente.invalid:5432/turnos"
    )
    motor = crear_engine(settings)

    with pytest.raises(OperationalError):
        verificar_conexion(motor)


def test_crear_engine_no_conecta_al_crearse(fabrica_settings):
    settings = fabrica_settings(
        database_url="postgresql+psycopg://app:app@host-inexistente.invalid:5432/turnos"
    )

    motor = crear_engine(settings)

    assert motor.url.host == "host-inexistente.invalid"


def test_guardia_acepta_una_base_de_pruebas_separada():
    validar_url_de_pruebas(URL_PRUEBAS, URL_DESARROLLO)


def test_guardia_rechaza_url_de_pruebas_ausente():
    with pytest.raises(ValueError, match="TEST_DATABASE_URL"):
        validar_url_de_pruebas(None, URL_DESARROLLO)


def test_guardia_rechaza_url_de_pruebas_vacia():
    with pytest.raises(ValueError, match="TEST_DATABASE_URL"):
        validar_url_de_pruebas("", URL_DESARROLLO)


@pytest.mark.parametrize(
    "url_pruebas",
    [
        URL_DESARROLLO,
        "postgresql+psycopg://otro:otra-clave-ficticia@db:5432/turnos",
        "postgresql+psycopg://app:app@db/turnos",
    ],
)
def test_guardia_rechaza_la_misma_base_que_desarrollo(url_pruebas):
    with pytest.raises(ValueError, match="desarrollo") as excinfo:
        validar_url_de_pruebas(url_pruebas, URL_DESARROLLO)

    assert "otra-clave-ficticia" not in str(excinfo.value)
    assert "app:app" not in str(excinfo.value)


@pytest.mark.parametrize(
    "url_pruebas",
    [
        "postgresql+psycopg://app:app@db-test:5432/turnos",
        "postgresql+psycopg://app:app@db-test:5432/turnos_test_copia",
        "postgresql+psycopg://app:app@db-test:5432/test",
    ],
)
def test_guardia_rechaza_nombre_de_base_que_no_termina_en_test(url_pruebas):
    with pytest.raises(ValueError, match="_test"):
        validar_url_de_pruebas(url_pruebas, URL_DESARROLLO)


def test_guardia_acepta_mismo_nombre_de_base_en_otro_host():
    # mismo nombre de base pero otro host/puerto: solo cuenta el sufijo _test
    validar_url_de_pruebas(
        "postgresql+psycopg://app:app@db-test:5432/turnos_test",
        "postgresql+psycopg://app:app@db-test:5433/turnos_test",
    )

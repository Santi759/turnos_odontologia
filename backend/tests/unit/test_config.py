import base64
import secrets

import pytest
from pydantic import ValidationError

from app.core import config as modulo_config
from app.core.config import cargar_configuracion

URL_VALIDA = "postgresql+psycopg://app:app@db:5432/turnos"


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    for nombre in (
        "DATABASE_URL",
        "TEST_DATABASE_URL",
        "DATABASE_LOGIN_URL",
        "DATABASE_MIGRATION_URL",
        "CORS_ALLOWED_ORIGINS",
        "APP_ENV",
        "AUTH_SECRET_KEY",
        "AUTH_SESSION_MINUTES",
        "AUTH_SESSION_MAX_HOURS",
        "AUTH_COOKIE_SECURE",
    ):
        monkeypatch.delenv(nombre, raising=False)


def test_carga_de_valores_validos(monkeypatch):
    clave = secrets.token_urlsafe(48)
    monkeypatch.setenv("DATABASE_URL", URL_VALIDA)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("AUTH_SECRET_KEY", clave)

    configuracion = cargar_configuracion()

    assert configuracion.database_url.get_secret_value() == URL_VALIDA
    assert configuracion.app_env == "local"
    assert configuracion.cors_allowed_origins == ["http://localhost:5173"]
    assert configuracion.auth_secret_key.get_secret_value() == clave
    assert clave not in repr(configuracion)
    assert len(configuracion.auth_hmac_key) == 48
    assert configuracion.auth_session_minutes == 30
    assert configuracion.auth_session_max_hours == 12
    assert configuracion.auth_cookie_secure is True


def _cargar_esperando_error(monkeypatch, **entorno):
    for nombre, valor in entorno.items():
        monkeypatch.setenv(nombre, valor)
    with pytest.raises(ValidationError) as excinfo:
        cargar_configuracion()
    return str(excinfo.value)


def _entorno_valido(**cambios):
    entorno = {
        "DATABASE_URL": URL_VALIDA,
        "CORS_ALLOWED_ORIGINS": "http://localhost:5173",
        "APP_ENV": "local",
        "AUTH_SECRET_KEY": secrets.token_urlsafe(48),
    }
    entorno.update(cambios)
    return entorno


def test_falta_database_url_menciona_la_variable(monkeypatch):
    entorno = _entorno_valido()
    del entorno["DATABASE_URL"]

    mensaje = _cargar_esperando_error(monkeypatch, **entorno)

    assert "DATABASE_URL" in mensaje


def test_falta_app_env_menciona_la_variable(monkeypatch):
    entorno = _entorno_valido()
    del entorno["APP_ENV"]

    mensaje = _cargar_esperando_error(monkeypatch, **entorno)

    assert "APP_ENV" in mensaje


def test_app_env_no_admitido_menciona_la_variable(monkeypatch):
    mensaje = _cargar_esperando_error(monkeypatch, **_entorno_valido(APP_ENV="produccion"))

    assert "APP_ENV" in mensaje


def test_el_error_no_revela_la_contrasena(monkeypatch):
    entorno = _entorno_valido(
        DATABASE_URL="postgresql+psycopg://app:clave-ficticia@db:5432/turnos",
        APP_ENV="produccion",
    )

    mensaje = _cargar_esperando_error(monkeypatch, **entorno)

    assert "clave-ficticia" not in mensaje
    assert "APP_ENV" in mensaje


def test_el_error_no_muestra_el_valor_recibido(monkeypatch):
    mensaje = _cargar_esperando_error(
        monkeypatch, **_entorno_valido(APP_ENV="valor-secreto-ficticio")
    )

    assert "valor-secreto-ficticio" not in mensaje


def test_varios_origenes_separados_por_comas(monkeypatch):
    for nombre, valor in _entorno_valido(
        CORS_ALLOWED_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
    ).items():
        monkeypatch.setenv(nombre, valor)

    configuracion = cargar_configuracion()

    assert configuracion.cors_allowed_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_origenes_con_espacios_se_recortan(monkeypatch):
    for nombre, valor in _entorno_valido(
        CORS_ALLOWED_ORIGINS=" http://localhost:5173 , http://127.0.0.1:5173 "
    ).items():
        monkeypatch.setenv(nombre, valor)

    assert cargar_configuracion().cors_allowed_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@pytest.mark.parametrize("valor", ["*", "http://localhost:5173,*", "", " , "])
def test_origenes_invalidos_se_rechazan(monkeypatch, valor):
    mensaje = _cargar_esperando_error(
        monkeypatch, **_entorno_valido(CORS_ALLOWED_ORIGINS=valor)
    )

    assert "CORS_ALLOWED_ORIGINS" in mensaje


def test_test_database_url_ausente_es_none(monkeypatch):
    for nombre, valor in _entorno_valido().items():
        monkeypatch.setenv(nombre, valor)

    assert cargar_configuracion().test_database_url is None


def test_test_database_url_presente_se_carga_como_secreto(monkeypatch):
    url = "postgresql+psycopg://app:clave-ficticia@db-test:5432/turnos_test"
    for nombre, valor in _entorno_valido(TEST_DATABASE_URL=url).items():
        monkeypatch.setenv(nombre, valor)

    configuracion = cargar_configuracion()

    assert configuracion.test_database_url is not None
    assert configuracion.test_database_url.get_secret_value() == url
    assert "clave-ficticia" not in repr(configuracion)


# --- Duraciones de sesion y cookie (tarea 2.1) --------------------------------


def _cargar(monkeypatch, **cambios):
    for nombre, valor in _entorno_valido(**cambios).items():
        monkeypatch.setenv(nombre, valor)
    return cargar_configuracion()


@pytest.mark.parametrize(
    ("minutos", "horas"), [("5", "12"), ("480", "24"), ("60", "1"), ("30", "12")]
)
def test_duraciones_validas_incluidos_los_limites(monkeypatch, minutos, horas):
    configuracion = _cargar(
        monkeypatch, AUTH_SESSION_MINUTES=minutos, AUTH_SESSION_MAX_HOURS=horas
    )

    assert configuracion.auth_session_minutes == int(minutos)
    assert configuracion.auth_session_max_hours == int(horas)


@pytest.mark.parametrize(
    ("variable", "valor"),
    [
        ("AUTH_SESSION_MINUTES", "4"),
        ("AUTH_SESSION_MINUTES", "481"),
        ("AUTH_SESSION_MINUTES", "abc"),
        ("AUTH_SESSION_MAX_HOURS", "0"),
        ("AUTH_SESSION_MAX_HOURS", "25"),
    ],
)
def test_duraciones_fuera_de_rango_mencionan_la_variable(monkeypatch, variable, valor):
    mensaje = _cargar_esperando_error(monkeypatch, **_entorno_valido(**{variable: valor}))

    assert variable in mensaje


def test_inactividad_mayor_que_el_absoluto_se_rechaza(monkeypatch):
    mensaje = _cargar_esperando_error(
        monkeypatch,
        **_entorno_valido(AUTH_SESSION_MINUTES="120", AUTH_SESSION_MAX_HOURS="1"),
    )

    assert "AUTH_SESSION_MINUTES" in mensaje


def test_cookie_sin_secure_se_rechaza_con_app_env_test(monkeypatch):
    mensaje = _cargar_esperando_error(
        monkeypatch, **_entorno_valido(APP_ENV="test", AUTH_COOKIE_SECURE="false")
    )

    assert "AUTH_COOKIE_SECURE" in mensaje


def test_cookie_sin_secure_se_acepta_con_app_env_local(monkeypatch):
    configuracion = _cargar(monkeypatch, APP_ENV="local", AUTH_COOKIE_SECURE="false")

    assert configuracion.auth_cookie_secure is False


def test_cookie_secure_true_se_acepta_con_app_env_test(monkeypatch):
    configuracion = _cargar(monkeypatch, APP_ENV="test", AUTH_COOKIE_SECURE="true")

    assert configuracion.auth_cookie_secure is True


# --- Validacion de AUTH_SECRET_KEY (tarea 2.2, DD-17) --------------------------


def _clave():
    return secrets.token_urlsafe(48)


def _rechazo_de_clave(monkeypatch, clave):
    mensaje = _cargar_esperando_error(monkeypatch, **_entorno_valido(AUTH_SECRET_KEY=clave))
    assert "AUTH_SECRET_KEY" in mensaje
    if clave.strip():
        assert clave not in mensaje
    return mensaje


def test_falta_auth_secret_key_menciona_la_variable(monkeypatch):
    entorno = _entorno_valido()
    del entorno["AUTH_SECRET_KEY"]

    assert "AUTH_SECRET_KEY" in _cargar_esperando_error(monkeypatch, **entorno)


@pytest.mark.parametrize("valor", ["", " ", "   "])
def test_auth_secret_key_vacia_se_rechaza(monkeypatch, valor):
    _rechazo_de_clave(monkeypatch, valor)


def test_auth_secret_key_corta_se_rechaza(monkeypatch):
    _rechazo_de_clave(monkeypatch, secrets.token_urlsafe(16))


def test_auth_secret_key_en_el_limite_de_32_bytes_se_acepta(monkeypatch):
    clave = secrets.token_urlsafe(32)  # 43 caracteres, 32 bytes

    assert len(_cargar(monkeypatch, AUTH_SECRET_KEY=clave).auth_hmac_key) == 32


def test_auth_secret_key_de_31_bytes_se_rechaza(monkeypatch):
    _rechazo_de_clave(monkeypatch, secrets.token_urlsafe(31))


@pytest.mark.parametrize("intruso", ["+", "/", ".", " ", "	", "!", "ñ"])
def test_auth_secret_key_con_caracter_fuera_de_base64url_se_rechaza(monkeypatch, intruso):
    clave = _clave()
    _rechazo_de_clave(monkeypatch, clave[:10] + intruso + clave[11:])


def test_auth_secret_key_con_relleno_de_mas_se_rechaza(monkeypatch):
    _rechazo_de_clave(monkeypatch, _clave() + "===")


def test_auth_secret_key_con_relleno_incorrecto_se_rechaza(monkeypatch):
    _rechazo_de_clave(monkeypatch, secrets.token_urlsafe(47) + "==")  # 63 caracteres: falta 1


def test_auth_secret_key_con_longitud_imposible_se_rechaza(monkeypatch):
    clave = _clave()[:61]  # longitud = 1 (mod 4): ningun texto base64 la produce
    _rechazo_de_clave(monkeypatch, clave)


def test_auth_secret_key_con_relleno_correcto_se_acepta(monkeypatch):
    crudo = secrets.token_bytes(47)
    clave = base64.urlsafe_b64encode(crudo).decode()  # termina en '='
    assert clave.endswith("=")

    assert _cargar(monkeypatch, AUTH_SECRET_KEY=clave).auth_hmac_key == crudo


def test_la_clave_hmac_son_los_bytes_decodificados(monkeypatch):
    crudo = secrets.token_bytes(48)
    clave = base64.urlsafe_b64encode(crudo).decode()

    assert _cargar(monkeypatch, AUTH_SECRET_KEY=clave).auth_hmac_key == crudo


@pytest.mark.parametrize("clave", ["a" * 64, "A" * 43, "0" * 100])
def test_auth_secret_key_trivial_se_rechaza(monkeypatch, clave):
    _rechazo_de_clave(monkeypatch, clave)


def test_auth_secret_key_de_baja_diversidad_se_rechaza(monkeypatch):
    clave = "".join(secrets.choice("abcdefghij") for _ in range(64))
    assert len(set(clave)) < 20

    _rechazo_de_clave(monkeypatch, clave)


def test_auth_secret_key_con_19_caracteres_distintos_se_rechaza_y_con_20_se_acepta(
    monkeypatch,
):
    # Texto no periodico construido con exactamente N simbolos distintos.
    def con_n_distintos(n):
        simbolos = "abcdefghijklmnopqrstuvwxyz"[:n]
        base = simbolos + "".join(secrets.choice(simbolos) for _ in range(64 - n))
        return "".join(secrets.SystemRandom().sample(base, len(base)))

    _rechazo_de_clave(monkeypatch, con_n_distintos(19))
    assert _cargar(monkeypatch, AUTH_SECRET_KEY=con_n_distintos(20))


def test_auth_secret_key_periodica_se_rechaza(monkeypatch):
    _rechazo_de_clave(monkeypatch, "ABCDEFGHIJKLMNOPQRSTUVWX" * 3)


def test_auth_secret_key_periodica_con_resto_parcial_se_rechaza(monkeypatch):
    bloque = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcd"  # 30 caracteres distintos
    _rechazo_de_clave(monkeypatch, (bloque * 3)[:70])  # periodo 30 <= 70 / 2


MARCADORES = [
    "cambiar",
    "reemplazar",
    "ficticio",
    "ficticia",
    "example",
    "ejemplo",
    "changeme",
    "secret",
    "password",
    "contrasena",
]


@pytest.mark.parametrize("marcador", MARCADORES)
def test_auth_secret_key_con_marcador_se_rechaza(monkeypatch, marcador):
    clave = _clave()
    _rechazo_de_clave(monkeypatch, clave[:20] + marcador + clave[20:])


@pytest.mark.parametrize("variante", ["Secret", "CHANGEME", "Ficticio"])
def test_auth_secret_key_con_marcador_en_otras_mayusculas_se_rechaza(monkeypatch, variante):
    clave = _clave()
    _rechazo_de_clave(monkeypatch, clave[:20] + variante + clave[20:])


def test_auth_secret_key_igual_a_la_plantilla_se_rechaza(monkeypatch):
    valida = _clave()
    monkeypatch.setattr(modulo_config, "VALOR_PLANTILLA_AUTH_SECRET_KEY", valida)

    _rechazo_de_clave(monkeypatch, valida)


def test_auth_secret_key_distinta_de_la_plantilla_se_acepta(monkeypatch):
    monkeypatch.setattr(modulo_config, "VALOR_PLANTILLA_AUTH_SECRET_KEY", _clave())

    assert _cargar(monkeypatch, AUTH_SECRET_KEY=_clave())


def test_el_valor_de_plantilla_vigente_no_es_una_clave_valida(monkeypatch):
    _rechazo_de_clave(monkeypatch, modulo_config.VALOR_PLANTILLA_AUTH_SECRET_KEY)


# --- Mensajes fijos por regla (tarea 2.3) --------------------------------------


def _reglas_de_clave():
    valida = _clave()
    marcada = valida[:20] + "changeme" + valida[20:]
    return [
        ("", modulo_config.MENSAJE_CLAVE_VACIA),
        (valida[:10] + "+" + valida[11:], modulo_config.MENSAJE_CLAVE_MAL_CODIFICADA),
        (secrets.token_urlsafe(16), modulo_config.MENSAJE_CLAVE_CORTA),
        ("a" * 64, modulo_config.MENSAJE_CLAVE_POCA_DIVERSIDAD),
        ("ABCDEFGHIJKLMNOPQRSTUVWX" * 3, modulo_config.MENSAJE_CLAVE_PERIODICA),
        (marcada, modulo_config.MENSAJE_CLAVE_CON_MARCADOR),
    ]


def test_cada_regla_de_la_clave_responde_su_propio_mensaje_fijo(monkeypatch):
    todos = {
        modulo_config.MENSAJE_CLAVE_VACIA,
        modulo_config.MENSAJE_CLAVE_MAL_CODIFICADA,
        modulo_config.MENSAJE_CLAVE_CORTA,
        modulo_config.MENSAJE_CLAVE_POCA_DIVERSIDAD,
        modulo_config.MENSAJE_CLAVE_PERIODICA,
        modulo_config.MENSAJE_CLAVE_CON_MARCADOR,
        modulo_config.MENSAJE_CLAVE_ES_LA_PLANTILLA,
    }
    assert len(todos) == 7
    for clave, esperado in _reglas_de_clave():
        if clave == "":
            # DD-34 (`env_ignore_empty`): vacia en el ENTORNO cuenta como no definida y la rechaza la
            # regla de obligatoria (`test_una_obligatoria_vacia_hace_fallar_la_carga`); la regla de
            # clave vacia sigue vigente para el valor recibido directamente.
            mensaje = _rechazo_directo_de_clave(clave)
        else:
            mensaje = _rechazo_de_clave(monkeypatch, clave)
        assert esperado in mensaje
        assert [otro for otro in todos - {esperado} if otro in mensaje] == []


def _rechazo_directo_de_clave(clave):
    with pytest.raises(ValidationError) as excinfo:
        modulo_config.Settings(**_entorno_valido(AUTH_SECRET_KEY=clave))
    mensaje = str(excinfo.value)
    assert "AUTH_SECRET_KEY" in mensaje
    return mensaje


def test_el_mensaje_de_plantilla_es_fijo_y_no_contiene_el_valor(monkeypatch):
    valida = _clave()
    monkeypatch.setattr(modulo_config, "VALOR_PLANTILLA_AUTH_SECRET_KEY", valida)

    mensaje = _rechazo_de_clave(monkeypatch, valida)

    assert modulo_config.MENSAJE_CLAVE_ES_LA_PLANTILLA in mensaje


def test_los_mensajes_fijos_nombran_la_variable_y_no_contienen_valores():
    for nombre in dir(modulo_config):
        if nombre.startswith("MENSAJE_CLAVE_"):
            texto = getattr(modulo_config, nombre)
            assert "AUTH_SECRET_KEY" in texto
            assert "{" not in texto and "%" not in texto


# --- 1.1 URLs de login y de administracion separadas (DD-02, R2-05) -------------------

URL_APP = "postgresql+psycopg://turnos_app:clave-app-ficticia@db:5432/turnos"
URL_LOGIN = "postgresql+psycopg://turnos_login:clave-login-ficticia@db:5432/turnos"
URL_ADMIN = "postgresql+psycopg://app:clave-admin-ficticia@db:5432/turnos"
CLAVES_FICTICIAS = ("clave-app-ficticia", "clave-login-ficticia", "clave-admin-ficticia")


def _cargar(monkeypatch, **cambios):
    for nombre, valor in _entorno_valido(DATABASE_URL=URL_APP, **cambios).items():
        monkeypatch.setenv(nombre, valor)
    return cargar_configuracion()


def test_las_urls_de_login_y_migracion_son_opcionales(monkeypatch):
    configuracion = _cargar(monkeypatch)

    assert configuracion.database_login_url is None
    assert configuracion.database_migration_url is None


def test_las_tres_urls_con_usuarios_distintos_cargan(monkeypatch):
    configuracion = _cargar(
        monkeypatch, DATABASE_LOGIN_URL=URL_LOGIN, DATABASE_MIGRATION_URL=URL_ADMIN
    )

    assert configuracion.database_login_url.get_secret_value() == URL_LOGIN
    assert configuracion.database_migration_url.get_secret_value() == URL_ADMIN
    for clave in CLAVES_FICTICIAS:
        assert clave not in repr(configuracion)
        assert clave not in str(configuracion)


def test_solo_la_url_de_login_o_solo_la_de_migracion_cargan(monkeypatch):
    assert _cargar(monkeypatch, DATABASE_LOGIN_URL=URL_LOGIN).database_migration_url is None
    monkeypatch.delenv("DATABASE_LOGIN_URL")
    assert _cargar(monkeypatch, DATABASE_MIGRATION_URL=URL_ADMIN).database_login_url is None


@pytest.mark.parametrize(
    ("login", "migracion", "variables"),
    [
        (URL_APP, None, ("DATABASE_URL", "DATABASE_LOGIN_URL")),
        (None, URL_APP, ("DATABASE_URL", "DATABASE_MIGRATION_URL")),
        (URL_LOGIN, URL_LOGIN, ("DATABASE_LOGIN_URL", "DATABASE_MIGRATION_URL")),
        # mismo usuario con hosts distintos: tambien se rechaza (R2-05)
        (
            "postgresql+psycopg://turnos_app:otra-clave-ficticia@otro-host:5433/otra:base".replace(
                ":otra:base", "/otra"
            ),
            None,
            ("DATABASE_URL", "DATABASE_LOGIN_URL"),
        ),
    ],
)
def test_el_mismo_usuario_en_dos_urls_falla_nombrando_ambas_variables_sin_valores(
    monkeypatch, login, migracion, variables
):
    cambios = {}
    if login:
        cambios["DATABASE_LOGIN_URL"] = login
    if migracion:
        cambios["DATABASE_MIGRATION_URL"] = migracion

    mensaje = _cargar_esperando_error(
        monkeypatch, **_entorno_valido(DATABASE_URL=URL_APP, **cambios)
    )

    for variable in variables:
        assert variable in mensaje
    for valor in (*CLAVES_FICTICIAS, "otra-clave-ficticia", "turnos_app:", "@db:"):
        assert valor not in mensaje


def test_mismo_host_puerto_y_base_con_usuarios_distintos_es_valido(monkeypatch):
    configuracion = _cargar(
        monkeypatch, DATABASE_LOGIN_URL=URL_LOGIN, DATABASE_MIGRATION_URL=URL_ADMIN
    )

    assert configuracion.database_url.get_secret_value() == URL_APP


def test_los_nombres_de_rol_distinguen_mayusculas(monkeypatch):
    configuracion = _cargar(
        monkeypatch,
        DATABASE_LOGIN_URL=URL_LOGIN.replace("turnos_login", "Turnos_App"),
    )

    assert configuracion.database_login_url is not None


# --- Variables vacias como no definidas (DD-34: `api` interpola opcionales con `${VAR:-}`) --------


def test_opcionales_vacias_toman_su_valor_por_defecto(monkeypatch):
    entorno = _entorno_valido(
        AUTH_SESSION_MINUTES="",
        AUTH_SESSION_MAX_HOURS="",
        AUTH_COOKIE_SECURE="",
        TEST_DATABASE_URL="",
    )
    for nombre, valor in entorno.items():
        monkeypatch.setenv(nombre, valor)

    configuracion = cargar_configuracion()

    assert configuracion.auth_session_minutes == 30
    assert configuracion.auth_session_max_hours == 12
    assert configuracion.auth_cookie_secure is True
    assert configuracion.test_database_url is None


@pytest.mark.parametrize(
    "variable", ["DATABASE_URL", "CORS_ALLOWED_ORIGINS", "APP_ENV", "AUTH_SECRET_KEY"]
)
def test_una_obligatoria_vacia_hace_fallar_la_carga(monkeypatch, variable):
    mensaje = _cargar_esperando_error(monkeypatch, **_entorno_valido(**{variable: ""}))

    assert variable in mensaje


def test_las_urls_de_rol_vacias_no_se_cargan(monkeypatch):
    entorno = _entorno_valido(DATABASE_LOGIN_URL="", DATABASE_MIGRATION_URL="")
    for nombre, valor in entorno.items():
        monkeypatch.setenv(nombre, valor)

    configuracion = cargar_configuracion()

    assert configuracion.database_login_url is None
    assert configuracion.database_migration_url is None

"""Comando local de creacion de roles contra `db-test` (tarea 6.2; DD-15, spec `aislamiento-base-de-datos`).

La sesion de base y las lecturas de terminal se inyectan. Los roles de PRUEBA (prefijo `tt_c04_`) se
crean dentro de la transaccion revertible de la fixture `sesion`, asi que nunca persisten: un fixture
verifica al terminar, con una conexion nueva, que no quedo ninguno. Los roles reales de `db-test`
solo se LEEN (verificacion sin cambios). Contrasenas ficticias; nunca se imprimen ni se envian en
texto plano. Nunca se toca la base de desarrollo (X2, D1).
"""

import secrets
from collections.abc import Iterator, Sequence

import pytest
from sqlalchemy import Engine, event, text
from sqlalchemy.orm import Session

from app.core.roles_bd import ROL_ACCESO_LOGIN, ROL_ACCESO_PREVIO, ROL_APP, ROL_LOGIN
from app.roles_postgres.__main__ import NombresDeRoles, main

PREFIJO = "tt_c04_"
NOMBRES = NombresDeRoles(
    app=f"{PREFIJO}app",
    login=f"{PREFIJO}login",
    duenio_previo=f"{PREFIJO}previo",
    duenio_login=f"{PREFIJO}acceso",
)
CLAVE_APP = "clave-ficticia-app-111111"
CLAVE_LOGIN = "clave-ficticia-login-222222"
CLAVE_NUEVA = "clave-ficticia-nueva-333333"


@pytest.fixture(autouse=True)
def entorno_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://app:secreto@host-inexistente.invalid:5432/turnos"
    )
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("AUTH_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")


@pytest.fixture(autouse=True)
def sin_roles_de_prueba_al_terminar(motor: Engine) -> Iterator[None]:
    yield
    with motor.connect() as conexion:
        restantes = conexion.execute(
            text("SELECT rolname FROM pg_roles WHERE rolname LIKE :patron"),
            {"patron": f"{PREFIJO}%"},
        ).scalars().all()
    assert restantes == []


def _terminal(*contrasenas: str):
    cola = list(contrasenas)
    return lambda pedido="": cola.pop(0)


def _correr(sesion: Session, argv: Sequence[str], leer_oculto, nombres: NombresDeRoles, capturadas):
    nueva = Session(
        bind=sesion.get_bind(), expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    motor_o_conexion = sesion.get_bind()

    def capturar(conexion, cursor, sentencia, parametros, contexto, many):
        capturadas.append((sentencia, parametros))

    event.listen(motor_o_conexion, "before_cursor_execute", capturar)
    try:
        return main(
            list(argv),
            abrir_sesion=lambda settings: nueva,
            leer_oculto=leer_oculto,
            es_interactivo=lambda: True,
            nombres=nombres,
        )
    finally:
        event.remove(motor_o_conexion, "before_cursor_execute", capturar)


def _escrituras(capturadas) -> list[str]:
    """Sentencias de modificacion de roles o datos (ignora lecturas y SAVEPOINT/RELEASE)."""
    verbos = ("CREATE", "ALTER", "DROP", "GRANT", "REVOKE", "INSERT", "UPDATE", "DELETE")
    return [s for s, _ in capturadas if s.lstrip().upper().startswith(verbos)]


def _fila(sesion: Session, nombre: str):
    return sesion.execute(
        text(
            "SELECT rolcanlogin, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb, rolreplication, "
            "rolpassword FROM pg_authid WHERE rolname = :n"
        ),
        {"n": nombre},
    ).one_or_none()


def _crear_todos(sesion: Session, capsys):
    capturadas: list = []
    codigo = _correr(
        sesion, ["crear"], _terminal(CLAVE_APP, CLAVE_APP, CLAVE_LOGIN, CLAVE_LOGIN), NOMBRES, capturadas
    )
    salida = capsys.readouterr()
    assert codigo == 0, salida.err
    return codigo, capturadas, salida


def test_creacion_de_los_cuatro_roles_con_atributos_y_verificador_scram(sesion, capsys):
    codigo, capturadas, salida = _crear_todos(sesion, capsys)

    assert codigo == 0
    assert salida.out.splitlines() == [
        f"rol creado: {NOMBRES.duenio_previo}",
        f"rol creado: {NOMBRES.duenio_login}",
        f"rol creado: {NOMBRES.app}",
        f"rol creado: {NOMBRES.login}",
    ]
    for nombre, con_login in (
        (NOMBRES.duenio_previo, False),
        (NOMBRES.duenio_login, False),
        (NOMBRES.app, True),
        (NOMBRES.login, True),
    ):
        fila = _fila(sesion, nombre)
        assert fila is not None and fila.rolcanlogin is con_login
        assert not any(fila[1:6])
        assert (fila.rolpassword or "").startswith("SCRAM-SHA-256$") is con_login
    # Los verificadores son distintos aunque la sal lo seria igual: contrasenas distintas.
    assert _fila(sesion, NOMBRES.app).rolpassword != _fila(sesion, NOMBRES.login).rolpassword


def test_las_sentencias_solo_llevan_verificadores_scram_nunca_la_contrasena(sesion, capsys):
    codigo, capturadas, salida = _crear_todos(sesion, capsys)

    assert codigo == 0
    sentencias = [s for s, _ in capturadas]
    con_clave = [s for s in sentencias if "PASSWORD" in s]
    assert len(con_clave) == 2
    assert all("PASSWORD 'SCRAM-SHA-256$" in s for s in con_clave)
    parametros = repr([p for _, p in capturadas])
    for clave in (CLAVE_APP, CLAVE_LOGIN):
        assert all(clave not in s for s in sentencias)
        assert clave not in parametros
        assert clave not in salida.out + salida.err


def test_segunda_ejecucion_no_cambia_atributos_ni_contrasenas(sesion, capsys):
    _crear_todos(sesion, capsys)
    antes = {n: _fila(sesion, n) for n in (NOMBRES.app, NOMBRES.login)}
    capturadas: list = []

    codigo = _correr(sesion, ["crear"], _terminal(), NOMBRES, capturadas)

    assert codigo == 0
    salida = capsys.readouterr().out.splitlines()
    assert salida == [
        f"rol existente verificado: {NOMBRES.duenio_previo}",
        f"rol existente verificado: {NOMBRES.duenio_login}",
        f"rol existente verificado: {NOMBRES.app}",
        f"rol existente verificado: {NOMBRES.login}",
    ]
    assert _escrituras(capturadas) == []
    assert {n: _fila(sesion, n) for n in antes} == antes


def test_los_roles_reales_de_db_test_se_verifican_sin_cambios(sesion, capsys):
    reales = NombresDeRoles(ROL_APP, ROL_LOGIN, ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN)
    antes = {n: _fila(sesion, n) for n in (ROL_APP, ROL_LOGIN)}
    capturadas: list = []

    codigo = _correr(sesion, ["crear"], _terminal(), reales, capturadas)

    assert codigo == 0
    assert _escrituras(capturadas) == []
    assert {n: _fila(sesion, n) for n in antes} == antes
    assert capsys.readouterr().out.count("rol existente verificado") == 4


@pytest.mark.parametrize(
    ("rol", "alter", "codigo_esperado"),
    [
        ("login", "ALTER ROLE {n} BYPASSRLS", "BYPASSRLS"),
        ("app", "ALTER ROLE {n} SUPERUSER", "SUPERUSER"),
        ("duenio_previo", "ALTER ROLE {n} LOGIN", "CON_LOGIN"),
        ("duenio_login", "ALTER ROLE {n} CREATEROLE", "CREATEROLE"),
        ("app", "ALTER ROLE {n} NOLOGIN", "SIN_LOGIN"),
    ],
)
def test_atributo_indebido_falla_sin_corregirlo(sesion, capsys, rol, alter, codigo_esperado):
    _crear_todos(sesion, capsys)
    nombre = getattr(NOMBRES, rol)
    sesion.execute(text(alter.format(n=nombre)))
    antes = _fila(sesion, nombre)
    capturadas: list = []

    codigo = _correr(sesion, ["crear"], _terminal(), NOMBRES, capturadas)

    salida = capsys.readouterr()
    assert codigo == 1
    assert nombre in salida.err and codigo_esperado in salida.err
    assert _escrituras(capturadas) == []
    assert _fila(sesion, nombre) == antes


def test_membresia_indebida_falla_sin_corregirla(sesion, capsys):
    _crear_todos(sesion, capsys)
    sesion.execute(text(f"GRANT {NOMBRES.duenio_login} TO {NOMBRES.duenio_previo}"))
    capturadas: list = []

    codigo = _correr(sesion, ["crear"], _terminal(), NOMBRES, capturadas)

    salida = capsys.readouterr()
    assert codigo == 1 and "MEMBRESIAS" in salida.err
    assert _escrituras(capturadas) == []


def test_contrasenas_iguales_no_crean_ni_el_segundo_rol(sesion, capsys):
    capturadas: list = []

    codigo = _correr(
        sesion,
        ["crear"],
        _terminal(CLAVE_APP, CLAVE_APP, CLAVE_APP, CLAVE_APP),
        NOMBRES,
        capturadas,
    )

    salida = capsys.readouterr()
    assert codigo == 1
    assert CLAVE_APP not in salida.out + salida.err
    assert _fila(sesion, NOMBRES.login) is None and _fila(sesion, NOMBRES.app) is None


def test_rotar_cambia_solo_el_verificador_indicado(sesion, capsys):
    _crear_todos(sesion, capsys)
    app_antes = _fila(sesion, NOMBRES.app)
    login_antes = _fila(sesion, NOMBRES.login)
    capturadas: list = []

    codigo = _correr(
        sesion,
        ["crear", "--rotar-contrasena", ROL_LOGIN],
        _terminal(CLAVE_NUEVA, CLAVE_NUEVA),
        NombresDeRoles(
            app=NOMBRES.app,
            login=NOMBRES.login,
            duenio_previo=NOMBRES.duenio_previo,
            duenio_login=NOMBRES.duenio_login,
        ),
        capturadas,
    )

    salida = capsys.readouterr()
    assert codigo == 0
    assert f"contraseña rotada: {NOMBRES.login}" in salida.out
    assert f"rol existente verificado: {NOMBRES.app}" in salida.out
    assert _fila(sesion, NOMBRES.app) == app_antes
    login_despues = _fila(sesion, NOMBRES.login)
    assert login_despues.rolpassword != login_antes.rolpassword
    assert login_despues.rolpassword.startswith("SCRAM-SHA-256$")
    assert login_despues[:6] == login_antes[:6]
    alter = [s for s, _ in capturadas if s.startswith("ALTER ROLE")]
    assert len(alter) == 1 and "PASSWORD 'SCRAM-SHA-256$" in alter[0]
    assert CLAVE_NUEVA not in alter[0] and CLAVE_NUEVA not in salida.out + salida.err

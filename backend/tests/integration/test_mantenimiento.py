"""Comando local de mantenimiento contra `db-test` (tarea 10.2; DD-28, PC-03, spec `mantenimiento-local`).

La sesion de base y el reloj se inyectan: el comando usa una segunda `Session` sobre la conexion y la
transaccion revertible de la fixture `sesion` (cada lote se confirma liberando su SAVEPOINT, y todo se
revierte al terminar). `DATABASE_URL` apunta a un host inexistente: si el comando intentara abrir su
propia conexion, la prueba fallaria. Nunca se toca la base de desarrollo (X2, D1).
"""

import secrets
from datetime import timedelta

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.mantenimiento.__main__ import main
from tests.integration.datos_auth import (
    AHORA,
    Entorno,
    RelojFijo,
    insertar_fallo,
    insertar_sesion,
)

MINUTOS_DE_INACTIVIDAD = 30


@pytest.fixture
def entorno(sesion: Session) -> Entorno:
    return Entorno(sesion)


@pytest.fixture(autouse=True)
def entorno_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://app:secreto@host-inexistente.invalid:5432/turnos"
    )
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("AUTH_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("AUTH_SESSION_MINUTES", str(MINUTOS_DE_INACTIVIDAD))
    monkeypatch.setenv("AUTH_SESSION_MAX_HOURS", "12")


def _ejecutar(entorno: Entorno, argv: list[str]) -> int:
    nueva = Session(
        bind=entorno.db.get_bind(), expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    return main(argv, abrir_sesion=lambda settings: nueva, reloj=RelojFijo(AHORA))


def _contar(entorno: Entorno, tabla: str) -> int:
    return entorno.db.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()


def _huella_de_dominio(entorno: Entorno):
    return entorno.db.execute(
        text(
            "SELECT (SELECT md5(string_agg(c::text, '|' ORDER BY c.id)) FROM consultorio c), "
            "(SELECT md5(string_agg(u::text, '|' ORDER BY u.id)) FROM usuario u)"
        )
    ).one()


def _intentos_vencidos(entorno: Entorno, cantidad: int) -> None:
    """`cantidad` fallos de hace 25 horas, insertados en bloque."""
    entorno.db.execute(
        text(
            "INSERT INTO intento_login (clave_cuenta, clave_ip, ocurrido_en) "
            "SELECT decode(md5(i::text) || md5(i::text || 'c'), 'hex'), "
            "decode(md5(i::text) || md5(i::text || 'i'), 'hex'), :t "
            "FROM generate_series(1, :n) AS i"
        ),
        {"t": AHORA - timedelta(hours=25), "n": cantidad},
    )
    entorno.db.commit()


def _sesiones_vencidas(entorno: Entorno, cantidad: int) -> None:
    """`cantidad` sesiones vencidas por inactividad, insertadas en bloque."""
    entorno.db.execute(
        text(
            "INSERT INTO sesion (consultorio_id, usuario_id, token_hmac, creada_en, ultimo_uso_en, "
            "vence_absoluto_en) "
            "SELECT :c, :u, decode(md5(i::text) || md5(i::text || 's'), 'hex'), :creada, :uso, :vence "
            "FROM generate_series(1, :n) AS i"
        ),
        {
            "c": entorno.a,
            "u": entorno.ua,
            "creada": AHORA - timedelta(hours=2),
            "uso": AHORA - timedelta(hours=1),
            "vence": AHORA + timedelta(hours=10),
            "n": cantidad,
        },
    )
    entorno.db.commit()


class EspiaDeBorrados:
    """Registra cada sentencia `DELETE` con las filas que afecto (en la conexion de la prueba)."""

    def __init__(self, entorno: Entorno, fallar_en_el_borrado_de_intentos: int | None = None) -> None:
        self.conexion = entorno.db.get_bind()
        self.borrados: list[tuple[str, int]] = []
        self.fallar_en = fallar_en_el_borrado_de_intentos
        self._intentos_vistos = 0

    def _antes(self, conn, cursor, statement, parameters, context, executemany) -> None:
        if statement.startswith("DELETE FROM intento_login"):
            self._intentos_vistos += 1
            if self._intentos_vistos == self.fallar_en:
                raise RuntimeError("fallo inyectado con persona@example.test")

    def _despues(self, conn, cursor, statement, parameters, context, executemany) -> None:
        if statement.startswith("DELETE"):
            self.borrados.append((statement.split()[2], cursor.rowcount))

    def __enter__(self) -> "EspiaDeBorrados":
        event.listen(self.conexion, "before_cursor_execute", self._antes)
        event.listen(self.conexion, "after_cursor_execute", self._despues)
        return self

    def __exit__(self, *args: object) -> None:
        event.remove(self.conexion, "before_cursor_execute", self._antes)
        event.remove(self.conexion, "after_cursor_execute", self._despues)

    def filas(self, tabla: str) -> list[int]:
        return [filas for nombre, filas in self.borrados if nombre == tabla]


# --- Solo borra lo vencido -------------------------------------------------------------------------


def test_solo_se_borran_sesiones_e_intentos_vencidos_y_el_dominio_no_cambia(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    db, a, ua = entorno.db, entorno.a, entorno.ua
    for _ in range(3):  # revocadas, por lo demas vigentes
        insertar_sesion(
            db, a, ua,
            creada_en=AHORA - timedelta(hours=1),
            ultimo_uso_en=AHORA - timedelta(minutes=1),  # sin vencer por inactividad ni absoluto
            revocada_en=AHORA - timedelta(seconds=30),
        )
    for _ in range(2):  # vencidas por inactividad (31 min sin uso)
        insertar_sesion(db, a, ua, creada_en=AHORA - timedelta(hours=1), ultimo_uso_en=AHORA - timedelta(minutes=31))
    insertar_sesion(  # vencida por tiempo absoluto con uso reciente (inactividad no vencida)
        db,
        a,
        ua,
        creada_en=AHORA - timedelta(hours=12, minutes=2),
        ultimo_uso_en=AHORA - timedelta(minutes=2),
        vence_absoluto_en=AHORA - timedelta(minutes=1),
    )
    validas = [
        insertar_sesion(db, a, ua, creada_en=AHORA - timedelta(hours=1), ultimo_uso_en=AHORA - timedelta(minutes=29)),
        insertar_sesion(db, a, ua, creada_en=AHORA - timedelta(minutes=5)),
    ]
    clave = secrets.token_bytes(32)
    for _ in range(4):
        insertar_fallo(db, clave, clave, AHORA - timedelta(hours=25))
    for _ in range(3):
        insertar_fallo(db, clave, clave, AHORA - timedelta(hours=23, minutes=59))
    db.commit()
    huella = _huella_de_dominio(entorno)

    codigo = _ejecutar(entorno, ["limpiar"])

    assert codigo == 0
    assert capsys.readouterr().out.strip() == "sesiones eliminadas: 6; intentos eliminados: 4"
    quedan = {fila[0] for fila in db.execute(text("SELECT id FROM sesion"))}
    assert quedan == set(validas)
    assert _contar(entorno, "intento_login") == 3
    assert tuple(_huella_de_dominio(entorno)) == tuple(huella)


def test_un_intento_de_exactamente_24_horas_no_se_borra_y_uno_de_24_horas_y_un_segundo_si(
    entorno: Entorno,
):
    clave = secrets.token_bytes(32)
    insertar_fallo(entorno.db, clave, clave, AHORA - timedelta(hours=24))
    insertar_fallo(entorno.db, clave, clave, AHORA - timedelta(hours=24, seconds=1))
    entorno.db.commit()

    _ejecutar(entorno, ["limpiar"])

    restantes = [f[0] for f in entorno.db.execute(text("SELECT ocurrido_en FROM intento_login"))]
    assert restantes == [AHORA - timedelta(hours=24)]


def test_la_inactividad_vigente_decide_cuando_vence_una_sesion(
    entorno: Entorno, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("AUTH_SESSION_MINUTES", "60")
    insertar_sesion(
        entorno.db, entorno.a, entorno.ua,
        creada_en=AHORA - timedelta(hours=2), ultimo_uso_en=AHORA - timedelta(minutes=45),
    )
    entorno.db.commit()

    _ejecutar(entorno, ["limpiar"])

    assert _contar(entorno, "sesion") == 1  # con 30 min estaria vencida; con 60 sigue valida


def test_sin_filas_vencidas_termina_con_codigo_0_y_no_borra_nada(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    insertar_sesion(entorno.db, entorno.a, entorno.ua, creada_en=AHORA - timedelta(minutes=5))
    clave = secrets.token_bytes(32)
    insertar_fallo(entorno.db, clave, clave, AHORA - timedelta(hours=1))
    entorno.db.commit()

    with EspiaDeBorrados(entorno) as espia:
        codigo = _ejecutar(entorno, ["limpiar"])

    assert codigo == 0
    assert capsys.readouterr().out.strip() == "sesiones eliminadas: 0; intentos eliminados: 0"
    assert (_contar(entorno, "sesion"), _contar(entorno, "intento_login")) == (1, 1)
    assert espia.filas("sesion") == [0] and espia.filas("intento_login") == [0]


# --- Lotes y transacciones -------------------------------------------------------------------------


def test_con_max_lotes_2_y_2500_intentos_se_borran_2000_en_lotes_de_a_lo_sumo_mil(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    _intentos_vencidos(entorno, 2500)

    with EspiaDeBorrados(entorno) as espia:
        codigo = _ejecutar(entorno, ["limpiar", "--max-lotes", "2"])

    assert codigo == 0
    assert _contar(entorno, "intento_login") == 500
    assert espia.filas("intento_login") == [1000, 1000]
    assert capsys.readouterr().out.strip() == "sesiones eliminadas: 0; intentos eliminados: 2000"


def test_cada_lote_se_confirma_aparte_un_error_en_el_tercero_conserva_los_dos_primeros(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    _intentos_vencidos(entorno, 2500)

    with EspiaDeBorrados(entorno, fallar_en_el_borrado_de_intentos=3) as espia:
        codigo = _ejecutar(entorno, ["limpiar"])

    capturada = capsys.readouterr()
    assert codigo != 0
    assert _contar(entorno, "intento_login") == 500
    assert espia.filas("intento_login") == [1000, 1000]
    for prohibido in ("persona", "@", "postgresql"):
        assert prohibido not in capturada.out + capturada.err


def test_la_ejecucion_por_defecto_borra_todo_en_lotes_de_a_lo_sumo_mil(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    _intentos_vencidos(entorno, 2500)
    _sesiones_vencidas(entorno, 1200)

    with EspiaDeBorrados(entorno) as espia:
        codigo = _ejecutar(entorno, ["limpiar"])

    assert codigo == 0
    assert (_contar(entorno, "intento_login"), _contar(entorno, "sesion")) == (0, 0)
    assert espia.filas("sesion") == [1000, 200]
    assert espia.filas("intento_login") == [1000, 1000, 500]
    assert capsys.readouterr().out.strip() == "sesiones eliminadas: 1200; intentos eliminados: 2500"


def test_un_lote_completo_exacto_hace_una_consulta_mas_y_termina(entorno: Entorno):
    _intentos_vencidos(entorno, 2000)

    with EspiaDeBorrados(entorno) as espia:
        _ejecutar(entorno, ["limpiar"])

    assert espia.filas("intento_login") == [1000, 1000, 0]
    assert _contar(entorno, "intento_login") == 0


# --- Salida ------------------------------------------------------------------------------------------


def test_la_salida_es_exactamente_el_resumen_sin_identificadores(
    entorno: Entorno, capsys: pytest.CaptureFixture[str]
):
    ids = [
        insertar_sesion(
            entorno.db, entorno.a, entorno.ua,
            creada_en=AHORA - timedelta(hours=1), ultimo_uso_en=AHORA - timedelta(minutes=40),
        )
        for _ in range(3)
    ]
    clave = secrets.token_bytes(32)
    for _ in range(4):
        insertar_fallo(entorno.db, clave, clave, AHORA - timedelta(hours=30))
    entorno.db.commit()

    _ejecutar(entorno, ["limpiar"])

    capturada = capsys.readouterr()
    assert capturada.out == "sesiones eliminadas: 3; intentos eliminados: 4\n"
    assert capturada.err == ""
    for prohibido in ("@", "postgresql", *[str(i) for i in ids]):
        assert prohibido not in capturada.out

"""Comando local de mantenimiento: guardia, argumentos y lotes (tarea 10.1; DD-28, PC-03).

Sin base: la sesion y las funciones de borrado de `acceso_admin` se sustituyen. Los borrados reales
se prueban en `tests/integration/test_mantenimiento.py` (10.2).
"""

import secrets
from datetime import UTC, datetime

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.auth import acceso_admin
from app.core.linea_de_comandos import ArgumentosInvalidos
from app.mantenimiento import limpieza
from app.mantenimiento.__main__ import analizar, main
from app.mantenimiento.limpieza import TAMANO_DE_LOTE, ResumenLimpieza, limpiar

URL_INEXISTENTE = "postgresql+psycopg://app:secreto@host-inexistente.invalid:5432/turnos"
# C-04: los comandos locales usan DATABASE_MIGRATION_URL (rol `app`); la de la API es otro rol.
URL_API_INEXISTENTE = "postgresql+psycopg://turnos_app:secreto@host-api-inexistente.invalid:5432/turnos"
AHORA = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)


def _entorno(monkeypatch: pytest.MonkeyPatch, app_env: str) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("DATABASE_URL", URL_API_INEXISTENTE)
    monkeypatch.setenv("DATABASE_MIGRATION_URL", URL_INEXISTENTE)
    monkeypatch.delenv("DATABASE_LOGIN_URL", raising=False)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("AUTH_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")


class SesionFalsa:
    def __init__(self) -> None:
        self.confirmaciones = 0
        self.reversiones = 0
        self.cierres = 0

    def commit(self) -> None:
        self.confirmaciones += 1

    def rollback(self) -> None:
        self.reversiones += 1

    def close(self) -> None:
        self.cierres += 1


class Borrados:
    """Sustituye `limpiar_sesiones` y `limpiar_intentos`: entrega cantidades por lote, en orden."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, sesiones=(), intentos=()) -> None:
        self.pendientes = {"sesiones": list(sesiones), "intentos": list(intentos)}
        self.llamadas: list[tuple[str, dict]] = []
        monkeypatch.setattr(
            acceso_admin, "limpiar_sesiones", lambda s, ahora, minutos, limite: self._lote("sesiones", ahora, minutos, limite)
        )
        monkeypatch.setattr(
            acceso_admin, "limpiar_intentos", lambda s, ahora, limite: self._lote("intentos", ahora, None, limite)
        )

    def _lote(self, tabla: str, ahora, minutos, limite) -> int:
        self.llamadas.append((tabla, {"ahora": ahora, "minutos": minutos, "limite": limite}))
        cola = self.pendientes[tabla]
        if not cola:
            return 0
        valor = cola.pop(0)
        if isinstance(valor, Exception):
            raise valor
        return valor

    def lotes(self, tabla: str) -> int:
        return sum(1 for nombre, _ in self.llamadas if nombre == tabla)


def _escuchar_conexiones() -> tuple[list[object], object]:
    intentos: list[object] = []

    def registrar(dialect, conn_rec, cargs, cparams):
        intentos.append(cparams.get("host"))

    event.listen(Engine, "do_connect", registrar)
    return intentos, registrar


# --- Guardia de entorno ---------------------------------------------------------------------


def test_app_env_test_se_rechaza_sin_abrir_sesion_ni_conectar(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "test")
    borrados = Borrados(monkeypatch, sesiones=[5], intentos=[5])
    aperturas: list[object] = []
    intentos, registrar = _escuchar_conexiones()
    try:
        codigo = main(["limpiar"], abrir_sesion=lambda settings: aperturas.append(1))  # type: ignore[arg-type,func-returns-value]
    finally:
        event.remove(Engine, "do_connect", registrar)  # type: ignore[arg-type]

    capturada = capsys.readouterr()
    salida = capturada.out + capturada.err
    assert codigo != 0
    assert "APP_ENV" in salida
    assert (intentos, aperturas, borrados.llamadas) == ([], [], [])
    for prohibido in ("host-inexistente", "postgresql", "secreto", "@"):
        assert prohibido not in salida


def test_el_comando_real_sin_costuras_si_intenta_conectar_con_app_env_local(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    # Control: con APP_ENV=local la guardia pasa y el comando SI intenta conectar, de modo que
    # el detector de la prueba anterior detecta lo que debe detectar.
    _entorno(monkeypatch, "local")
    intentos, registrar = _escuchar_conexiones()
    try:
        codigo = main(["limpiar"])
    finally:
        event.remove(Engine, "do_connect", registrar)  # type: ignore[arg-type]

    capturada = capsys.readouterr()
    salida = capturada.out + capturada.err
    assert codigo != 0
    assert "host-inexistente.invalid" in intentos
    for prohibido in ("host-inexistente", "postgresql", "secreto", "@"):
        assert prohibido not in salida


# --- Argumentos -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["limpiar", "--max-lotes", "0"],
        ["limpiar", "--max-lotes", "1001"],
        ["limpiar", "--max-lotes", "abc"],
        ["limpiar", "--max-lotes", "-5"],
        ["limpiar", "--max-lotes", "1.5"],
        ["limpiar", "--max-lotes"],
        ["borrar"],
        ["borrar", "--max-lotes", "10"],
        [],
        ["limpiar", "--otra"],
    ],
)
def test_los_argumentos_invalidos_se_rechazan_antes_de_conectar(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], argv: list[str]
):
    _entorno(monkeypatch, "local")  # la guardia pasaria: lo que rechaza es la validacion
    borrados = Borrados(monkeypatch, sesiones=[5], intentos=[5])
    aperturas: list[object] = []
    intentos, registrar = _escuchar_conexiones()
    try:
        codigo = main(argv, abrir_sesion=lambda settings: aperturas.append(1))  # type: ignore[arg-type,func-returns-value]
    finally:
        event.remove(Engine, "do_connect", registrar)  # type: ignore[arg-type]

    capturada = capsys.readouterr()
    assert codigo != 0
    assert "argumentos no validos" in capturada.err
    assert (intentos, aperturas, borrados.llamadas) == ([], [], [])


@pytest.mark.parametrize(
    ("argv", "esperado"),
    [
        (["limpiar"], 100),
        (["limpiar", "--max-lotes", "1"], 1),
        (["limpiar", "--max-lotes", "1000"], 1000),
        (["limpiar", "--max-lotes", "37"], 37),
    ],
)
def test_el_maximo_de_lotes_por_defecto_y_los_limites_se_aceptan(argv: list[str], esperado: int):
    assert analizar(argv).max_lotes == esperado


@pytest.mark.parametrize("valor", ["0", "1001", "abc"])
def test_analizar_lanza_argumentos_invalidos_sin_repetir_el_valor(valor: str):
    with pytest.raises(ArgumentosInvalidos) as excinfo:
        analizar(["limpiar", "--max-lotes", valor])

    assert valor not in str(excinfo.value)


# --- Lotes (la limpieza usa la sesion y las funciones de acceso previo) --------------------------------


def test_sin_filas_vencidas_hay_un_lote_por_tabla_cada_uno_confirmado(
    monkeypatch: pytest.MonkeyPatch,
):
    borrados = Borrados(monkeypatch)
    sesion = SesionFalsa()

    resumen = limpiar(sesion, AHORA, 30, max_lotes=5)  # type: ignore[arg-type]

    assert TAMANO_DE_LOTE == 1000
    assert resumen == ResumenLimpieza(sesiones=0, intentos=0)
    assert (borrados.lotes("sesiones"), borrados.lotes("intentos")) == (1, 1)
    assert sesion.confirmaciones == 2


def test_se_detiene_al_borrar_menos_de_mil_y_suma_las_cantidades(monkeypatch: pytest.MonkeyPatch):
    borrados = Borrados(monkeypatch, sesiones=[1000, 200], intentos=[1000, 1000, 400])
    sesion = SesionFalsa()

    resumen = limpiar(sesion, AHORA, 30, max_lotes=100)  # type: ignore[arg-type]

    assert resumen == ResumenLimpieza(sesiones=1200, intentos=2400)
    assert (borrados.lotes("sesiones"), borrados.lotes("intentos")) == (2, 3)
    assert all(datos["limite"] == 1000 for _, datos in borrados.llamadas)
    assert sesion.confirmaciones == 5  # un commit por lote


def test_se_detiene_al_llegar_al_maximo_de_lotes_por_tabla(monkeypatch: pytest.MonkeyPatch):
    borrados = Borrados(monkeypatch, sesiones=[1000] * 10, intentos=[1000] * 10)
    sesion = SesionFalsa()

    resumen = limpiar(sesion, AHORA, 30, max_lotes=2)  # type: ignore[arg-type]

    assert resumen == ResumenLimpieza(sesiones=2000, intentos=2000)
    assert (borrados.lotes("sesiones"), borrados.lotes("intentos")) == (2, 2)


def test_la_limpieza_usa_el_reloj_y_la_inactividad_recibidos(monkeypatch: pytest.MonkeyPatch):
    borrados = Borrados(monkeypatch)

    limpiar(SesionFalsa(), AHORA, 45, max_lotes=1)  # type: ignore[arg-type]

    por_tabla = dict(borrados.llamadas)
    assert por_tabla["sesiones"] == {"ahora": AHORA, "minutos": 45, "limite": 1000}
    assert por_tabla["intentos"] == {"ahora": AHORA, "minutos": None, "limite": 1000}


# --- main: ejecucion, errores y salida ----------------------------------------------------------------


def test_main_ejecuta_la_limpieza_con_el_maximo_por_defecto_y_muestra_solo_cantidades(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    borrados = Borrados(monkeypatch, sesiones=[3], intentos=[1000] * 150)
    sesion = SesionFalsa()

    codigo = main(["limpiar"], abrir_sesion=lambda settings: sesion)  # type: ignore[arg-type,return-value]

    assert codigo == 0
    assert capsys.readouterr().out.strip() == "sesiones eliminadas: 3; intentos eliminados: 100000"
    assert borrados.lotes("intentos") == 100  # maximo por defecto
    assert sesion.cierres == 1


def test_main_respeta_el_maximo_de_lotes_indicado(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    borrados = Borrados(monkeypatch, intentos=[1000] * 10)

    codigo = main(["limpiar", "--max-lotes", "2"], abrir_sesion=lambda settings: SesionFalsa())  # type: ignore[arg-type,return-value]

    assert codigo == 0
    assert borrados.lotes("intentos") == 2
    assert capsys.readouterr().out.strip() == "sesiones eliminadas: 0; intentos eliminados: 2000"


def test_un_error_en_un_lote_termina_con_codigo_distinto_de_cero_sin_datos_sensibles(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    Borrados(
        monkeypatch,
        intentos=[1000, 1000, RuntimeError("fallo con persona@example.test y postgresql://x")],
    )
    sesion = SesionFalsa()

    codigo = main(["limpiar"], abrir_sesion=lambda settings: sesion)  # type: ignore[arg-type,return-value]

    capturada = capsys.readouterr()
    salida = capturada.out + capturada.err
    assert codigo != 0
    assert sesion.confirmaciones == 3  # 1 de sesiones (vacia) + 2 lotes de intentos confirmados
    assert sesion.reversiones == 1 and sesion.cierres == 1
    for prohibido in ("persona", "@", "postgresql"):
        assert prohibido not in salida
    assert "intentos eliminados" not in salida  # no hay resumen parcial enganoso

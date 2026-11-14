"""Comando local de credenciales: guardia y entrada (tarea 9.1; DD-22, specs `credenciales-locales`).

Sin base: la sesion, las lecturas de terminal y la busqueda de cuenta se inyectan (D1: datos ficticios).
"""

import secrets
import unicodedata
import uuid
from collections.abc import Sequence

import pytest
from argon2 import PasswordHasher, Type
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.auth import acceso_admin
from app.auth.cuenta import Cuenta
from app.credenciales.__main__ import main

URL_INEXISTENTE = "postgresql+psycopg://app:secreto@host-inexistente.invalid:5432/turnos"
# C-04: los comandos locales usan DATABASE_MIGRATION_URL (rol `app`); la de la API es otro rol.
URL_API_INEXISTENTE = "postgresql+psycopg://turnos_app:secreto@host-api-inexistente.invalid:5432/turnos"
CODIGO = "ficticio-a"
EMAIL = "persona.ficticia@example.test"
CONTRASENA = "clave-de-prueba-a1"
OTRA_CONTRASENA = "clave-de-prueba-a2"
# Argon2id de costo minimo: el costo real se prueba en test_auth_contrasenas.py.
HASHER_RAPIDO = PasswordHasher(
    time_cost=2, memory_cost=1024, parallelism=2, hash_len=32, salt_len=16, type=Type.ID
)


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


class Terminal:
    """Lecturas inyectadas: registra cada llamada y entrega las respuestas en orden."""

    def __init__(self, visibles: Sequence[str] = (), ocultas: Sequence[str] = ()) -> None:
        self.visibles = list(visibles)
        self.ocultas = list(ocultas)
        self.pedidos_visibles: list[str] = []
        self.pedidos_ocultos: list[str] = []

    def leer_visible(self, pedido: str = "") -> str:
        self.pedidos_visibles.append(pedido)
        return self.visibles.pop(0)

    def leer_oculto(self, pedido: str = "") -> str:
        self.pedidos_ocultos.append(pedido)
        return self.ocultas.pop(0)


class Escenario:
    """Cuenta ficticia, sesion falsa y registro de escrituras, inyectados en el comando."""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        credencial: str | None = None,
        cuenta_existe: bool = True,
        interactivo: bool = True,
        consultorio_nombre: str = "Consultorio Ficticio A",
        nombre_usuario: str = "Persona Ficticia",
    ) -> None:
        self.sesion = SesionFalsa()
        self.interactivo = interactivo
        self.aperturas = 0
        self.escrituras: list[tuple] = []
        self.revocaciones: list[tuple] = []
        self.consultorio_id = uuid.uuid4()
        self.usuario_id = uuid.uuid4()
        cuenta = Cuenta(
            usuario_id=self.usuario_id,
            consultorio_id=self.consultorio_id,
            email=EMAIL,
            nombre=nombre_usuario,
            rol="secretaria",
            credencial=credencial,
            usuario_activo=True,
            consultorio_nombre=consultorio_nombre,
            consultorio_activo=True,
        )
        monkeypatch.setattr(
            acceso_admin,
            "buscar_cuenta",
            lambda s, codigo, email: cuenta if cuenta_existe else None,
        )

        def escribir(s, consultorio_id, usuario_id, nueva, esperada):
            self.escrituras.append((consultorio_id, usuario_id, nueva, esperada))
            return True

        def revocar(s, consultorio_id, usuario_id, ahora):
            self.revocaciones.append((consultorio_id, usuario_id, ahora))
            return 2

        monkeypatch.setattr(acceso_admin, "escribir_credencial", escribir)
        monkeypatch.setattr(acceso_admin, "revocar_sesiones_de_usuario", revocar)

    def abrir_sesion(self, settings: object) -> SesionFalsa:
        self.aperturas += 1
        return self.sesion

    def ejecutar(self, terminal: Terminal, argv: Sequence[str] = ()) -> int:
        return main(
            list(argv),
            abrir_sesion=self.abrir_sesion,
            leer_visible=terminal.leer_visible,
            leer_oculto=terminal.leer_oculto,
            es_interactivo=lambda: self.interactivo,
            hasher=HASHER_RAPIDO,
        )


def _salida(capsys: pytest.CaptureFixture[str]) -> str:
    capturada = capsys.readouterr()
    return capturada.out + capturada.err


def _escuchar_conexiones() -> tuple[list[object], object]:
    intentos: list[object] = []

    def registrar(dialect, conn_rec, cargs, cparams):
        intentos.append(cparams.get("host"))

    event.listen(Engine, "do_connect", registrar)
    return intentos, registrar


# --- Guardia de entorno -------------------------------------------------------------------


def test_app_env_test_se_rechaza_sin_conectar_ni_leer(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "test")
    escenario = Escenario(monkeypatch)
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[CONTRASENA, CONTRASENA])
    intentos, registrar = _escuchar_conexiones()
    try:
        codigo = escenario.ejecutar(terminal)
    finally:
        event.remove(Engine, "do_connect", registrar)  # type: ignore[arg-type]

    salida = _salida(capsys)
    assert codigo != 0
    assert "APP_ENV" in salida
    assert intentos == []
    assert escenario.aperturas == 0
    assert (terminal.pedidos_visibles, terminal.pedidos_ocultos) == ([], [])
    for prohibido in ("host-inexistente", "postgresql", "secreto", "@"):
        assert prohibido not in salida


def test_el_comando_real_sin_costuras_si_intenta_conectar_con_app_env_local(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    # Control: con APP_ENV=local el comando pasa la guardia y SI intenta conectar, de modo que
    # el detector de la prueba anterior detecta lo que debe detectar.
    _entorno(monkeypatch, "local")
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[CONTRASENA, CONTRASENA])
    intentos, registrar = _escuchar_conexiones()
    try:
        codigo = main(
            [],
            leer_visible=terminal.leer_visible,
            leer_oculto=terminal.leer_oculto,
            es_interactivo=lambda: True,
        )
    finally:
        event.remove(Engine, "do_connect", registrar)  # type: ignore[arg-type]

    assert codigo != 0
    assert "host-inexistente.invalid" in intentos
    salida = _salida(capsys)
    for prohibido in ("host-inexistente", "postgresql", "secreto", "@", CODIGO):
        assert prohibido not in salida


# --- Entrada ----------------------------------------------------------------------------------


def test_la_entrada_no_interactiva_se_rechaza_antes_de_pedir_nada(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch, interactivo=False)
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[CONTRASENA, CONTRASENA])

    codigo = escenario.ejecutar(terminal)

    assert codigo != 0
    assert "terminal interactiva" in _salida(capsys)
    assert (terminal.pedidos_visibles, terminal.pedidos_ocultos) == ([], [])
    assert escenario.aperturas == 0


@pytest.mark.parametrize("opcion", ["--contrasena", "--password"])
@pytest.mark.parametrize("forma", ["separada", "con_igual"])
def test_los_argumentos_de_contrasena_no_se_reconocen_ni_se_repiten(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], opcion: str, forma: str
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch)
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[CONTRASENA, CONTRASENA])
    argv = [opcion, CONTRASENA] if forma == "separada" else [f"{opcion}={CONTRASENA}"]

    codigo = escenario.ejecutar(terminal, argv)

    salida = _salida(capsys)
    assert codigo != 0
    assert "argumento" in salida
    assert CONTRASENA not in salida
    assert escenario.aperturas == 0
    assert (terminal.pedidos_visibles, terminal.pedidos_ocultos) == ([], [])


def test_las_dos_lecturas_de_la_contrasena_usan_la_lectura_oculta(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch)
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[CONTRASENA, CONTRASENA])

    codigo = escenario.ejecutar(terminal)

    assert codigo == 0, _salida(capsys)
    assert len(terminal.pedidos_ocultos) == 2
    # La lectura visible solo pidio el codigo y el email: ninguna lectura de contrasena.
    assert len(terminal.pedidos_visibles) == 2
    assert all("ontrase" not in pedido for pedido in terminal.pedidos_visibles)


def test_la_confirmacion_distinta_falla_sin_cambios(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch)
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[CONTRASENA, OTRA_CONTRASENA])

    codigo = escenario.ejecutar(terminal)

    salida = _salida(capsys)
    assert codigo != 0
    assert "no coinciden" in salida
    assert escenario.escrituras == []
    assert escenario.sesion.confirmaciones == 0
    assert CONTRASENA not in salida and OTRA_CONTRASENA not in salida


# --- Cuenta, credencial previa y reemplazo -----------------------------------------------------

HASH_PREVIO = HASHER_RAPIDO.hash("contrasena-previa-ficticia-1")


def test_una_cuenta_inexistente_falla_con_mensaje_generico_sin_pedir_la_contrasena(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch, cuenta_existe=False)
    terminal = Terminal(visibles=[CODIGO, "nadie@example.test"], ocultas=[CONTRASENA, CONTRASENA])

    codigo = escenario.ejecutar(terminal)

    salida = _salida(capsys)
    assert codigo != 0
    assert "no se encontró la cuenta indicada" in salida
    assert terminal.pedidos_ocultos == []
    assert escenario.escrituras == [] and escenario.sesion.confirmaciones == 0
    assert "nadie" not in salida and CODIGO not in salida


def test_sin_reemplazar_completa_solo_una_credencial_nula_con_un_hash_argon2id(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch, credencial=None)
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[CONTRASENA, CONTRASENA])

    codigo = escenario.ejecutar(terminal)

    assert codigo == 0
    ((consultorio_id, usuario_id, nueva, esperada),) = escenario.escrituras
    assert (consultorio_id, usuario_id) == (escenario.consultorio_id, escenario.usuario_id)
    assert esperada is None
    assert nueva.startswith("$argon2id$") and CONTRASENA not in nueva
    assert HASHER_RAPIDO.verify(nueva, CONTRASENA)
    assert escenario.revocaciones == []
    assert escenario.sesion.confirmaciones == 1
    assert _salida(capsys).strip() == "credencial establecida"


def test_con_credencial_y_sin_reemplazar_falla_mencionando_reemplazar_sin_cambios(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch, credencial=HASH_PREVIO)
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[CONTRASENA, CONTRASENA])

    codigo = escenario.ejecutar(terminal)

    assert codigo != 0
    assert "--reemplazar" in _salida(capsys)
    assert terminal.pedidos_ocultos == []
    assert escenario.escrituras == [] and escenario.revocaciones == []
    assert escenario.sesion.confirmaciones == 0


def test_el_reemplazo_confirmado_escribe_con_la_credencial_leida_y_revoca_sus_sesiones(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch, credencial=HASH_PREVIO)
    terminal = Terminal(
        visibles=[CODIGO, EMAIL, "REEMPLAZAR"], ocultas=[CONTRASENA, CONTRASENA]
    )

    codigo = escenario.ejecutar(terminal, ["--reemplazar"])

    assert codigo == 0, _salida(capsys)
    ((_, _, nueva, esperada),) = escenario.escrituras
    assert esperada == HASH_PREVIO
    assert HASHER_RAPIDO.verify(nueva, CONTRASENA)
    ((consultorio_id, usuario_id, _),) = escenario.revocaciones
    assert (consultorio_id, usuario_id) == (escenario.consultorio_id, escenario.usuario_id)
    assert escenario.sesion.confirmaciones == 1


def test_el_reemplazo_informa_solo_la_cantidad_de_sesiones_revocadas(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch, credencial=HASH_PREVIO)
    terminal = Terminal(
        visibles=[CODIGO, EMAIL, "REEMPLAZAR"], ocultas=[CONTRASENA, CONTRASENA]
    )

    escenario.ejecutar(terminal, ["--reemplazar"])

    assert _salida(capsys).strip() == "credencial reemplazada; sesiones revocadas: 2"


@pytest.mark.parametrize("respuesta", ["no", "", "reemplazar", " REEMPLAZAR"])
def test_el_reemplazo_sin_la_confirmacion_exacta_falla_sin_cambios(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], respuesta: str
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch, credencial=HASH_PREVIO)
    terminal = Terminal(visibles=[CODIGO, EMAIL, respuesta], ocultas=[CONTRASENA, CONTRASENA])

    codigo = escenario.ejecutar(terminal, ["--reemplazar"])

    assert codigo != 0
    assert "no confirmado" in _salida(capsys)
    assert escenario.escrituras == [] and escenario.revocaciones == []
    assert escenario.sesion.confirmaciones == 0


def test_si_la_credencial_cambio_desde_la_lectura_no_se_confirma_ni_se_revocan_sesiones(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch, credencial=HASH_PREVIO)
    monkeypatch.setattr(acceso_admin, "escribir_credencial", lambda *a: False)
    terminal = Terminal(
        visibles=[CODIGO, EMAIL, "REEMPLAZAR"], ocultas=[CONTRASENA, CONTRASENA]
    )

    codigo = escenario.ejecutar(terminal, ["--reemplazar"])

    assert codigo != 0
    assert "cambió" in _salida(capsys)
    assert escenario.revocaciones == []
    assert escenario.sesion.confirmaciones == 0
    assert escenario.sesion.reversiones == 1


# --- Politica de contrasenas nuevas (DD-16) -------------------------------------------------------

FRASE_LARGA = ("zrtqplmvkw" * 13)[:129]
RECHAZADAS = [
    pytest.param("zrtqplmvkwjb48", "15", id="14-puntos-de-codigo"),
    pytest.param(FRASE_LARGA, "128", id="129-puntos-de-codigo"),
    pytest.param(" " * 20, "espacios", id="solo-espacios"),
    pytest.param("123456789012345", "común", id="comun"),
    pytest.param("QWERTYUIOPasdfgh", "común", id="comun-con-otras-mayusculas"),
    pytest.param("mi-clave-ficticio-a-2026", "término del contexto", id="codigo"),
    pytest.param("persona.ficticia-de-verano", "término del contexto", id="parte-local"),
    pytest.param("verano-ficticia-2026-largo", "término del contexto", id="token-de-la-parte-local"),
    pytest.param("TURNOS de la tarde 2026", "término del contexto", id="turnos"),
    pytest.param("odontología-del-barrio", "término del contexto", id="odontologia-con-diacritico"),
    pytest.param("mañana-PÉRSONA-libre-26", "término del contexto", id="persona-sin-diacriticos"),
    pytest.param("O.D.O.N.T.O.L.O.G.I.A-2026-x", "término del contexto", id="con-separadores"),
    pytest.param("mi consultorio preferido 2026", "término del contexto", id="consultorio-fijo"),
]
ACEPTADAS = [
    pytest.param("zrtqplmvkwjb489", id="15-puntos-de-codigo"),
    pytest.param(FRASE_LARGA[:128], id="128-puntos-de-codigo"),
    pytest.param("ﬁ" * 8 + "-2026", id="ligaduras-21-tras-NFKC"),
    pytest.param("una frase larga con ñandú 2026", id="espacios-y-unicode"),
    pytest.param("mi example de test largo 2026", id="terminos-genericos-del-dominio"),
    pytest.param(CONTRASENA, id="contrasena-de-las-specs"),
]


@pytest.mark.parametrize(("contrasena", "fragmento"), RECHAZADAS)
def test_una_contrasena_que_incumple_la_politica_falla_sin_cambios_y_sin_repetirla(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    contrasena: str,
    fragmento: str,
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch)
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[contrasena, contrasena])

    codigo = escenario.ejecutar(terminal)

    salida = _salida(capsys)
    assert codigo != 0
    assert fragmento in salida
    assert escenario.escrituras == [] and escenario.sesion.confirmaciones == 0
    assert contrasena not in salida
    assert (contrasena.strip() or contrasena) not in salida  # sin espacios ni recortada
    for prohibido in ("ficticio", "persona", CODIGO, EMAIL):
        assert prohibido not in salida.lower()


@pytest.mark.parametrize("contrasena", ACEPTADAS)
def test_una_contrasena_que_cumple_la_politica_se_acepta(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], contrasena: str
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch)
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[contrasena, contrasena])

    codigo = escenario.ejecutar(terminal)

    assert codigo == 0, _salida(capsys)
    ((_, _, nueva, _),) = escenario.escrituras
    assert HASHER_RAPIDO.verify(nueva, unicodedata.normalize("NFKC", contrasena))


@pytest.mark.parametrize(
    "contrasena", ["mi-sonrisas-secreta-2026", "marta-y-su-guitarra-2026"]
)
def test_los_tokens_del_nombre_del_consultorio_y_del_usuario_se_rechazan(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], contrasena: str
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(
        monkeypatch,
        consultorio_nombre="Clinica Sonrisas del Valle",
        nombre_usuario="Marta Lopez",
    )
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[contrasena, contrasena])

    codigo = escenario.ejecutar(terminal)

    salida = _salida(capsys)
    assert codigo != 0
    assert "término del contexto" in salida
    assert escenario.escrituras == []
    assert "sonrisas" not in salida.lower() and "marta" not in salida.lower()


def test_la_politica_se_evalua_antes_que_la_confirmacion_del_reemplazo(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch, credencial=HASH_PREVIO)
    terminal = Terminal(visibles=[CODIGO, EMAIL, "REEMPLAZAR"], ocultas=["corta", "corta"])

    codigo = escenario.ejecutar(terminal, ["--reemplazar"])

    assert codigo != 0
    assert len(terminal.pedidos_visibles) == 2  # no llego a pedir la confirmacion
    assert escenario.revocaciones == [] and escenario.escrituras == []


# --- 6.5 Revision local de hashes (`--revisar-hashes`, DD-32) -------------------------------------

from app.auth.acceso_admin import CredencialParaRevision  # noqa: E402


def _hash(**parametros) -> str:
    base = dict(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID)
    base.update(parametros)
    return PasswordHasher(**base).hash(CONTRASENA)


def _siete_cuentas() -> list[CredencialParaRevision]:
    credenciales = [
        _hash(),  # vigente
        _hash(time_cost=2),  # parametros anteriores
        _hash(memory_cost=19456),  # parametros anteriores
        _hash(type=Type.I),  # formato no admitido
        _hash(type=Type.D),  # formato no admitido
        "esto no es un hash",  # formato no admitido
        None,  # sin credencial
    ]
    return [CredencialParaRevision(uuid.uuid4(), uuid.uuid4(), c) for c in credenciales]


def _revision(monkeypatch, cuentas: list[CredencialParaRevision] | None = None, **opciones):
    escenario = Escenario(monkeypatch, **opciones)
    filas = _siete_cuentas() if cuentas is None else cuentas
    monkeypatch.setattr(acceso_admin, "listar_credenciales_para_revision", lambda sesion: filas)
    return escenario, filas


def test_revisar_y_reemplazar_son_excluyentes_y_fallan_antes_de_conectar(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario, _ = _revision(monkeypatch)
    terminal = Terminal(visibles=[CODIGO, EMAIL], ocultas=[CONTRASENA, CONTRASENA])
    intentos, registrar = _escuchar_conexiones()
    try:
        codigo = escenario.ejecutar(terminal, ["--revisar-hashes", "--reemplazar"])
    finally:
        event.remove(Engine, "do_connect", registrar)  # type: ignore[arg-type]

    assert codigo == 1 and intentos == []
    assert escenario.aperturas == 0
    assert (terminal.pedidos_visibles, terminal.pedidos_ocultos) == ([], [])
    assert "argumento" in _salida(capsys)


def test_revisar_con_app_env_test_se_rechaza_sin_conectar(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "test")
    escenario, _ = _revision(monkeypatch)

    codigo = escenario.ejecutar(Terminal(), ["--revisar-hashes"])

    assert codigo == 1 and escenario.aperturas == 0
    assert "APP_ENV" in _salida(capsys)


def test_revisar_sin_terminal_se_rechaza_sin_conectar(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario, _ = _revision(monkeypatch, interactivo=False)

    codigo = escenario.ejecutar(Terminal(), ["--revisar-hashes"])

    assert codigo == 1 and escenario.aperturas == 0
    assert "terminal interactiva" in _salida(capsys)


def test_revisar_sin_url_de_administracion_la_menciona_sin_conectar(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    monkeypatch.delenv("DATABASE_MIGRATION_URL")
    intentos, registrar = _escuchar_conexiones()
    try:
        codigo = main(["--revisar-hashes"], es_interactivo=lambda: True)
    finally:
        event.remove(Engine, "do_connect", registrar)  # type: ignore[arg-type]

    salida = _salida(capsys)
    assert codigo == 1 and intentos == []
    assert "DATABASE_MIGRATION_URL" in salida
    for prohibido in ("host-api", "postgresql", "secreto", "@"):
        assert prohibido not in salida


def test_la_revision_clasifica_siete_cuentas_y_lista_las_cinco_a_restablecer(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario, filas = _revision(monkeypatch)
    terminal = Terminal()

    codigo = escenario.ejecutar(terminal, ["--revisar-hashes"])

    salida = _salida(capsys)
    assert codigo == 0
    lineas = salida.splitlines()
    assert lineas[:4] == [
        "hashes vigentes: 1",
        "hashes con parámetros anteriores: 2",
        "hashes con formato no admitido: 3",
        "usuarios sin credencial: 1",
    ]
    a_restablecer = sorted(
        f"restablecer: consultorio {f.consultorio_id} usuario {f.usuario_id}"
        for f in filas[1:6]
    )
    assert sorted(lineas[4:]) == a_restablecer
    assert f"{filas[0].usuario_id}" not in salida and f"{filas[6].usuario_id}" not in salida
    assert (terminal.pedidos_visibles, terminal.pedidos_ocultos) == ([], [])


def test_la_revision_no_escribe_ni_confirma_y_siempre_revierte_y_cierra(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario, _ = _revision(monkeypatch)

    codigo = escenario.ejecutar(Terminal(), ["--revisar-hashes"])

    assert codigo == 0
    assert (escenario.sesion.confirmaciones, escenario.sesion.reversiones, escenario.sesion.cierres) == (0, 1, 1)
    assert escenario.escrituras == [] and escenario.revocaciones == []


def test_la_salida_de_la_revision_no_contiene_datos_sensibles(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario, _ = _revision(monkeypatch)

    escenario.ejecutar(Terminal(), ["--revisar-hashes"])

    salida = _salida(capsys)
    for prohibido in ("$argon2", "@", "ficticio-a", "postgresql", "esto no es un hash"):
        assert prohibido not in salida


def test_la_revision_sin_cuentas_a_restablecer_no_lista_ninguna(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    cuentas = [CredencialParaRevision(uuid.uuid4(), uuid.uuid4(), _hash()) for _ in range(2)]
    cuentas.append(CredencialParaRevision(uuid.uuid4(), uuid.uuid4(), None))
    escenario, _ = _revision(monkeypatch, cuentas)

    codigo = escenario.ejecutar(Terminal(), ["--revisar-hashes"])

    assert codigo == 0
    assert _salida(capsys).splitlines() == [
        "hashes vigentes: 2",
        "hashes con parámetros anteriores: 0",
        "hashes con formato no admitido: 0",
        "usuarios sin credencial: 1",
    ]


def test_un_fallo_al_listar_se_informa_con_mensaje_fijo_y_revierte(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _entorno(monkeypatch, "local")
    escenario = Escenario(monkeypatch)

    def romper(sesion):
        raise RuntimeError("detalle interno con postgresql://x@y")

    monkeypatch.setattr(acceso_admin, "listar_credenciales_para_revision", romper)

    codigo = escenario.ejecutar(Terminal(), ["--revisar-hashes"])

    salida = _salida(capsys)
    assert codigo == 1
    assert "detalle interno" not in salida and "postgresql" not in salida
    assert (escenario.sesion.confirmaciones, escenario.sesion.reversiones) == (0, 1)

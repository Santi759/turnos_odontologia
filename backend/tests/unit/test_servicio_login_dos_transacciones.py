"""Login en dos transacciones con dos `Session` espia (5.5, 5.6; DD-26, DD-27), sin base.

Las funciones de acceso se sustituyen: lo que se verifica es el ORDEN, el rol de cada paso, que
no haya T2 en rechazos, 429 ni 503, y la traduccion del agotamiento del pool de login.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from app.auth import acceso_login, acceso_previo, intentos, servicio as modulo_servicio
from app.auth.concurrencia import LimitadorArgon2, ServicioOcupado
from app.auth.cuenta import Cuenta
from app.auth.servicio import (
    ConfigAuth,
    LoginBloqueado,
    LoginRechazado,
    ServicioAuth,
)

AHORA = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
CONSULTORIO = uuid.UUID("0199a000-0000-7000-8000-00000000000a")
USUARIO = uuid.UUID("0199a000-0000-7000-8000-0000000000a1")


class Registro:
    def __init__(self) -> None:
        self.eventos: list[str] = []


class SesionEspia:
    """Cuenta confirmaciones y reversiones; opcionalmente falla al primer `execute`."""

    def __init__(self, nombre: str, registro: Registro, fallo_al_conectar: BaseException | None = None):
        self.nombre = nombre
        self.registro = registro
        self.fallo_al_conectar = fallo_al_conectar
        self.info: dict = {}

    def execute(self, *_a, **_k):
        if self.fallo_al_conectar is not None:
            raise self.fallo_al_conectar

    def commit(self) -> None:
        self.registro.eventos.append(f"{self.nombre}:commit")

    def rollback(self) -> None:
        self.registro.eventos.append(f"{self.nombre}:rollback")


class VerificadorEspia:
    def __init__(self, registro: Registro, correcta: bool = True):
        self.registro = registro
        self.correcta = correcta
        self.llamadas = 0

    def verificar(self, contrasena, almacenado):
        self.llamadas += 1
        self.registro.eventos.append("verificar")
        return self.correcta

    def hashear(self, *_a):
        raise AssertionError("el login no hashea")

    def necesita_rehash(self, *_a):
        raise AssertionError("el login no decide rehash")


class Reloj:
    def ahora(self):
        return AHORA


def _cuenta(**cambios) -> Cuenta:
    base = dict(
        usuario_id=USUARIO,
        consultorio_id=CONSULTORIO,
        email="persona.ficticia@example.test",
        nombre="Persona Ficticia",
        rol="secretaria",
        credencial="hash-ficticio",
        usuario_activo=True,
        consultorio_nombre="Consultorio Ficticio",
        consultorio_activo=True,
    )
    base.update(cambios)
    return Cuenta(**base)


@pytest.fixture
def entorno(monkeypatch):
    registro = Registro()
    estado = {"cuenta": _cuenta(), "bloqueo": None}

    def tomar_locks(db, *_a):
        db.execute()  # primera consulta de T1: aqui se pide la conexion del pool
        registro.eventos.append(f"{db.nombre}:locks")

    monkeypatch.setattr(intentos, "tomar_locks", tomar_locks)
    monkeypatch.setattr(intentos, "bloqueo_vigente", lambda db, *a: estado["bloqueo"])
    monkeypatch.setattr(acceso_login, "buscar_cuenta", lambda db, *a: (registro.eventos.append(f"{db.nombre}:buscar"), estado["cuenta"])[1])
    monkeypatch.setattr(acceso_login, "registrar_fallo", lambda db, *a: registro.eventos.append(f"{db.nombre}:registrar_fallo"))
    monkeypatch.setattr(acceso_login, "limpiar_intentos", lambda db, *a: registro.eventos.append(f"{db.nombre}:limpiar_intentos"))
    monkeypatch.setattr(acceso_login, "descartar_fallos_de_cuenta", lambda db, *a: registro.eventos.append(f"{db.nombre}:descartar"))
    monkeypatch.setattr(modulo_servicio, "fijar_consultorio_de_login", lambda db, c: registro.eventos.append(f"{db.nombre}:fijar_contexto"))
    monkeypatch.setattr(acceso_previo, "limpiar_sesiones", lambda db, *a: registro.eventos.append(f"{db.nombre}:limpiar_sesiones"))
    monkeypatch.setattr(acceso_previo, "resolver_sesion", lambda db, *a: None)
    monkeypatch.setattr(
        acceso_previo,
        "crear_sesion",
        lambda db, *a: (registro.eventos.append(f"{db.nombre}:crear_sesion"), uuid.uuid4())[1],
    )
    verificador = VerificadorEspia(registro)
    servicio = ServicioAuth(
        ConfigAuth(clave_hmac=b"k" * 48, minutos_inactividad=30, horas_maximas=12),
        Reloj(),
        verificador,
        LimitadorArgon2(),
    )
    return servicio, registro, estado, verificador


def _login(servicio, registro, **sesiones):
    db_login = sesiones.get("db_login") or SesionEspia("login", registro)
    db = sesiones.get("db") or SesionEspia("app", registro)
    return servicio.iniciar_sesion(
        db_login,
        db,
        codigo="Consultorio-A",
        email="Persona.Ficticia@example.test",
        contrasena="contrasena-ficticia",
        ip_normalizada="203.0.113.7",
    )


def test_exito_t1_se_confirma_antes_de_abrir_t2_y_el_verificador_corre_una_vez(entorno):
    servicio, registro, _estado, verificador = entorno

    iniciada = _login(servicio, registro)

    eventos = registro.eventos
    assert eventos.index("login:commit") < eventos.index("app:fijar_contexto")
    assert eventos.index("verificar") > eventos.index("login:locks")  # con los locks tomados
    assert eventos.index("verificar") < eventos.index("login:descartar")
    assert verificador.llamadas == 1
    assert eventos[-1] == "app:commit"
    assert iniciada.rol == "secretaria"


def test_el_orden_de_t1_y_t2_es_el_del_diseno(entorno):
    servicio, registro, *_ = entorno

    _login(servicio, registro)

    assert registro.eventos == [
        "login:locks",
        "login:buscar",
        "verificar",
        "login:descartar",
        "login:limpiar_intentos",
        "login:commit",
        "app:fijar_contexto",
        "app:limpiar_sesiones",
        "app:crear_sesion",
        "app:commit",
    ]


def test_el_rechazo_registra_el_fallo_y_nunca_abre_t2(entorno):
    servicio, registro, _estado, verificador = entorno
    verificador.correcta = False

    with pytest.raises(LoginRechazado):
        _login(servicio, registro)

    assert not any(e.startswith("app:") for e in registro.eventos)
    assert "login:registrar_fallo" in registro.eventos
    assert verificador.llamadas == 1


@pytest.mark.parametrize(
    "cambios", [{"usuario_activo": False}, {"consultorio_activo": False}, {"credencial": None}]
)
def test_cuenta_no_utilizable_verifica_una_vez_y_rechaza_sin_t2(entorno, cambios):
    servicio, registro, estado, verificador = entorno
    estado["cuenta"] = _cuenta(**cambios)
    verificador.correcta = cambios.get("credencial", "x") is not None

    with pytest.raises(LoginRechazado):
        _login(servicio, registro)

    assert verificador.llamadas == 1
    assert not any(e.startswith("app:") for e in registro.eventos)


def test_cuenta_inexistente_verifica_una_vez_contra_el_hash_ficticio(entorno):
    servicio, registro, estado, verificador = entorno
    estado["cuenta"] = None

    with pytest.raises(LoginRechazado):
        _login(servicio, registro)

    assert verificador.llamadas == 1
    assert "login:registrar_fallo" in registro.eventos
    assert not any(e.startswith("app:") for e in registro.eventos)


def test_el_bloqueo_responde_429_sin_verificar_ni_abrir_t2(entorno):
    servicio, registro, estado, verificador = entorno
    estado["bloqueo"] = 42

    with pytest.raises(LoginBloqueado) as info:
        _login(servicio, registro)

    assert info.value.retry_after == 42
    assert verificador.llamadas == 0
    assert registro.eventos == ["login:locks", "login:commit", "login:rollback"]
    assert not any(e.startswith("app:") for e in registro.eventos)


def test_sin_cupo_de_argon2_hay_503_sin_fallo_ni_t2(entorno):
    servicio, registro, *_ = entorno
    servicio.limitador = LimitadorArgon2(cupos=1, espera_segundos=0)
    assert servicio.limitador.semaforo.acquire(timeout=0)  # el unico cupo, retenido

    with pytest.raises(ServicioOcupado):
        _login(servicio, registro)

    assert "login:registrar_fallo" not in registro.eventos
    assert "login:rollback" in registro.eventos
    assert not any(e.startswith("app:") for e in registro.eventos)


def test_pool_de_login_agotado_se_traduce_a_servicio_ocupado_con_rollback(entorno):
    servicio, registro, _estado, verificador = entorno
    db_login = SesionEspia("login", registro, fallo_al_conectar=PoolTimeoutError("pool agotado"))

    with pytest.raises(ServicioOcupado):
        _login(servicio, registro, db_login=db_login)

    assert registro.eventos == ["login:rollback"]
    assert verificador.llamadas == 0


def test_pool_de_turnos_app_agotado_en_t2_sigue_siendo_un_error_generico(entorno, monkeypatch):
    servicio, registro, *_ = entorno

    def agotado(db, c):
        raise PoolTimeoutError("pool agotado")

    monkeypatch.setattr(modulo_servicio, "fijar_consultorio_de_login", agotado)

    with pytest.raises(PoolTimeoutError):
        _login(servicio, registro)

    assert "app:rollback" in registro.eventos
    assert "login:commit" in registro.eventos  # T1 persiste (DD-27)


def test_fallo_en_t2_revierte_t2_y_conserva_t1(entorno, monkeypatch):
    servicio, registro, *_ = entorno

    def falla(db, *a):
        raise RuntimeError("fallo inyectado")

    monkeypatch.setattr(acceso_previo, "crear_sesion", falla)

    with pytest.raises(RuntimeError):
        _login(servicio, registro)

    assert registro.eventos.count("login:commit") == 1
    assert registro.eventos[-1] == "app:rollback"
    assert "app:commit" not in registro.eventos

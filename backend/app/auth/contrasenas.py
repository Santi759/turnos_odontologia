"""Hash y verificacion de contrasenas con Argon2id (DD-15, DD-16)."""

import secrets
import unicodedata
from collections.abc import Iterable
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from argon2 import PasswordHasher, Type, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError

TIME_COST = 3
MEMORY_COST_KIB = 65536
PARALLELISM = 4
HASH_LEN = 32
SALT_LEN = 16
PREFIJO_HASH = f"$argon2id$v=19$m={MEMORY_COST_KIB},t={TIME_COST},p={PARALLELISM}$"
_TIPO_ADMITIDO = Type.ID

RUTA_RECURSOS = Path(__file__).resolve().parent / "recursos"
LONGITUD_MINIMA = 15
LONGITUD_MAXIMA = 128
LONGITUD_MINIMA_DE_TERMINO = 4
TERMINOS_FIJOS = frozenset({"turnos", "odontologia", "consultorio", "turnosodontologia"})


class Hasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, hash: str, password: str) -> bool: ...  # noqa: A002
    def check_needs_rehash(self, hash: str) -> bool: ...  # noqa: A002


def normalizar_contrasena(contrasena: str) -> str:
    """Unica normalizacion de contrasenas: NFKC (sin recortar ni cambiar mayusculas)."""
    return unicodedata.normalize("NFKC", contrasena)


def crear_hasher() -> PasswordHasher:
    return PasswordHasher(
        time_cost=TIME_COST,
        memory_cost=MEMORY_COST_KIB,
        parallelism=PARALLELISM,
        hash_len=HASH_LEN,
        salt_len=SALT_LEN,
        type=_TIPO_ADMITIDO,
    )


def _es_formato_admitido(almacenado: object) -> bool:
    """Solo cadenas PHC `$argon2id$` que la libreria puede analizar."""
    if not isinstance(almacenado, str) or not almacenado.startswith("$argon2id$"):
        return False
    try:
        extract_parameters(almacenado)
    except InvalidHashError:
        return False
    return True


class VerificadorContrasenas:
    """Hash y verificacion; el hash ficticio se calcula una vez al construirlo."""

    def __init__(self, hasher: Hasher | None = None) -> None:
        self._hasher: Hasher = hasher if hasher is not None else crear_hasher()
        # Contrasena aleatoria descartada: el hash ficticio no corresponde a ninguna cuenta.
        self.hash_ficticio: str = self._hasher.hash(_contrasena_aleatoria())

    def hashear(self, contrasena: str) -> str:
        return self._hasher.hash(normalizar_contrasena(contrasena))

    def verificar(self, contrasena: str, almacenado: str | None) -> bool:
        """Verifica tras NFKC. Un formato no admitido usa el hash ficticio una vez y falla."""
        normalizada = normalizar_contrasena(contrasena)
        if not _es_formato_admitido(almacenado):
            self._verificar(self.hash_ficticio, normalizada)  # costo uniforme; el resultado se descarta
            return False
        assert almacenado is not None
        return self._verificar(almacenado, normalizada)

    def necesita_rehash(self, almacenado: str | None) -> bool:
        if not _es_formato_admitido(almacenado):
            return False
        assert almacenado is not None
        return self._hasher.check_needs_rehash(almacenado)

    def _verificar(self, hash_: str, contrasena: str) -> bool:
        try:
            return bool(self._hasher.verify(hash_, contrasena))
        except (VerificationError, InvalidHashError):
            return False


def _contrasena_aleatoria() -> str:
    return secrets.token_urlsafe(32)


# --- Politica de contrasenas nuevas (DD-16) -------------------------------


class ReglaContrasena(str, Enum):
    LONGITUD = "longitud"
    SOLO_ESPACIOS = "solo_espacios"
    COMUN = "comun"
    CONTEXTO = "contexto"


_MENSAJES = {
    ReglaContrasena.LONGITUD: f"La contrasena debe tener entre {LONGITUD_MINIMA} y {LONGITUD_MAXIMA} caracteres.",
    ReglaContrasena.SOLO_ESPACIOS: "La contrasena no puede estar formada solo por espacios en blanco.",
    ReglaContrasena.COMUN: "La contrasena es demasiado comun.",
    ReglaContrasena.CONTEXTO: "La contrasena contiene datos de la cuenta o del sistema.",
}


class ContrasenaRechazada(ValueError):
    """Contrasena nueva rechazada; el mensaje nombra la regla sin repetir la contrasena."""

    def __init__(self, regla: ReglaContrasena) -> None:
        super().__init__(_MENSAJES[regla])
        self.regla = regla


def _sin_marcas(texto: str) -> str:
    """Pasos 1 a 3 de la forma compacta: NFKC, casefold, NFKD sin marcas combinantes."""
    descompuesto = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", texto).casefold())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def forma_compacta(texto: str) -> str:
    """Forma compacta (DD-16): solo caracteres alfanumericos tras NFKC, casefold y NFKD sin marcas."""
    return "".join(c for c in _sin_marcas(texto) if c.isalnum())


def _tokens(texto: str) -> list[str]:
    """Secuencias maximales de caracteres alfanumericos del texto sin marcas."""
    tokens: list[str] = []
    actual: list[str] = []
    for caracter in _sin_marcas(texto):
        if caracter.isalnum():
            actual.append(caracter)
        elif actual:
            tokens.append("".join(actual))
            actual = []
    if actual:
        tokens.append("".join(actual))
    return tokens


def _leer_lista(nombre: str) -> list[str]:
    lineas = (RUTA_RECURSOS / nombre).read_text(encoding="utf-8").splitlines()
    return [linea for linea in lineas if linea and not linea.startswith("#")]


@lru_cache(maxsize=1)
def _contrasenas_comunes() -> frozenset[str]:
    return frozenset(forma_compacta(entrada) for entrada in _leer_lista("contrasenas_comunes.txt")) - {""}


@lru_cache(maxsize=1)
def _terminos_genericos() -> frozenset[str]:
    return frozenset(forma_compacta(entrada) for entrada in _leer_lista("terminos_genericos.txt")) - {""}


def _largos(terminos: Iterable[str]) -> set[str]:
    return {t for t in terminos if len(t) >= LONGITUD_MINIMA_DE_TERMINO}


def terminos_de_contexto(
    *, codigo: str, email: str, nombre_consultorio: str, nombre_usuario: str
) -> frozenset[str]:
    """Terminos (en forma compacta) que una contrasena nueva no puede contener (DD-16, PC-06)."""
    genericos = _terminos_genericos()
    parte_local, _, dominio = email.rpartition("@") if "@" in email else (email, "", "")
    terminos: set[str] = {forma_compacta(codigo), forma_compacta(parte_local)}  # (a) y (b)
    terminos |= _largos(_tokens(parte_local))  # (b)
    etiquetas = {forma_compacta(etiqueta) for etiqueta in dominio.split(".")}
    terminos |= _largos(etiquetas) - genericos  # (c)
    for nombre in (nombre_consultorio, nombre_usuario):  # (d)
        terminos |= _largos(_tokens(nombre)) - genericos
    terminos |= TERMINOS_FIJOS  # (e): la lista generica no los elimina
    terminos.discard("")
    return frozenset(terminos)


def validar_contrasena_nueva(contrasena: str, terminos_contexto: Iterable[str] = ()) -> None:
    """Aplica la politica a una contrasena nueva; lanza `ContrasenaRechazada` si no la cumple."""
    normalizada = normalizar_contrasena(contrasena)
    if not LONGITUD_MINIMA <= len(normalizada) <= LONGITUD_MAXIMA:
        raise ContrasenaRechazada(ReglaContrasena.LONGITUD)
    if normalizada.isspace():
        raise ContrasenaRechazada(ReglaContrasena.SOLO_ESPACIOS)
    compacta = forma_compacta(normalizada)
    if compacta in _contrasenas_comunes():
        raise ContrasenaRechazada(ReglaContrasena.COMUN)
    if any(termino in compacta for termino in set(terminos_contexto) if termino):
        raise ContrasenaRechazada(ReglaContrasena.CONTEXTO)

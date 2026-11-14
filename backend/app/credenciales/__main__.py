"""Comando local de credenciales (DD-22, DA-07, DA-10).

Establece (o reemplaza) la credencial de un usuario existente, identificado por el codigo de su
consultorio y su email. Es el unico medio de obtener credenciales en C-03.

Uso (solo desarrollo local; requiere una terminal interactiva):

    docker compose run --rm -it api python -m app.credenciales [--reemplazar | --revisar-hashes]

Con `--revisar-hashes` (excluyente con `--reemplazar`, DD-32) no pide datos: en una transaccion de solo
lectura clasifica la credencial de todos los usuarios (vigente, parametros anteriores, formato no
admitido, sin credencial) e informa cantidades y los `id` de consultorio y usuario de las cuentas a
restablecer. Nunca modifica filas ni muestra hashes, emails ni codigos.

Sin `--revisar-hashes`, el comando pide, en este orden: el codigo del consultorio, el email, la contrasena nueva dos veces
(lectura oculta con `getpass`) y, con `--reemplazar`, escribir `REEMPLAZAR`.

Reglas:
- Solo corre con `APP_ENV=local` y solo sobre `DATABASE_MIGRATION_URL`; con otro entorno falla antes de
  abrir ninguna conexion.
- La contrasena nunca se acepta por argumentos, variables de entorno, archivos ni entrada redirigida:
  el unico argumento que existe es `--reemplazar` y cualquier otro falla sin repetir lo recibido.
- Por defecto solo completa una credencial nula. `--reemplazar` es una accion administrativa
  explicita: exige confirmacion, reemplaza la credencial y revoca todas las sesiones del usuario.
- Se aplica la politica de contrasenas nuevas (15 a 128 caracteres tras NFKC, sin contrasenas comunes
  ni terminos del contexto) y se guarda un hash Argon2id.
- La salida solo contiene textos fijos y cantidades: nunca la contrasena, el hash, el email, el
  codigo del consultorio ni URLs de conexion (X1).
"""

import getpass
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import acceso_admin
from app.auth.cuenta import Cuenta
from app.auth.contrasenas import (
    ContrasenaRechazada,
    Hasher,
    EstadoHash,
    ReglaContrasena,
    clasificar_hash,
    crear_hasher,
    normalizar_contrasena,
    terminos_de_contexto,
    validar_contrasena_nueva,
)
from app.auth.reloj import Reloj, RelojSistema
from app.core.config import Settings, cargar_configuracion
from app.core.database import AdministracionNoConfigurada, abrir_sesion_de_administracion
from app.core.linea_de_comandos import AnalizadorSinEco, ArgumentosInvalidos

PALABRA_DE_CONFIRMACION = "REEMPLAZAR"

# Un texto fijo por regla: nunca repite la contrasena ni el termino que la rechazo (X1).
MENSAJES_DE_POLITICA = {
    ReglaContrasena.LONGITUD: "la contraseña debe tener entre 15 y 128 caracteres",
    ReglaContrasena.SOLO_ESPACIOS: "la contraseña no puede estar formada solo por espacios",
    ReglaContrasena.COMUN: "la contraseña es una contraseña común",
    ReglaContrasena.CONTEXTO: "la contraseña contiene un término del contexto",
}


class Fallo(Exception):
    """Fin anticipado con un mensaje fijo (sin datos sensibles) y codigo de salida 1."""


def _abrir_sesion_por_defecto(settings: Settings) -> Session:
    return abrir_sesion_de_administracion(settings)


def _stdin_es_terminal() -> bool:
    return sys.stdin.isatty()


@dataclass(frozen=True, slots=True)
class Opciones:
    reemplazar: bool
    revisar_hashes: bool


def _analizar(argv: Sequence[str]) -> Opciones:
    """Opciones del comando; cualquier otro argumento o la combinacion excluyente falla sin eco."""
    analizador = AnalizadorSinEco(prog="python -m app.credenciales")
    grupo = analizador.add_mutually_exclusive_group()
    grupo.add_argument("--reemplazar", action="store_true")
    grupo.add_argument("--revisar-hashes", action="store_true")
    argumentos = analizador.parse_args(list(argv))
    return Opciones(reemplazar=argumentos.reemplazar, revisar_hashes=argumentos.revisar_hashes)


def _validar_politica(contrasena: str, cuenta: Cuenta, codigo: str) -> None:
    terminos = terminos_de_contexto(
        codigo=codigo.strip().lower(),
        email=cuenta.email,
        nombre_consultorio=cuenta.consultorio_nombre,
        nombre_usuario=cuenta.nombre,
    )
    try:
        validar_contrasena_nueva(contrasena, terminos)
    except ContrasenaRechazada as rechazo:
        raise Fallo(MENSAJES_DE_POLITICA[rechazo.regla]) from None


def _pedir_contrasena(
    leer_oculto: Callable[[str], str], cuenta: Cuenta, codigo: str
) -> str:
    primera = leer_oculto("Contrasena nueva: ")
    segunda = leer_oculto("Repita la contrasena: ")
    if primera != segunda:
        raise Fallo("las contrasenas no coinciden")
    _validar_politica(primera, cuenta, codigo)
    return primera


def _establecer(
    sesion: Session,
    cuenta: Cuenta,
    contrasena: str,
    *,
    reemplazar: bool,
    hasher: Hasher,
    reloj: Reloj,
) -> str:
    """Escribe la credencial (con control optimista) y, al reemplazar, revoca las sesiones."""
    nueva = hasher.hash(normalizar_contrasena(contrasena))
    if not acceso_admin.escribir_credencial(
        sesion, cuenta.consultorio_id, cuenta.usuario_id, nueva, cuenta.credencial
    ):
        raise Fallo("la credencial cambió desde que se leyó; reintente")
    if not reemplazar:
        return "credencial establecida"
    revocadas = acceso_admin.revocar_sesiones_de_usuario(
        sesion, cuenta.consultorio_id, cuenta.usuario_id, reloj.ahora()
    )
    return f"credencial reemplazada; sesiones revocadas: {revocadas}"


def _ejecutar(
    sesion: Session,
    codigo: str,
    email: str,
    *,
    reemplazar: bool,
    leer_visible: Callable[[str], str],
    leer_oculto: Callable[[str], str],
    hasher: Hasher,
    reloj: Reloj,
) -> str:
    cuenta = acceso_admin.buscar_cuenta(sesion, codigo, email)
    if cuenta is None:
        raise Fallo("no se encontró la cuenta indicada")
    if cuenta.credencial is not None and not reemplazar:
        raise Fallo("el usuario ya tiene una credencial; use --reemplazar para cambiarla")
    contrasena = _pedir_contrasena(leer_oculto, cuenta, codigo)
    if reemplazar:
        respuesta = leer_visible(f"Escriba {PALABRA_DE_CONFIRMACION} para confirmar: ")
        if respuesta != PALABRA_DE_CONFIRMACION:
            raise Fallo("reemplazo no confirmado")
    return _establecer(
        sesion, cuenta, contrasena, reemplazar=reemplazar, hasher=hasher, reloj=reloj
    )


def _revisar_hashes(sesion: Session) -> list[str]:
    """Informe de solo lectura (DD-32): cantidades por clase y `id` de las cuentas a restablecer."""
    cantidades = dict.fromkeys(EstadoHash, 0)
    a_restablecer: list[str] = []
    for fila in acceso_admin.listar_credenciales_para_revision(sesion):
        estado = clasificar_hash(fila.credencial)
        cantidades[estado] += 1
        if estado in (EstadoHash.PARAMETROS_ANTERIORES, EstadoHash.FORMATO_NO_ADMITIDO):
            a_restablecer.append(
                f"restablecer: consultorio {fila.consultorio_id} usuario {fila.usuario_id}"
            )
    return [
        f"hashes vigentes: {cantidades[EstadoHash.VIGENTE]}",
        f"hashes con parámetros anteriores: {cantidades[EstadoHash.PARAMETROS_ANTERIORES]}",
        f"hashes con formato no admitido: {cantidades[EstadoHash.FORMATO_NO_ADMITIDO]}",
        f"usuarios sin credencial: {cantidades[EstadoHash.SIN_CREDENCIAL]}",
        *a_restablecer,
    ]


def _fallar(mensaje: str) -> int:
    print(f"error: {mensaje}", file=sys.stderr)
    return 1


def _revisar(settings: Settings, abrir_sesion: Callable[[Settings], Session]) -> int:
    try:
        sesion = abrir_sesion(settings)
    except AdministracionNoConfigurada as exc:
        return _fallar(str(exc))
    try:
        lineas = _revisar_hashes(sesion)
    except Exception:
        return _fallar("no se pudo revisar las credenciales")
    finally:
        sesion.rollback()  # la transaccion es de solo lectura: nunca se confirma
        sesion.close()
    for linea in lineas:
        print(linea)
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    abrir_sesion: Callable[[Settings], Session] = _abrir_sesion_por_defecto,
    leer_visible: Callable[[str], str] = input,
    leer_oculto: Callable[[str], str] = getpass.getpass,
    es_interactivo: Callable[[], bool] = _stdin_es_terminal,
    hasher: Hasher | None = None,
    reloj: Reloj | None = None,
) -> int:
    """Las costuras son para las pruebas; el comando real usa los valores por defecto."""
    try:
        opciones = _analizar(sys.argv[1:] if argv is None else argv)
    except ArgumentosInvalidos as exc:
        return _fallar(str(exc))
    try:
        settings = cargar_configuracion()
    except ValidationError:
        return _fallar("configuracion invalida; revisar las variables de entorno")
    if settings.app_env != "local":
        return _fallar("el comando de credenciales solo se ejecuta con APP_ENV=local")
    if not es_interactivo():
        return _fallar("se requiere una terminal interactiva")

    if opciones.revisar_hashes:
        return _revisar(settings, abrir_sesion)
    reemplazar = opciones.reemplazar
    codigo = leer_visible("Codigo del consultorio: ")
    email = leer_visible("Email del usuario: ")
    try:
        sesion = abrir_sesion(settings)
    except AdministracionNoConfigurada as exc:
        return _fallar(str(exc))
    try:
        resultado = _ejecutar(
            sesion,
            codigo,
            email,
            reemplazar=reemplazar,
            leer_visible=leer_visible,
            leer_oculto=leer_oculto,
            hasher=hasher or crear_hasher(),
            reloj=reloj or RelojSistema(),
        )
        sesion.commit()
    except Fallo as fallo:
        sesion.rollback()
        return _fallar(str(fallo))
    except Exception:
        sesion.rollback()
        return _fallar("no se pudo establecer la credencial")
    finally:
        sesion.close()
    print(resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

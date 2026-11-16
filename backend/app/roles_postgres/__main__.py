"""Comando local de creacion de roles de PostgreSQL (DD-15, DA-02).

Crea o verifica, de forma idempotente, los cuatro roles del Change `aislamiento-roles-rbac`:
los dos roles duenios de las funciones de acceso (`ROL_ACCESO_PREVIO` y `ROL_ACCESO_LOGIN` de `roles_bd`, sin LOGIN) y
`turnos_app` y `turnos_login` (con LOGIN, roles de conexion de la API).

Uso (solo desarrollo local; requiere una terminal interactiva y la autorizacion del autor):

    docker compose run --rm -it --no-deps admin python -m app.roles_postgres crear [--rotar-contrasena ROL]

Servicio `admin` (DD-34): el unico que recibe `DATABASE_MIGRATION_URL`; con `api` el comando falla sin
conectar.

`ROL` es `turnos_app` o `turnos_login`. Reglas:
- Solo corre con `APP_ENV=local` y solo sobre `DATABASE_MIGRATION_URL`; con otro entorno, sin esa URL,
  sin terminal o con argumentos invalidos falla antes de abrir ninguna conexion y antes de pedir
  contrasenas.
- Los roles existentes se VERIFICAN (atributos y membresias) y nunca se corrigen en silencio.
- La contrasena de cada rol de conexion que falte (o que se rote) se pide dos veces con lectura
  oculta; la de `turnos_login` debe ser distinta de la de `turnos_app` (comparacion en memoria
  dentro de la misma ejecucion). Nunca se acepta por argumentos ni por entorno.
- La sentencia nunca lleva la contrasena: se envia un verificador `SCRAM-SHA-256` calculado del lado
  del cliente (`PGconn.encrypt_password` de libpq).
- Se piden todas las contrasenas antes de ejecutar ninguna sentencia: si algo falla no se crea nada.
- La salida solo contiene textos fijos con el nombre del rol (nunca contrasenas ni URLs).
"""

import getpass
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, cargar_configuracion
from app.core.database import AdministracionNoConfigurada, abrir_sesion_de_administracion
from app.core.linea_de_comandos import AnalizadorSinEco, ArgumentosInvalidos
from app.core.roles_bd import (
    ROL_ACCESO_LOGIN,
    ROL_ACCESO_PREVIO,
    ROL_APP,
    ROL_LOGIN,
    ROLES_CON_LOGIN,
    violaciones_de_rol,
)

_NOMBRE_VALIDO = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_VERIFICADOR_SCRAM = re.compile(
    r"^SCRAM-SHA-256\$[0-9]+:[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+:[A-Za-z0-9+/=]+$"
)
_ATRIBUTOS_SIN_PRIVILEGIOS = (
    "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
)


@dataclass(frozen=True, slots=True)
class NombresDeRoles:
    """Nombres efectivos de los cuatro roles (las pruebas usan nombres propios)."""

    app: str = ROL_APP
    login: str = ROL_LOGIN
    duenio_previo: str = ROL_ACCESO_PREVIO
    duenio_login: str = ROL_ACCESO_LOGIN

    def canonico(self, nombre: str) -> str:
        """Nombre real de `roles_bd` que corresponde a `nombre` (para evaluar atributos)."""
        return dict(zip(
            (self.app, self.login, self.duenio_previo, self.duenio_login),
            (ROL_APP, ROL_LOGIN, ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN),
            strict=True,
        ))[nombre]


class Fallo(Exception):
    """Fin anticipado con un mensaje fijo (sin datos sensibles) y codigo de salida 1."""


def _abrir_sesion_por_defecto(settings: Settings) -> Session:
    return abrir_sesion_de_administracion(settings)


def _stdin_es_terminal() -> bool:
    return sys.stdin.isatty()


def _cifrar_scram(sesion: Session, rol: str, contrasena: str) -> str:
    """Verificador `SCRAM-SHA-256` calculado con libpq en el cliente (la contrasena no viaja)."""
    pgconn = sesion.connection().connection.driver_connection.pgconn  # type: ignore[union-attr]
    return pgconn.encrypt_password(
        contrasena.encode(), rol.encode(), b"scram-sha-256"
    ).decode()


def _analizar(argv: Sequence[str]) -> str | None:
    """Devuelve el rol a rotar (o `None`); cualquier argumento invalido falla sin eco."""
    analizador = AnalizadorSinEco(prog="python -m app.roles_postgres")
    subcomandos = analizador.add_subparsers(dest="comando", required=True)
    crear = subcomandos.add_parser("crear")
    crear.add_argument("--rotar-contrasena", choices=ROLES_CON_LOGIN, default=None)
    return analizador.parse_args(list(argv)).rotar_contrasena


# --- Lecturas y escrituras de catalogo ---------------------------------------------------


def _puede_crear_roles(sesion: Session) -> bool:
    return bool(
        sesion.execute(
            text(
                "SELECT (rolcreaterole OR rolsuper) AS puede_crear_roles "
                "FROM pg_catalog.pg_roles WHERE rolname = current_user"
            )
        ).scalar_one()
    )


def _leer_rol(sesion: Session, nombre: str) -> Mapping[str, object] | None:
    return (
        sesion.execute(
            text(
                "SELECT rolname, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb, "
                "rolreplication, rolcanlogin FROM pg_catalog.pg_roles WHERE rolname = :nombre"
            ),
            {"nombre": nombre},
        )
        .mappings()
        .one_or_none()
    )


def _tiene_membresias(sesion: Session, nombre: str) -> bool:
    return bool(
        sesion.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members m "
                "JOIN pg_catalog.pg_roles r ON r.oid IN (m.member, m.roleid) "
                "WHERE r.rolname = :nombre)"
            ),
            {"nombre": nombre},
        ).scalar_one()
    )


def _nombre_seguro(nombre: str) -> str:
    if not _NOMBRE_VALIDO.fullmatch(nombre):
        raise Fallo("nombre de rol no valido")
    return nombre


def _verificador_seguro(verificador: str) -> str:
    """Solo un verificador SCRAM bien formado entra en una sentencia (sin comillas ni `%`)."""
    if not _VERIFICADOR_SCRAM.fullmatch(verificador):
        raise Fallo("no se pudo calcular el verificador de la contraseña")
    return verificador


def _crear_rol(sesion: Session, nombre: str, *, con_login: bool, verificador: str | None) -> None:
    sentencia = f"CREATE ROLE {_nombre_seguro(nombre)} {'LOGIN' if con_login else 'NOLOGIN'}"
    if verificador is not None:
        sentencia += f" PASSWORD '{_verificador_seguro(verificador)}'"
    sesion.connection().exec_driver_sql(f"{sentencia} {_ATRIBUTOS_SIN_PRIVILEGIOS}")


def _cambiar_contrasena(sesion: Session, nombre: str, verificador: str) -> None:
    sesion.connection().exec_driver_sql(
        f"ALTER ROLE {_nombre_seguro(nombre)} PASSWORD '{_verificador_seguro(verificador)}'"
    )


def _verificar_existente(sesion: Session, fila: Mapping[str, object], nombres: NombresDeRoles) -> None:
    nombre = str(fila["rolname"])
    violaciones = list(
        violaciones_de_rol({**fila, "rolname": nombres.canonico(nombre)})
    )
    if _tiene_membresias(sesion, nombre):
        violaciones.append("MEMBRESIAS")
    if violaciones:
        raise Fallo(f"el rol {nombre} existe con atributos indebidos: {', '.join(violaciones)}")


# --- Contrasenas ---------------------------------------------------------------------------


def _pedir_contrasena(leer_oculto: Callable[[str], str], rol: str) -> str:
    primera = leer_oculto(f"Contrasena de {rol}: ")
    segunda = leer_oculto(f"Repita la contrasena de {rol}: ")
    if primera != segunda:
        raise Fallo("las contraseñas no coinciden")
    if not primera:
        raise Fallo("la contraseña no puede estar vacía")
    return primera


def _ejecutar(
    sesion: Session,
    rotar: str | None,
    *,
    nombres: NombresDeRoles,
    leer_oculto: Callable[[str], str],
    cifrar_contrasena: Callable[[Session, str, str], str],
) -> list[str]:
    if not _puede_crear_roles(sesion):
        raise Fallo("el rol de administración no puede crear roles")
    orden = (
        (nombres.duenio_previo, False),
        (nombres.duenio_login, False),
        (nombres.app, True),
        (nombres.login, True),
    )
    existentes = {nombre: _leer_rol(sesion, nombre) for nombre, _ in orden}
    for fila in existentes.values():
        if fila is not None:
            _verificar_existente(sesion, fila, nombres)

    rotar_nombre = {ROL_APP: nombres.app, ROL_LOGIN: nombres.login}.get(rotar or "")
    contrasenas: dict[str, str] = {}
    for nombre, con_login in orden:
        if con_login and (existentes[nombre] is None or nombre == rotar_nombre):
            contrasenas[nombre] = _pedir_contrasena(leer_oculto, nombre)
    if nombres.app in contrasenas and contrasenas.get(nombres.login) == contrasenas[nombres.app]:
        raise Fallo("las contraseñas de los dos roles deben ser distintas")

    salida: list[str] = []
    for nombre, con_login in orden:
        verificador = (
            cifrar_contrasena(sesion, nombre, contrasenas[nombre]) if nombre in contrasenas else None
        )
        if existentes[nombre] is None:
            _crear_rol(sesion, nombre, con_login=con_login, verificador=verificador)
            salida.append(f"rol creado: {nombre}")
        elif verificador is not None:
            _cambiar_contrasena(sesion, nombre, verificador)
            salida.append(f"contraseña rotada: {nombre}")
        else:
            salida.append(f"rol existente verificado: {nombre}")
    return salida


def _fallar(mensaje: str) -> int:
    print(f"error: {mensaje}", file=sys.stderr)
    return 1


def main(
    argv: Sequence[str] | None = None,
    *,
    abrir_sesion: Callable[[Settings], Session] = _abrir_sesion_por_defecto,
    leer_oculto: Callable[[str], str] = getpass.getpass,
    es_interactivo: Callable[[], bool] = _stdin_es_terminal,
    cifrar_contrasena: Callable[[Session, str, str], str] = _cifrar_scram,
    nombres: NombresDeRoles = NombresDeRoles(),
) -> int:
    """Las costuras son para las pruebas; el comando real usa los valores por defecto."""
    try:
        rotar = _analizar(sys.argv[1:] if argv is None else argv)
    except ArgumentosInvalidos as exc:
        return _fallar(str(exc))
    try:
        settings = cargar_configuracion()
    except ValidationError:
        return _fallar("configuracion invalida; revisar las variables de entorno")
    if settings.app_env != "local":
        return _fallar("el comando de roles solo se ejecuta con APP_ENV=local")
    if not es_interactivo():
        return _fallar("se requiere una terminal interactiva")
    try:
        sesion = abrir_sesion(settings)
    except AdministracionNoConfigurada as exc:
        return _fallar(str(exc))
    try:
        salida = _ejecutar(
            sesion,
            rotar,
            nombres=nombres,
            leer_oculto=leer_oculto,
            cifrar_contrasena=cifrar_contrasena,
        )
        sesion.commit()
    except Fallo as fallo:
        sesion.rollback()
        return _fallar(str(fallo))
    except Exception:
        sesion.rollback()
        return _fallar("no se pudieron crear o verificar los roles")
    finally:
        sesion.close()
    for linea in salida:
        print(linea)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Roles de PostgreSQL del Change `aislamiento-roles-rbac` y evaluacion pura de sus atributos.

Constantes unicas para la migracion, el comando de roles, las guardias de la API y las pruebas
(DD-01, DD-13). Sin I/O: la evaluacion recibe una fila de `pg_roles` ya leida.
"""

from collections.abc import Mapping

ROL_APP = "turnos_app"
ROL_LOGIN = "turnos_login"
ROL_ACCESO_PREVIO = "turnos_acceso_previo"
ROL_ACCESO_LOGIN = "turnos_acceso_login"

ROLES_CON_LOGIN = (ROL_APP, ROL_LOGIN)
ROLES_DUENOS = (ROL_ACCESO_PREVIO, ROL_ACCESO_LOGIN)
TODOS_LOS_ROLES = (*ROLES_CON_LOGIN, *ROLES_DUENOS)

# Atributos que ninguno de los cuatro roles puede tener, en el orden en que se informan.
_ATRIBUTOS_PROHIBIDOS = (
    ("rolsuper", "SUPERUSER"),
    ("rolbypassrls", "BYPASSRLS"),
    ("rolcreaterole", "CREATEROLE"),
    ("rolcreatedb", "CREATEDB"),
    ("rolreplication", "REPLICATION"),
)


def violaciones_de_rol(fila: Mapping[str, object]) -> tuple[str, ...]:
    """Codigos fijos de lo que no cumple una fila de `pg_roles` (vacio si es correcta).

    Los roles de conexion deben tener `LOGIN`; los duenios de funciones, no. Ninguno puede ser
    superusuario ni tener `BYPASSRLS`, `CREATEROLE`, `CREATEDB` ni `REPLICATION`.
    """
    nombre = fila["rolname"]
    if nombre not in TODOS_LOS_ROLES:
        raise ValueError("rol no gestionado por este Change")
    violaciones = [codigo for columna, codigo in _ATRIBUTOS_PROHIBIDOS if fila[columna]]
    if nombre in ROLES_CON_LOGIN and not fila["rolcanlogin"]:
        violaciones.append("SIN_LOGIN")
    if nombre in ROLES_DUENOS and fila["rolcanlogin"]:
        violaciones.append("CON_LOGIN")
    return tuple(violaciones)


def violaciones_de_conexion(esperado: str, fila: Mapping[str, object]) -> tuple[str, ...]:
    """Codigos fijos de lo que no cumple una conexion de la API (guardia de DD-29, R2-05).

    `esperado` es `turnos_app` o `turnos_login` y `usuario_actual` debe coincidir EXACTAMENTE: un
    rol con los mismos privilegios pero otro nombre se rechaza. Nunca devuelve valores.
    """
    if esperado not in ROLES_CON_LOGIN:
        raise ValueError("solo turnos_app y turnos_login son roles de conexion de la API")
    violaciones: list[str] = []
    if fila["usuario_actual"] != esperado:
        violaciones.append("ROL_INESPERADO")
    violaciones.extend(codigo for columna, codigo in _ATRIBUTOS_PROHIBIDOS if fila[columna])
    if fila["duenio_de_objetos"]:
        violaciones.append("DUENIO_DE_OBJETOS")
    if fila["con_membresias"]:
        violaciones.append("MEMBRESIAS")
    if fila["escribe_credencial"]:
        violaciones.append("ESCRIBE_CREDENCIAL")
    if esperado == ROL_APP:
        if fila["lee_credencial"]:
            violaciones.append("LEE_CREDENCIAL")
        if fila["ejecuta_buscar_cuenta"]:
            violaciones.append("EJECUTA_LOGIN")
    else:
        if fila["escribe_usuario"]:
            violaciones.append("ESCRIBE_USUARIO")
        if fila["privilegio_en_tablas"]:
            violaciones.append("TABLAS_ACCESIBLES")
        if not fila["ejecuta_buscar_cuenta"]:
            violaciones.append("SIN_BUSCAR_CUENTA")
    return tuple(violaciones)


# Funciones del esquema `acceso` (DD-25). Sesion: dueno `turnos_acceso_previo`, las ejecuta
# `turnos_app`. Login: dueno `turnos_acceso_login`, las ejecuta `turnos_login`.
FUNCIONES_DE_SESION = (
    "resolver_sesion",
    "renovar_sesion",
    "revocar_sesion_por_token",
    "limpiar_sesiones",
)
FUNCIONES_DE_LOGIN = (
    "buscar_cuenta",
    "registrar_fallo",
    "fallos_de_cuenta",
    "fallos_de_ip",
    "descartar_fallos_de_cuenta",
    "limpiar_intentos",
)

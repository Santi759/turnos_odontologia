"""aislamiento por roles y RLS: privilegios minimos, esquema acceso y politicas

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-10

C-04 `aislamiento-roles-rbac` (DD-01, DD-03, DD-07, DD-09, DD-13, DD-25). Una sola transaccion.
No crea roles (son del cluster y llevan contrasenas: `python -m app.roles_postgres crear` en
desarrollo y `db/test-init/10_roles_prueba.sh` en db-test), no crea tablas y no modifica filas.
Verifica al comienzo los cuatro roles y falla, sin cambios, si alguno no cumple.
"""
from typing import Sequence, Union

from alembic import op

from app.core.roles_bd import (
    FUNCIONES_DE_LOGIN,
    FUNCIONES_DE_SESION,
    ROL_ACCESO_LOGIN,
    ROL_ACCESO_PREVIO,
    ROL_APP,
    ROL_LOGIN,
    ROLES_CON_LOGIN,
    ROLES_DUENOS,
    TODOS_LOS_ROLES,
)

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LISTA_DE_ROLES = ", ".join(f"'{rol}'" for rol in TODOS_LOS_ROLES)
_ROLES_CON_LOGIN_SQL = ", ".join(f"'{rol}'" for rol in ROLES_CON_LOGIN)
_ROLES_DUENOS_SQL = ", ".join(f"'{rol}'" for rol in ROLES_DUENOS)

# Mensajes fijos: nombran el rol y nunca incluyen datos.
_VERIFICACION_PREVIA = f"""
DO $verificacion$
DECLARE
    r pg_catalog.pg_roles%ROWTYPE;
    nombre text;
BEGIN
    FOREACH nombre IN ARRAY ARRAY[{_LISTA_DE_ROLES}] LOOP
        SELECT * INTO r FROM pg_catalog.pg_roles WHERE rolname = nombre;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'falta el rol %: crearlo antes de aplicar 0004', nombre;
        END IF;
        IF r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication THEN
            RAISE EXCEPTION 'el rol % tiene atributos no admitidos', nombre;
        END IF;
        IF nombre IN ({_ROLES_CON_LOGIN_SQL}) AND NOT r.rolcanlogin THEN
            RAISE EXCEPTION 'el rol % debe tener LOGIN', nombre;
        END IF;
        IF nombre IN ({_ROLES_DUENOS_SQL}) AND r.rolcanlogin THEN
            RAISE EXCEPTION 'el rol % no debe tener LOGIN', nombre;
        END IF;
        IF EXISTS (
            SELECT 1 FROM pg_catalog.pg_auth_members m
              JOIN pg_catalog.pg_roles a ON a.oid = m.member
              JOIN pg_catalog.pg_roles b ON b.oid = m.roleid
             WHERE a.rolname = nombre OR b.rolname = nombre
        ) THEN
            RAISE EXCEPTION 'el rol % no debe ser miembro de otro rol ni tener miembros', nombre;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_catalog.pg_class c WHERE c.relowner = r.oid)
           OR EXISTS (SELECT 1 FROM pg_catalog.pg_proc p WHERE p.proowner = r.oid)
           OR EXISTS (SELECT 1 FROM pg_catalog.pg_namespace s WHERE s.nspowner = r.oid) THEN
            RAISE EXCEPTION 'el rol % no debe ser duenio de objetos', nombre;
        END IF;
    END LOOP;
END
$verificacion$
"""

_EXPRESION_CONSULTORIO = "NULLIF(current_setting('app.consultorio_id', true), '')::uuid"

# (tabla, columna del consultorio)
_TABLAS_POR_CONSULTORIO = (
    ("consultorio", "id"),
    ("usuario", "consultorio_id"),
    ("sesion", "consultorio_id"),
)
_TABLAS_CON_RLS = ("consultorio", "usuario", "sesion", "intento_login")

_POLITICAS = (
    ("pol_consultorio_acceso_previo", "consultorio", "FOR SELECT", ROL_ACCESO_PREVIO),
    ("pol_usuario_acceso_previo", "usuario", "FOR SELECT", ROL_ACCESO_PREVIO),
    ("pol_sesion_acceso_previo_lectura", "sesion", "FOR SELECT", ROL_ACCESO_PREVIO),
    ("pol_sesion_acceso_previo_cambio", "sesion", "FOR UPDATE", ROL_ACCESO_PREVIO),
    ("pol_sesion_acceso_previo_limpieza", "sesion", "FOR DELETE", ROL_ACCESO_PREVIO),
    ("pol_consultorio_acceso_login", "consultorio", "FOR SELECT", ROL_ACCESO_LOGIN),
    ("pol_usuario_acceso_login_lectura", "usuario", "FOR SELECT", ROL_ACCESO_LOGIN),
    ("pol_intento_login_acceso_login", "intento_login", "FOR ALL", ROL_ACCESO_LOGIN),
)

_PRIVILEGIOS = (
    f"GRANT USAGE ON SCHEMA public TO {ROL_APP}, {ROL_ACCESO_PREVIO}, {ROL_ACCESO_LOGIN}",
    # turnos_app: sin credencial, sin token_hmac legible, sin intento_login (DD-07).
    f"GRANT SELECT ON public.consultorio TO {ROL_APP}",
    f"GRANT SELECT (id, consultorio_id, email, nombre, rol, activo, creado_en) ON public.usuario TO {ROL_APP}",
    f"GRANT SELECT (id, consultorio_id, usuario_id, creada_en, ultimo_uso_en, vence_absoluto_en, "
    f"revocada_en) ON public.sesion TO {ROL_APP}",
    f"GRANT INSERT (consultorio_id, usuario_id, token_hmac, creada_en, ultimo_uso_en, "
    f"vence_absoluto_en) ON public.sesion TO {ROL_APP}",
    f"GRANT UPDATE (revocada_en) ON public.sesion TO {ROL_APP}",
    # turnos_acceso_previo: sin credencial ni intento_login.
    f"GRANT SELECT (id, nombre, activo) ON public.consultorio TO {ROL_ACCESO_PREVIO}",
    f"GRANT SELECT (id, consultorio_id, email, nombre, rol, activo) ON public.usuario TO {ROL_ACCESO_PREVIO}",
    f"GRANT SELECT, DELETE ON public.sesion TO {ROL_ACCESO_PREVIO}",
    f"GRANT UPDATE (ultimo_uso_en, revocada_en) ON public.sesion TO {ROL_ACCESO_PREVIO}",
    # turnos_acceso_login: solo lectura de usuario (R2-03: nada de INSERT/UPDATE/DELETE) y sin sesion.
    f"GRANT SELECT (id, codigo, nombre, activo) ON public.consultorio TO {ROL_ACCESO_LOGIN}",
    f"GRANT SELECT (id, consultorio_id, email, nombre, rol, credencial, activo) ON public.usuario TO {ROL_ACCESO_LOGIN}",
    f"GRANT SELECT, DELETE ON public.intento_login TO {ROL_ACCESO_LOGIN}",
    f"GRANT INSERT (clave_cuenta, clave_ip, ocurrido_en) ON public.intento_login TO {ROL_ACCESO_LOGIN}",
    f"GRANT UPDATE (descartado_para_cuenta) ON public.intento_login TO {ROL_ACCESO_LOGIN}",
    # turnos_login: ningun privilegio de tabla (solo ejecutara funciones del esquema acceso).
)


# --- Funciones del esquema `acceso` (DD-09, DD-25) -----------------------------------------------
# Todas: SECURITY DEFINER de su dueno, search_path = pg_catalog, pg_temp, objetos con esquema,
# sin SQL dinamico, sin parametros uuid, una fila como maximo. Entradas validadas con 22023.
# Ninguna escribe `usuario` (R2-03): no existe funcion de rehash.
_CABECERA = "LANGUAGE plpgsql {volatilidad} SECURITY DEFINER SET search_path = pg_catalog, pg_temp"

_VALIDAR_HMAC = """
    IF {p} IS NULL OR octet_length({p}) <> 32 THEN
        RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'clave hmac invalida';
    END IF;"""
_VALIDAR_INSTANTE = """
    IF {p} IS NULL OR {p} > now() + interval '5 minutes' THEN
        RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'instante invalido';
    END IF;"""


def _hmac(parametro: str) -> str:
    return _VALIDAR_HMAC.format(p=parametro)


def _instante(parametro: str) -> str:
    return _VALIDAR_INSTANTE.format(p=parametro)


def _cuerpo(volatilidad: str, cuerpo: str, declaraciones: str = "") -> str:
    return (
        f"{_CABECERA.format(volatilidad=volatilidad)}\nAS $f$\n{declaraciones}BEGIN{cuerpo}\nEND\n$f$"
    )


_DECLARA_N = "DECLARE n integer;\n"

# (nombre, firma para DROP/GRANT, definicion completa, dueno, rol que ejecuta)
_FUNCIONES = (
    # --- login: dueno turnos_acceso_login, ejecuta turnos_login -------------------------------
    (
        "buscar_cuenta",
        "text, text",
        "CREATE FUNCTION acceso.buscar_cuenta(p_codigo text, p_email text, "
        "OUT o_consultorio_id uuid, OUT o_usuario_id uuid, OUT o_email text, OUT o_nombre text, "
        "OUT o_rol text, OUT o_consultorio_nombre text, OUT o_usuario_activo boolean, "
        "OUT o_consultorio_activo boolean, OUT o_credencial text) "
        + _cuerpo(
            "STABLE",
            """
    IF p_codigo IS NULL OR p_email IS NULL
       OR char_length(p_codigo) > 64 OR char_length(p_email) > 254 THEN
        RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'entrada invalida';
    END IF;
    SELECT c.id, u.id, u.email, u.nombre, u.rol, c.nombre, u.activo, c.activo,
           CASE WHEN u.activo AND c.activo THEN u.credencial END
      INTO o_consultorio_id, o_usuario_id, o_email, o_nombre, o_rol, o_consultorio_nombre,
           o_usuario_activo, o_consultorio_activo, o_credencial
      FROM public.usuario u
      JOIN public.consultorio c ON c.id = u.consultorio_id
     WHERE c.codigo = lower(btrim(p_codigo)) AND u.email = lower(btrim(p_email));""",
        ),
        ROL_ACCESO_LOGIN,
        ROL_LOGIN,
    ),
    (
        "registrar_fallo",
        "bytea, bytea, timestamptz",
        "CREATE FUNCTION acceso.registrar_fallo(p_clave_cuenta bytea, p_clave_ip bytea, "
        "p_ocurrido_en timestamptz) RETURNS void "
        + _cuerpo(
            "VOLATILE",
            _hmac("p_clave_cuenta")
            + _hmac("p_clave_ip")
            + _instante("p_ocurrido_en")
            + """
    INSERT INTO public.intento_login (clave_cuenta, clave_ip, ocurrido_en)
    VALUES (p_clave_cuenta, p_clave_ip, p_ocurrido_en);""",
        ),
        ROL_ACCESO_LOGIN,
        ROL_LOGIN,
    ),
    (
        "fallos_de_cuenta",
        "bytea, timestamptz",
        "CREATE FUNCTION acceso.fallos_de_cuenta(p_clave_cuenta bytea, p_desde timestamptz) "
        "RETURNS timestamptz[] "
        + _cuerpo(
            "STABLE",
            _hmac("p_clave_cuenta")
            + """
    IF p_desde IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'instante invalido';
    END IF;
    RETURN COALESCE((
        SELECT array_agg(r.ocurrido_en ORDER BY r.ocurrido_en)
          FROM (SELECT i.ocurrido_en FROM public.intento_login i
                 WHERE i.clave_cuenta = p_clave_cuenta AND NOT i.descartado_para_cuenta
                   AND i.ocurrido_en > p_desde
                 ORDER BY i.ocurrido_en DESC LIMIT 5) r), ARRAY[]::timestamptz[]);""",
        ),
        ROL_ACCESO_LOGIN,
        ROL_LOGIN,
    ),
    (
        "fallos_de_ip",
        "bytea, timestamptz",
        "CREATE FUNCTION acceso.fallos_de_ip(p_clave_ip bytea, p_desde timestamptz) "
        "RETURNS timestamptz[] "
        + _cuerpo(
            "STABLE",
            _hmac("p_clave_ip")
            + """
    IF p_desde IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'instante invalido';
    END IF;
    RETURN COALESCE((
        SELECT array_agg(r.ocurrido_en ORDER BY r.ocurrido_en)
          FROM (SELECT i.ocurrido_en FROM public.intento_login i
                 WHERE i.clave_ip = p_clave_ip AND i.ocurrido_en > p_desde
                 ORDER BY i.ocurrido_en DESC LIMIT 30) r), ARRAY[]::timestamptz[]);""",
        ),
        ROL_ACCESO_LOGIN,
        ROL_LOGIN,
    ),
    (
        "descartar_fallos_de_cuenta",
        "bytea",
        "CREATE FUNCTION acceso.descartar_fallos_de_cuenta(p_clave_cuenta bytea) RETURNS integer "
        + _cuerpo(
            "VOLATILE",
            _hmac("p_clave_cuenta")
            + """
    UPDATE public.intento_login SET descartado_para_cuenta = true
     WHERE clave_cuenta = p_clave_cuenta AND NOT descartado_para_cuenta;
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;""",
            _DECLARA_N,
        ),
        ROL_ACCESO_LOGIN,
        ROL_LOGIN,
    ),
    (
        "limpiar_intentos",
        "timestamptz",
        "CREATE FUNCTION acceso.limpiar_intentos(p_ahora timestamptz) RETURNS integer "
        + _cuerpo(
            "VOLATILE",
            _instante("p_ahora")
            + """
    DELETE FROM public.intento_login WHERE id IN (
        SELECT i.id FROM public.intento_login i
         WHERE i.ocurrido_en < p_ahora - interval '24 hours'
         ORDER BY i.ocurrido_en LIMIT 100);
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;""",
            _DECLARA_N,
        ),
        ROL_ACCESO_LOGIN,
        ROL_LOGIN,
    ),
    # --- sesion: dueno turnos_acceso_previo, ejecuta turnos_app -------------------------------
    (
        "resolver_sesion",
        "bytea",
        "CREATE FUNCTION acceso.resolver_sesion(p_token_hmac bytea, "
        "OUT o_sesion_id uuid, OUT o_consultorio_id uuid, OUT o_usuario_id uuid, OUT o_email text, "
        "OUT o_nombre text, OUT o_rol text, OUT o_consultorio_nombre text, "
        "OUT o_usuario_activo boolean, OUT o_consultorio_activo boolean, "
        "OUT o_creada_en timestamptz, OUT o_ultimo_uso_en timestamptz, "
        "OUT o_vence_absoluto_en timestamptz, OUT o_revocada_en timestamptz) "
        + _cuerpo(
            "STABLE",
            _hmac("p_token_hmac")
            + """
    SELECT s.id, s.consultorio_id, s.usuario_id, u.email, u.nombre, u.rol, c.nombre,
           u.activo, c.activo, s.creada_en, s.ultimo_uso_en, s.vence_absoluto_en, s.revocada_en
      INTO o_sesion_id, o_consultorio_id, o_usuario_id, o_email, o_nombre, o_rol,
           o_consultorio_nombre, o_usuario_activo, o_consultorio_activo, o_creada_en,
           o_ultimo_uso_en, o_vence_absoluto_en, o_revocada_en
      FROM public.sesion s
      JOIN public.usuario u ON u.consultorio_id = s.consultorio_id AND u.id = s.usuario_id
      JOIN public.consultorio c ON c.id = s.consultorio_id
     WHERE s.token_hmac = p_token_hmac;""",
        ),
        ROL_ACCESO_PREVIO,
        ROL_APP,
    ),
    (
        "renovar_sesion",
        "bytea, timestamptz",
        "CREATE FUNCTION acceso.renovar_sesion(p_token_hmac bytea, p_ahora timestamptz) "
        "RETURNS boolean "
        + _cuerpo(
            "VOLATILE",
            _hmac("p_token_hmac")
            + _instante("p_ahora")
            + """
    UPDATE public.sesion SET ultimo_uso_en = p_ahora
     WHERE token_hmac = p_token_hmac AND revocada_en IS NULL AND p_ahora < vence_absoluto_en
       AND p_ahora - ultimo_uso_en >= interval '60 seconds';
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n > 0;""",
            _DECLARA_N,
        ),
        ROL_ACCESO_PREVIO,
        ROL_APP,
    ),
    (
        "revocar_sesion_por_token",
        "bytea, timestamptz",
        "CREATE FUNCTION acceso.revocar_sesion_por_token(p_token_hmac bytea, p_ahora timestamptz) "
        "RETURNS boolean "
        + _cuerpo(
            "VOLATILE",
            _hmac("p_token_hmac")
            + _instante("p_ahora")
            + """
    UPDATE public.sesion SET revocada_en = p_ahora
     WHERE token_hmac = p_token_hmac AND revocada_en IS NULL;
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n > 0;""",
            _DECLARA_N,
        ),
        ROL_ACCESO_PREVIO,
        ROL_APP,
    ),
    (
        "limpiar_sesiones",
        "timestamptz, integer",
        "CREATE FUNCTION acceso.limpiar_sesiones(p_ahora timestamptz, p_minutos_inactividad integer) "
        "RETURNS integer "
        + _cuerpo(
            "VOLATILE",
            _instante("p_ahora")
            + """
    IF p_minutos_inactividad IS NULL OR p_minutos_inactividad < 5 OR p_minutos_inactividad > 480 THEN
        RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'inactividad invalida';
    END IF;
    DELETE FROM public.sesion WHERE id IN (
        SELECT s.id FROM public.sesion s
         WHERE s.revocada_en IS NOT NULL OR s.vence_absoluto_en <= p_ahora
            OR s.ultimo_uso_en + make_interval(mins => p_minutos_inactividad) <= p_ahora
         ORDER BY s.ultimo_uso_en LIMIT 100);
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;""",
            _DECLARA_N,
        ),
        ROL_ACCESO_PREVIO,
        ROL_APP,
    ),
)
assert {f[0] for f in _FUNCIONES} == {*FUNCIONES_DE_LOGIN, *FUNCIONES_DE_SESION}


def upgrade() -> None:
    op.execute(_VERIFICACION_PREVIA)

    # DD-08 (decision del autor, 2026-11-10, opcion 3): convencion uniforme, tambien en `sesion`.
    # `id` ya es PK, asi que la unicidad compuesta es trivialmente valida y no modifica filas.
    op.create_unique_constraint(
        op.f("uq_sesion_consultorio_id_id"), "sesion", ["consultorio_id", "id"]
    )
    op.execute("CREATE SCHEMA acceso")
    op.execute("REVOKE ALL ON SCHEMA acceso FROM PUBLIC")
    op.execute(f"GRANT USAGE ON SCHEMA acceso TO {ROL_APP}, {ROL_LOGIN}")
    for sentencia in _PRIVILEGIOS:
        op.execute(sentencia)

    for tabla in _TABLAS_CON_RLS:
        op.execute(f"ALTER TABLE public.{tabla} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{tabla} FORCE ROW LEVEL SECURITY")

    # Politica cerrada por defecto (DD-03): sin contexto (NULL o '') cero filas y escritura
    # rechazada; un valor no UUID falla cerrado con 22P02.
    for tabla, columna in _TABLAS_POR_CONSULTORIO:
        op.execute(
            f"CREATE POLICY pol_{tabla}_aislamiento ON public.{tabla} "
            f"USING ({columna} = {_EXPRESION_CONSULTORIO}) "
            f"WITH CHECK ({columna} = {_EXPRESION_CONSULTORIO})"
        )
    for nombre, tabla, orden, rol in _POLITICAS:
        con_check = " WITH CHECK (true)" if orden in ("FOR UPDATE", "FOR ALL") else ""
        op.execute(
            f"CREATE POLICY {nombre} ON public.{tabla} {orden} TO {rol} USING (true){con_check}"
        )

    for nombre, firma, definicion, duenio, ejecuta in _FUNCIONES:
        op.execute(definicion)
        op.execute(f"ALTER FUNCTION acceso.{nombre}({firma}) OWNER TO {duenio}")
        op.execute(f"REVOKE ALL ON FUNCTION acceso.{nombre}({firma}) FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION acceso.{nombre}({firma}) TO {ejecuta}")


def downgrade() -> None:
    # Solo se ejecuta contra la base de pruebas efimera (db-test). Revierte exactamente lo que
    # agrega `upgrade`, sin CASCADE y sin eliminar roles ni modificar filas.
    for nombre, firma, _definicion, _duenio, _ejecuta in reversed(_FUNCIONES):
        op.execute(f"DROP FUNCTION acceso.{nombre}({firma})")
    for nombre, tabla, _orden, _rol in reversed(_POLITICAS):
        op.execute(f"DROP POLICY {nombre} ON public.{tabla}")
    for tabla, _columna in reversed(_TABLAS_POR_CONSULTORIO):
        op.execute(f"DROP POLICY pol_{tabla}_aislamiento ON public.{tabla}")
    for tabla in reversed(_TABLAS_CON_RLS):
        op.execute(f"ALTER TABLE public.{tabla} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{tabla} DISABLE ROW LEVEL SECURITY")
    roles = ", ".join(TODOS_LOS_ROLES)
    # El REVOKE de tabla retira tambien los privilegios de columna concedidos.
    op.execute(f"REVOKE ALL PRIVILEGES ON TABLE public.consultorio, public.usuario, public.sesion, public.intento_login FROM {roles}")
    op.execute(f"REVOKE ALL ON SCHEMA public FROM {ROL_APP}, {ROL_ACCESO_PREVIO}, {ROL_ACCESO_LOGIN}")
    op.execute("DROP SCHEMA acceso")
    op.drop_constraint(op.f("uq_sesion_consultorio_id_id"), "sesion", type_="unique")

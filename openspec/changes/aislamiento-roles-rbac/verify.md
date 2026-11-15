# Verify tecnico (grupo 12): aislamiento-roles-rbac (C-04)

> Todo contra `db-test` efimera (o sin base, en las unitarias). Nada toco `db`, `api` ni `frontend` de desarrollo, ningun `.env*`, ninguna credencial real. Datos ficticios. Ningun comando con `getpass` se ejecuto de verdad. Fecha: 2026-11-10. `openspec` 1.14.1.

## 12.1 Migracion 0004 en db-test

Ciclo manual sobre `db-test` nueva (`alembic -x target=test`):

| Comando | Resultado |
|---|---|
| `upgrade head` | `0001 -> 0002 -> 0003 -> 0004` |
| `current` | `0004 (head)` |
| `downgrade 0003` | `Running downgrade 0004 -> 0003` |
| `current` | `0003` |
| `upgrade head` | `Running upgrade 0003 -> 0004` |
| `current` | `0004 (head)` |

Pruebas (`test_migracion_aislamiento.py`, `test_migraciones.py`, `test_migracion_autenticacion.py`, `test_convenciones_esquema.py`): **50 passed** (verificacion previa de roles, subida con huella de filas igual, bajada con catalogo igual al de 0003 y roles conservados, resubida identica, `uq_sesion_consultorio_id_id`). Registrado: OK.

## 12.2 Roles y privilegios con conexiones reales

`tests/isolation/test_arnes.py`, `test_catalogo_roles.py`, `test_privilegios.py`, `test_funciones_acceso.py`, `test_login_sin_escritura.py`, `test_guardia_rol_api.py`: **163 passed** (catalogo de roles, matriz de privilegios, 42501 reales, funciones de acceso, login sin escritura de credenciales, guardias de rol). OK.

## 12.3 RLS y aislamiento entre consultorios

`test_rls.py`, `test_contexto_transaccional.py`, `test_acceso_cruzado.py`, `test_registro.py`: **42 passed**. OK.

## 12.4 Autorizacion

`tests/unit/test_autorizacion.py`, `test_consultorio_cliente.py`, `test_lecturas_de_peticion.py`, `test_comparaciones_de_rol.py`, `tests/integration/test_autorizacion_roles.py`, `test_consultorio_cliente.py`, `test_dependencias_auth.py`: **97 passed** (`require_rol`, matriz de roles, 401/403/404, 422 de `consultorio_id` y de `X-Consultorio-Id`, lista blanca de lecturas). OK.

## 12.5 Regresion de C-03 y PD-04

- `tests/isolation/test_regresion_auth.py`, `test_pool_login.py`, `test_conexiones_login.py` y `tests/unit/test_presupuesto_conexiones.py`, `test_pools_y_guardias.py`: **42 passed en cada una de 3 corridas consecutivas** (estables).
- `tests/integration` completo: **509 passed**.
- Las nueve condiciones de 5.7 en verde con la configuracion real de los pools (login 4/11, app 5/10, espera 30 s, `connect_timeout` 5; **valores sin cambios**, ver `app/core/database.py`). Ninguna prueba de concurrencia, permisos, RLS, sesiones, aislamiento ni pools fallo en esta sesion.
- Adaptaciones de pruebas de C-03 (todas justificadas en `tdd-evidencia.md`): 3 casos de `test_dependencias_auth.py` por el 422 de `consultorio_id`/`X-Consultorio-Id` (delta `validacion-entrada`); las de sesiones anteriores (firmas de `acceso_*`, rehash, apps de prueba).

OK.

## 12.6 Validacion de OpenSpec

- `openspec validate aislamiento-roles-rbac --strict`: `Change 'aislamiento-roles-rbac' is valid` (codigo 0).
- `openspec validate --specs --strict`: `Totals: 15 passed, 0 failed (15 items)` (codigo 0).

## 12.7 `scripts/test.ps1` completo (sesion 2026-11-14, tras 1.6 y 10.2)

`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1`: **codigo 0** ("Todas las suites pasaron."). Solo db-test efimera y contenedores efimeros; db-test eliminada al terminar.

| Paso | Resultado |
|---|---|
| 0. autoprueba | 22 casos `[OK]`, 0 `[FALLA]` (incluye 'Plantilla completa con valores ficticios') |
| 2. unitarias | **765 passed** (incluidas las 19 de superposicion; +3 de la plantilla de 1.6 respecto de 762) |
| 5. integracion | **509 passed** |
| 6. aislamiento (`turnos_app` y `turnos_login`) | **234 passed** |
| 7. `tsc --noEmit` | OK |
| 8. Vitest | **2 passed** (1 archivo) |

Antes del runner: pruebas de la plantilla (1.6) **23 passed**. `test_superposicion_turnos.py` no cambio. La matriz de `tdd-evidencia.md` cubre **194 de 194** escenarios (referencias verificadas contra el codigo).

Validaciones de OpenSpec de esta sesion: `openspec validate aislamiento-roles-rbac --strict` -> `Change 'aislamiento-roles-rbac' is valid` (codigo 0); `openspec validate --specs --strict` -> `Totals: 15 passed, 0 failed` (codigo 0).

## 12.8 Decision go/no-go hacia la transicion (grupo 13), reevaluada el 2026-11-14

**GO.** 12.1 a 12.7 completas y en verde con resultados reales:
1. La tarea 1.6 se completo (plantilla editada a mano por el autor; GREEN 23 passed; escenario cubierto): ya no hay escenarios sin prueba (194 de 194).
2. El grupo 11 (documentacion) esta completo (11.1 a 11.8 marcadas).
3. El punto 3 del NO-GO anterior (comandos interactivos con `getpass`) **no bloquea el Verify**: esos comandos se ejecutan de verdad en el grupo 13 (autorizacion A2) y en Apply se probaron con lecturas inyectadas.
4. Runner con codigo 0, validaciones estrictas en verde, regresion de C-03 y PD-04 en verde (12.5).

Pendiente documental D2 (fuera de C-04): PA-03 y PA-11 en `knowledge-base/10_preguntas_abiertas.md` y US-001 en `knowledge-base/06_funcionalidades.md` siguen abiertas/"Condicionada" aunque C-03 las resolvio; se corrigen en un cambio documental aparte (ver seccion siguiente).

El GO no autoriza nada por si mismo: **el grupo 13 NO se inicio**; requiere las autorizaciones A1 a A5 del autor.

## Pendiente documental separado de C-04 (decisión D2 del autor, 2026-11-14)

`knowledge-base/10_preguntas_abiertas.md:110` (PA-03) y `:118` (PA-11) siguen como abiertas y `knowledge-base/06_funcionalidades.md:15` (US-001) sigue "Condicionada" por ellas, aunque C-03 las resolvió. Por decisión del autor no se modifican en C-04; quedan registradas como posible desactualización a corregir en un cambio documental aparte.

## Checkpoint de Git previo al grupo 13 (autorizado por el autor, 2026-11-14)

El autor revisó personalmente `git diff -- .env.example` y autorizó un commit local de checkpoint de C-04 antes de la transición del grupo 13, con los 124 archivos auditados (se excluye `backend/tests/unit/test_superposicion_turnos.py`, que conserva una diferencia preexistente de finales de línea). El checkpoint no archiva el Change, no inicia el grupo 13, no aplica 0004 en desarrollo ni modifica PostgreSQL de desarrollo; C-04 sigue activo y la tarea 15.1 queda abierta para el commit de cierre.

## 13.1 Precondición de la transición: confirmación manual del autor (2026-11-14)

12.8 = GO. El autor confirmó manualmente, sin que Claude leyera ni modificara su `.env`:

- `POSTGRES_USER` es `app`.
- Cambió la contraseña del rol `app` dentro de PostgreSQL (`\password app`) y actualizó `POSTGRES_PASSWORD` en su `.env` privado.
- `DATABASE_MIGRATION_URL` está configurada con el usuario `app` y su contraseña de administración actual.
- `DATABASE_URL` sigue usando `app` y no se modifica hasta la tarea 13.5.
  - **Corrección (2026-11-15):** la verificación de A2 mostró que la configuración efectiva ya usaba el usuario `turnos_app` en `DATABASE_URL` cuando se crearon los roles; el autor había adelantado ese cambio de la 13.5 (ver sección "13.3"). `DATABASE_LOGIN_URL` sigue sin configurarse.
- `DATABASE_LOGIN_URL` todavía no está configurada.

Estado observado en ese momento (solo lectura): servicio `db` en ejecución y sano (contenedor creado el 2026-11-14, volumen `pgdata` presente), `api` y `frontend` detenidos. A1 (13.2) no se inició: requiere la autorización del autor.

## 13.2 A1: respaldo y verificación previa de solo lectura (2026-11-14, autorizado por el autor)

**Resultado: APROBADO.** Ninguna escritura en PostgreSQL; sin roles nuevos ni migraciones.

Condiciones previas: directorio `C:\dev\turnos_odontologia`, rama `main`, HEAD `5410556`; `.env.example` sin cambios (`git diff --quiet` rc=0, sin leer su contenido); `db` en ejecución y sano (`pg_isready` rc=0); `api` y `frontend` detenidos.

**Paso 1, conectividad administrativa** (`docker compose run --rm --no-deps -T api python -I -c …` con `DATABASE_MIGRATION_URL`, transacción de solo lectura; solo se imprimieron campos fijos): `usuario=app superusuario=True servidor=18.6 (Debian 18.6-1.pgdg13+2) revision=0003`, rc=0. El contenedor efímero se eliminó y el servicio `api` siguió detenido.

**Paso 2, estado previo** (`psql -w` por socket dentro de `db`, con `default_transaction_read_only=on`, confirmado por la sesión):

- `pg_hba_file_rules`: `local all all trust` (el respaldo no necesita contraseña); conexiones `host` externas con `scram-sha-256`.
- Alembic: `0003`.
- Roles (sin `pg_*`): solo `app` (superusuario, login, createrole, createdb, bypassrls, inherit).
- Roles de C-04 (`turnos_app`, `turnos_login`, `turnos_acceso_previo`, `turnos_acceso_login`): 0. Esquema `acceso`: 0.
- Filas y huella por tabla de `public` (`md5(string_agg(fila::text ORDER BY fila::text))`; las huellas no revelan datos y se comparan en 13.4 y 14.4):

| Tabla | Filas | Huella md5 |
|---|---|---|
| `alembic_version` | 1 | `bf4237522c7b85a4efabdd9d2d3d84a7` |
| `consultorio` | 2 | `b74c6edfab8ba5d584e63210aa614e49` |
| `intento_login` | 0 | `d41d8cd98f00b204e9800998ecf8427e` |
| `sesion` | 0 | `d41d8cd98f00b204e9800998ecf8427e` |
| `usuario` | 6 | `03a0edf4612c014ecb3b96a5ab926bcb` |

**Permisos del respaldo** (opción 1 del autor): `C:\dev\respaldos_turnos\` hereda lectura para `BUILTIN\Usuarios` y modificación para `Authenticated Users`, por lo que se creó la subcarpeta `C:\dev\respaldos_turnos\c04_20261114\` y se le quitó la herencia con `icacls /inheritance:r /grant:r` por SID: la cuenta del proceso (obtenida con `whoami /user`), `S-1-5-18` (SYSTEM) y `S-1-5-32-544` (Administradores), con control total `(OI)(CI)F`. SDDL resultante: `D:PAI(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;<SID de la cuenta del autor>)`; sin Usuarios, Everyone ni Authenticated Users. Los permisos de la carpeta padre y de los respaldos anteriores, y el SHA-256 de los respaldos anteriores, quedaron idénticos antes y después.

**Paso 3, respaldo**: con `set -o noclobber` y comprobación previa de ruta libre, `docker compose exec -T db sh -c 'exec pg_dump --no-password --format=custom --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' > C:\dev\respaldos_turnos\c04_20261114\20261114_pre_0004.dump`; **rc=0**. Sin credenciales en la línea de comandos ni en la salida.

**Paso 4, verificación del archivo**:

- Ruta: `C:\dev\respaldos_turnos\c04_20261114\20261114_pre_0004.dump` (fuera del repositorio).
- Tamaño: 13156 bytes. Firma: `PGDMP`.
- `pg_restore --list` (dentro de `db`, leyendo el archivo por la entrada estándar): rc=0; `Format: CUSTOM`; 36 entradas de TOC; `pg_dump` y servidor 18.6; 5 entradas `TABLE DATA` (`alembic_version`, `consultorio`, `intento_login`, `sesion`, `usuario`), igual a las 5 tablas del paso 2.
- SHA-256: `bdbff5b176b1cb8efc050fff0d0c03c062a2604b89b4ad68fa47d15054e37ead`.
- Permisos del archivo: heredados de la subcarpeta restringida: Administradores, SYSTEM y la cuenta del autor, con control total.

`pg_restore --list` solo lee el índice del archivo: **no equivale a una restauración integral de prueba**. No se restauró nada sobre la base de desarrollo.

**Estado posterior**: las consultas del paso 2 repetidas dan un resultado idéntico (revisión `0003`, solo el rol `app`, sin roles de C-04 ni esquema `acceso`, mismas filas y huellas). `db` sano; `api` y `frontend` detenidos. A2 no se inició: requiere su propia autorización.

## 13.3 A2: creación de roles (ejecutada por el autor, verificada por Claude; 2026-11-15)

**Resultado: APROBADO.** Roles creados por el autor con el comando administrativo del proyecto; Claude no ejecutó `roles_postgres` ni ninguna sentencia de escritura.

**Ejecución del autor** (desde su PowerShell; salidas transcritas por el autor, sin contraseñas):

1. `docker compose run --rm -it api python -m app.roles_postgres crear`: falló porque no coincidieron las dos entradas de la contraseña de `turnos_app` (error fijo, rollback, sin cambios). Sin `--no-deps`, este comando recreó el contenedor `db` (creado de nuevo a las 00:02:40 UTC, después de A1) porque el `.env` había cambiado.
2. Mismo comando: `rol creado: turnos_acceso_previo`, `rol creado: turnos_acceso_login`, `rol creado: turnos_app`, `rol creado: turnos_login`.
3. `docker compose run --rm -it --no-deps -e DATABASE_URL=postgresql+psycopg://turnos_app@db:5432/sin_uso api python -m app.roles_postgres crear`: los cuatro roles existentes y verificados, sin cambios.

El autor confirmó que las contraseñas de `turnos_app` y `turnos_login` son distintas entre sí y distintas de la administrativa de `app` (el comando no puede compararlas con la de `app`).

**Configuración efectiva** (contenedor efímero `--no-deps`; solo se imprimieron nombres de usuario y si cada variable está definida): `DATABASE_URL` con usuario `turnos_app`, `DATABASE_LOGIN_URL` sin definir y `DATABASE_MIGRATION_URL` con usuario `app`; `Settings` válida. Por eso el segundo intento funcionó sin el override.

**Excepción de secuencia (opción 1 del autor) no necesaria:** el `DATABASE_URL` ficticio del tercer intento solo se usó para pasar `Settings._validar_roles_distintos` y nunca para conectar, y la configuración efectiva ya era válida. No se registra como excepción aplicada. Es una medida temporal, no una configuración permanente.

**Rotación de la contraseña de `turnos_app`:** el autor no recordaba la contraseña ingresada y había puesto la de `app` en `DATABASE_URL`. Con autorización, ejecutó `docker compose run --rm -it --no-deps api python -m app.roles_postgres crear --rotar-contrasena turnos_app`, con la salida `rol existente verificado: turnos_acceso_previo`, `rol existente verificado: turnos_acceso_login`, `contraseña rotada: turnos_app`, `rol existente verificado: turnos_login`, y luego actualizó `DATABASE_URL` en su `.env` con la contraseña nueva. La contraseña de `app` no necesitó rotarse: solo había estado en el mismo `.env`, que ya la contiene.

**Verificación de Claude** (solo lectura; sin leer `.env` ni imprimir URLs o contraseñas):

- Conexión TCP real con `DATABASE_URL` desde un contenedor efímero hacia `db` (regla `host all all all scram-sha-256`, por lo que la contraseña se verificó): `usuario=turnos_app superusuario=False bypassrls=False conexion_tcp=True`, rc=0. Un primer intento devolvió `ProgrammingError` porque la consulta leía `pg_hba_file_rules`, vista reservada a superusuarios: confirma que `turnos_app` no puede leerla; es el único `ERROR` en los logs de `db`.
- Digests de los verificadores (comparados en silencio, sin mostrarlos, contra una referencia tomada antes de la rotación): `turnos_app` CAMBIÓ; `turnos_login` y `app` sin cambios.
- Roles:

| Rol | LOGIN | SUPERUSER | CREATEDB | CREATEROLE | BYPASSRLS | REPLICATION | Contraseña SCRAM |
|---|---|---|---|---|---|---|---|
| `turnos_acceso_previo` | no | no | no | no | no | no | sin contraseña |
| `turnos_acceso_login` | no | no | no | no | no | no | sin contraseña |
| `turnos_app` | sí | no | no | no | no | no | sí |
| `turnos_login` | sí | no | no | no | no | no | sí |

- Membresías: 0 filas. Objetos propios de los roles `turnos_*`: 0. Privilegios `SELECT/INSERT/UPDATE/DELETE` de `turnos_app` y `turnos_login` sobre las cinco tablas: todos `false` (llegan con `0004`).
- `app` conserva superusuario, login, createrole, createdb, bypassrls e inherit.
- Alembic `0003`; esquema `acceso` ausente; filas y huellas de las cinco tablas idénticas a A1; `pg_hba` idéntico a A1.
- Recreación del contenedor `db` (intento 1): misma imagen `postgres:18.6-trixie`, mismo volumen `pgdata`, 0 reinicios, parámetros no predeterminados iguales a los de la imagen; sin efectos sobre configuración persistente ni datos.
- Logs de `db`: ningún `CREATE ROLE` ni `ALTER ROLE` registrado, ningún verificador SCRAM.
- Respaldo A1: SHA-256 `bdbff5b176b1cb8efc050fff0d0c03c062a2604b89b4ad68fa47d15054e37ead` sin cambios; permisos restringidos heredados (Administradores, SYSTEM y la cuenta del autor).

**Limitación:** en A1 no se guardó el digest del verificador de `app`. La referencia más antigua se tomó antes de verificar A2, cuando los intentos del autor ya habían ocurrido. Se confirma que no cambió desde entonces, ni durante la rotación, y que `roles_postgres` nunca ejecuta `ALTER ROLE app`; no existe comparación directa contra A1.

Estado al cerrar A2: `db` sano; `api` y `frontend` detenidos. A3 no se inició: requiere su propia autorización.

## 13.4 A3: migración 0004 en desarrollo (2026-11-15, autorizada por el autor)

**Resultado: APROBADO.** Única escritura en PostgreSQL: el upgrade `0003 -> 0004`.

**Precondiciones repetidas antes de migrar** (solo lectura, todas en verde):

- `db` sano; `api` y `frontend` detenidos.
- Alembic `0003`.
- Los cuatro roles correctos, sin membresías ni objetos propios.
- Esquema `acceso`, políticas, `uq_sesion_consultorio_id_id` y funciones en 0.
- Las 25 columnas que usan los GRANT presentes.
- 0 sesiones y 0 locks ajenos.
- Filas y huellas idénticas a A1.
- Respaldo A1 intacto (SHA-256 `bdbff5b1…37ead`, permisos restringidos).

**Ejecución:** `docker compose run --rm --no-deps -T api alembic upgrade 0004`, con **rc=0**. Usa `DATABASE_MIGRATION_URL` (usuario `app`) y no necesita `DATABASE_LOGIN_URL`. Salida: `Context impl PostgresqlImpl.`, `Will assume transactional DDL.`, `Running upgrade 0003 -> 0004, aislamiento por roles y RLS: privilegios minimos, esquema acceso y politicas` (sin URLs).

**Verificación posterior** (solo lectura, como `app`):

- `alembic_version` = `0004`.
- Esquema `acceso`: dueño `app`, `USAGE` solo para `turnos_app` y `turnos_login`, sin `USAGE` para `PUBLIC`.
- 10 funciones, todas `SECURITY DEFINER` con `search_path=pg_catalog, pg_temp` y sin `EXECUTE` para `PUBLIC`:
  - Dueño `turnos_acceso_login`, `EXECUTE` solo para `turnos_login`: `buscar_cuenta`, `registrar_fallo`, `fallos_de_cuenta`, `fallos_de_ip`, `descartar_fallos_de_cuenta` y `limpiar_intentos`.
  - Dueño `turnos_acceso_previo`, `EXECUTE` solo para `turnos_app`: `resolver_sesion`, `renovar_sesion`, `revocar_sesion_por_token` y `limpiar_sesiones`.
- 11 políticas en `public`:
  - De aislamiento, para `PUBLIC` (`ALL`): `pol_consultorio_aislamiento`, `pol_usuario_aislamiento` y `pol_sesion_aislamiento`.
  - Para `turnos_acceso_previo`: lectura de `consultorio` y `usuario`, y lectura, cambio y limpieza de `sesion`.
  - Para `turnos_acceso_login`: lectura de `consultorio` y `usuario`, y `ALL` sobre `intento_login`.
- RLS habilitada y forzada en `consultorio`, `usuario`, `sesion` e `intento_login`; `alembic_version` sin RLS.
- `uq_sesion_consultorio_id_id` presente: `UNIQUE (consultorio_id, id)`.
- Matriz de privilegios:

| Rol | Lectura | Escritura |
|---|---|---|
| `turnos_app` | `consultorio` (todas las columnas); `usuario` sin `credencial`; `sesion` sin `token_hmac`; nada de `intento_login` | `INSERT (consultorio_id, usuario_id, token_hmac, creada_en, ultimo_uso_en, vence_absoluto_en)` y `UPDATE (revocada_en)` en `sesion` |
| `turnos_login` | ninguna tabla | ninguna |
| `turnos_acceso_previo` | `consultorio (id, nombre, activo)`; `usuario` sin `credencial`; `sesion` completa | `UPDATE (ultimo_uso_en, revocada_en)` y `DELETE` en `sesion` |
| `turnos_acceso_login` | `consultorio (id, codigo, nombre, activo)`; `usuario` con `credencial`; `intento_login` | `INSERT (clave_cuenta, clave_ip, ocurrido_en)`, `UPDATE (descartado_para_cuenta)` y `DELETE` en `intento_login` |

- Roles sin cambios: mismos atributos y ninguna membresía. Los verificadores de `app`, `turnos_app` y `turnos_login` no cambiaron (digests comparados en silencio). `app` conserva sus atributos.
- Filas y huellas de `consultorio` (2), `usuario` (6), `sesion` (0) e `intento_login` (0) **idénticas a A1**. Solo cambió la huella de `alembic_version`, como se esperaba (`0003 -> 0004`).
- Logs de `db` desde el inicio de A3: 0 líneas, 0 `ERROR`, 0 `FATAL`.
- `db` sano; `api` y `frontend` detenidos. Respaldo A1 sin cambios.

Las pruebas funcionales con `turnos_app` y `turnos_login` corresponden al grupo 14. A4 no se inició: requiere la 13.5 y su propia autorización.

## 13.5 Configuración efectiva de las tres conexiones (2026-11-15)

El autor agregó `DATABASE_LOGIN_URL` (usuario `turnos_login`) a su `.env`. Claude no leyó ni modificó el archivo. **Resultado: APROBADO.**

**Configuración efectiva** (contenedor efímero `docker compose run --rm --no-deps -T api python -c …`; solo se imprimieron usuario y host):

- `DATABASE_URL`: usuario `turnos_app`, host `db`.
- `DATABASE_LOGIN_URL`: usuario `turnos_login`, host `db`.
- `DATABASE_MIGRATION_URL`: usuario `app`, host `db`.
- Tres usuarios distintos; `Settings` válida.

**Conexiones TCP reales** desde el contenedor hacia `db` (regla `scram-sha-256`, contraseñas verificadas; transacción de solo lectura; rc=0):

- `DATABASE_LOGIN_URL`: `usuario=turnos_login super=False bypassrls=False createdb=False createrole=False tcp=True`.
- `DATABASE_URL`: `usuario=turnos_app super=False bypassrls=False createdb=False createrole=False tcp=True`.

**Catálogo** (como `app`, `default_transaction_read_only=on`):

- `turnos_login` no tiene privilegios de tabla ni de columna sobre ningún objeto de `public` (0 y 0).
- Tiene `USAGE` en `acceso` y `EXECUTE` sobre las 6 funciones de login (`buscar_cuenta`, `descartar_fallos_de_cuenta`, `fallos_de_cuenta`, `fallos_de_ip`, `limpiar_intentos` y `registrar_fallo`, cuyo dueño es `turnos_acceso_login`). No tiene `EXECUTE` sobre las 4 de sesión. Ninguna función se invocó.
- Alembic `0004`; `pg_isready` rc=0; `db` sano; `api` y `frontend` detenidos; logs de `db` sin `ERROR` ni `FATAL` desde A3.

## 13.6 A4: reconstrucción y arranque de la API (2026-11-15, autorizado por el autor)

**Resultado: APROBADO.** Con esto termina la indisponibilidad de la API, que había empezado en A0.

**Precondiciones** (solo lectura, todas en verde):

- `db` sano (`pg_isready` rc=0); `api` y `frontend` detenidos.
- Catálogo idéntico al verificado en A3 (Alembic `0004`, esquema, funciones, políticas, RLS, privilegios) y huellas iguales a A3.
- Configuración efectiva válida: `DATABASE_URL` con `turnos_app`, `DATABASE_LOGIN_URL` con `turnos_login`, `DATABASE_MIGRATION_URL` con `app`.
- Respaldo A1 intacto; Git sin cambios inesperados.
- Contenedor `db` registrado: creado el 2026-11-15 a las 00:02:40 UTC.

**Riesgo evitado:** la etiqueta `config-hash` del contenedor `db` no coincidía con la configuración actual de Compose (el `.env` cambió después de su recreación). Sin `--no-deps`, `up` lo habría recreado. Por eso `--no-deps` fue obligatorio.

**Ejecución:**

- `docker compose build api`: rc=0, imagen `turnos_odontologia-api` construida (dependencias sin cambios desde C-03).
- `docker compose up -d --no-deps api`: rc=0 (`Recreate`, `Recreated`, `Starting`, `Started`; solo el contenedor `api`).

**Verificación:**

- `api` en ejecución, 0 reinicios. `db`: **el mismo contenedor y la misma fecha de creación** (no se recreó ni reinició). `frontend` sigue detenido.
- `GET http://127.0.0.1:8000/api/health`: **HTTP 200** y `{"status":"ok"}`.
- Logs de `api`: `Started server process` y `Application startup complete.`; 0 líneas con `error` o `traceback`.
- Guardias de rol con conexiones reales (`docker compose exec -T api python -c …` con los motores de la API, sin HTTP ni datos de negocio): `turnos_app guardia OK current_user=turnos_app` y `turnos_login guardia OK current_user=turnos_login`. La guardia `verificar_rol_de_conexion` consultó el catálogo en cada conexión nueva y no encontró violaciones. El health no consulta la base, por eso se verificaron las guardias aparte.
- PostgreSQL: catálogo idéntico al de A3 (Alembic `0004`), huellas iguales a A3, logs de `db` desde el inicio de A4 sin líneas (0 `ERROR`, 0 `FATAL`).

A5 no se inició: requiere su propia autorización.

## Preparación de A5: restablecimiento de la credencial de `administracion.a` (2026-11-15)

El autor no recordaba la contraseña del usuario ficticio `administracion.a@example.test` (Consultorio Demo A), necesaria para las pruebas de humo de 13.7. Con autorización, la restableció desde su PowerShell con el comando del proyecto `docker compose run --rm -it --no-deps api python -m app.credenciales --reemplazar`. Tecleó el código y el email, ingresó la contraseña nueva dos veces con `getpass` y confirmó con `REEMPLAZAR`. La contraseña quedó en el gestor de contraseñas del autor; no se registra en ningún lado. El autor no transcribió la salida del comando; el resultado se comprobó con la verificación siguiente. Esta acción no forma parte del alcance de C-04: es un dato del seed ficticio necesario para A5.

**Verificación posterior** (solo lectura, `default_transaction_read_only=on`; digests comparados en silencio contra una referencia tomada antes del restablecimiento; ningún hash mostrado):

- `md5(credencial)` por usuario: solo cambió `administracion.a`. Las otras cinco cuentas no cambiaron: `administracion.b` conserva su credencial y `secretaria.a`, `odontologia.a`, `secretaria.b` y `odontologia.b` siguen sin credencial.
- `administracion.a`: usuario `01a1a95a-dd90-73e7-9496-c7d22e827a4f`, consultorio `01a1a95a-dd90-73e7-9496-c7d08d776d19` (`c-c7d08d776d19`), rol administrador, activa, consultorio activo; credencial `argon2id`, `v=19`, `m=65536,t=3,p=4` (parámetros de la política).
- Huellas: `consultorio` (2), `sesion` (0), `intento_login` (0) y `alembic_version` sin cambios. `usuario` (6 filas) cambió de `03a0edf4612c014ecb3b96a5ab926bcb` a `2206e1d0e565428adf0ab791c98a3a79` solo por esa credencial: es la nueva referencia de `usuario` para A5 y para 14.4.
- Catálogo de seguridad idéntico al verificado en A3: Alembic `0004`, esquema `acceso`, 10 funciones, 11 políticas, RLS forzada, matriz de privilegios. Roles sin cambios.
- `api` en ejecución con health 200; `db` sano, con el mismo contenedor y la misma fecha de creación; `frontend` detenido.
- Logs de `db` desde A4: sin líneas (0 `ERROR`, 0 `FATAL`).

La 13.7 (A5) no se inició ni se marcó: requiere su propia autorización. La prueba de que la contraseña nueva funciona es el login de A5.

## 13.7 A5: pruebas de humo de autenticación (2026-11-15, autorizadas por el autor)

**Resultado: APROBADO.**

**Precondiciones** (solo lectura, todas en verde):

- `api` en ejecución y `GET /api/health` 200; `db` sano; `frontend` detenido.
- Catálogo, roles y privilegios idénticos a A3; guardias de rol `turnos_app` y `turnos_login` OK.
- `administracion.a` activa con credencial `argon2id m=65536,t=3,p=4`.

Referencias previas, tomadas el 2026-11-15 a las 22:03:55 UTC:

| Tabla | Filas | Huella |
|---|---|---|
| `consultorio` | 2 | `b74c6edfab8ba5d584e63210aa614e49` |
| `usuario` | 6 | `2206e1d0e565428adf0ab791c98a3a79` |
| `sesion` | 0 | vacía |
| `intento_login` | 0 | vacía |

**Script:** `a5_humo.py`, en el directorio temporal de la sesión de Claude, fuera del repositorio. Usa solo la biblioteca estándar y revisado antes de ejecutarlo:

- Destino único `http://127.0.0.1:8000`, sin proxies; `Origin: http://localhost:5173`.
- Cuenta ficticia `c-c7d08d776d19` / `administracion.a@example.test`.
- Contraseña con `getpass`, borrada tras el login. Token y CSRF solo en memoria; nunca impresos ni guardados. De las cookies solo se muestran los atributos.
- Exactamente cinco solicitudes, sin reintentos; termina si el login no da 200.

**Ejecución del autor** (en su PowerShell, una sola vez; resultados transcritos por el autor):

1. `POST /api/auth/login`: **200**, `cache-control=no-store`, CSRF presente, cookie `turnos_session` presente con `HttpOnly`, `SameSite=Lax`, `Max-Age=43200`. Identidad: Administración Demo A, administrador, Consultorio Demo A.
2. `GET /api/auth/me`: **200**, misma identidad.
3. `POST /api/auth/logout`: **204**, cookie borrada con `Max-Age=0`.
4. `GET /api/auth/me` con el token revocado: **401** ("No autenticado").
5. `POST /api/auth/logout` con el token revocado: **401** ("No autenticado").

**Verificación posterior** (solo lectura; `token_hmac` nunca impreso):

- `sesion`: exactamente **1 fila** nueva (`01a1e13f-4f09-79bd-b0e5-ac5a20178315`). Es del Consultorio Demo A (`c-c7d08d776d19`) y de `administracion.a` (administrador), con `consultorio_id` coherente con el del usuario. Creada después del inicio de A5 y **revocada** (`revocada_en` definido, no anterior a `creada_en`). `ultimo_uso_en = creada_en` (el `/me` llegó antes de 60 s y no renovó). Vencimiento absoluto de 12 h; HMAC de 32 bytes. Esto demuestra en la base la revocación que mostró el 401 del paso 4.
- `intento_login`: 0 filas (ningún fallo; el descarte y la limpieza no tuvieron filas que tocar).
- Huellas: `consultorio`, `usuario` y `alembic_version` **iguales** a las referencias; solo cambió `sesion` (de 0 a 1 fila, huella `ec8065a351609b4b93669e8a6b8aee6d`), por el flujo ejecutado. El login no escribió `usuario` (sin rehash).
- Catálogo idéntico a A3 (Alembic `0004`, esquema `acceso`, 10 funciones, 11 políticas, RLS forzada, matriz de privilegios). Roles sin cambios; verificadores de `app`, `turnos_app` y `turnos_login` sin cambios.
- `api` en ejecución con health 200; `db` sano, con el mismo contenedor; `frontend` detenido.
- Logs de `api` desde A5: exactamente `POST /api/auth/login` 200, `GET /api/auth/me` 200, `POST /api/auth/logout` 204, `GET /api/auth/me` 401, `POST /api/auth/logout` 401 y el health 200 de la verificación. 0 `error`, `traceback` o `exception`; 0 `WARNING`; 0 `login_rechazado`.
- Logs de `db` desde A5: dos líneas de checkpoint automático (`checkpoint starting: time` y `checkpoint complete`); 0 `ERROR`, 0 `FATAL`.

El grupo 14 no se inició: requiere su propia autorización.

## 14. Verificación posterior al despliegue (2026-11-15, autorizada por el autor)

**Resultado: APROBADO.** Solo lecturas, sin solicitudes de autenticación nuevas ni cambios de datos. Inicio: 22:15:15 UTC.

### 14.1 Conectividad

- `api` en ejecución.
- `GET http://127.0.0.1:8000/api/health`: HTTP 200, `{"status":"ok"}`.
- `pg_isready` del servicio `db`: rc=0; `db` sano, con el mismo contenedor desde el 2026-11-15 a las 00:02:40 UTC.
- `frontend` detenido.

### 14.2 Rol real de la API

IP del contenedor `api`: `172.18.0.3`. Consulta de solo lectura sobre `pg_stat_activity` y `pg_roles` (conexiones `client backend`, sin la propia):

| `usename` | `client_addr` | Desde `api` | Estado | `rolsuper` | `rolbypassrls` | Conexiones |
|---|---|---|---|---|---|---|
| `turnos_app` | 172.18.0.3 | sí | idle (pool) | f | f | 1 |
| `turnos_login` | 172.18.0.3 | sí | idle (pool) | f | f | 1 |

Las conexiones de la API usan exclusivamente `turnos_app` y `turnos_login` (este último, del pool del login de A5) y ninguno es superusuario ni tiene `BYPASSRLS`. No se generaron solicitudes para provocarlas. Las guardias de rol ya se habían verificado en A4 y A5.

### 14.3 Login, sesiones y permisos

**(a) Login, `/me` y logout:** se reutiliza la evidencia de A5 (sección "13.7"), con decisión del autor. Fue ejecutada después del despliegue A4 con el mismo código y la misma base: login 200, `/me` 200, logout 204, `/me` y logout con el token revocado 401, y la sesión revocada en la base. No se repitió el login ni se creó otra sesión.

**(b) y (c):** script `g14_143.py` (directorio temporal de la sesión de Claude, fuera del repositorio), ejecutado con `docker compose exec -T api python -`.

- Usa los motores reales de la API (`crear_engine` y `crear_engine_login`, con sus guardias de rol).
- Cada escenario es una transacción `READ ONLY` independiente, con `set_config('app.consultorio_id', …, true)` y `ROLLBACK` al terminar.
- Solo `SELECT count(...)`; sin `INSERT`, `UPDATE`, `DELETE` ni funciones de `acceso`.
- Se imprimen solo conteos y SQLSTATE. rc=0.

| Escenario | Rol | Resultado | Esperado |
|---|---|---|---|
| b1 sin contexto | `turnos_app` | `consultorio=0`, `usuario=0`, `sesion=0` | falla cerrada ✅ |
| b2 contexto Demo A | `turnos_app` | `consultorio=1`, `usuario=3`, `sesion=1` (revocada), `0` usuarios y `0` consultorios de otro consultorio | solo sus filas ✅ |
| b3 contexto Demo B | `turnos_app` | `consultorio=1`, `usuario=3`, `sesion=0`, `0` filas de otro consultorio | aislamiento entre consultorios ✅ |
| b4 contexto no UUID | `turnos_app` | SQLSTATE `22P02` | falla cerrada ✅ |
| b5 `usuario.credencial` e `intento_login` | `turnos_app` | SQLSTATE `42501` y `42501` | sin acceso ✅ |
| c1 `SELECT` sobre `consultorio`, `usuario`, `sesion` e `intento_login` | `turnos_login` | SQLSTATE `42501` en las cuatro | sin privilegios de tabla ✅ |

El rechazo de escrituras con el contexto de otro consultorio (`WITH CHECK`) no se probó en desarrollo porque exigiría intentar escribir. Está cubierto por la suite de aislamiento del Verify técnico en `db-test`.

### 14.4 Integridad de datos

Filas y huellas actuales comparadas con A1 (13.2). Solo aparecen las tres diferencias aceptadas por el autor, con causa y alcance verificados nuevamente:

| Tabla | A1 | Ahora | Causa verificada |
|---|---|---|---|
| `consultorio` | 2 · `b74c6edfab8ba5d584e63210aa614e49` | igual | — |
| `intento_login` | 0 | igual | — |
| `usuario` | 6 · `03a0edf4612c014ecb3b96a5ab926bcb` | 6 · `2206e1d0e565428adf0ab791c98a3a79` | Restablecimiento autorizado de la credencial de `administracion.a`. Única credencial distinta de la referencia previa al restablecimiento; las seis credenciales son idénticas a las de la verificación posterior al restablecimiento |
| `sesion` | 0 | 1 · `ec8065a351609b4b93669e8a6b8aee6d` | Sesión `01a1e13f-4f09-79bd-b0e5-ac5a20178315` de A5 (Consultorio Demo A, `administracion.a`), **sigue revocada** |
| `alembic_version` | `0003` · `bf4237522c7b85a4efabdd9d2d3d84a7` | `0004` · `f88e773196fa9b9dc6a5dc9dd4fea330` | Migración A3 |

**Cadena de evidencia del cambio de `usuario`:** la huella de `usuario` fue `03a0edf4…` en A1, A2, A3 y A4, y cambió solo con el restablecimiento. No hay una huella de A1 calculada sin la columna `credencial`; desde ahora queda como referencia `e3b0b6c83c6930d6272f3b2d71d802bc`.

Respecto de las referencias posteriores a A5: **sin ninguna diferencia**.

Además, comprobado en solo lectura:

- Catálogo idéntico a A3: Alembic `0004`, esquema `acceso` (dueño `app`), 10 funciones `SECURITY DEFINER` con dueños, `search_path` y `EXECUTE` correctos, 11 políticas, RLS habilitada y forzada en las cuatro tablas, `uq_sesion_consultorio_id_id` y la matriz de privilegios de tabla y columna.
- Roles con los mismos atributos y sin membresías; verificadores de `app`, `turnos_app` y `turnos_login` sin cambios.
- Respaldo A1: SHA-256 `bdbff5b176b1cb8efc050fff0d0c03c062a2604b89b4ad68fa47d15054e37ead` sin cambios; permisos restringidos heredados (Administradores, SYSTEM y la cuenta del autor).
- Logs de `db` desde el inicio del grupo 14: 14 líneas, **7 `ERROR`, todos esperados**, uno por cada prueba negativa (1 `invalid input syntax for type uuid` de b4; 6 `permission denied`: `usuario` x2, `intento_login` x2, `consultorio` y `sesion`, de b5 y c1). Cada uno va con su `STATEMENT` (`select count(...)` sin datos). 0 `FATAL`, ninguna otra línea.
- Logs de `api` desde el inicio del grupo 14: solo `GET /api/health` 200; 0 `error`, `traceback` o `exception`; 0 `WARNING`.

### 14.5 Cierre de la transición

Con este registro la transición controlada de desarrollo (grupo 13) y su verificación posterior (grupo 14) quedan terminadas sin incidentes. La 13.8 (procedimiento de recuperación) **no fue requerida**: no se ejecutó rollback, downgrade ni restauración.

Pendiente: 15.1 (commit de cierre con autorización del autor) y Archive.

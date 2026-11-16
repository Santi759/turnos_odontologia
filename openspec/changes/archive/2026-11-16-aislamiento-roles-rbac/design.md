# Diseño: aislamiento-roles-rbac (C-04)

> Governance **CRITICO**. Este diseño aplica las decisiones D1 a D8 aprobadas por el autor antes del Propose (aquí DA-01 a DA-08), las decisiones PD-01 (opción B + D), PD-02 (422), PD-03 (contraseñas efímeras), X1 y X2 que el autor tomó en la primera revisión con `/opsx:update` del 2026-11-09 (sección "Decisiones del autor en la revisión") y las decisiones R2-01 a R2-08 de la segunda revisión del mismo día (sección "Decisiones del autor en la segunda revisión: login sin rehash"), que **eliminan el rehash del login** y prevalecen sobre la primera revisión donde la contradigan. Las decisiones derivadas (DD-xx) son propuestas técnicas dentro de ese marco; ya no quedan ramas de diseño abiertas por PD-01. En la tercera revisión del mismo día (sección "Decisiones del autor en la tercera revisión") el autor decidió **PD-04** como configuración inicial de los pools del MVP, **sujeta a validación por pruebas** (DD-33), y el orden del plan: Verify técnico previo a la transición, transición controlada de desarrollo y verificación posterior al despliegue (R3-01 a R3-06). La autorización A0 sigue pendiente (R2-08). **Ninguna parte de este documento autoriza** crear roles en la base de desarrollo, aplicar `0004` en desarrollo, editar el `.env` del autor, reiniciar la API ni hacer commits: cada paso tiene su punto de autorización en `tasks.md` (tarea 0.3 y grupo 13).

## Contexto

Ver `proposal.md` (Why). Estado observado en el código (HEAD 683a4ef):

- **Base**: el único rol no del sistema es `app` (superusuario, `BYPASSRLS`, dueño de la base y de las 5 tablas). La API se conecta como `app` (`main.py`: `crear_engine(settings)` sobre `DATABASE_URL`); el seed, `app.credenciales` y `app.mantenimiento` usan el mismo motor. Sin políticas ni RLS; el esquema `public` no concede `CREATE` a `PUBLIC` (PostgreSQL 18.6).
- **Modelo**: `consultorio` (`id` UUIDv7, `codigo` único), `usuario` (`consultorio_id` FK, `UNIQUE (consultorio_id, id)` `uq_usuario_consultorio_id_id`, `UNIQUE (consultorio_id, email)`, `CHECK rol IN (...)`, `credencial` nula admitida), `sesion` (FK compuesta `(consultorio_id, usuario_id)` → `usuario`, `token_hmac` único), `intento_login` (global, sin `consultorio_id`, claves HMAC de 32 bytes, `descartado_para_cuenta`). `Rol` ya existe como `StrEnum` en `app/models/usuario.py`.
- **Identidad**: `auth/dependencias.py` `identidad_actual` (:123-144) devuelve `IdentidadAutenticada` congelada con `rol: str` (:37) y construye el único `ContextoConsultorio` (:143). `obtener_sesion_db` abre una `Session` por petición desde `app.state.fabrica_sesiones` (FastAPI la cachea por petición: identidad y ruta comparten la misma `Session`). 403 solo se usa para `Origin` y CSRF.
- **Servicio**: `auth/servicio.py` `resolver_identidad` (:196) resuelve y renueva en una transacción y confirma en un `finally` (:204); `iniciar_sesion` (:81) hace todo el login en **una** transacción sobre una `Session`: locks consultivos, bloqueos, `buscar_cuenta`, una verificación Argon2 (real o con el hash ficticio) bajo el cupo de 4 (DD-29 de C-03), fallo o éxito con rehash (`escribir_credencial` con control optimista `credencial IS NOT DISTINCT FROM :esperada`), limpieza, revocación de la sesión entrante, descarte de fallos y `crear_sesion`.
- **Acceso previo**: `auth/acceso_previo.py` concentra 14 operaciones con `text()` sin contexto (`insertar_consultorio`, `buscar_cuenta` que devuelve el hash, `resolver_sesion`, `crear_sesion`, `renovar_sesion`, `revocar_sesion`, `revocar_sesiones_de_usuario`, `registrar_fallo`, `fallos_de_cuenta`, `fallos_de_ip`, `descartar_fallos_de_cuenta`, `limpiar_intentos`, `escribir_credencial`, `limpiar_sesiones`).
- **Repositorios**: `RepositorioAcotado` filtra siempre por `consultorio_id`; `ConsultorioRepositorio` por `id`; `select(Usuario)` selecciona todas las columnas, incluida `credencial`.
- **Esquemas**: `EsquemaEntrada` con `extra="forbid"`; `tests/unit/test_esquemas_sin_consultorio.py` lo recorre.
- **Pruebas**: `tests/integration/conftest.py` `sesion` (transacción exterior + `Session(join_transaction_mode="create_savepoint")`, siempre revierte); `app_auth.crear_app_de_prueba` y `crear_app_real` crean su propio `sessionmaker` sobre esa conexión; `datos_auth.Entorno` (2 consultorios, mismo email, `secretaria`); `test_rutas_protegidas.py` recorre las rutas y su lista blanca. `tests/isolation/` solo tiene `__init__.py` y `scripts/test.ps1` no lo ejecuta. Integración con `TEST_DATABASE_URL` (rol `app` de `db-test`). Línea base: 936 pruebas de C-03 en verde y 15 specs válidas con `--strict`.
- **Alembic**: `env.py` → `resolver_url_de_migracion` (`DATABASE_URL`, o `TEST_DATABASE_URL` con `-x target=test` y la guardia `validar_url_de_pruebas`, que exige el sufijo `_test`).
- **Compose**: `db-test` con `POSTGRES_USER/PASSWORD: app`, `tmpfs`, sin volúmenes ni puertos (la autoprueba exige cero volúmenes); el runner genera `AUTH_SECRET_KEY` efímera y la pasa por nombre. El servicio `api` de desarrollo monta `./backend:/app` y arranca con `uvicorn --reload`: **cualquier cambio de código hecho durante Apply se recarga en caliente en la API de desarrollo si está levantada** (ver "Plan de migración").
- **Prueba existente afectada por DA-06**: `test_dependencias_auth.py` espera hoy contexto A con `consultorio_id` de B en query y en `X-Consultorio-Id`.

## Objetivos / No objetivos

**Objetivos**: cumplir las cuatro capacidades nuevas y las deltas de las modificadas; dejar convenciones verificables que todo Change posterior herede (roles de conexión separados, RLS por tabla, claves compuestas, registro de aislamiento, `require_rol`); que `turnos_app` no tenga **ningún** camino directo ni indirecto para leer o escribir `usuario.credencial`; que **ningún** rol del camino de login (`turnos_login` ni el dueño de sus funciones) pueda escribirla (R2-01); conservar toda la funcionalidad de C-03 y sus 936 pruebas (con los ajustes justificados de "Compatibilidad").

**No objetivos**: endpoints de usuarios (C-05), frontend (C-06), tablas de negocio, permisos de "recursos propios" del odontólogo, membresías multi-consultorio, endpoints públicos (D4), protección completa ante una aplicación comprometida (DD-06), roles de producción o despliegues.

## Decisiones aprobadas por el autor (antes del Propose)

| Id | Decisión del autor | Cómo se aplica |
|---|---|---|
| DA-01 (D1) | Defensa en profundidad: repositorios acotados + convención de claves compuestas verificada por una prueba de esquema + RLS | DD-03, DD-08, DD-19; specs `aislamiento-base-de-datos`, `repositorios-acotados` |
| DA-02 (D2) | `turnos_app` LOGIN sin `SUPERUSER`/`BYPASSRLS`/`CREATEROLE`/`CREATEDB`, sin objetos propios; administración y migraciones con el rol existente `app`; roles **fuera de Alembic** (db-test: script en `/docker-entrypoint-initdb.d`; desarrollo: comando explícito idempotente con autorización); `0004` falla si faltan; credenciales separadas (`DATABASE_MIGRATION_URL`); el autor edita su `.env` | DD-01, DD-02, DD-13, DD-14, DD-15, DD-20, DD-29 |
| DA-03 (D3) | Acceso previo al contexto con funciones `SECURITY DEFINER` de privilegio mínimo, sujetas a revisión de seguridad y pruebas de abuso; la exposición de hashes **no** se acepta automáticamente | DD-09 a DD-12, DD-25 a DD-33; PD-01 y R2-01 decididas |
| DA-04 (D4) | `require_rol` con `Rol` tipado, reutilizable y centralizado; **no** se aprueba la matriz futura; C-04 solo prueba el mecanismo | DD-16, DD-17 |
| DA-05 (D5) | 401 sin identidad; 403 por rol sin consultar existencia; 404 idéntico para ajeno o inexistente | DD-17, DD-18 |
| DA-06 (D6) | Cuerpo con `consultorio_id` → 422 (ya vigente); query `consultorio_id` → 422; cabeceras de una lista **cerrada** → rechazo; nunca derivan el contexto | DD-18; PD-02 y X1 decididas |
| DA-07 (D7) | Un usuario = un consultorio en la v0.1 (se mantienen DC-05/DC-06); sin membresías | Sin cambios de modelo; PA-06 resuelta (tareas de documentación) |
| DA-08 (D8) | Las actualizaciones de documentación son tareas de Apply, no de este Propose | Grupo 11 de `tasks.md` |

## Decisión del autor durante Apply: UNIQUE en `sesion` (2026-11-10, opción 3)

Durante la tarea 3.4 se comprobó que el esquema real de C-03 contradecía la afirmación "ya conforme" de DD-08: `sesion` tiene `consultorio_id` pero no tenía `UNIQUE (consultorio_id, id)` (solo `usuario` lo declaraba; la FK compuesta `sesion` → `usuario` sí era conforme). El autor eligió la **opción 3**: convención DD-08 **uniforme, sin excepciones** y **sin tocar la migración 0003**. Consecuencias:
- `0004` agrega `uq_sesion_consultorio_id_id UNIQUE (consultorio_id, id)` sobre `sesion` (con `op.f(...)`); es trivialmente válida porque `id` ya es PK, no modifica filas y su `downgrade` la elimina, dejando exactamente el esquema de `0003`.
- El modelo `Sesion` declara la misma `UniqueConstraint` con el mismo nombre, de modo que la comparación de metadatos sigue sin diferencias.
- La prueba de esquema (3.4) no admite excepciones.

## Decisiones del autor en la revisión (opsx:update, 2026-11-09)

| Id | Decisión del autor | Cómo se aplica |
|---|---|---|
| PD-01 | Opción **B + D**: rol `turnos_login` y variable `DATABASE_LOGIN_URL` separados para el login; `turnos_app` sin ningún camino directo ni indirecto para leer o modificar `usuario.credencial`; `turnos_login` con los privilegios mínimos de la autenticación; `buscar_cuenta` devuelve el hash solo con usuario y consultorio activos y credencial no nula, manteniendo la verificación ficticia; ~~rehash conservado con salvaguardas~~ (**sustituido por R2-01**: sin rehash en el login); reconocer que una aplicación totalmente comprometida puede abusar de todas sus conexiones (desde DD-34, verificable: el proceso de la API no recibe credenciales de administración) | DD-01, DD-02, DD-09 a DD-11, DD-25 a DD-31, DD-34 |
| PD-02 | 422 para la cabecera prohibida | DD-18 |
| PD-03 | Contraseñas efímeras generadas por el runner para `turnos_app` y `turnos_login` en `db-test`, nunca mostradas ni versionadas | DD-14, DD-21, DD-23 |
| X1 | La lista explícita de cabeceras rechazadas es **solo** `X-Consultorio-Id` (sin distinguir mayúsculas); ninguna otra cabecera ni parámetro se usa jamás como fuente de identidad o de consultorio | DD-18 |
| X2 | Cerrar todas las ramas de diseño ligadas a PD-01; un único plan de implementación | Todo el documento y `tasks.md` |

## Decisiones del autor en la segunda revisión: login sin rehash (opsx:update, 2026-11-09)

Decisiones finales del autor, aplicadas sin ramas. Prevalecen sobre PD-01 en lo que respecta al rehash.

| Id | Decisión del autor | Cómo se aplica |
|---|---|---|
| R2-01 | **Eliminar el rehash automático del login.** El login verifica contraseñas y crea sesiones, pero **nunca** modifica `usuario.credencial`. Es una modificación explícita del comportamiento de C-03 | Delta `autenticacion-sesion`: REMOVED "Contraseñas con Argon2id y rehash" + ADDED "Contraseñas con Argon2id sin rehash en el login"; MODIFIED "Verificaciones de contraseña simultáneas acotadas"; delta `modelo-consultorios-usuarios`; DD-26 |
| R2-02 | Mantener `turnos_login` separado de `turnos_app` | DD-01, DD-25, DD-27 |
| R2-03 | Mantener `turnos_acceso_login` solo si sigue siendo necesario, sin escritura sobre `usuario`; quitar `reemplazar_credencial_por_rehash` y toda función que escriba credenciales; minimizar sus privilegios | DD-25 (sigue siendo necesario: ver allí); "Roles y privilegios"; delta `acceso-previo-al-contexto` |
| R2-04 | Parámetros Argon2id actuales para verificar; sin función de actualización de credenciales desde el login; la exigencia de "parámetros exactos" del rehash desaparece (ya no hay función en la base); la política de hashes **nuevos** queda donde la usa el comando de credenciales | DD-09, DD-26, DD-32 |
| R2-05 | Roles distintos entre `DATABASE_URL`, `DATABASE_LOGIN_URL` y `DATABASE_MIGRATION_URL`, comparando **usuarios** al cargar la configuración (sin exigir hosts ni puertos distintos) y verificando `current_user` en cada conexión (más las guardias de atributos, membresías, dueños y capacidades) | DD-02, DD-29; deltas `configuracion-backend` y `aislamiento-base-de-datos` |
| R2-06 | Dos transacciones solo si hacen falta; reevaluar sin rehash y documentar qué pasa si falla la segunda | DD-27 (siguen haciendo falta) y su tabla de fallos |
| R2-07 | El comando de roles rechaza contraseñas iguales: se mantiene | DD-15 |
| R2-08 | A0 (detener la API de desarrollo) **no** está autorizada todavía: queda como autorización futura separada y pendiente | Tarea 0.3, "Plan de migración" (paso previo A0), "Decisiones pendientes" |

**Limitación aceptada (R2-01), por escrito**: los hashes **no se actualizan automáticamente al iniciar sesión**. Consecuencia: si cambia la política de Argon2id, los hashes existentes conservan sus parámetros anteriores (siguen autenticando) hasta que el administrador restablezca la contraseña de cada cuenta con el comando local. Mitigación: el informe `python -m app.credenciales --revisar-hashes` (DD-32) lista las cuentas afectadas sin mostrar hashes; en la v0.1 todos los hashes ya usan los parámetros vigentes salvo los de pruebas (DT-08).

### Correspondencia con las condiciones obligatorias del autor

| Condición | Decisión |
|---|---|
| 1. RLS cerrada sin contexto | DD-03 |
| 2. Contexto transaccional | DD-04 |
| 3. COMMIT, ROLLBACK, savepoints y fixture | DD-05 |
| 4. Conexiones reales como `turnos_app`/`turnos_login` y credenciales de `db-test` | DD-20, DD-21 |
| 5. Login antes del contexto | DD-10, DD-27 y "Secuencias" |
| 6. Privilegios mínimos por tabla y función | DD-07, DD-25 y "Roles y privilegios" |
| 7. `intento_login` | DD-12 |
| 8. `SECURITY DEFINER` | DD-09, DD-25 |
| 9. Exposición de hashes | DD-11 (decidida), DD-26, DD-30 |
| 10. Límite de RLS ante una aplicación comprometida | DD-06 |
| 11. Credenciales de administración | DD-02, DD-15 |
| 12. Regresión de C-03 | DD-24 y "Compatibilidad" |
| FK y RLS; `FORCE`; superusuario | DD-03, DD-08 |
| 403 antes de buscar | DD-17 |
| Registro de rutas protegidas | DD-22 |
| Paso del runner y autoprueba | DD-23 |

### Respuestas al análisis pedido para PD-01

| Punto | Respuesta |
|---|---|
| 1. Reparto de funciones entre `turnos_app`, `turnos_login`, dueños y `app`; segundo dueño | DD-25 |
| 2. Funciones privilegiadas que el login necesita | DD-25 (lista mínima: 6 tras R2-01) |
| 3. Dueño, privilegios por columna, ACL y análisis de abuso por función | DD-09, DD-25 y "Roles y privilegios" |
| 4. Por qué el rehash no sustituye una contraseña arbitraria | Ya no aplica: no hay rehash (R2-01, DD-26) |
| 5. Identificación exacta de la cuenta verificada | DD-27 (el par de `buscar_cuenta` solo fija el contexto y crea la sesión en T2) |
| 6. Límites de intentos y anti-enumeración | DD-31 |
| 7. Motores, transacciones, orden y fallos | DD-27 |
| 8. Conexión de login restringida al endpoint | DD-28 |
| 9. Datos de autenticación alcanzables por SQL por rol | DD-30 |
| 10. Aislamiento entre consultorios | DD-31 |

## Decisiones del autor en la tercera revisión: pools y orden de Verify (opsx:update, 2026-11-09)

Decisiones finales del autor, aplicadas sin ramas. No modifican ninguna decisión anterior (DA-01 a DA-08, PD-01 a PD-03, X1, X2, R2-01 a R2-08 siguen vigentes).

| Id | Decisión del autor | Cómo se aplica |
|---|---|---|
| R3-01 | **PD-04 aprobada como configuración inicial del MVP**, sujeta a validación por pruebas (no son valores finales de producción). Motor de login (`turnos_login`): `pool_size=4`, `max_overflow=11`, `pool_timeout=30` s, `pool_pre_ping` activo, `connect_timeout=5` s; si no se obtiene conexión dentro de la espera → 503 genérico (mismo cuerpo que el 503 de servicio ocupado existente), `rollback` y **sin** registrar intento fallido. Motor de aplicación (`turnos_app`): `pool_size=5`, `max_overflow=10`, `pool_timeout=30` s, `pool_pre_ping` activo, `connect_timeout=5` s | DD-27, DD-33; requisito "Pool de conexiones del login acotado" (delta `acceso-previo-al-contexto`); tarea 5.5 |
| R3-02 | Estos valores **no garantizan automáticamente** la concurrencia de C-03. PD-04 se valida de forma definitiva solo cuando pasan en `db-test` las nueve pruebas de validación con la configuración **real** de los pools (no `pool_size=50`) y conexiones reales de `turnos_login` y `turnos_app` | DD-33; tareas 5.7 y 12.5 |
| R3-03 | **Regla ante fallos**: si alguna prueba de validación falla, no se cambian las expectativas ni se reduce la cobertura; se detiene el trabajo, se investiga la causa raíz y se presentan alternativas al autor (por ejemplo, `lock_timeout`, pool mayor u otro orden) | DD-33; tarea 5.7 |
| R3-04 | **Orden del plan**: A. Verify técnico previo a la transición (solo `db-test`) → B. Transición controlada de desarrollo (A1, A2, A3, edición manual del `.env` por el autor, A4, A5) → C. Verificación posterior al despliegue. A se completa antes de cualquier cambio en el PostgreSQL de desarrollo | "Plan de migración"; grupos 12, 13 y 14 de `tasks.md` |
| R3-05 | **A0** sigue siendo una autorización separada y pendiente antes del primer cambio de código: solo `docker compose stop api` (nunca `down`, `rm`, `-v` ni `stop` sin servicio), con comprobaciones previas y posteriores; la API se vuelve a levantar solo en A4. Las tareas 0.1, 0.2 y 0.4 pueden ejecutarse antes de A0 (el runner usa contenedores efímeros) | Tarea 0.3; "Plan de migración" |
| R3-06 | Notas de producción fuera del alcance de C-04: medir; `lock_timeout` para los locks consultivos; dimensionamiento por proceso; PgBouncer en modo transacción compatible con `set_config(..., true)` y con locks consultivos de transacción; límites del pool de hilos de AnyIO | DD-33 |

## Decisiones del autor tras la revisión de seguridad RT3 (opsx:update, 2026-11-15)

La revisión de seguridad RT3 que `CHANGES.md` exige al archivar un Change de gobernanza crítica encontró un hallazgo **ALTO** (ALTO-1): el servicio `api` cargaba el mismo `env_file: .env` que `db` y que los comandos de administración, de modo que el proceso permanente de la API recibía `DATABASE_MIGRATION_URL` (rol `app`, superusuario) y `POSTGRES_PASSWORD`. El código de la API nunca las usa, pero su presencia contradecía DD-06 y PD-01. Decisiones del autor, sin ramas:

| Id | Decisión | Dónde |
|---|---|---|
| RT3-01 | Corregir ALTO-1 **antes de Archive**, con la alternativa A: lista explícita de variables para `api`, servicio `admin` separado y efímero para la administración y guardia de arranque de la aplicación web. No se acepta como deuda para un despliegue futuro | DD-34, grupo 16 de `tasks.md` |
| RT3-02 | Los hallazgos bajos (limpieza de sesiones entre consultorios, guardia de rol solo al conectar, privilegios por defecto del esquema `acceso`) se registran como deuda técnica futura y no se implementan en C-04 | DT-10 a DT-12 |
| RT3-03 | Los hallazgos informativos se remiten a la deuda existente (DT-01 a DT-03, DT-05, DT-06) y se registran en `verify.md` junto con el informe RT3 | `verify.md` |
| RT3-04 | Las evidencias de los grupos 13 a 15 se conservan tal como se registraron (comandos con el servicio `api` incluidos); la corrección se ejecuta y se registra en el grupo 16 | `tasks.md`, `verify.md` |
| RT3-05 | Segunda revisión RT3 (2026-11-15): **ALTO-2** — `api` montaba `./backend:/app` con escritura y `admin` ejecuta ese mismo código; un compromiso de `api` podía plantar código que luego corre con la credencial `app`. Se corrige antes de Archive montando el código **de solo lectura** en `api` y en `admin` | DD-34 (ampliación) |
| RT3-06 | **MEDIO-1** — `TEST_DATABASE_URL` en el entorno permanente de `api`, sin garantía de que sea ficticia. Se corrige antes de Archive: el runner genera una contraseña efímera de `db-test`, arma `TEST_DATABASE_URL` en su proceso y la pasa por nombre solo a los contenedores efímeros de prueba | DD-34 (ampliación) |
| RT3-07 | **Bajo-4** — Compose prioriza el shell sobre `.env` al interpolar; `crear_app` no valida los usuarios de `DATABASE_URL` y `DATABASE_LOGIN_URL` al arrancar (la guardia de rol DD-29 rechaza cada conexión indebida). Queda como deuda técnica, sin corrección en C-04 | DT-13 |

## Decisiones derivadas

### DD-01. Roles de PostgreSQL
- `turnos_app`: `LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION`, sin objetos propios. Rol de `DATABASE_URL`: toda la API salvo la transacción de credenciales e intentos del login.
- `turnos_login`: mismos atributos que `turnos_app`, sin objetos propios y **sin privilegios sobre ninguna tabla**. Rol de `DATABASE_LOGIN_URL`: solo la transacción de credenciales e intentos de `POST /api/auth/login` (DD-27, DD-28).
- `turnos_acceso_previo`: `NOLOGIN` con los mismos `NO…`; dueño **solo** de las 4 funciones de sesión de `acceso`, que ejecuta `turnos_app`. Sin ningún privilegio sobre `usuario.credencial` ni sobre `intento_login`.
- `turnos_acceso_login`: `NOLOGIN` con los mismos `NO…`; dueño **solo** de las 6 funciones de cuenta e intentos de `acceso`, que ejecuta `turnos_login` (DD-25). **Sin `INSERT`, `UPDATE` ni `DELETE` sobre `usuario`** (R2-03): solo lee las columnas de la búsqueda de cuenta.
- `app` (existente): superusuario, dueño de la base, del esquema `acceso` y de las tablas; lo usan Alembic y los comandos locales de administración (`DATABASE_MIGRATION_URL`). Como superusuario **siempre** omite RLS, aun con `FORCE`: riesgo aceptado del rol de administración (DT-01), no de la API. Nunca lo usa la API (DD-29).
- Ninguno de los cuatro roles nuevos es miembro de otro rol ni tiene miembros (en particular, ninguno pertenece a `pg_read_all_data`, `pg_write_all_data`, `pg_signal_backend` ni a `app`). `0004` lo verifica (DD-13).
- *Alternativas descartadas*: (1) crear roles en Alembic: las contraseñas son secretos y los roles son de todo el clúster; (2) dueño de funciones con `BYPASSRLS`: ampliaría el impacto de cualquier error en una función a todas las filas de todas las tablas; (3) un único dueño para las 10 funciones: ver DD-25.

### DD-02. Credenciales separadas para la API, el login y la administración
- `DATABASE_URL` → `turnos_app` (API). `DATABASE_LOGIN_URL` (nueva, `SecretStr`, opcional en `Settings` porque los comandos locales no la usan) → `turnos_login`; `crear_app` falla con un mensaje fijo que la nombra si falta. `DATABASE_MIGRATION_URL` (`SecretStr`, opcional) → `app`, usada por Alembic en desarrollo y por `app.seed`, `app.credenciales`, `app.mantenimiento` y `app.roles_postgres` mediante `crear_engine_admin(settings)`, que falla con un mensaje fijo si falta (nunca recurre a `DATABASE_URL` ni a `DATABASE_LOGIN_URL`).
- Validador de `Settings` (R2-05): dos URLs definidas entre `DATABASE_URL`, `DATABASE_LOGIN_URL` y `DATABASE_MIGRATION_URL` con el **mismo usuario** (`make_url(...).username`, comparación exacta tras decodificar, porque los nombres de rol de PostgreSQL distinguen mayúsculas) hacen fallar la carga con un error que nombra ambas variables sin valores, **aunque difieran host o puerto**. No se exige host, puerto ni base distintos: usar la misma instancia con roles distintos es lo normal. La API, además, verifica en cada conexión `current_user` y las capacidades del rol (DD-29), lo que detecta URLs intercambiadas o un rol inesperado.
- `validar_url_de_pruebas` compara también contra `DATABASE_LOGIN_URL` y `DATABASE_MIGRATION_URL`.
- En pruebas: `TEST_DATABASE_URL` sigue siendo `app` de `db-test` (migraciones e integración); el arnés de aislamiento deriva de ella las URLs de `turnos_app` y `turnos_login` cambiando usuario y contraseña (`make_url(...).set(username=..., password=<TURNOS_APP_TEST_PASSWORD | TURNOS_LOGIN_TEST_PASSWORD>)`), sin otras variables con URL.
- **Comando de credenciales (condición 11)**: necesita escribir `usuario.credencial` de cualquier usuario, también de inactivos, y revocar sus sesiones; desde R2-01 es el **único** escritor de credenciales y además ofrece el informe `--revisar-hashes` (DD-32). Corre con el rol de administración y usa consultas propias en `app/auth/acceso_admin.py` (no las funciones de `acceso`, que ocultan la credencial de cuentas no utilizables). `acceso_admin` solo puede importarse desde los comandos locales (prueba estática). Mismo criterio para `mantenimiento` y el seed. **Nunca** usan `turnos_login`.
- *Alternativa*: un rol de administración no superusuario dedicado (`turnos_admin`): queda como deuda antes de cualquier despliegue (DT-01).

### DD-03. Política RLS cerrada por defecto (condición 1)
En `consultorio` (columna `id`), `usuario` y `sesion` (columna `consultorio_id`): `ENABLE` + `FORCE ROW LEVEL SECURITY` y una política permisiva para `PUBLIC` (todas las órdenes):
`USING (<col> = NULLIF(current_setting('app.consultorio_id', true), '')::uuid) WITH CHECK (<misma expresión>)`.
- Sin variable (`NULL`) o vacía (`''`) → `NULL` → la comparación no es verdadera → **cero filas** y toda escritura rechazada.
- Valor no UUID → error `22P02` → fallo cerrado, nunca "todas las filas".
- `FORCE` sujeta también al dueño si alguna vez no fuera superusuario; el superusuario `app` sigue omitiéndola (DT-01).
- `intento_login`: `ENABLE` + `FORCE` sin política para `PUBLIC` y una política `TO turnos_acceso_login` (DD-12).
- Las políticas de lectura y escritura de los dueños (`TO turnos_acceso_previo`, `TO turnos_acceso_login`, `USING (true)`) solo cubren las columnas que cada dueño tiene concedidas: la columna limita lo que la política deja ver.
- `turnos_login` no tiene privilegios de tabla: RLS no le aplica porque ninguna consulta suya llega a las tablas salvo a través de las funciones (que se ejecutan como su dueño).
- *Alternativas descartadas*: `current_setting` sin `missing_ok` (error en lugar de cero filas); políticas `AS RESTRICTIVE` (no hacen falta con una sola política permisiva por rol).

### DD-04. Contexto transaccional desde un evento de la sesión (condición 2)
`app/core/contexto_bd.py`:
- `CLAVE = "consultorio_id"` en `Session.info`.
- `registrar_contexto_transaccional(fabrica)`: escucha `after_begin` de la `sessionmaker` y ejecuta, en la conexión de la transacción que empieza, `SELECT pg_catalog.set_config('app.consultorio_id', :valor, true)` con `str(uuid)` si `session.info[CLAVE]` existe y `''` si no.
- `aplicar_contexto(db, contexto: ContextoConsultorio)`: guarda el UUID en `db.info` y, si la `Session` ya está en una transacción, ejecuta el mismo `set_config(..., true)` de inmediato.
- `fijar_consultorio_de_login(db, consultorio_id)`: solo el login, en la transacción de creación de la sesión sobre la `Session` de `turnos_app` (DD-27), con el `consultorio_id` devuelto por `buscar_cuenta` para la cuenta verificada; no toca `db.info`.
- `crear_fabrica_de_sesiones(engine_o_conexion, **opciones)` registra siempre el evento (fábrica de `turnos_app` y fábricas de prueba). La fábrica de login (`crear_fabrica_de_sesiones_login`) **no** lo registra y nada fija contexto en ella: `turnos_login` no lee tablas (DD-27).
- **Nunca** `SET`/`set_config(..., false)` con un consultorio. Defensa adicional: el evento `reset` del pool del motor de `turnos_app` ejecuta `RESET app.consultorio_id` al devolver la conexión (si falla, la conexión se invalida).
- Prueba estática: la única aparición de `app.consultorio_id` en `app/` es la de `contexto_bd.py`, y `aplicar_contexto`/`fijar_consultorio_de_login` solo se llaman desde `auth/dependencias.py` y `auth/servicio.py` (spec `repositorios-acotados`).
- *Alternativas descartadas*: `SET` de sesión al tomar la conexión (persiste en el pool); fijarlo en cada repositorio (dispersa el punto de control); verificar en `RepositorioAcotado` que el contexto de la base coincide (rompería pruebas existentes; RLS ya impone la coincidencia).

### DD-05. Recuperación del contexto tras COMMIT, ROLLBACK y savepoints (condición 3)
- **COMMIT**: `set_config(..., true)` termina con la transacción; la siguiente transacción de la misma `Session` dispara `after_begin` y lo vuelve a fijar desde `db.info`. `resolver_identidad` confirma en su `finally`; la dependencia aplica el contexto **después**, sin transacción abierta, así que la primera consulta de la ruta abre una transacción que ya lo tiene. Con el pool, tras el `COMMIT` la conexión puede ser otra: el evento cubre ambos casos.
- **ROLLBACK**: revierte el valor; la siguiente transacción lo vuelve a fijar.
- **ROLLBACK TO SAVEPOINT**: revierte los `set_config` locales hechos después del savepoint; `RELEASE` los conserva. `begin_nested()` no dispara `after_begin`.
- **Fixture de integración** (`join_transaction_mode="create_savepoint"`): `after_begin` se dispara al iniciar cada savepoint y fija el valor en la transacción exterior, que siempre se revierte. Como la fixture conecta como `app` (superusuario), RLS no filtra: integración ejerce el camino pero no lo verifica; eso lo hace `tests/isolation/` (DD-20).
- Escenarios probados con conexiones reales de `turnos_app`: COMMIT → siguiente transacción con contexto; ROLLBACK; savepoint revertido; conexión del pool reutilizada sin contexto; transacción sin identidad con `''`.

### DD-06. Límite de RLS y de los roles ante una aplicación comprometida (condición 10)
RLS con `app.consultorio_id` fijado por la propia aplicación **no protege ante una aplicación comprometida**: quien ejecute SQL arbitrario como `turnos_app` puede fijar otro contexto y leer o escribir otro consultorio dentro de los privilegios de `turnos_app` (incluido crear una sesión para cualquier usuario: tiene `INSERT` en `sesion` con su propio `token_hmac`). RLS protege ante **errores de programación**. Contra una inyección en código de negocio actúan los privilegios mínimos (DD-07) y la separación de roles (DD-25): esa inyección no lee ni reescribe hashes, `token_hmac` ni `intento_login`.
**Reconocimiento explícito (PD-01)**: una aplicación **totalmente** comprometida (ejecución de código en el proceso de la API) tiene las credenciales de `turnos_app` y de `turnos_login` (y **solo** esas: desde DD-34 el proceso de la API no recibe `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB` ni `PGPASSWORD`, y la guardia de arranque rechaza crear la aplicación si alguna aparece) y puede abusar de **todas** sus conexiones: leer hashes de cuentas conocidas con `buscar_cuenta` (para atacarlos fuera de línea), crear sesiones con `turnos_app` para cualquier usuario y fijar cualquier contexto. Desde R2-01 **no** puede reescribir credenciales con ninguna conexión de la API. El compromiso del proceso sigue siendo un **riesgo residual explícito**. La separación de roles reduce el impacto de una **inyección SQL acotada a un camino** (negocio frente a login), no el de un compromiso del proceso.
**Corrección RT3 (2026-11-15, RT3-01)**: hasta DD-34 la afirmación anterior **no se cumplía** en la configuración local, porque el servicio `api` cargaba el `.env` completo y su proceso tenía la credencial del superusuario `app`; con ella, un compromiso del proceso podía omitir RLS y reescribir credenciales. DD-34 la vuelve verificable (nombres de variables del contenedor, guardia de arranque y pruebas). Fuera de alcance: quien controle el host, Docker (`docker exec` sobre `db`) o el archivo `.env` (DT-02).
*Alternativas fuera de alcance*: identidad de base por usuario final o contexto firmado verificado en la base; costosas y no exigidas por PA-04.

### DD-07. Privilegios mínimos (condición 6)
Ver "Roles y privilegios". Principios: privilegios por **columna** donde una columna es secreta (`usuario.credencial`, `sesion.token_hmac`); sin `DELETE` para la API; `turnos_app` sin privilegios sobre `intento_login` ni `alembic_version`; `turnos_login` sin privilegios sobre **ninguna** tabla; sin `INSERT`/`UPDATE` sobre `usuario` ni `consultorio` en C-04; `USAGE` explícito en `public` (solo `turnos_app` y los dueños) y en `acceso` (solo `turnos_app` y `turnos_login`), sin `CREATE`. Consecuencias en el código: `Usuario.credencial` y `Sesion.token_hmac` pasan a `deferred=True, deferred_raiseload=True`.

### DD-08. Claves foráneas compuestas además de RLS
Las verificaciones de integridad referencial y de unicidad de PostgreSQL **no aplican RLS**. Por eso toda tabla con `consultorio_id` (salvo `consultorio`) declara `UNIQUE (consultorio_id, id)` y toda FK hacia una tabla de consultorio incluye `consultorio_id` (la FK `sesion` → `usuario` ya la incluía; **`sesion` no declaraba su propio `UNIQUE (consultorio_id, id)` en C-03, así que `0004` lo agrega**, ver la decisión del autor del 2026-11-10). Una prueba de esquema sobre `pg_constraint` lo verifica para todas las tablas de `public` y se prueba a sí misma con una tabla temporal no conforme; otra exige RLS habilitada y forzada en toda tabla de `public` salvo `alembic_version`, y la política exacta de DD-03 en las tablas con `consultorio_id`.

### DD-09. Funciones `SECURITY DEFINER` (condición 8)
- Esquema dedicado `acceso` (dueño `app`), `REVOKE ALL ON SCHEMA acceso FROM PUBLIC`, `GRANT USAGE` solo a `turnos_app` y `turnos_login`. Sin `CREATE` para nadie salvo el dueño.
- Cada función: dueño `turnos_acceso_previo` o `turnos_acceso_login` según DD-25; `SECURITY DEFINER`; `SET search_path = pg_catalog, pg_temp`; objetos calificados (`public.usuario`); `REVOKE ALL ON FUNCTION … FROM PUBLIC` y `GRANT EXECUTE` a **exactamente un** rol (`turnos_app` para las de `turnos_acceso_previo`, `turnos_login` para las de `turnos_acceso_login`); `plpgsql` (todas validan entradas); **sin SQL dinámico** (`EXECUTE`/`format`); como máximo una fila (`proretset` falso).
- **Sin parámetros de entrada `uuid`**, sin excepciones (la única, el rehash, desaparece con R2-01). Las funciones seleccionan por código y email, HMAC del token o clave HMAC de intento.
- Validación de entradas: HMAC y claves exactamente 32 bytes (`22023` si no); código y email no nulos y con longitudes ≤ `MAXIMO_CODIGO`/`MAXIMO_EMAIL` de `EntradaLogin`; instantes no posteriores a `now() + 5 min`; `p_minutos_inactividad` 5–480; límites fijos de 100 filas por limpieza y 5/30 instantes por conteo. Los errores usan mensajes fijos sin valores. La exigencia de "formato exacto de la política" para un hash nuevo desaparece con la función de rehash (R2-04): la base ya no recibe hashes nuevos desde la API.
- Análisis de abuso por función (entradas, salidas, efectos, oráculos, tiempos, filas, errores): ver la tabla de DD-25.
- Prueba de catálogo: para cada función de `acceso`, dueño esperado, `prosecdef`, `proconfig = {search_path=pg_catalog, pg_temp}`, ACL exacta (dueño + un único rol con `EXECUTE`, sin `PUBLIC`), tipos de entrada sin `uuid`, `proretset = false`, `prolang = plpgsql`, sin `EXECUTE` en `prosrc`; y que el conjunto de funciones de `acceso` sea exactamente el de DD-25.
- *Alternativas descartadas*: (1) acceso previo con un rol con `BYPASSRLS`; (2) fijar el contexto antes de resolver la sesión a partir de un dato de la cookie (circular y manipulable).

### DD-10. Autenticación antes de que exista el contexto (condición 5)
Ver DD-27 y "Secuencias". Resumen: la transacción de credenciales del login (T1) corre sobre `turnos_login`, que no lee tablas: locks consultivos, conteo de bloqueos, búsqueda de la cuenta, verificación Argon2, fallos y descarte pasan por las funciones de `turnos_acceso_login` (sin rehash, R2-01). Solo tras una verificación exitosa de una cuenta activa, la transacción de sesión (T2) sobre `turnos_app` fija el contexto **de esa transacción** al consultorio de la cuenta (`fijar_consultorio_de_login`) y crea la sesión con un `INSERT` normal sujeto a `WITH CHECK`. Un login rechazado nunca abre T2 ni fija contexto. La resolución de identidad en cada petición empieza sin contexto: `resolver_sesion` y `renovar_sesion` por HMAC; el contexto se aplica después, en la dependencia.

### DD-11. Exposición de hashes Argon2id (condición 9) — **decidida: PD-01 = B + D**
**Problema**: `buscar_cuenta` debe devolver la credencial para verificarla en Python (Argon2id no existe en PostgreSQL). Si la ejecutara `turnos_app`, una inyección en código de negocio podría obtener hashes de cuentas conocidas (y, en la primera revisión, reemplazarlos con el rehash).

| Opción | Qué protege | Costo | Residual | Estado |
|---|---|---|---|---|
| (a) Función con hash ejecutable por `turnos_app` | Nada adicional | Ninguno | Robo de hashes (y, con el rehash de la primera revisión, toma de cuentas) | Descartada |
| **(b) Rol y motor de login separados** (`turnos_login`, `DATABASE_LOGIN_URL`) | Una inyección en código de negocio (`turnos_app`) no lee ni reescribe hashes (sin privilegio directo ni función alguna que los toque) | Segunda credencial y pool; dos roles dueños; dependencia de `Session` de login; pruebas extra | Inyección en el camino de login (pequeño, parametrizado, revisado) o compromiso del proceso (DD-06) | **Adoptada** |
| (c) Contador de llamadas en `buscar_cuenta` | Frena extracción masiva | Escritura en una lectura; no distingue al legítimo | No impide extracciones dirigidas | Descartada |
| **(d) Hash solo si usuario y consultorio activos y credencial no nula** | Reduce la superficie a cuentas utilizables | Ninguno | Las cuentas utilizables son las valiosas | **Adoptada** |
| (e) Escritura de credenciales | Solo el comando local con el rol de administración (DD-32); **sin rehash en el login** (R2-01, DD-26): ningún rol del camino de login escribe `usuario` | Restablecer contraseñas para cambiar parámetros | Hashes no actualizados automáticamente (DT-08) | **Adoptada (R2-01)** |
| Verificar en la base | — | `pgcrypto` no implementa Argon2 | No viable | — |

### DD-12. `intento_login` solo mediante funciones (condición 7)
| Alternativa | Riesgo ante SQL arbitrario |
|---|---|
| Privilegios directos | Leer todas las claves; borrar filas recientes (reiniciar bloqueos); insertar claves para bloquear cuentas o IP ajenas; descartes masivos |
| RLS por clave | No hay dueño natural de la fila; no reduce el riesgo |
| **Solo funciones de `turnos_acceso_login`, ejecutables solo por `turnos_login` (adoptada)** | Sin lectura de claves existentes; registrar o descartar exige conocer una clave (requiere `AUTH_SECRET_KEY`); limpieza solo > 24 h, ≤ 100 por llamada, instante acotado; conteos solo de la clave dada |
Residual: con SQL como `turnos_login`, inserción de filas con claves aleatorias (crecimiento) o descarte de los fallos de una clave conocida; lo acotan la limpieza y el comando de mantenimiento. `turnos_app` **no** tiene privilegios sobre la tabla **ni** `EXECUTE` sobre ninguna función de intentos: una inyección en negocio no puede reiniciar bloqueos.

### DD-13. Migración 0004: verificación previa y contenido
Bloque `DO` al comienzo que falla (`RAISE EXCEPTION` con mensaje fijo que nombra el rol, sin datos) si: falta alguno de `turnos_app`, `turnos_login`, `turnos_acceso_previo`, `turnos_acceso_login`; `turnos_app` o `turnos_login` no tienen `LOGIN` o tienen `SUPERUSER`/`BYPASSRLS`/`CREATEROLE`/`CREATEDB`/`REPLICATION`; algún dueño tiene `LOGIN` o esos atributos; alguno de los cuatro es miembro de otro rol o tiene miembros; alguno es dueño de tablas, funciones, esquemas o secuencias. Alembic ejecuta la migración en una transacción: el fallo deja la base en `0003` sin cambios. La migración no crea roles ni tablas y no modifica filas. Los nombres de roles son constantes de `app/core/roles_bd.py` (migración, comando de roles, guardias y pruebas).

### DD-14. Roles en `db-test`: script de inicialización
`db/test-init/10_roles_prueba.sh` (versionado, ASCII, montado de solo lectura en `/docker-entrypoint-initdb.d/` de `db-test`): falla (`exit 1`) si `TURNOS_APP_TEST_PASSWORD` o `TURNOS_LOGIN_TEST_PASSWORD` están vacías o son iguales; si no, ejecuta `psql` con `ON_ERROR_STOP=1`, lee los valores con `\getenv` (no aparecen en argumentos de procesos) y crea `turnos_app` y `turnos_login` (`LOGIN PASSWORD :'clave'` con los `NO…`) y `turnos_acceso_previo` y `turnos_acceso_login` (`NOLOGIN` con los `NO…`). Como `db-test` usa `tmpfs`, `initdb` y el script corren en cada arranque. El servicio declara `environment: - TURNOS_APP_TEST_PASSWORD` y `- TURNOS_LOGIN_TEST_PASSWORD` sin valor; si faltan, el script falla y `up --wait` falla (fallo rápido). Los valores quedan en el entorno del contenedor efímero, que el runner elimina siempre al terminar (DT-04).

### DD-15. Roles en desarrollo: comando explícito e idempotente
`docker compose run --rm -it --no-deps admin python -m app.roles_postgres crear [--rotar-contrasena {turnos_app,turnos_login}]` (servicio `admin` desde DD-34; la transición del grupo 13 lo ejecutó con `api`, antes de la corrección): `argparse` antes de conectar → guardia `APP_ENV=local` sin conectar → exige TTY → motor de administración (`DATABASE_MIGRATION_URL`; falla si falta) → verifica que el rol conectado puede crear roles → `turnos_acceso_previo` y `turnos_acceso_login`: crea si faltan; si existen, verifica atributos y membresías y falla si difieren (nunca los "corrige" en silencio) → `turnos_app` y `turnos_login`: si falta, pide la contraseña dos veces con `getpass` y crea el rol con un verificador `SCRAM-SHA-256` calculado del lado del cliente (`PGconn.encrypt_password` de libpq vía psycopg), de modo que la sentencia nunca lleva la contraseña en claro; rechaza que la contraseña de `turnos_login` sea igual a la de `turnos_app` en la misma ejecución (comparación en memoria); si existe, verifica atributos y no toca la contraseña salvo `--rotar-contrasena <rol>` → `COMMIT` → salida solo con textos fijos (`rol creado: <nombre>`, `rol existente verificado: <nombre>`, `contraseña rotada: <nombre>`). Nunca imprime ni registra contraseñas. Costuras de prueba: `leer_oculto`, `es_interactivo`, `abrir_sesion`, `cifrar_contrasena`. Solo se ejecuta en desarrollo con autorización del autor (tarea 12.3); el autor escribe luego las contraseñas en su `.env`.
*Alternativa*: script `psql` manual con `\password` (sin verificación de atributos ni pruebas automatizadas).

### DD-16. `Rol` tipado y `require_rol` (DA-04)
- `IdentidadAutenticada.rol: Rol`. `identidad_actual` convierte con `Rol(valor)`; un valor desconocido → 401 con el cuerpo de no autenticado y un registro con el código fijo `rol_desconocido`.
- `app/auth/autorizacion.py`: `require_rol(*roles: Rol)` valida al declararse (`ValueError` sin roles, `TypeError` si algún valor no es `Rol`) y devuelve una dependencia que depende de `identidad_actual` y responde 403 `{"detail": "Acceso denegado."}` con `Cache-Control: no-store` si el rol no está permitido. Es el **único** lugar con comparaciones de rol (prueba estática).
- La matriz de `03_actores_y_roles.md` sigue siendo [PROP]: C-04 no declara permisos de negocio.
- *Alternativa*: registro central de permisos con nombre; C-05 puede introducirlo sobre `require_rol`.

### DD-17. Orden de respuestas: 401 → 403 → 404 (DA-05)
Convención para rutas protegidas: `verificar_origen` (403, métodos que cambian estado) → `identidad_actual` (401) → `exigir_csrf` (403) → `require_rol` (403) → validación de query y cuerpo (422) → acceso al recurso (404). El rechazo por rol no consulta la base: la prueba cuenta las sentencias sobre `usuario` con `before_cursor_execute` y espera cero. Limitación conocida: un cuerpo JSON malformado se analiza antes de las dependencias y responde 422 antes del 401/403; no revela datos del recurso.

### DD-18. 404 idéntico y consultorio enviado por el cliente (DA-05, DA-06, PD-02, X1)
- **404**: `no_encontrado()` en `app/api/errores.py` → 404 `{"detail": "No encontrado."}` con `Cache-Control: no-store`; la prueba compara estado, cuerpo y cabeceras.
- **Rechazo del consultorio del cliente**: dependencia global `rechazar_consultorio_del_cliente` en `FastAPI(dependencies=[...])` de `crear_app` (y de las apps de prueba), evaluada antes que las dependencias de cada ruta: parámetro de query con nombre `casefold() == "consultorio_id"` o cabecera `X-Consultorio-Id` (comparación sin distinguir mayúsculas; **es la única cabecera de la lista**, X1) → `HTTPException(422)` con `Cache-Control: no-store` y detalle `[{"type": "consultorio_no_admitido", "loc": ["query"|"header", "<nombre>"], "msg": "El consultorio no se acepta del cliente."}]`, sin el valor. **Estado 422 decidido por el autor (PD-02)**: misma clase de error para cuerpo, query y cabecera; 400 ya significa en esta API "condición de la conexión".
- **Otras cabeceras** (`X-Consultorio`, `Consultorio-Id`, `X-Tenant-Id` o cualquier otra): no se rechazan, y **ningún código de la aplicación las lee**. La garantía no es una lista negra sino que la identidad y el consultorio salen solo de la sesión. Prueba estática reforzada: en `app/`, todo acceso a `request.headers`, `request.query_params` o `request.cookies` está en una lista blanca exacta de (módulo, nombre leído) — hoy `Origin`, `Content-Type`, `X-CSRF-Token`, la cookie `turnos_session` y los usados por el propio rechazo —; un acceso nuevo, o la lectura de cualquier nombre que contenga `consultorio` o `tenant` fuera del rechazo, hace fallar la prueba.
- **Efecto en el orden del login**: con el parámetro o la cabecera prohibidos, el 422 precede al 403 de `Origin`, al 400 de dirección y al 415; sin ellos, el orden de C-03 no cambia.

### DD-19. Convención para tablas futuras
Toda tabla nueva con datos de consultorio, en su propia migración: `consultorio_id uuid NOT NULL`; `UNIQUE (consultorio_id, id)`; FK compuestas; `ENABLE` + `FORCE ROW LEVEL SECURITY`; política de DD-03; privilegios mínimos para `turnos_app` por columna; **ningún** privilegio para `turnos_login`; entradas en el registro de aislamiento por cada ruta nueva. Las pruebas de DD-08 y de privilegios hacen fallar la suite si falta algo. `CHANGES.md` dejará de fijar números de migración (tareas de documentación).

### DD-20. Pruebas con conexiones reales de `turnos_app` y `turnos_login` (condición 4)
`tests/isolation/conftest.py`:
- Guardia: `validar_url_de_pruebas(TEST_DATABASE_URL, DATABASE_URL, DATABASE_LOGIN_URL, DATABASE_MIGRATION_URL)`; nunca la base de desarrollo.
- `motor_admin` (rol `app` de `db-test`) para preparar y limpiar datos **confirmados**; `motor_app` y `motor_login` con las URLs derivadas (DD-02) y verificación inicial `current_user` igual al rol esperado, `NOT rolsuper`, `current_database()` termina en `_test`; si falta `TURNOS_APP_TEST_PASSWORD` o `TURNOS_LOGIN_TEST_PASSWORD`, la suite **falla** (no se omite).
- Datos: dos consultorios A y B con un usuario por rol cada uno, credenciales Argon2id ficticias; `TRUNCATE intento_login, sesion, usuario, consultorio` antes y después de cada prueba (motor de administración).
- App real (`crear_app` con `DATABASE_URL` y `DATABASE_LOGIN_URL` derivadas), sin sustituir las fábricas: motores, eventos de contexto y guardias de rol son los de producción. Se inyectan solo reloj, verificador y limitador del servicio, como en C-03.
- Pruebas de RLS y privilegios "en bruto" con conexiones reales de cada rol; `SET ROLE` desde administración solo como complemento.
- El arnés no usa la fixture de transacción revertida: limpia con `TRUNCATE`.

### DD-21. Credenciales de `turnos_app` y `turnos_login` en `db-test` (condición 4) — **decidida: PD-03 = efímeras**
`New-ContrasenaRolPruebaEfimera` en `scripts/lib/Pasos.ps1` (CSPRNG, 32 bytes, base64url sin relleno, 43 caracteres) se llama dos veces por ejecución; los valores (distintos) quedan solo en `$env:TURNOS_APP_TEST_PASSWORD` y `$env:TURNOS_LOGIN_TEST_PASSWORD`, se pasan por nombre (`environment` de `db-test` y `-e` del paso de aislamiento), nunca se muestran ni escriben y se retiran en `finally`. Para ejecutar el arnés a mano hay que generar los valores en la sesión de PowerShell con esa misma función. *Alternativa descartada por el autor*: valor ficticio fijo en `docker-compose.yml`.

### DD-22. Registro de aislamiento obligatorio
`tests/isolation/registro.py` declara `REGISTRO: dict[tuple[str, str], Caso]` con `Caso = RecursoPorId(...) | SesionPropia(justificacion)`. `test_registro.py` reutiliza el recorrido de `tests/integration/test_rutas_protegidas.py` (extraído a `tests/rutas.py`) y exige igualdad exacta entre las rutas de la app real que dependen de `identidad_actual` y las claves del registro; se prueba con una app con una ruta protegida extra no registrada. Hoy: `GET /api/auth/me` y `POST /api/auth/logout` (`SesionPropia`).

### DD-23. Runner y autoprueba
- `scripts/test.ps1`: genera `TURNOS_APP_TEST_PASSWORD` y `TURNOS_LOGIN_TEST_PASSWORD` junto a `AUTH_SECRET_KEY`; paso nuevo **6** `pruebas de aislamiento con los roles turnos_app y turnos_login (db-test)` = `docker compose run --rm --no-deps -e AUTH_SECRET_KEY -e TURNOS_APP_TEST_PASSWORD -e TURNOS_LOGIN_TEST_PASSWORD api python -m pytest -p no:cacheprovider tests/isolation -v`, inmediatamente después de integración; los pasos del frontend pasan a 7 y 8; `finally` retira las tres variables.
- `scripts/tests/autoprueba.ps1`: (1) "Base de pruebas separada y efímera" admite exactamente un montaje `bind` de solo lectura del script de roles y exige las dos variables sin valor en `environment`; (2) formato y unicidad de las contraseñas efímeras; (3) `test.ps1` pasa ambas por nombre, sin literal, y las retira; (4) el paso de `tests/isolation` sigue al de `tests/integration`; (5) el caso aislado "Funciona sin clave en .env" incorpora el script de roles y las contraseñas efímeras; (6) caso aislado: `db-test` sin contraseñas no arranca y no existen los roles de conexión.

### DD-24. Regresión de C-03 (condición 12)
- Las 934 pruebas de backend (pytest) más 2 de Vitest siguen ejecutándose; integración conecta como `app` (superusuario) con ambas fábricas (aplicación y login) sobre la misma conexión de la fixture y ejerce los caminos nuevos.
- `tests/isolation/test_regresion_auth.py` repite con conexiones **reales** de `turnos_app` y `turnos_login` (no solo superusuario): login exitoso y rechazos genéricos (contraseña incorrecta, email y código inexistentes, usuario y consultorio inactivos, sin credencial), `/me`, logout, renovación tras 61 s, login con hash `t=2` **sin cambios en la credencial** (R2-01), límite por cuenta y por IP, descarte tras éxito, revocación de la sesión entrante (también de otro consultorio), CSRF, desactivación con sesión abierta y cambio de `AUTH_SECRET_KEY`.

### DD-25. Reparto de funciones, dueños y concesiones (PD-01; análisis 1–3)
**Lista mínima que necesita el login (6, tras R2-01)**: lo que hoy hace la transacción del login antes de crear la sesión, sin el rehash — contar bloqueos (2), buscar la cuenta (1), registrar el fallo (1), descartar fallos (1) y limpiar intentos (1). Todas pasan a `turnos_login`. `reemplazar_credencial_por_rehash` **se elimina** (R2-03): no existe en `0004`. La creación de la sesión, la revocación de la sesión entrante y la limpieza de sesiones **no** pasan a `turnos_login`: se hacen en T2 con `turnos_app` (DD-27), porque darlas a `turnos_login` exigiría una función que cree sesiones para identificadores dados (acuñar sesiones de cualquier usuario sin tocar hashes) y privilegios de `turnos_login` sobre `sesion`.

**Segundo dueño (decisión: sí; R2-03 lo reconfirma)**: `turnos_acceso_login` sigue siendo necesario porque las 6 funciones de login leen `usuario.credencial` e `intento_login` y su dueño necesita esos privilegios, que `turnos_login` no debe tener (sin privilegios de tabla) y que `turnos_acceso_previo` no puede tener sin abrir un camino de `turnos_app` a `credencial`. Sus privilegios quedan minimizados a **lectura** de las columnas de `buscar_cuenta` y al manejo de `intento_login`; **ningún** privilegio de escritura sobre `usuario`. Con un único dueño de las 10 funciones, ese dueño necesitaría `SELECT (credencial)`, y un error lógico en cualquier función ejecutable por `turnos_app` (por ejemplo, un `JOIN` que devuelva una columna de más en `resolver_sesion`) podría exponer hashes a `turnos_app`. Con dos dueños, la garantía "`turnos_app` no tiene camino indirecto a `credencial`" es **estructural y verificable en el catálogo**: toda función que `turnos_app` puede ejecutar pertenece a `turnos_acceso_previo`, y `turnos_acceso_previo` no tiene ningún privilegio sobre `usuario.credencial` (`has_column_privilege` falso). Costo: un rol `NOLOGIN` más, un bloque de concesiones y políticas más y una fila más en la verificación de `0004`; se acepta.

| Función | Dueño | `EXECUTE` | Entradas | Devuelve | Efectos | Análisis de abuso (quien ejecuta SQL como el rol concedido) |
|---|---|---|---|---|---|---|
| `buscar_cuenta(p_codigo text, p_email text)` | `turnos_acceso_login` | `turnos_login` | código y email normalizados en la función (`lower(btrim)`), longitudes acotadas | 1 fila `OUT`: `consultorio_id`, `usuario_id`, email, nombre, rol, nombre del consultorio, activos, credencial **solo** si ambos activos y no nula (D); todo nulo si no existe | ninguno (`STABLE`) | Oráculo de existencia de cuentas por (código, email) y hashes de cuentas utilizables: requiere conocer el par; sin listado; misma consulta en todos los casos (sin diferencia de tiempo apreciable). Residual: DD-30 |
| `registrar_fallo(p_clave_cuenta bytea, p_clave_ip bytea, p_ocurrido_en timestamptz)` | `turnos_acceso_login` | `turnos_login` | 2 claves de 32 bytes, instante acotado | void | `INSERT` de 1 fila | Bloquear una cuenta o IP ajena exige su clave HMAC (requiere `AUTH_SECRET_KEY`); claves aleatorias solo agregan ruido (limpieza) |
| `fallos_de_cuenta(p_clave_cuenta bytea, p_desde timestamptz)` | `turnos_acceso_login` | `turnos_login` | clave, instante | `timestamptz[]` ≤ 5, solo no descartados | ninguno | Solo instantes de la clave dada; sin claves ni filas ajenas |
| `fallos_de_ip(p_clave_ip bytea, p_desde timestamptz)` | `turnos_acceso_login` | `turnos_login` | clave, instante | `timestamptz[]` ≤ 30 | ninguno | Ídem |
| `descartar_fallos_de_cuenta(p_clave_cuenta bytea)` | `turnos_acceso_login` | `turnos_login` | clave | integer | `UPDATE` de los fallos de esa clave | Reiniciar el bloqueo de una cuenta exige su clave; la IP no se reinicia |
| `limpiar_intentos(p_ahora timestamptz)` | `turnos_acceso_login` | `turnos_login` | instante acotado a `now() + 5 min` | integer | `DELETE` ≤ 100 filas de más de 24 h | No puede borrar fallos recientes (la ventana de bloqueo es de 15 min) |
| `resolver_sesion(p_token_hmac bytea)` | `turnos_acceso_previo` | `turnos_app` | HMAC de 32 bytes | 1 fila `OUT` de sesión + usuario + consultorio, **sin** `token_hmac` ni credencial (el dueño no puede leerlos) | ninguno | Requiere el HMAC de un token (clave de la aplicación + token); HMAC desconocido → sin fila |
| `renovar_sesion(p_token_hmac bytea, p_ahora timestamptz)` | `turnos_acceso_previo` | `turnos_app` | HMAC, instante acotado | boolean | `UPDATE (ultimo_uso_en)` de 1 fila | Misma condición que C-03 (≥ 60 s, sin revocar, antes del absoluto); no extiende el absoluto |
| `revocar_sesion_por_token(p_token_hmac bytea, p_ahora timestamptz)` | `turnos_acceso_previo` | `turnos_app` | HMAC, instante acotado | boolean | `UPDATE (revocada_en)` de 1 fila | Revocar una sesión ajena exige su HMAC |
| `limpiar_sesiones(p_ahora timestamptz, p_minutos_inactividad integer)` | `turnos_acceso_previo` | `turnos_app` | instante acotado, 5–480 | integer | `DELETE` ≤ 100 sesiones inválidas | Solo revocadas o vencidas según el instante acotado; no borra sesiones válidas |

`turnos_app` no ejecuta ninguna de las 6 primeras; `turnos_login` no ejecuta ninguna de las 4 últimas. Ninguna de las 10 escribe `usuario`. `app` (superusuario) puede ejecutarlas todas, pero solo la usan Alembic y los comandos, que no las llaman (usan `acceso_admin`). En Python: `app/auth/acceso_login.py` (las 6 funciones de login; importable solo desde `auth/servicio.py` y `auth/intentos.py`, prueba estática), `app/auth/acceso_previo.py` (las 4 de sesión, la creación de la sesión y la revocación por `id` del logout bajo contexto) y `app/auth/acceso_admin.py` (comandos; único módulo con `escribir_credencial`, DD-32).

### DD-26. Login sin rehash (R2-01, R2-03, R2-04)
- **Comportamiento**: el login verifica la contraseña contra el hash almacenado (real o ficticio) y **nunca** escribe `usuario.credencial`. `ServicioAuth._verificar` devuelve solo si autentica; el login no llama a `necesita_rehash` ni a `hashear`. El cupo de DD-29 de C-03 cubre una sola verificación por login. Un hash Argon2id válido con parámetros anteriores sigue autenticando y queda **idéntico**.
- **En la base**: no existe ninguna función que escriba credenciales; `turnos_acceso_login` no tiene `INSERT`, `UPDATE` ni `DELETE` sobre `usuario` (ni `UPDATE (credencial)`) y no hay política `FOR UPDATE` sobre `usuario` para él; `turnos_login` no tiene privilegios de tabla. Se eliminan de la primera revisión: `reemplazar_credencial_por_rehash`, su `GRANT EXECUTE`, `GRANT UPDATE (credencial) ... TO turnos_acceso_login`, la política `pol_usuario_acceso_login_rehash`, la expresión de "formato exacto de la política" y su prueba de igualdad con `contrasenas.py`, y la excepción de parámetros `uuid`.
- **En Python**: `escribir_credencial` pasa a `acceso_admin` (solo comandos locales); `auth/servicio.py` no importa `acceso_admin` (prueba estática); ninguna ruta escribe `credencial` (prueba estática sobre `app/api/` y `app/auth/`: el único `UPDATE usuario SET credencial` de `app/` está en `acceso_admin.py`).
- **Verificación**: (a) catálogo: ninguna función que `turnos_login` pueda ejecutar pertenece a un rol con `UPDATE` sobre `usuario` o sobre `usuario.credencial` (`pg_proc` × `has_function_privilege` × `has_table_privilege`/`has_column_privilege` del dueño); `turnos_login` y `turnos_acceso_login` sin `INSERT`/`UPDATE`/`DELETE` sobre `usuario`; `to_regprocedure('acceso.reemplazar_credencial_por_rehash(uuid,uuid,text,text)')` nulo; (b) comportamiento: login exitoso con hash `t=2`, exitoso con hash vigente y rechazado → credencial idéntica byte a byte y `xmin` de la fila sin cambios; registro de sentencias sin `UPDATE`/`INSERT`/`DELETE` sobre `usuario`.
- **Por qué es más seguro**: con el rehash, quien controlara el camino de login podía reemplazar el hash de una cuenta conocida y tomarla (DT-05 de la primera revisión). Sin rehash, un camino de login comprometido solo puede **leer** hashes de cuentas conocidas (ataque fuera de línea contra Argon2id de 64 MiB) y no tomar cuentas reescribiéndolos.
- **Limitación aceptada** (R2-01): los hashes no se actualizan automáticamente al iniciar sesión; tras un cambio de política, los existentes conservan sus parámetros hasta que el administrador restablezca la contraseña (DD-32, DT-08). Cambiar la política sigue requiriendo solo cambiar las constantes de `contrasenas.py` (la base no las conoce).
- **Modificación de C-03**: delta `autenticacion-sesion` (REMOVED "Contraseñas con Argon2id y rehash" con **Reason** y **Migration**; ADDED "Contraseñas con Argon2id sin rehash en el login"; MODIFIED "Verificaciones de contraseña simultáneas acotadas", que ya no menciona el rehash) y delta `modelo-consultorios-usuarios` ("Usuario sin credencial utilizable": solo escribe el comando local). Se eligió REMOVED + ADDED y no MODIFIED porque OpenSpec 1.14.1 exige conservar en un MODIFIED todos los escenarios de la spec principal, y el escenario "Rehash al cambiar parámetros" contradice el comportamiento nuevo; renombrarlo con contenido opuesto ("nombre conservado") confundiría la trazabilidad. Pruebas de C-03 afectadas: ver "Compatibilidad".

### DD-27. Motores, transacciones, orden del login y fallos parciales (análisis 7; R2-06)
**¿Siguen haciendo falta dos transacciones? Sí.** Sin rehash, T1 ya no escribe credenciales, pero los dos roles siguen siendo necesarios: `turnos_login` no tiene privilegios de tabla y darle una función que cree sesiones le permitiría acuñar sesiones de cualquier (consultorio, usuario) sin conocer contraseñas desde el camino de login; `turnos_app` no puede hacer T1 porque leería credenciales. Dos roles implican dos conexiones y, por lo tanto, dos transacciones (unirlas exigiría una transacción distribuida, desproporcionada). La sesión se crea en T2 con `turnos_app`, bajo `WITH CHECK` del consultorio de la cuenta verificada.

**¿Argon2 fuera de toda transacción? No (decisión, justificada contra el diseño real de C-03).** En C-03 la atomicidad del conteo se logra con `pg_advisory_xact_lock` por cuenta y luego por IP (`intentos.tomar_locks`), locks **de transacción** que se mantienen desde el conteo hasta el `COMMIT`, cubriendo conteo → verificación → registro del fallo (diseño de C-03: "el lock se mantiene durante la verificación Argon2 (~100 ms) y, en el peor caso, durante la espera de un cupo (≤ 3 s)"). Alternativas evaluadas:
- (a) Verificar fuera de la conexión (T1a conteo y búsqueda, Argon2 sin conexión, T1b registro): al confirmar T1a se liberan los locks y dos intentos concurrentes del mismo par leerían los mismos 4 fallos y ambos se evaluarían → 6 evaluaciones; rompe "Conteo atómico ante intentos concurrentes" (10 → exactamente 5 × 401 y 5 × 429). **Descartada**.
- (b) Locks consultivos de sesión (`pg_advisory_lock`) entre T1a y T1b: siguen atados a la conexión (habría que retenerla igual) y un desbloqueo fallido dejaría locks en una conexión del pool. **Descartada**.
- (c) Reserva previa (registrar el fallo antes de verificar y anularlo si autentica): cambia la semántica de C-03 (el contador de IP cuenta todos los fallos, incluidos los descartados, así que un éxito consumiría cupo de IP) y exige una función de borrado o anulación nueva. **Descartada**.

Por eso la verificación ocurre **dentro de T1**, con la conexión del pool de login retenida durante la espera de los locks, la espera del cupo (≤ 3 s) y la verificación (~50–100 ms, 64 MiB). La `Session` de `turnos_app` de la petición es perezosa y la ruta de login no tiene otra dependencia que la use, así que **no** toma conexión hasta T2: cada login retiene **como máximo una conexión** a la vez. El dimensionamiento del pool de login lo acota (DD-33).

**Secuencia final** (detalle en "Secuencias"): T1 (`turnos_login`): `BEGIN` → locks (cuenta → IP) → conteos → [429: `COMMIT` sin escrituras] → `buscar_cuenta` → cupo [sin cupo: `ROLLBACK`, 503] → una verificación (real o ficticia) → **rechazo**: `registrar_fallo`, `limpiar_intentos`, `COMMIT`, 401 → **éxito**: `descartar_fallos_de_cuenta`, `limpiar_intentos`, `COMMIT` (la conexión vuelve al pool) → T2 (`turnos_app`): `BEGIN` (contexto `''`) → `fijar_consultorio_de_login` → `limpiar_sesiones` → `resolver_sesion(cookie)` y, si es válida, `revocar_sesion_por_token` → `INSERT INTO sesion ... RETURNING id` → `COMMIT` → 200 con cookie y `X-CSRF-Token`.

**Efectos de cada punto de fallo**:

| Punto de fallo | Respuesta HTTP | Estado de la base |
|---|---|---|
| Rechazos previos (422 consultorio del cliente, 403 `Origin`, 400 dirección, 415, 422 cuerpo) | Los de C-03 / DD-18 | Sin conexiones; nada cambia |
| Sin conexión del pool de login dentro de `pool_timeout` (30 s; PD-04, DD-33) | 503 genérico con el cuerpo de servicio ocupado, `Retry-After: 5` y `Cache-Control: no-store` | `rollback` de la sesión de login; nada cambia; sin fallo registrado ni sesión |
| Error de base en T1 antes del `COMMIT` (incluida la guardia de DD-29 al conectar) | 500 genérico sin datos | `ROLLBACK`: nada persiste, sin fallo registrado |
| Bloqueo vigente | 429 con `Retry-After` | `COMMIT` sin escrituras |
| Sin cupo de Argon2 en 3 s | 503 | `ROLLBACK`; sin fallo registrado |
| Excepción del verificador Argon2 (no una contraseña incorrecta) | 500 genérico; cupo liberado (PC-02) | `ROLLBACK`; sin fallo registrado (igual que C-03) |
| Contraseña incorrecta o cuenta no utilizable | 401 genérico | `registrar_fallo` y `limpiar_intentos` confirmados |
| Éxito de T1 | — | Fallos de la cuenta descartados y limpieza confirmados; credencial **intacta** |
| T2 falla (contexto, limpieza, revocación de la entrante, `INSERT` o `COMMIT`) | 500 genérico, sin `Set-Cookie` ni `X-CSRF-Token` | `ROLLBACK` de T2: sin sesión nueva y la sesión entrante **no** se revoca. Persiste T1: los fallos de la cuenta quedan descartados (quien llamó demostró conocer la contraseña) y la limpieza de intentos viejos. Diferencia con C-03 (una sola transacción revertía también el descarte); credencial intacta. El usuario reintenta |
| `COMMIT` de T2 con resultado incierto (conexión perdida durante el `COMMIT`) | 500 genérico | La sesión puede existir sin que el cliente reciba la cookie: queda huérfana, nadie conoce su token, vence por inactividad y `limpiar_sesiones` la borra |
| Desconexión del cliente | La ruta es síncrona (hilo del pool de AnyIO) y no se cancela: el servidor termina T1 y T2 y la respuesta se descarta | Igual que un login completo: fallo registrado si fue rechazo; si fue éxito, descarte confirmado, entrante revocada y sesión huérfana como en la fila anterior |

Intentos: solo se registra fallo en el 401 (login evaluado), nunca en 429, 503 ni 500, como en C-03. El descarte por éxito se confirma en T1, antes de T2. La revocación de la sesión entrante ocurre en T2 y solo persiste si T2 confirma.

- **Dos motores y dos fábricas**, sin conexiones compartidas: `app.state.engine`/`fabrica_sesiones` (`turnos_app`, con el evento de contexto y `RESET` en el reset del pool) y `app.state.engine_login`/`fabrica_sesiones_login` (`turnos_login`, sin evento de contexto, pool acotado de DD-33, reset por defecto, que revierte). Ambos con la guardia de DD-29 en el evento `connect`.
- **Carrera conocida (preexistente en C-03)**: entre la lectura de la cuenta en T1 y el `COMMIT` de T2, el comando de credenciales puede reemplazar la contraseña y revocar las sesiones del usuario; la sesión creada en T2 sobreviviría al reemplazo. La ventana crece de una a dos transacciones (milisegundos). Se documenta (DT-07); cerrarla exigiría que `turnos_app` compare la credencial, que es justamente lo que PD-01 prohíbe. El login nunca sobrescribe la credencial nueva (no escribe).
- **Desactivación concurrente**: si el usuario se desactiva entre T1 y T2, la sesión se crea pero `resolver_sesion` la rechaza en la primera petición (comportamiento de C-03).
- **Contexto**: solo en el motor de `turnos_app`. El motor de login no fija contexto y `turnos_login` no tiene privilegios de tabla, así que el contexto no le afecta.
- **Pruebas** (conexiones reales): T1 y T2 usan conexiones de roles distintos y no coexisten (`current_user` y momentos registrados por eventos); la verificación ocurre con los locks tomados (`pg_locks` consultado desde el verificador de prueba); fallo inyectado en T2 con cuatro fallos previos → sin sesión, fallos descartados, credencial intacta, login posterior 200; pool de una conexión por motor reutilizado entre logins sin contexto residual; el motor de login no ejecuta `set_config` de `app.consultorio_id`; conteo atómico con los roles (10 → 5 × 401 + 5 × 429).

### DD-28. Conexión de login restringida a `POST /api/auth/login` (análisis 8)
- `obtener_sesion_login(request)` (dependencia en `app/auth/dependencias.py`) abre una `Session` de `app.state.fabrica_sesiones_login`. Solo la ruta `POST /api/auth/login` la declara.
- Prueba de recorrido: en la app real, la única ruta (método, camino) cuyo árbol de dependencias contiene `obtener_sesion_login` es `POST /api/auth/login`; una app de prueba con otra ruta que la use hace fallar la verificación.
- Pruebas estáticas: `fabrica_sesiones_login` y `engine_login` de `app.state` solo se mencionan en `app/main.py` y en `obtener_sesion_login`; `crear_engine_login` solo se llama desde `app/main.py`; `obtener_sesion_login` solo se importa en `app/api/auth.py`; `acceso_login` solo desde `auth/servicio.py` y `auth/intentos.py`; los comandos locales (`seed`, `credenciales`, `mantenimiento`, `roles_postgres`) no importan nada de lo anterior ni leen `DATABASE_LOGIN_URL`.
- El servicio recibe ambas `Session` de forma explícita (`iniciar_sesion(db_login, db, ...)`); `resolver_identidad` y `cerrar_sesion` solo reciben la de `turnos_app`.

### DD-29. Guardias de rol de las conexiones de la API
- **Al cargar la configuración** (DD-02, R2-05): usuarios distintos entre las tres URLs; no se comparan host ni puerto.
- **Al crear la app**: sin `DATABASE_LOGIN_URL` → error fijo; la app no arranca.
- **En cada conexión nueva** (evento `connect`, antes de entregarla al pool), consultas de catálogo sin datos de negocio; si alguna falla, se cierra la conexión y la petición termina en un error genérico sin datos:
  - Ambos motores: `current_user` es **exactamente** el rol esperado de ese motor (`turnos_app` o `turnos_login`, constantes de `roles_bd`; R2-05); el rol no es superusuario, no tiene `BYPASSRLS`, `CREATEROLE`, `CREATEDB` ni `REPLICATION`, no es dueño de tablas, funciones ni esquemas y no es miembro de ningún rol.
  - Motor de `turnos_app`: `has_column_privilege(current_user, 'public.usuario', 'credencial', 'SELECT')` y `'UPDATE'` falsos; `has_function_privilege` falso sobre `acceso.buscar_cuenta` (detecta `DATABASE_URL` apuntada a `turnos_login`, además de la comparación de `current_user`).
  - Motor de login: ningún privilegio sobre `consultorio`, `usuario`, `sesion` ni `intento_login`, y `EXECUTE` sobre `acceso.buscar_cuenta`; `has_table_privilege(current_user, 'public.usuario', 'UPDATE')` y `has_column_privilege(..., 'credencial', 'UPDATE')` falsos (detecta `DATABASE_LOGIN_URL` apuntada a `turnos_app` o a `app`).
- Los motores de administración y de pruebas de integración no tienen guardia (usan `app`).

### DD-30. Datos de autenticación alcanzables por SQL según el rol (análisis 9)
| Dato | `turnos_app` | `turnos_login` | Dueños (`NOLOGIN`) | `app` |
|---|---|---|---|---|
| `usuario.credencial` | **No**: ni columna ni función (estructural, DD-25) | Solo **lectura** vía `buscar_cuenta` de un (código, email) exacto, solo cuentas utilizables (D); **ninguna escritura** (R2-01) | `turnos_acceso_login`: solo lectura; `turnos_acceso_previo`: nada | Todo (comando de credenciales, DD-32) |
| `sesion.token_hmac` | Escritura en el `INSERT` de su sesión; **sin lectura**; resolución solo por HMAC exacto | **No** | `turnos_acceso_previo`: lectura (para buscar por HMAC) | Todo |
| `intento_login` (claves y fallos) | **No** | Solo vía funciones por clave exacta: conteos de instantes, registro, descarte, limpieza acotada | `turnos_acceso_login`: todo según DD-12 | Todo |
| Emails y nombres de usuarios | Con contexto de su consultorio (RLS); con SQL arbitrario, de cualquier consultorio fijando el contexto (DD-06); de la sesión resuelta | Solo los de la cuenta del (código, email) que ya conoce | Según columnas concedidas | Todo |
| `consultorio.codigo` | Con contexto (RLS) | No (lo recibe como entrada) | `turnos_acceso_login` | Todo |
No alcanzable por ningún rol de la API: listado de hashes, listado de `token_hmac`, listado de claves de intentos, lectura de `alembic_version`.

### DD-31. Anti-enumeración, límites de intentos y aislamiento preservados (análisis 6 y 10)
- **Anti-enumeración (6)**: mismo 401 genérico para todos los rechazos; `buscar_cuenta` es una única consulta con el mismo plan para cuentas existentes, inexistentes, inactivas o sin credencial; si no devuelve credencial, el verificador corre contra el hash ficticio con los mismos parámetros (exactamente una verificación por login evaluado, escenario de C-03); el cupo de 4 verificaciones (DD-29 de C-03) no cambia y se toma después de evaluar bloqueos y buscar la cuenta, igual que antes; sin rehash, cada login evaluado hace exactamente una operación Argon2 bajo el cupo.
- **Límites de intentos (6)**: los locks consultivos, los conteos y el bloqueo se evalúan en T1 **antes** de la verificación, como en C-03; registrar, contar, descartar y limpiar quedan en la misma transacción que la verificación (T1), con los locks tomados durante la verificación (DD-27), así que el conteo atómico ante intentos concurrentes se conserva.
- **Aislamiento entre consultorios (10)**: RLS para `turnos_app` sin cambios; `turnos_login` no tiene privilegios de tabla y solo ejecuta funciones que devuelven ≤ 1 fila ligada a (código, email) o que actúan sobre claves HMAC de intentos; ninguna escribe `usuario`, así que un login (de A o de quien sea) no puede afectar ninguna credencial; la sesión se crea en T2 bajo `WITH CHECK` con el consultorio de la cuenta verificada.

### DD-32. Mantenimiento administrativo de hashes, local y explícito (R2-01, R2-04)
**Verdad técnica**: un hash Argon2id no puede volver a derivarse con otros parámetros sin la contraseña en claro. Sin rehash en el login, la única forma de llevar una cuenta a los parámetros vigentes es **establecer una contraseña nueva**. Por eso el mantenimiento administrativo solo puede (1) **informar** qué cuentas tienen hashes desactualizados o no admitidos y (2) dejar que el administrador **restablezca** la contraseña de esas cuentas.

- **Dónde**: se **extiende** el comando existente `app.credenciales` (spec `credenciales-locales`) en lugar de crear un módulo nuevo: reutiliza la guardia `APP_ENV=local`, la exigencia de TTY, el motor de administración (`DATABASE_MIGRATION_URL`), las pruebas de salida sin datos sensibles (X1) y la escritura condicionada; así hay **un único** lugar del código que escribe credenciales.
- **Informe**: `docker compose run --rm -it --no-deps admin python -m app.credenciales --revisar-hashes` (servicio `admin` desde DD-34). `--revisar-hashes` y `--reemplazar` son excluyentes (error de argumentos antes de conectar). Flujo: argumentos → guardia `APP_ENV=local` sin conectar → TTY → motor de administración (falla sin `DATABASE_MIGRATION_URL`) → transacción `READ ONLY` → `acceso_admin.listar_credenciales_para_revision` (consultorio, usuario, credencial de **todos** los usuarios, activos o no) → clasificación en memoria con la función pura `contrasenas.clasificar_hash` → `ROLLBACK` → salida.
- **Clasificación** (`clasificar_hash(almacenado) -> EstadoHash`, misma lógica que el verificador): `SIN_CREDENCIAL` (nula); `FORMATO_NO_ADMITIDO` (no empieza con `$argon2id$` o la librería no la analiza: `$argon2i$`, `$argon2d$`, texto arbitrario; estas cuentas **no pueden autenticar** desde C-03); `PARAMETROS_ANTERIORES` (Argon2id analizable con `m`, `t`, `p`, versión, longitud de sal o de hash distintos de la política: `check_needs_rehash` verdadero; **autentican**); `VIGENTE`.
- **Salida** (solo textos fijos, cantidades e identificadores no secretos): `hashes vigentes: N`, `hashes con parámetros anteriores: N`, `hashes con formato no admitido: N`, `usuarios sin credencial: N` y, por cada cuenta con parámetros anteriores o formato no admitido, `restablecer: consultorio <uuid> usuario <uuid>`. Nunca hashes, prefijos de hash, emails, códigos, nombres ni URLs. Los hashes solo existen en memoria del proceso efímero. Limitación: para restablecer con `--reemplazar` el administrador necesita el código y el email de la cuenta, que el informe no muestra (X1); en el entorno local los conoce por el seed ficticio. Una opción de selección por `id` queda fuera de C-04.
- **Restablecimiento**: el `--reemplazar` existente (contraseña dos veces con `getpass`, política de contraseñas nuevas, confirmación `REEMPLAZAR`), que escribe un hash con los parámetros vigentes de `crear_hasher()` y revoca las sesiones del usuario en la misma transacción.
- **Protección ante credenciales modificadas en paralelo (D)**: el comando lee la credencial al buscar la cuenta y escribe con `escribir_credencial(..., esperada=<la leída>)`, un `UPDATE ... WHERE ... AND credencial IS NOT DISTINCT FROM :esperada` dentro de la transacción de administración (comparación e intercambio; ya existe desde C-03). En READ COMMITTED, si otra transacción confirmó un cambio después de la lectura, la condición se reevalúa sobre la versión confirmada y no coincide: 0 filas → `Fallo("la credencial cambió desde que se leyó; reintente")` → `ROLLBACK` (no se escribe y **no** se revocan sesiones). Se prefiere la comparación e intercambio a `SELECT ... FOR UPDATE` porque la lectura ocurre antes de las lecturas interactivas de la contraseña y la confirmación: un `FOR UPDATE` retendría el lock de la fila mientras el administrador escribe, bloqueando cualquier otra escritura de esa cuenta durante un tiempo humano.
- **Sin exposición**: sin endpoint HTTP; `acceso_admin` solo se importa desde los comandos locales (prueba estática); ninguna ruta de `app/api/` ni módulo de `app/auth/` escribe `credencial` (prueba estática); `turnos_app` y `turnos_login` no tienen privilegios para hacerlo (pruebas de catálogo). El comando usa el rol de administración, nunca `DATABASE_URL` ni `DATABASE_LOGIN_URL`.

### DD-33. Conexiones y dimensionamiento de los pools (**PD-04 decidida: configuración inicial del MVP, sujeta a validación por pruebas**)
No hay requisitos de carga en la KB para la v0.1. El autor aprobó (R3-01) la configuración de abajo como **configuración inicial del MVP**, no como valores definitivos de producción. Estos valores **no garantizan por sí solos** la concurrencia de C-03 (R3-02): PD-04 queda validada de forma definitiva solo cuando pasan en `db-test` las nueve pruebas de validación de esta sección con la configuración **real** de los pools (no el `pool_size=50` de las pruebas de C-03) y conexiones reales de `turnos_login` y `turnos_app`.

Datos de partida verificados en el código y en C-03 (lectura, sin ejecutar nada):
- Cupo de Argon2: `CUPOS_POR_PROCESO = 4` y `ESPERA_MAXIMA_SEGUNDOS = 3.0` → 503 (`app/auth/concurrencia.py`; spec de C-03).
- `ServicioAuth.iniciar_sesion` retiene la conexión mientras espera `pg_advisory_xact_lock` (`app/auth/intentos.py`, sin `lock_timeout`), el cupo de Argon2 y la verificación. En C-04, T1 retiene **una** conexión de login durante esas esperas (DD-27); la conexión de `turnos_app` solo se toma en T2, después de devolver la de login.
- La ruta `def login` es síncrona: corre en el pool de hilos de AnyIO (40 hilos por defecto), así que un proceso puede tener hasta ~40 logins en curso.
- `app/core/database.py` crea el motor con `create_engine` solo con `pool_pre_ping=True` y `connect_timeout=5`: valores por defecto de SQLAlchemy (`QueuePool`, `pool_size=5`, `max_overflow=10`, `pool_timeout=30` s).
- Las pruebas de concurrencia de C-03 (`tests/integration/test_concurrencia_login.py`) usan su propio motor con `pool_size=50`, así que el pool nunca fue el cuello de botella en ellas: 40 de una IP → 30 × 401 + 10 × 429; 10 del mismo par → 5 × 401 + 5 × 429; 8 cuentas distintas → máximo 4 verificaciones simultáneas y 8 × 401.
- PostgreSQL: `max_connections = 100` y `superuser_reserved_connections = 3`; `docker-compose.yml` no los cambia. `db` (desarrollo) y `db-test` son instancias separadas. La API de desarrollo es un solo proceso (`uvicorn --reload`).

Configuración inicial aprobada (por proceso de la API):

| Motor | Rol | `pool_size` | `max_overflow` | Máximo | `pool_timeout` | `pool_pre_ping` | `connect_timeout` |
|---|---|---|---|---|---|---|---|
| Login (`crear_engine_login`) | `turnos_login` | 4 | 11 | 15 | 30 s | sí | 5 s |
| Aplicación (`crear_engine_desde_url`) | `turnos_app` | 5 | 10 | 15 | 30 s | sí | 5 s |

- **Valores explícitos** en constantes nombradas de `app/core/database.py` (nunca implícitos por omisión de SQLAlchemy), ambos motores con la guardia de DD-29; una prueba unitaria lee la configuración efectiva de cada pool.
- **Agotamiento del pool de login**: si un login no obtiene conexión dentro de `pool_timeout`, `sqlalchemy.exc.TimeoutError` se traduce al **503 de servicio ocupado existente** (cuerpo `{"detail": "Servicio ocupado. Intente más tarde."}`, `Retry-After: 5`, `Cache-Control: no-store`), con `rollback` de la sesión de login, **sin** registrar intento fallido ni crear sesión (requisito "Pool de conexiones del login acotado"). Un agotamiento del pool de `turnos_app` durante T2 sigue la fila "T2 falla" de DD-27, sin cambios.
- **Por proceso**: los pools y el cupo de Argon2 son **por proceso**; cada proceso adicional de la API suma hasta 30 conexiones y 4 cupos.
- **Presupuesto**: `(15 + 15) × procesos + comandos locales ≤ max_connections − superuser_reserved_connections − margen`. Desarrollo (un proceso): 30 + 1–2 de un comando local ≈ 32 de 97 disponibles. `db-test`: fixture de integración + motores de la app real del arnés (≤ 30) + administración + el motor de 50 de las pruebas de concurrencia de C-03 (que no conviven con otros pools grandes) < 97. El margen es una constante nombrada de la prueba de la condición 9, registrada en `tdd-evidencia.md`.

**Pruebas de validación de PD-04** (tarea 5.7; solo `db-test`; app real con la configuración real de los pools y conexiones reales de `turnos_login` y `turnos_app`):
1. 40 intentos concurrentes desde la misma IP (pares distintos) → exactamente 30 × 401 y 10 × 429.
2. 10 intentos concurrentes de la misma cuenta → 5 × 401 y 5 × 429.
3. 8 intentos concurrentes de cuentas distintas → 8 × 401.
4. Como máximo 4 verificaciones Argon2 simultáneas por proceso (verificador de prueba bloqueado hasta una señal).
5. Agotamiento forzado con un motor de login de prueba (`pool_size=1`, `max_overflow=0`, `pool_timeout` corto y la conexión retenida) → 503 genérico y `rollback`.
6. Sin contaminación de contexto entre conexiones reutilizadas: `app.consultorio_id` vacío al reutilizar una conexión de `turnos_app`.
7. Ningún 503 (pool o cupo) registra un intento fallido.
8. Ninguna conexión retenida al terminar (`checkedout() == 0` en ambos pools) y ningún lock consultivo tomado (`pg_locks`).
9. Presupuesto de conexiones correcto considerando ambos pools, los comandos locales y la cantidad de procesos de la API (prueba unitaria de configuración; documenta que pools y cupo son por proceso).

**Regla ante fallos (R3-03)**: si cualquiera de estas pruebas falla, **no** se cambian las expectativas ni se reduce la cobertura; se detiene el trabajo, se investiga la causa raíz y se presentan alternativas al autor (por ejemplo, `lock_timeout` para los locks consultivos, pool mayor u otro orden de adquisición). No se avanza a la transición de desarrollo (grupo 13) sin su decisión.

**Notas para producción (fuera del alcance de C-04; R3-06)**: medir con carga real antes de fijar valores; `lock_timeout` para la espera de los locks consultivos; dimensionar por proceso (pools y cupo se multiplican por la cantidad de procesos); si se usa PgBouncer, modo transacción compatible con `set_config(..., true)` y con `pg_advisory_xact_lock` (ambos de alcance de transacción); límites del pool de hilos de AnyIO.

**Riesgos residuales**: (1) ráfagas de una sola IP retienen conexiones de login mientras esperan el lock de esa IP (sin `lock_timeout`): con 15 conexiones y 30 s de espera, otros usuarios pueden esperar o recibir 503 (disponibilidad, sin pérdida de confidencialidad; misma clase que DT-11 de C-03); (2) con 40 hilos de AnyIO y 15 conexiones de login, los logins restantes esperan conexión ocupando hilos hasta 30 s. Las condiciones 1 a 3 y 8 los ejercen.
- *Alternativas*: la propuesta anterior (4 + 4 con espera de 3 s) queda sustituida por R3-01; `max_overflow=0` (las esperas de locks consumirían todo el pool); valores por defecto implícitos (no documentan la decisión).

### DD-34. Separación del entorno de la API y del entorno administrativo (RT3-01)

**Problema** (ALTO-1): `api` y la administración compartían `env_file: .env`; el proceso permanente de la API recibía la credencial de superusuario. **Objetivo**: que el proceso de la aplicación web reciba solo lo que necesita y que toda operación con la credencial `app` ocurra en un contenedor efímero distinto.

**Servicio `api` (permanente)**:
- Sin `env_file`. Un mapa `environment` con **exactamente** estas claves, cada una con su valor interpolado de forma explícita desde `.env` (`CLAVE: ${CLAVE...}`; nunca la forma de lista sin valor, que tomaría el valor del shell): obligatorias con `${CLAVE:?mensaje}` (`DATABASE_URL`, `DATABASE_LOGIN_URL`, `AUTH_SECRET_KEY`, `CORS_ALLOWED_ORIGINS`, `APP_ENV`); opcionales con `${CLAVE:-}` (`AUTH_SESSION_MINUTES`, `AUTH_SESSION_MAX_HOURS`, `AUTH_COOKIE_SECURE`), y el literal `WATCHFILES_FORCE_POLLING` (nueve claves desde RT3-06; la primera versión de DD-34 incluía `TEST_DATABASE_URL`).
- `TEST_DATABASE_URL` **no** forma parte del entorno permanente (RT3-06): el runner la entrega por nombre solo a los contenedores efímeros de prueba (ver "Ampliación RT3" abajo).
- Nunca recibe `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB` ni `PGPASSWORD`.
- `Settings` pasa a ignorar variables vacías (`env_ignore_empty=True`): una opcional interpolada vacía toma su valor por defecto; una obligatoria vacía sigue fallando.

**Servicio `admin` (efímero)**:
- Misma imagen del backend (un `image` común, construida una sola vez), `env_file: .env`, montaje `./backend:/app:ro` (RT3-05), `depends_on: db` (los comandos documentados usan `--no-deps`), **sin `ports`**, `restart: "no"`, `profiles: ["admin"]` y **ningún** otro servicio depende de él.
- Uso exclusivo: `docker compose run --rm --no-deps admin <comando>` (`-it` cuando el comando pide datos): `alembic upgrade head` (y `alembic current`), `python -m app.seed`, `python -m app.credenciales [...]`, `python -m app.roles_postgres crear [...]`, `python -m app.mantenimiento`.
- **El perfil no basta** para impedir un uso permanente: `docker compose up admin` o `docker compose --profile admin up` lo seleccionan explícitamente. Por eso su **comando por defecto termina de inmediato** con código distinto de cero y un mensaje fijo que indica usar `docker compose run --rm --no-deps admin <comando>`; con `restart: "no"` el contenedor queda detenido y nunca sirve peticiones. Además, la guardia de arranque de la aplicación web (abajo) **rechaza** crear la aplicación con el entorno de `admin`: aunque se le pidiera `uvicorn`, no hay API con credenciales de administración. La autoprueba del runner verifica estas propiedades en `docker-compose.yml` y la verificación posterior comprueba que no queda ningún contenedor `admin` en ejecución.

**Guardia de arranque de la aplicación web** (`crear_app`, antes de crear motores; excepción `CredencialAdministrativaEnLaApi` con mensaje fijo que **solo nombra** las variables):
- Rechaza si `settings.database_migration_url` está definida.
- Rechaza si el entorno del proceso define `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD` o `PGPASSWORD`.
- Se aplica a la aplicación web (incluido `uvicorn --factory app.main:crear_app`) y a toda prueba que la construya. **No** afecta a los comandos administrativos legítimos: Alembic, `seed`, `credenciales`, `roles_postgres` y `mantenimiento` no llaman a `crear_app` y siguen usando `DATABASE_MIGRATION_URL` con `abrir_sesion_de_administracion`.

**Propagación accidental desde PowerShell**: una variable definida en el shell **no** llega a `api` porque `api` no tiene `env_file` y solo recibe las claves de su mapa; el shell solo puede influir en esas claves (Compose prioriza el shell sobre `.env` al interpolar), y si alguien pusiera la credencial `app` en `DATABASE_URL` o `DATABASE_LOGIN_URL`, la guardia de rol (DD-29) rechaza la conexión (`ROL_INESPERADO`, `SUPERUSER`). Pasarla con `-e` a `api` la expone al proceso, pero la guardia de arranque rechaza la aplicación web. El runner (`scripts/test.ps1`) **se niega a empezar**, con un mensaje que solo nombra las variables, si el proceso de PowerShell define `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD` o `PGPASSWORD`, y nunca las pasa con `-e`.

**Comandos que cambian**: solo el servicio (`api` → `admin`); argumentos y salidas iguales. Usar `api` para administrar **falla cerrado** con el mensaje fijo existente que menciona `DATABASE_MIGRATION_URL`, sin conectar. El runner sigue usando `api` (pytest y `alembic -x target=test`), ahora sin credenciales de administración de desarrollo; la guardia de base de pruebas sigue comparando `TEST_DATABASE_URL` con `DATABASE_URL` y `DATABASE_LOGIN_URL`.

**Base de desarrollo**: la corrección **no** modifica PostgreSQL (Alembic `0004`, RLS, roles, privilegios y datos intactos). Despliegue: recrear solo `api` con `docker compose up -d --no-deps api` (`--no-deps` obligatorio: el `config-hash` de `db` está desactualizado y `up` sin esa opción lo recrearía), con autorización A6 del autor. `.env` y `.env.example` no cambian.

**Ampliación RT3 (segunda revisión, 2026-11-15; RT3-05 y RT3-06)**:

- **Código de solo lectura (ALTO-2)**: `api` y `admin` montan `./backend:/app:ro`; ningún otro montaje escribible sobre el código, sin `privileged`, `cap_add` ni `security_opt` nuevos. Así un compromiso del proceso de la API no puede modificar el código que después ejecuta `admin` con la credencial `app`. Escrituras legítimas revisadas: `PYTHONDONTWRITEBYTECODE=1` (imagen) evita los `.pyc`; pytest corre con `-p no:cacheprovider` y sus archivos temporales van a `tmp_path` (`/tmp`); Alembic (`upgrade`, `current`), el seed y los comandos de credenciales, roles y mantenimiento no escriben en `/app`; `uvicorn --reload` solo lee y detecta cambios hechos en el host. Limitación aceptada: las migraciones nuevas se escriben en el host (editor), no con `alembic revision` dentro de un contenedor. Fuera de alcance: quien controle el host o el árbol del repositorio.
- **URL de pruebas efímera (MEDIO-1)**: `scripts/test.ps1` genera en cada ejecución una contraseña aleatoria del superusuario de `db-test` (`TURNOS_DB_TEST_PASSWORD`, mismo tratamiento que las de los roles), `db-test` la recibe interpolada en `POSTGRES_PASSWORD` (`${TURNOS_DB_TEST_PASSWORD:-}`: sin ella, PostgreSQL no inicializa y `db-test` no arranca) y el runner arma `TEST_DATABASE_URL` en su propio proceso con host `db-test` y base `turnos_test`. Solo se pasa por nombre (`-e TEST_DATABASE_URL`) a los contenedores efímeros de las migraciones de pruebas, de integración y de aislamiento, y se retira al terminar. Ninguna contraseña de `db-test` queda en archivos versionados, imágenes ni salidas. La guardia de base de pruebas (`validar_url_de_pruebas`) no cambia. `TEST_DATABASE_URL` de `.env` deja de usarse (DT-14). Sin servicio de pruebas adicional.

*Alternativas descartadas*: archivos `.env.api` y `.env` separados (nueva plantilla y edición manual de archivos privados, más superficie de error); solo la guardia (la API no arrancaría sin separar el entorno); ejecutar la administración en `db` (la imagen no tiene la aplicación).

## Roles y privilegios

| Objeto | `turnos_app` | `turnos_login` | `turnos_acceso_previo` (dueño de 4 funciones de sesión) | `turnos_acceso_login` (dueño de 6 funciones de login) | `app` |
|---|---|---|---|---|---|
| Esquema `public` | `USAGE` | — | `USAGE` | `USAGE` | dueño |
| Esquema `acceso` | `USAGE` | `USAGE` | — | — | dueño |
| `consultorio` | `SELECT` (todas) + política de consultorio | — | `SELECT (id, nombre, activo)` + `FOR SELECT USING (true)` | `SELECT (id, codigo, nombre, activo)` + `FOR SELECT USING (true)` | dueño |
| `usuario` | `SELECT (id, consultorio_id, email, nombre, rol, activo, creado_en)` — **sin `credencial`** | — | `SELECT (id, consultorio_id, email, nombre, rol, activo)` + `FOR SELECT USING (true)` — **sin `credencial`** | `SELECT (id, consultorio_id, email, nombre, rol, credencial, activo)` + `FOR SELECT USING (true)` — **sin `INSERT`, `UPDATE` ni `DELETE`** (R2-03) | dueño |
| `sesion` | `SELECT` sin `token_hmac`; `INSERT (consultorio_id, usuario_id, token_hmac, creada_en, ultimo_uso_en, vence_absoluto_en)`; `UPDATE (revocada_en)`; sin `DELETE` | — | `SELECT`, `UPDATE (ultimo_uso_en, revocada_en)`, `DELETE` + políticas `FOR SELECT/UPDATE/DELETE USING (true)` | — | dueño |
| `intento_login` | — | — | — | `SELECT`, `INSERT (clave_cuenta, clave_ip, ocurrido_en)`, `UPDATE (descartado_para_cuenta)`, `DELETE` + `FOR ALL USING (true) WITH CHECK (true)` | dueño |
| `alembic_version` | — | — | — | — | dueño |
| Funciones de `acceso` | `EXECUTE` solo sobre las 4 de `turnos_acceso_previo` | `EXECUTE` solo sobre las 6 de `turnos_acceso_login` | dueño de 4 | dueño de 6 | superusuario |

**Escritura de `usuario.credencial`**: ningún rol del camino de la API la tiene (`turnos_app`, `turnos_login`, `turnos_acceso_previo`, `turnos_acceso_login`: todos sin `UPDATE` de tabla ni de columna); solo `app` (comando local, DD-32).

Justificación: `consultorio` completo para `turnos_app` porque ningún dato es secreto; `usuario` sin `credencial` para `turnos_app` **y** para el dueño de las funciones que ejecuta (DD-25); `sesion` sin `token_hmac` en lectura; `turnos_login` sin tablas (solo funciones); `intento_login` solo para `turnos_acceso_login`; `turnos_acceso_login` limitado a leer las columnas de `buscar_cuenta` (las de nombre y rol hacen falta para la respuesta del login). Si PostgreSQL exigiera `USAGE` sobre la secuencia de identidad de `intento_login`, se concede solo a `turnos_acceso_login` (verificado por prueba). C-05 agregará `INSERT`/`UPDATE` sobre columnas de `usuario` para `turnos_app` (nunca `credencial`).

## Esbozo de la migración 0004 (diseño, no se crea en el Propose)

```sql
-- revision 0004, down_revision 0003. Una sola transaccion. Sin roles, tablas ni filas.
DO $$
DECLARE r pg_catalog.pg_roles%ROWTYPE; nombre text;
BEGIN
  FOREACH nombre IN ARRAY ARRAY['turnos_app', 'turnos_login'] LOOP
    SELECT * INTO r FROM pg_catalog.pg_roles WHERE rolname = nombre;
    IF NOT FOUND THEN RAISE EXCEPTION 'falta el rol %: crearlo antes de aplicar 0004', nombre; END IF;
    IF NOT r.rolcanlogin OR r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication THEN
      RAISE EXCEPTION 'el rol % tiene atributos no admitidos', nombre; END IF;
  END LOOP;
  FOREACH nombre IN ARRAY ARRAY['turnos_acceso_previo', 'turnos_acceso_login'] LOOP
    SELECT * INTO r FROM pg_catalog.pg_roles WHERE rolname = nombre;
    IF NOT FOUND THEN RAISE EXCEPTION 'falta el rol %: crearlo antes de aplicar 0004', nombre; END IF;
    IF r.rolcanlogin OR r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication THEN
      RAISE EXCEPTION 'el rol % tiene atributos no admitidos', nombre; END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members m
               JOIN pg_catalog.pg_roles a ON a.oid = m.member
               JOIN pg_catalog.pg_roles b ON b.oid = m.roleid
              WHERE a.rolname IN ('turnos_app','turnos_login','turnos_acceso_previo','turnos_acceso_login')
                 OR b.rolname IN ('turnos_app','turnos_login','turnos_acceso_previo','turnos_acceso_login')) THEN
    RAISE EXCEPTION 'los roles de la aplicacion no deben tener membresias'; END IF;
  -- (igual que antes) ningun objeto de pg_class, pg_proc ni pg_namespace pertenece a esos cuatro roles
END $$;

-- DD-08 (decision del autor 2026-11-10): convencion uniforme tambien en sesion.
ALTER TABLE public.sesion ADD CONSTRAINT uq_sesion_consultorio_id_id UNIQUE (consultorio_id, id);

CREATE SCHEMA acceso;
REVOKE ALL ON SCHEMA acceso FROM PUBLIC;
GRANT USAGE ON SCHEMA acceso TO turnos_app, turnos_login;
GRANT USAGE ON SCHEMA public TO turnos_app, turnos_acceso_previo, turnos_acceso_login;

-- turnos_app
GRANT SELECT ON public.consultorio TO turnos_app;
GRANT SELECT (id, consultorio_id, email, nombre, rol, activo, creado_en) ON public.usuario TO turnos_app;
GRANT SELECT (id, consultorio_id, usuario_id, creada_en, ultimo_uso_en, vence_absoluto_en, revocada_en)
  ON public.sesion TO turnos_app;
GRANT INSERT (consultorio_id, usuario_id, token_hmac, creada_en, ultimo_uso_en, vence_absoluto_en)
  ON public.sesion TO turnos_app;
GRANT UPDATE (revocada_en) ON public.sesion TO turnos_app;
-- turnos_acceso_previo (sin credencial ni intento_login)
GRANT SELECT (id, nombre, activo) ON public.consultorio TO turnos_acceso_previo;
GRANT SELECT (id, consultorio_id, email, nombre, rol, activo) ON public.usuario TO turnos_acceso_previo;
GRANT SELECT, DELETE ON public.sesion TO turnos_acceso_previo;
GRANT UPDATE (ultimo_uso_en, revocada_en) ON public.sesion TO turnos_acceso_previo;
-- turnos_acceso_login (sin sesion)
GRANT SELECT (id, codigo, nombre, activo) ON public.consultorio TO turnos_acceso_login;
GRANT SELECT (id, consultorio_id, email, nombre, rol, credencial, activo) ON public.usuario TO turnos_acceso_login;
-- R2-03: ningun INSERT, UPDATE ni DELETE sobre usuario para turnos_acceso_login.
GRANT SELECT, DELETE ON public.intento_login TO turnos_acceso_login;
GRANT INSERT (clave_cuenta, clave_ip, ocurrido_en) ON public.intento_login TO turnos_acceso_login;
GRANT UPDATE (descartado_para_cuenta) ON public.intento_login TO turnos_acceso_login;
-- turnos_login: ningun privilegio de tabla.

-- RLS forzada (DD-03)
ALTER TABLE public.consultorio   ENABLE ROW LEVEL SECURITY; ALTER TABLE public.consultorio   FORCE ROW LEVEL SECURITY;
ALTER TABLE public.usuario       ENABLE ROW LEVEL SECURITY; ALTER TABLE public.usuario       FORCE ROW LEVEL SECURITY;
ALTER TABLE public.sesion        ENABLE ROW LEVEL SECURITY; ALTER TABLE public.sesion        FORCE ROW LEVEL SECURITY;
ALTER TABLE public.intento_login ENABLE ROW LEVEL SECURITY; ALTER TABLE public.intento_login FORCE ROW LEVEL SECURITY;

CREATE POLICY pol_consultorio_aislamiento ON public.consultorio
  USING (id = NULLIF(current_setting('app.consultorio_id', true), '')::uuid)
  WITH CHECK (id = NULLIF(current_setting('app.consultorio_id', true), '')::uuid);
CREATE POLICY pol_usuario_aislamiento ON public.usuario
  USING (consultorio_id = NULLIF(current_setting('app.consultorio_id', true), '')::uuid)
  WITH CHECK (consultorio_id = NULLIF(current_setting('app.consultorio_id', true), '')::uuid);
CREATE POLICY pol_sesion_aislamiento ON public.sesion
  USING (consultorio_id = NULLIF(current_setting('app.consultorio_id', true), '')::uuid)
  WITH CHECK (consultorio_id = NULLIF(current_setting('app.consultorio_id', true), '')::uuid);
CREATE POLICY pol_consultorio_acceso_previo ON public.consultorio FOR SELECT TO turnos_acceso_previo USING (true);
CREATE POLICY pol_usuario_acceso_previo ON public.usuario FOR SELECT TO turnos_acceso_previo USING (true);
CREATE POLICY pol_sesion_acceso_previo_lectura ON public.sesion FOR SELECT TO turnos_acceso_previo USING (true);
CREATE POLICY pol_sesion_acceso_previo_cambio ON public.sesion FOR UPDATE TO turnos_acceso_previo
  USING (true) WITH CHECK (true);
CREATE POLICY pol_sesion_acceso_previo_limpieza ON public.sesion FOR DELETE TO turnos_acceso_previo USING (true);
CREATE POLICY pol_consultorio_acceso_login ON public.consultorio FOR SELECT TO turnos_acceso_login USING (true);
CREATE POLICY pol_usuario_acceso_login_lectura ON public.usuario FOR SELECT TO turnos_acceso_login USING (true);
CREATE POLICY pol_intento_login_acceso_login ON public.intento_login TO turnos_acceso_login
  USING (true) WITH CHECK (true);

-- Funcion de sesion (ejemplo; dueño turnos_acceso_previo, EXECUTE solo turnos_app)
CREATE FUNCTION acceso.resolver_sesion(p_token_hmac bytea,
    OUT o_sesion_id uuid, OUT o_consultorio_id uuid, OUT o_usuario_id uuid, OUT o_email text,
    OUT o_nombre text, OUT o_rol text, OUT o_consultorio_nombre text, OUT o_usuario_activo boolean,
    OUT o_consultorio_activo boolean, OUT o_creada_en timestamptz, OUT o_ultimo_uso_en timestamptz,
    OUT o_vence_absoluto_en timestamptz, OUT o_revocada_en timestamptz)
  LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog, pg_temp
AS $f$
BEGIN
  IF p_token_hmac IS NULL OR octet_length(p_token_hmac) <> 32 THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'hmac invalido';
  END IF;
  SELECT s.id, s.consultorio_id, s.usuario_id, u.email, u.nombre, u.rol, c.nombre, u.activo, c.activo,
         s.creada_en, s.ultimo_uso_en, s.vence_absoluto_en, s.revocada_en
    INTO o_sesion_id, o_consultorio_id, o_usuario_id, o_email, o_nombre, o_rol, o_consultorio_nombre,
         o_usuario_activo, o_consultorio_activo, o_creada_en, o_ultimo_uso_en, o_vence_absoluto_en, o_revocada_en
    FROM public.sesion s
    JOIN public.usuario u ON u.consultorio_id = s.consultorio_id AND u.id = s.usuario_id
    JOIN public.consultorio c ON c.id = s.consultorio_id
   WHERE s.token_hmac = p_token_hmac;
END
$f$;
ALTER FUNCTION acceso.resolver_sesion(bytea) OWNER TO turnos_acceso_previo;
REVOKE ALL ON FUNCTION acceso.resolver_sesion(bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acceso.resolver_sesion(bytea) TO turnos_app;

-- R2-03: no existe funcion de rehash ni ninguna funcion que escriba usuario.
-- Las demas funciones siguen la tabla de DD-25.
```

`downgrade()` (solo `db-test`): `DROP FUNCTION` de cada función de `acceso` y `DROP SCHEMA acceso` (sin `CASCADE`), `DROP CONSTRAINT uq_sesion_consultorio_id_id`, `DROP POLICY` de cada política, `NO FORCE` + `DISABLE ROW LEVEL SECURITY` en las cuatro tablas, `REVOKE` de cada privilegio concedido (tablas, columnas, esquema `public`) a los cuatro roles. No elimina roles ni modifica filas. La prueba compara el catálogo tras la bajada con el de `0003` y verifica que los roles siguen existiendo; una nueva subida deja el mismo catálogo que la primera.

## Secuencias

**Login** (`POST /api/auth/login`):
0. `rechazar_consultorio_del_cliente` → 422 si hay `consultorio_id` en la query o la cabecera `X-Consultorio-Id` (DD-18).
1. `verificar_origen` → 403. 2. `exigir_direccion_cliente` → 400. 3. `exigir_json` → 415. 4. Cuerpo `EntradaLogin` → 422. (Sin cambios respecto de C-03.)
5. Normalizar código, email y contraseña; calcular `clave_cuenta` y `clave_ip`.

```
API (servicio)                  motor login (turnos_login)                motor app (turnos_app)
 |-- T1 BEGIN ------------------>|
 |   pg_advisory_xact_lock x2    |
 |   acceso.fallos_de_cuenta/ip  |--> 429: COMMIT sin escrituras
 |   acceso.buscar_cuenta        |   (fila con credencial solo si utilizable)
 |   [cupo Argon2: 503 -> ROLLBACK]
 |   verificar (real o ficticio), una sola vez, con los locks tomados; SIN rehash
 |   fallo: registrar_fallo, limpiar_intentos, COMMIT --> 401
 |   exito: descartar_fallos_de_cuenta, limpiar_intentos, COMMIT (conexion devuelta)
 |-- T2 BEGIN (after_begin: '') -------------------------------------------->|
 |   fijar_consultorio_de_login(consultorio de la cuenta)                    |
 |   acceso.limpiar_sesiones; acceso.resolver_sesion(cookie) -> revocar_sesion_por_token
 |   INSERT sesion ... RETURNING id (WITH CHECK)                             |
 |   COMMIT ------------------------------------------------------------------>|--> 200 + cookie + X-CSRF-Token
 |   (T2 falla: ROLLBACK de T2, 500 sin cookie; T1 ya confirmada: ver tabla de DD-27)
```

**Petición protegida**: `rechazar_consultorio_del_cliente` (422) → [`verificar_origen` (403)] → `identidad_actual`: transacción de `turnos_app` con contexto `''` → `acceso.resolver_sesion(hmac)` → validez en Python → `acceso.renovar_sesion(hmac, ahora)` → `COMMIT` → `Rol(rol)` (401 si desconocido) → `ContextoConsultorio` → `aplicar_contexto` → [`exigir_csrf` (403)] → [`require_rol` (403)] → ruta (su primera transacción ya tiene el contexto). No usa el motor de login.

**Logout**: igual que una petición protegida que cambia estado; `UPDATE sesion SET revocada_en ... WHERE id = :id AND revocada_en IS NULL` bajo el contexto, `COMMIT`, 204.

## Modelo de amenazas (matriz breve)

| Riesgo | Mitigación en C-04 | Residual |
|---|---|---|
| Filtro por consultorio omitido | RLS forzada cerrada por defecto; repositorios acotados | Superusuario de administración omite RLS (DT-01) |
| Referencia a una fila de otro consultorio | Claves compuestas + prueba de esquema | Tablas futuras: la prueba falla |
| Contexto que persiste en el pool | `set_config` local, `after_begin`, `RESET`, prueba con pool de una conexión | — |
| Inyección SQL en código de negocio (`turnos_app`) | Sin hashes (ni columna ni función, DD-25), sin `token_hmac` en lectura, sin `intento_login`, sin `DELETE` | Fijar otro contexto, leer/escribir lo que `turnos_app` puede y acuñar sesiones (DD-06, DT-03) |
| Inyección SQL en el camino de login (`turnos_login`) | Código pequeño, parametrizado, sin SQL dinámico; funciones de una fila con entradas validadas; sin tablas | Robo de hashes de cuentas conocidas para ataque fuera de línea (DT-05); enumeración por (código, email); reinicio del bloqueo de una clave conocida. **Sin toma de cuentas por reescritura**: no hay escritura de credenciales (R2-01) |
| Compromiso del proceso de la API | Fuera del alcance de las barreras de base | Abuso de ambas conexiones: leer hashes de cuentas conocidas, acuñar sesiones, fijar contexto (DD-06, DT-03); **riesgo residual explícito** |
| Reescritura de credenciales desde la API | Ningún rol del camino de la API tiene `UPDATE` sobre `usuario`; sin función de escritura; pruebas de catálogo y estáticas (DD-26) | Compromiso del proceso con acceso a la credencial de administración (fuera de la API) |
| Hashes con parámetros desactualizados tras un cambio de política | Informe `--revisar-hashes` y restablecimiento local (DD-32) | Las cuentas no restablecidas conservan parámetros anteriores (DT-08) |
| Escritura administrativa sobre una credencial cambiada en paralelo | Comparación e intercambio en el comando (DD-32) | — |
| Agotamiento del pool de login | Pool acotado (15 conexiones por proceso, espera de 30 s) y 503 sin intento registrado (PD-04, DD-33), validado por las nueve pruebas de la tarea 5.7 | Ráfagas de una IP pueden demorar o provocar 503 a otros (disponibilidad); sin `lock_timeout` (nota de producción) |
| Uso indebido de la conexión de login fuera del login | Dependencia exclusiva, recorrido de rutas, pruebas estáticas, guardia del motor | Código nuevo que eluda la dependencia: lo detectan las pruebas estáticas |
| URLs intercambiadas o rol privilegiado | Validador de roles distintos; guardias por conexión de DD-29; verificación de `0004` | Error del operador en otro motor fuera de la guardia |
| Abuso de funciones `SECURITY DEFINER` | `search_path` fijo, objetos calificados, sin SQL dinámico, entradas validadas, ACL de un único rol, dos dueños, prueba de catálogo, pruebas de abuso | Errores lógicos en el cuerpo de una función |
| Reinicio de bloqueos borrando intentos | Solo funciones de `turnos_login`; limpieza > 24 h, ≤ 100, instante acotado | Ruido con claves aleatorias |
| Consultorio enviado por el cliente | 422 por cuerpo, query y `X-Consultorio-Id`; contexto solo de la sesión; prueba estática de lecturas de cabeceras | — |
| Enumeración de cuentas por el login HTTP | 401 único, verificación ficticia, mismo cupo, mismos conteos | Diferencias de microsegundos |
| Credencial reemplazada durante un login | El login no escribe credenciales: nunca la sobrescribe | Sesión creada tras el reemplazo (DT-07) |
| Secretos de roles en el repositorio o registros | Roles fuera de Alembic; contraseñas efímeras en `db-test`; verificador SCRAM en desarrollo; sin impresión | Valores efímeros en el entorno del contenedor (DT-04) |

## Plan de pruebas

- **Unitarias** (`tests/unit/`): `require_rol`; conversión de `Rol`; `rechazar_consultorio_del_cliente` (query con variantes de mayúsculas; `X-Consultorio-Id` en minúsculas y mayúsculas; `X-Consultorio`, `Consultorio-Id`, `X-Tenant-Id` y `X-Request-Id` **no** rechazadas; detalle sin valor); `contexto_bd` con conexión espía; configuración (`DATABASE_LOGIN_URL`, `DATABASE_MIGRATION_URL`, roles distintos entre las tres, errores sin valores, `crear_app` sin `DATABASE_LOGIN_URL`); resolución de URL de migración; guardia de URL de pruebas con las tres URLs; motor de administración en los comandos; comando `roles_postgres` (guardia, TTY, argumentos, contraseñas distintas, salida sin contraseña, verificador SCRAM con función inyectada); servicio con dos `Session` espía (orden T1 → T2, sin T2 en rechazos, el verificador se llama una vez y nunca `hashear` ni `necesita_rehash` en el login); `clasificar_hash` (vigente, `t=2`, `m=19456`, `$argon2i$`, `$argon2d$`, texto, nulo); comando de credenciales con `--revisar-hashes` (argumentos excluyentes antes de conectar, transacción de solo lectura, salida sin datos sensibles); configuración: usuarios iguales con hosts distintos rechazados y mismo servidor con usuarios distintos admitido; estáticas (único punto de `app.consultorio_id`; llamadas de contexto; comparaciones de rol; único `UPDATE ... credencial` de `app/` en `acceso_admin.py` y ninguna ruta que lo alcance; `acceso_admin`, `acceso_login`, `obtener_sesion_login`, `fabrica_sesiones_login` y `crear_engine_login` solo donde DD-28 permite; lista blanca de lecturas de cabeceras, query y cookies); configuración efectiva de ambos pools y traducción del agotamiento del pool de login al 503 (DD-33); presupuesto de conexiones (condición 9 de DD-33).
- **Integración** (`tests/integration/`, rol `app` de `db-test`): migración `0004` (roles ausentes, atributos indebidos, membresías, subida con datos, bajada y resubida idénticas, catálogo); convenciones de esquema; wrappers de `acceso_login`/`acceso_previo` (equivalencia con C-03); recorrido de rutas para `obtener_sesion_login`; ajustes de "Compatibilidad".
- **Aislamiento** (`tests/isolation/`, conexiones reales `turnos_app` y `turnos_login`): `test_catalogo_roles.py` (atributos y membresías de los cuatro roles), `test_privilegios.py` (matriz exacta; `turnos_app` sin `SELECT`/`UPDATE` de `credencial` y sin `EXECUTE` de las 6 funciones de login; `turnos_login` y `turnos_acceso_login` sin `INSERT`/`UPDATE`/`DELETE` sobre `usuario`; `turnos_login` sin ningún privilegio de tabla, sin leer `sesion`, sin `EXECUTE` de las 4 de sesión, sin poder ejecutar `SET ROLE`, `CREATE ROLE` ni crear objetos), `test_rls.py`, `test_contexto_transaccional.py`, `test_funciones_acceso.py` (catálogo de dueños, ACL, `search_path`, `proconfig`, conjunto exacto y abuso), `test_login_sin_escritura.py` (R2-01: función de rehash inexistente y sin `EXECUTE`; recorrido de `pg_proc` de las funciones ejecutables por `turnos_login` y privilegios de sus dueños; login exitoso con `t=2`, exitoso vigente y rechazado con credencial y `xmin` idénticos; registro de sentencias sin escrituras sobre `usuario`; credencial reemplazada por el comando durante un login), `test_comando_credenciales_admin.py` (informe sobre datos ficticios de las cuatro clases, comparación e intercambio ante un cambio confirmado en paralelo sin revocar sesiones, restablecimiento que deja la cuenta vigente), `test_conexiones_login.py` (DD-27: roles por transacción y sin coexistencia, verificación con locks tomados, fallo inyectado en T2 con sus efectos, pools sin contaminación, conteo atómico con los roles; y `test_pool_login.py` con las condiciones 1 a 8 de validación de PD-04 de DD-33 sobre la configuración real de los pools), `test_guardia_rol_api.py` (DD-29 en ambos motores, incluido un rol con otro nombre y los mismos privilegios), `test_registro.py`, `test_acceso_cruzado.py`, `test_regresion_auth.py` (DD-24).
- **Runner**: autoprueba con los casos de DD-23; `scripts/test.ps1` completo como evidencia de Verify.
- Cada escenario de las deltas se mapea a una prueba en la matriz de `tdd-evidencia.md` (tarea 10.2).

## Compatibilidad con C-01 a C-03

Ajustes previstos sobre pruebas y código existentes, cada uno justificado por una delta:
- `tests/integration/test_dependencias_auth.py`: el caso con `consultorio_id` de B en query y en `X-Consultorio-Id` pasa a esperar 422 (delta `autenticacion-sesion`, DA-06) y se agrega el caso sin esos datos.
- `tests/integration/test_migraciones.py` y `test_migracion_autenticacion.py`: `head` = `0004`; cadena `0003` → `0004`.
- `tests/unit/test_migraciones.py`: el destino de desarrollo usa `DATABASE_MIGRATION_URL` y falla sin ella.
- `tests/unit/test_config.py`, `tests/unit/conftest.py` (`fabrica_settings`) y pruebas de la plantilla: `DATABASE_MIGRATION_URL` y `DATABASE_LOGIN_URL`.
- `tests/unit/test_seed.py`, `test_credenciales.py`, `test_mantenimiento.py`: la sesión por defecto usa el motor de administración.
- `tests/integration/test_acceso_previo.py` (y las que importen operaciones movidas): operaciones de login a `acceso_login`, de sesión por HMAC en `acceso_previo`, de comandos en `acceso_admin`; `escribir_credencial` pasa a `acceso_admin` (solo comandos) y sus pruebas (`test_escribir_credencial_*`) se mueven con él sin cambiar aserciones; se ajustan importaciones y firmas sin cambiar la intención.
- `tests/integration/test_servicio_auth.py` y pruebas del servicio: `iniciar_sesion` recibe la `Session` de login y la de aplicación (en integración, ambas sobre la conexión de la fixture); aserciones sin cambios **salvo R2-01**: `test_rehash_al_iniciar_sesion_con_parametros_desactualizados` pasa a esperar la credencial idéntica tras dos logins exitosos (justificación: REMOVED "Contraseñas con Argon2id y rehash"); `test_sin_rehash_si_los_parametros_son_vigentes_o_si_el_login_falla` no cambia.
- `tests/integration/test_argon2_real.py` (R2-01): `test_login_http_con_hash_de_t2_responde_200_y_la_credencial_pasa_a_los_parametros_vigentes` pasa a esperar 200 y la credencial `t=2` idéntica (y un segundo login 200 sin cambios); `test_login_http_con_hash_vigente_no_cambia_la_credencial` y `test_login_http_fallido_con_hash_de_t2_no_reescribe_la_credencial` no cambian.
- `tests/unit/test_auth_contrasenas.py`: las pruebas de `necesita_rehash` se conservan (lo usa `clasificar_hash`).
- `tests/integration/app_auth.py`: las fábricas usan `crear_fabrica_de_sesiones` (con evento) y se agrega `fabrica_sesiones_login` sobre la misma conexión; la app de prueba registra `rechazar_consultorio_del_cliente`; rutas de prueba nuevas solo ahí.
- `tests/integration/test_rutas_protegidas.py`: recorrido extraído a `tests/rutas.py` sin cambiar aserciones.
- `scripts/tests/autoprueba.ps1`: casos de DD-23.
- Sin cambios: `tests/unit/test_superposicion_turnos.py` (19 pruebas), las respuestas de login, `/me` y logout, el orden de rechazos del login sin consultorio del cliente, la cookie y el CSRF.

## Riesgos / Trade-offs

- [`0004` y las nuevas variables son BREAKING para desarrollo] → todo se prueba en `db-test`; en desarrollo, solo después del Verify técnico (grupo 12), autorizaciones separadas (grupo 13), verificación posterior (grupo 14) y ventanas de indisponibilidad documentadas ("Plan de migración").
- [`uvicorn --reload` con el código montado] → los cambios de Apply se recargarían en la API de desarrollo; detenerla exige la autorización A0, **todavía no otorgada** (R2-08, tarea 0.3): sin ella, Apply no edita código.
- [Integración sigue como superusuario] → `tests/isolation/` con conexiones reales de ambos roles es obligatorio en el runner.
- [Sin rehash en el login] → los hashes no se actualizan solos (DT-08); informe y restablecimiento locales (DD-32).
- [Dos transacciones en el login] → orden y fallos de DD-27, probados con fallos inyectados.
- [Instantes acotados a `now() + 5 min`] → la tarea 0.4 verifica los relojes de las pruebas de C-03.
- [Segundo pool y conexión retenida durante la espera de locks, el cupo y Argon2] → configuración inicial de PD-04 con 503 ante agotamiento del pool de login (DD-33); validada por las nueve pruebas de la tarea 5.7 antes de tocar desarrollo; si alguna falla, regla R3-03.
- [Valores de PD-04 iniciales, no de producción] → notas de producción en DD-33 (medición, `lock_timeout`, dimensionamiento por proceso, PgBouncer, hilos de AnyIO).
- [Columnas diferidas] → un acceso sin cargar lanza error: hace visibles los usos indebidos.

## Plan de migración (desarrollo; cada paso con autorización explícita y separada del autor)

Claude nunca lee ni escribe `.env`, nunca ve ni genera contraseñas de desarrollo y no ejecuta ningún paso sin el "sí" del autor para ese paso. Ante cualquier resultado inesperado: **detenerse y consultar**. El plan tiene un paso previo (A0) y tres etapas en orden estricto (R3-04); ninguna etapa empieza sin que la anterior termine con su resultado registrado.

**Paso previo — A0 (tarea 0.3; autorización pendiente, R2-08 y R3-05)**: antes del primer cambio de código, detener **solo** la API de desarrollo con `docker compose stop api`, porque `uvicorn --reload` con `./backend` montado recargaría cada cambio de Apply. Nunca `down`, `rm`, `-v` ni `stop` sin nombre de servicio; la base de desarrollo sigue levantada y no se toca. Comprobaciones previas y posteriores de solo lectura: `docker compose ps`; `pg_isready` del servicio `db`; `curl` a `/api/health` (después: código `000`); `pg_stat_activity` sin conexiones desde la IP del contenedor `api`; volumen `pgdata` presente. La API queda **no disponible** desde A0 hasta A4, único punto en que se vuelve a levantar. Las tareas 0.1, 0.2 y 0.4 pueden ejecutarse antes de A0 (el runner usa contenedores efímeros y `db-test`).

**A. Verify técnico previo a la transición (grupo 12; solo `db-test`)**: `0004` probada en `db-test` (subida con datos, bajada y resubida); roles y privilegios con conexiones reales; RLS y aislamiento entre consultorios; autorización; regresión de C-03; validación de PD-04 (nueve condiciones de DD-33); `openspec validate aislamiento-roles-rbac --strict`; evidencia de la implementación en `tdd-evidencia.md` y `verify.md`. Se completa **antes** de cualquier cambio en el PostgreSQL de desarrollo; si algo falla, no se pasa a B.

**B. Transición controlada de desarrollo (grupo 13)**:

| Paso | Tarea | Qué | Precondiciones (go) | Impacto en disponibilidad |
|---|---|---|---|---|
| Preparación | 13.1 | El autor agrega `DATABASE_MIGRATION_URL` (credencial de administración que ya usa) a su `.env` | Grupo 12 completo (12.8 = go); confirmación del autor (Claude no ve el archivo) | Ninguno |
| A1 | 13.2 | Respaldo `pg_dump -Fc` de la base de desarrollo en `C:\dev\respaldos_turnos\<fecha>_pre_0004.dump` (fuera del repositorio) y verificación previa **de solo lectura**: revisión `0003`, cantidad de filas y huella por tabla, lista de roles | Autorización A1; espacio en disco | Ninguno (lecturas) |
| A2 | 13.3 | Crear roles: `docker compose run --rm -it api python -m app.roles_postgres crear`; el autor teclea las contraseñas de `turnos_app` y `turnos_login` | Autorización A2; A1 verificado; salida solo con textos fijos | Ninguno (los roles no tienen privilegios hasta `0004`) |
| A3 | 13.4 | Aplicar `0004`: `docker compose run --rm api alembic upgrade head` con `DATABASE_MIGRATION_URL`; luego verificación de solo lectura del catálogo (políticas, RLS forzada, privilegios, funciones, dueños) y huella de filas igual a la de A1 | Autorización A3; A2 verificado | La API sigue detenida; si alguien levantara el código previo conectado como `app`, funcionaría (superusuario omite RLS), pero no se recomienda |
| `.env` | 13.5 | El autor edita su `.env`: `DATABASE_URL` → `turnos_app`, `DATABASE_LOGIN_URL` → `turnos_login`, `DATABASE_MIGRATION_URL` → `app` | Confirmación del autor (Claude no ve el archivo) | — |
| A4 | 13.6 | Reconstruir y levantar la API: `docker compose build api` y `docker compose up -d api`; comprobar solo que arrancó (sin volcar variables) | Autorización A4; A3 y edición del `.env` hechos | Fin de la indisponibilidad si arranca. Con el código nuevo y un `.env` incompleto la API **no arranca** o rechaza conexiones (guardias DD-29): ese es el comportamiento esperado |
| A5 | 13.7 | Pruebas de humo: `GET /api/health`; login con un usuario ficticio del seed (contraseña tecleada por el autor), `/me`, logout | Autorización A5 | Ninguno |
| Recuperación | 13.8 | Ante fallos: detenerse y consultar; el autor revierte su `.env`; con autorización, `alembic downgrade 0003` con la credencial de administración y volver al código previo; restaurar el respaldo **solo** con autorización expresa si hubiera pérdida de datos; los roles pueden quedar (sin privilegios) | Autorización específica para cada acción | API no disponible hasta completar la reversión |

**C. Verificación posterior al despliegue (grupo 14; solo lecturas, con el "sí" del autor)**: conectividad (servicio, `GET /api/health`, `pg_isready`); rol real de la API mediante una consulta de solo lectura (`current_user` = `turnos_app`, y `turnos_login` en el login; ninguno superusuario); login, sesiones y permisos (contexto vacío → cero filas como `turnos_app`; contexto de un consultorio → solo sus filas; `turnos_app` sin lectura de `credencial`); integridad de datos (cantidad de filas y huellas iguales a las de A1, salvo las filas de sesión e intentos generadas por las pruebas, identificadas); el resultado se registra en `verify.md` **antes** de dar la transición por terminada.

**Go/no-go**: no se pasa de un paso al siguiente si el anterior no terminó con el resultado esperado registrado; en particular, no se toca la base de desarrollo sin el grupo 12 completo, no se aplica `0004` sin respaldo verificado ni roles verificados, y no se levanta la API nueva sin `0004` aplicada y el `.env` actualizado por el autor. Entre A0 y A4 la API de desarrollo no está disponible; el autor puede abortar en cualquier paso y volver al código previo (la base queda en `0003` hasta A3).

## Impacto en Changes posteriores

- **C-05 `gestion-usuarios`**: `INSERT`/`UPDATE` por columnas de `usuario` para `turnos_app` (nunca `credencial`); un cambio de contraseña desde la API exigiría una función nueva con diseño propio (fuera de C-04); `require_rol(Rol.ADMINISTRADOR)`; entradas del registro de aislamiento.
- **C-06 `frontend-base-sesion`**: manejar 403, 404 genérico y 422 por consultorio enviado.
- **C-07 en adelante**: convención de DD-19; `turnos_login` sin privilegios sobre tablas nuevas; migraciones `0005+`.

## Deuda técnica

- **DT-01**: el rol de administración es superusuario y omite RLS; un rol de administración dedicado queda para antes de cualquier despliegue.
- **DT-02**: `PUBLIC` conserva `TEMP` y `CONNECT` sobre la base; revocarlos (y `statement_timeout`/`CONNECTION LIMIT` para `turnos_app` y `turnos_login`) queda como endurecimiento futuro.
- **DT-03**: RLS y la separación de roles no protegen ante una aplicación comprometida; con SQL arbitrario como `turnos_app` se puede fijar otro contexto y acuñar sesiones; con el proceso comprometido, ambas conexiones (DD-06).
- **DT-04**: las contraseñas efímeras de `db-test` viven en el entorno del contenedor mientras corre.
- **DT-05**: con un camino de login comprometido (`turnos_login`), robo de hashes de cuentas conocidas para ataque fuera de línea; ya **no** hay toma de cuentas por reescritura (R2-01).
- **DT-06**: `buscar_cuenta` es un oráculo de existencia de cuentas por (código, email) para quien ejecute SQL como `turnos_login` (sin límite en la base).
- **DT-07**: carrera preexistente entre un login en curso y un reemplazo de credencial con revocación (DD-27).
- **DT-08** (limitación aceptada, R2-01): los hashes no se actualizan automáticamente al iniciar sesión; tras un cambio de política conservan sus parámetros hasta que el administrador restablece la contraseña (DD-32).
- **DT-09**: el informe de hashes muestra identificadores y no código ni email (X1); restablecer exige que el administrador conozca la cuenta.
- **DT-10** (RT3, bajo): `acceso.limpiar_sesiones`, que ejecuta `turnos_app`, borra sesiones vencidas o revocadas de **todos** los consultorios y recibe del llamador la inactividad (mínimo 5 minutos); una inyección SQL en el código de negocio podría cerrar sesiones inactivas de otros consultorios (denegación de servicio, sin lectura de datos). Recomendación: fijar la inactividad del lado del servidor o acotar la limpieza.
- **DT-11** (RT3, bajo): la guardia de rol (DD-29) se evalúa solo al abrir cada conexión; un cambio de privilegios sobre conexiones ya abiertas no se detecta hasta reconectar. Recomendación: documentar o revalidar periódicamente.
- **DT-13** (RT3, bajo-4): Compose prioriza las variables del shell sobre `.env` al interpolar las claves permitidas de `api`; si el shell definiera `DATABASE_URL` o `DATABASE_LOGIN_URL` con otra credencial, `api` la recibiría. Mitigación vigente: la guardia de rol (DD-29) rechaza toda conexión cuyo usuario no sea exactamente `turnos_app` o `turnos_login`, o que sea superusuario, y el runner rechaza variables de administración en su proceso. Recomendación: validar al arrancar los usuarios de ambas URLs.
- **DT-14** (RT3-06): `TEST_DATABASE_URL` sigue en la plantilla y en `.env`, pero el runner ya no la usa; retirarla requiere editar `.env.example` (lo hace el autor) y ajustar las pruebas de la plantilla en un cambio posterior.
- **DT-12** (RT3, bajo): sin `ALTER DEFAULT PRIVILEGES` en el esquema `acceso`, una función futura creada sin `REVOKE` quedaría ejecutable por `PUBLIC` (atenuado: solo `turnos_app` y `turnos_login` tienen `USAGE` en `acceso`). Recomendación: privilegios por defecto o prueba de convención en C-07 o posterior.

## Decisiones pendientes para el autor

| Id | Pregunta | Decisión | Estado |
|---|---|---|---|
| PD-01 | Exposición de hashes y destino del rehash | B + D: `turnos_login` y `DATABASE_LOGIN_URL`; hash solo de cuentas utilizables (DD-11, DD-25). El rehash de la primera revisión queda **sustituido por R2-01** (sin rehash en el login, DD-26) | **Decidida** (2026-11-09; rehash revisado el mismo día) |
| PD-02 | Estado HTTP del rechazo por cabecera | 422 (DD-18) | **Decidida** (2026-11-09) |
| PD-03 | Credenciales de los roles de conexión en `db-test` | Efímeras del runner para `turnos_app` y `turnos_login` (DD-21) | **Decidida** (2026-11-09) |
| R2-01 a R2-08 | Login sin rehash, roles, guardias, transacciones, A0 | Ver "Decisiones del autor en la segunda revisión" | **Decididas** (2026-11-09) |
| PD-04 | Dimensionamiento de los pools y respuesta ante agotamiento del pool de login | Configuración inicial del MVP (R3-01, DD-33): login `pool_size=4`, `max_overflow=11`; aplicación `pool_size=5`, `max_overflow=10`; ambos `pool_timeout=30` s, `pool_pre_ping` y `connect_timeout=5` s; 503 genérico ante agotamiento del pool de login, con `rollback` y sin intento registrado | **Decidida** (2026-11-09) como configuración inicial; **validación pendiente** (tareas 5.7 y 12.5; regla ante fallos R3-03) |
| R3-01 a R3-06 | PD-04, validación, regla ante fallos, orden A → B → C, A0, notas de producción | Ver "Decisiones del autor en la tercera revisión" | **Decididas** (2026-11-09) |
| RT3-01 | Hallazgo ALTO-1 de la revisión de seguridad RT3 | Corregir antes de Archive con la alternativa A (DD-34); bajos como DT-10 a DT-12 | **Decidida** (2026-11-15) |
| RT3-05 a RT3-07 | ALTO-2, MEDIO-1 y Bajo-4 de la segunda revisión RT3 | Corregir ALTO-2 y MEDIO-1 antes de Archive (ampliación de DD-34); Bajo-4 como DT-13 | **Decidida** (2026-11-15) |
| A0 | Detener la API de desarrollo antes de editar código | Autorización separada (tarea 0.3): solo `docker compose stop api`, con comprobaciones previas y posteriores | **Pendiente** (R2-08, R3-05): sin ella Apply no edita código |

No quedan decisiones de diseño abiertas. PD-04 está decidida como configuración inicial del MVP y su validación definitiva depende de las nueve pruebas de la tarea 5.7 (verificadas otra vez en 12.5); si alguna falla se aplica R3-03 (detenerse, investigar y consultar al autor). La única autorización pendiente antes de editar código es A0; las de la transición (A1 a A5) se piden en el grupo 13, solo después del Verify técnico del grupo 12.

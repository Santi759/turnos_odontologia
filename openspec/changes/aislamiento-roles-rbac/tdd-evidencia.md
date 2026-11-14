# Evidencia TDD: aislamiento-roles-rbac (C-04)

> Apply ejecutado solo contra `db-test` (autorizacion del autor limitada al entorno aislado). Datos ficticios. Ninguna contrasena, token ni hash se registra aqui.

## 0. Linea base y decisiones

### 0.1 Linea base (antes de tocar codigo)

- Verificacion del aislamiento del runner (lectura de `docker-compose.yml` y `scripts/test.ps1`, sin `docker compose config`): `db-test` sin `depends_on`, sin puertos, con `tmpfs`; el runner usa `run --rm --no-deps` y `up -d --wait db-test`, y elimina `db-test` en `finally`.
- `scripts/test.ps1` completo: codigo 0. Autoprueba OK; unitarias backend **516 passed**; integracion **418 passed** (total backend **934**; la cifra de 936 de la documentacion de C-03 difiere en 2: se registra la medida real); `tsc` OK; Vitest 2 pruebas pasadas. Las 19 de `test_superposicion_turnos.py` estan dentro de las unitarias (verde).
- `openspec validate --specs --strict`: 15 passed, 0 failed.
- `git status --short` previo: ` M backend/tests/unit/test_superposicion_turnos.py` (finales de linea, ajeno al Change) y `?? openspec/changes/aislamiento-roles-rbac/`.
- `api`, `db` y `frontend` de desarrollo permanecen detenidos (`Exited (255)`) durante todo Apply.

### 0.2 Decisiones registradas (referencia a `design.md`)

- DA-01 a DA-08 (decisiones aprobadas antes del Propose), PD-01 = B + D (rol de login separado, hash solo de cuentas utilizables), PD-02 = 422 para consultorio del cliente, PD-03 = contrasenas efimeras para `turnos_app` y `turnos_login` en `db-test`, X1 = solo `X-Consultorio-Id` entre las cabeceras rechazadas, X2 = plan unico.
- Segunda revision R2-01 a R2-08: login sin rehash (`usuario.credencial` nunca se escribe desde la API), `turnos_acceso_login` sin escritura sobre `usuario`, roles distintos por usuario y `current_user` exacto (R2-05), dos transacciones (T1 `turnos_login`, T2 `turnos_app`), A0 pendiente (luego cumplida por estado preexistente, 0.3).
- Tercera revision R3-01 a R3-06: PD-04 = configuracion inicial de los pools (login 4/11/30 s, app 5/10/30 s, `pre_ping`, `connect_timeout` 5), sujeta a validacion por 5.7 y 12.5; regla ante fallos (detenerse, no cambiar expectativas); orden A (grupo 12) -> B (13) -> C (14); alcance de A0; notas de produccion.
- Alcance de este Apply (instruccion del autor): grupos 0 a 12 solo en `db-test`; el grupo 11 (KB y CHANGES.md) no se escribe, se redacta en `propuesta-documentacion.md`; la tarea 1.6 (`.env.example`) no se ejecuta sin autorizacion especifica y se redacta en `propuesta-env-example.md`.

### 0.4 Relojes inyectados en las pruebas de C-03

Busqueda de solo lectura en `backend/tests/`: los relojes fijos son `AHORA = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)` (`tests/integration/datos_auth.py`, `test_modelo_autenticacion.py`, `tests/unit/test_auth_intentos.py`, `tests/unit/test_mantenimiento.py`) y valores de `2026-11-02` (superposicion de turnos, sin escritura de acceso). Todos son **anteriores** a la fecha real (2026-11-10): ninguno supera el limite `now() + 5 min` de las funciones de `acceso`. Sin ajustes necesarios.


## Evidencia por tarea (grupos 1 a 3)

Convenciones: las pruebas unitarias se ejecutan con `docker compose run --rm --no-deps api python -m pytest` (sin base); las de integracion y aislamiento, contra `db-test` efimera con el mismo flujo del runner (contrasenas efimeras de rol por nombre, `db-test` eliminada al terminar). Ninguna conexion toco `db`, `api` ni `frontend` de desarrollo.

### Grupo 1: configuracion y credenciales separadas

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/unit/test_config.py` | Unit | 516 unit (linea base) | 33 fallas en la primera ejecucion de 1.1 a 1.3 | 132 verdes | mismo usuario con mismo host, otro host, par login/migracion; usuarios distintos validos; mayusculas de rol; secretos ausentes de `repr` y errores | mensajes fijos por regla |
| 1.2 | `tests/unit/test_database.py` | Unit | idem | idem | idem | login, migracion, ambas ausentes, distinta valida | idem |
| 1.3 | `tests/unit/test_migraciones.py` | Unit | idem | idem | idem | desarrollo usa migracion y nunca `DATABASE_URL`; sin ella error; destinos de pruebas sin cambio; guardia contra migracion | idem |
| 1.4 | `tests/unit/test_comandos_administracion.py` (nuevo) | Unit | idem | `ImportError` de `AdministracionNoConfigurada` | 93 verdes (con seed, credenciales, mantenimiento) | 3 comandos x (sin URL, `APP_ENV=test`, sesion por defecto en `host-admin.invalid`) | un helper comun `abrir_sesion_de_administracion` |
| 1.5 | `tests/unit/test_crear_app.py` | Unit | idem | 4 fallas | 548 unit verdes | sin URL de login, motores a hosts distintos, ninguno a migracion, fabrica de login | - |
| 1.6 | - | - | - | - | - | - | **NO ejecutada**: requiere autorizacion especifica; contenido propuesto en `propuesta-env-example.md`. Ninguna prueba depende de ella |
| 1.7 | - | Unit | - | - | `tests/unit` 580 verdes al final del grupo 3 | - | mensajes sin valores |

Ajustes a pruebas existentes (justificados; ninguna expectativa se debilito):
- `tests/unit/test_migraciones.py`: `_settings()` pasa a `DATABASE_URL` de `turnos_app` y `DATABASE_MIGRATION_URL` con el usuario `app` (delta `base-de-datos-local`: desarrollo resuelve a la URL de administracion); `_ejecutar_upgrade_sql` acepta `migration_url`. Mismas aserciones.
- `tests/unit/test_seed.py`, `test_credenciales.py`, `test_mantenimiento.py`: el entorno de los casos "el comando real intenta conectar" define `DATABASE_MIGRATION_URL` (el host inexistente de siempre) y una `DATABASE_URL` de otro rol, porque los comandos ya no usan `DATABASE_URL`. Mismas aserciones.
- `tests/unit/conftest.py` (`fabrica_settings` con `DATABASE_LOGIN_URL` de otro usuario; limpieza de las URLs de rol del entorno) y `tests/unit/test_documentacion.py`, `tests/integration/app_auth.py` (`settings_de_prueba`): `crear_app` exige `DATABASE_LOGIN_URL`.

### Grupo 2: roles en db-test, runner y arnes

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 | `tests/unit/test_roles_bd.py` | Unit | 548 unit | escrito antes; se ejecuto junto con el codigo (no hay corrida roja separada) | 32 verdes | 4 roles x 5 atributos, sin LOGIN, duenio con LOGIN, varias violaciones, rol ajeno | - |
| 2.2 | `scripts/tests/autoprueba.ps1` | Script | autoprueba verde en la linea base | casos escritos antes que `New-ContrasenaRolPruebaEfimera`; no se ejecuto corrida roja separada (la funcion no existia) | caso verde | formato 43 caracteres y valores distintos | - |
| 2.3 | `scripts/tests/autoprueba.ps1`, `db/test-init/10_roles_prueba.sh`, `docker-compose.yml` | Script | idem | idem | "Base de pruebas separada y efimera" y "db-test sin contrasenas no arranca" verdes | un montaje bind de solo lectura; ambas variables por nombre sin valor; arranque rechazado sin contrasenas (proyecto `autoprueba-sinroles`) | - |
| 2.4 | `scripts/tests/autoprueba.ps1`, `scripts/test.ps1` | Script | idem | idem | casos de `test.ps1` verdes | dos variables por nombre, sin literal, retiradas en `finally`; paso 6 tras integracion; frontend 7 y 8; caso aislado "Funciona sin clave" con script de roles | - |
| 2.5 | `tests/isolation/test_arnes.py` | Isolation | n/a (suite nueva) | conftest y pruebas escritos juntos; la corrida roja fue la ausencia de `tests/isolation` (el paso 6 no existia) | 8 verdes con la base en `0003` y luego `0004` | roles de ambos motores, no superusuario, base `_test`, URLs derivadas, datos A/B confirmados, idempotencia, limpieza | - |
| 2.6 | - | - | - | - | autoprueba completa verde (22 casos) | - | scripts ASCII |

Autoprueba completa: 22 casos OK, codigo 0.

### Grupo 3: migracion 0004 (solo db-test)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.1 | `tests/integration/test_migracion_aislamiento.py` | Integration | 418 integracion | 19 fallas (revision 0004 inexistente) | 19 verdes tras 3.2 | 4 roles ausentes; 7 atributos indebidos; 3 membresias; rol duenio de objetos; subida con huella; bajada con catalogo normalizado (ACL por defecto) y resubida identica | - |
| 3.2 | `alembic/versions/0004_aislamiento_roles_rbac.py` | Integration | idem | idem | 19/19 | - | constantes de `roles_bd` en la migracion |
| 3.3 | `test_migraciones.py`, `test_migracion_autenticacion.py` | Integration | 2 fallas esperadas (`head` = 0003) | 2 fallas | 441 integracion verdes | cadena 0001-0004 | - |
| 3.4 | `tests/integration/test_convenciones_esquema.py` | Integration | - | falla real | **RESUELTO el 2026-11-10 (opcion 3)**; ver la seccion de resolucion al final | - | - |
| 3.5, 3.6 | - | - | - | - | **NO iniciadas** | - | - |

Nota de alcance de 0004 en este punto: contiene la verificacion previa de roles, el esquema `acceso` (sin funciones todavia, llegan en 5.2), los privilegios de la matriz, RLS habilitada y forzada en las cuatro tablas y las politicas de DD-03 y de los duenios. `downgrade` sin `CASCADE`, sin eliminar roles ni modificar filas.

Ajustes a pruebas existentes en 3.3: `test_la_revision_head_es_0003_y_depende_de_0002` pasa a `test_la_revision_0003_depende_de_0002_y_head_es_0004` y `test_cadena_de_revisiones_0001_0002_0003` a `..._0004` (`head` ahora es 0004; la cadena de 0003 se conserva). Resto de integracion sin cambios (441 verdes + 3 xfail de 3.4).

## PUNTO DE CONTROL 3.4: incompatibilidad no contemplada con C-03 (resuelto: ver la seccion final)

**Hallazgo.** La regla de DD-08 y del requisito de `aislamiento-base-de-datos` ("Toda tabla con `consultorio_id`, salvo `consultorio`, DEBE tener `UNIQUE (consultorio_id, id)`") y la afirmacion de la tarea 3.4 ("actual conforme") no se cumplen sobre el esquema real de C-03: `usuario` tiene `uq_usuario_consultorio_id_id`, pero **`sesion` tiene `consultorio_id` y no tiene `UNIQUE (consultorio_id, id)`** (solo `PK(id)`, `UNIQUE(token_hmac)` y la FK compuesta hacia `usuario`). `design.md` DD-08 y la tarea dicen "hoy: sesion -> usuario, ya conforme", lo que se refiere a la FK, no a la clave unica propia de `sesion`.

**Que se hizo.** La prueba de esquema se escribio contra la regla textual y detecta la violacion. No se modifico el esquema ni se debilito la regla: las tres pruebas afectadas quedan con `xfail(strict=True)` y razon explicita, para que la suite no quede en rojo sin decision y para que el marcador falle (strict) cuando se resuelva y haya que retirarlo.

**Alternativas para decidir (del autor, D6).**
1. Agregar a `0004` `ALTER TABLE sesion ADD CONSTRAINT uq_sesion_consultorio_id_id UNIQUE (consultorio_id, id)` (trivialmente valida porque `id` ya es PK; nada referencia `sesion`; agrega un indice y toca el esbozo aprobado de 0004; habria que ajustar spec y `downgrade`).
2. Mantener el esquema y acotar la regla en la spec y la prueba a "tablas referenciables por otras tablas" (excluir `sesion`, que no es destino de ninguna FK), con la justificacion de que la unicidad compuesta solo existe para sostener FKs compuestas entrantes.
3. Variante de 1: modelar tambien el UNIQUE en el modelo ORM (`Sesion.__table_args__`) para que la comparacion de metadatos siga sin diferencias.

Hasta que el autor elija, no se avanza con 3.5 ni con los grupos siguientes (la decision puede modificar `0004`, de la que dependen las pruebas de privilegios y RLS).

## Estado de las suites al detenerse (todo contra db-test, nada de desarrollo)

- Unitarias: 580 passed (incluye las 19 de superposicion, sin cambios).
- Integracion: 441 passed, 3 xfailed (los xfail son los de 3.4).
- Aislamiento: 8 passed (arnes).
- Autoprueba del runner: 22 casos OK.

## Resolucion del punto de control 3.4 (decision del autor, 2026-11-10: opcion 3)

El autor eligio la opcion 3: convencion DD-08 uniforme, sin excepciones y sin tocar `0003`. Cambios:
- `alembic/versions/0004_aislamiento_roles_rbac.py`: `op.create_unique_constraint(op.f("uq_sesion_consultorio_id_id"), "sesion", ["consultorio_id", "id"])` en `upgrade`, y `op.drop_constraint(..., type_="unique")` en `downgrade`.
- `app/models/sesion.py`: `UniqueConstraint("consultorio_id", "id", name="uq_sesion_consultorio_id_id")` agregada, sin tocar las restricciones existentes (`uq_sesion_token_hmac`, etc.).
- `design.md` (decision registrada, DD-08 corregido, esbozo y `downgrade` de 0004), `tasks.md` (3.2 y 3.4).

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.4 | `tests/integration/test_convenciones_esquema.py` (7 pruebas) | Integration | 441 passed + 3 xfail antes del cambio | las 3 pruebas en `xfail(strict=True)` fallaban de verdad por `sesion` sin UNIQUE (fallas reales vistas antes de marcarlas) | 7/7 verdes sin marca; marcas retiradas | esquema real conforme; tabla sin clave compuesta ni RLS detectada; FK sin `consultorio_id` detectada; tabla conforme sin violaciones; politica distinta detectada; referencia cruzada rechazada por la FK compuesta | - |
| 3.4 (migracion) | `tests/integration/test_migracion_aislamiento.py` (+2) | Integration | 19 | n/a | 21/21 | restriccion creada con nombre y definicion `UNIQUE (consultorio_id, id)` consultada en `pg_constraint`; tras la bajada solo queda `uq_sesion_token_hmac` | - |

Nota sobre el retiro de las marcas: se retiraron en el mismo paso que el cambio de la migracion y el modelo; la confirmacion de que pasan es la corrida posterior sin marca (7 verdes). Con `strict=True` la marca habria fallado como XPASS, lo que equivale a la confirmacion que pedia el autor, pero no se hizo una corrida intermedia separada con las marcas puestas y la restriccion ya creada.

Verificaciones solicitadas (todas en db-test efimera; nada de desarrollo):
1. 0004 aplicada en db-test (`alembic upgrade head` del flujo del runner): `Running upgrade 0003 -> 0004`.
2. Restriccion en el catalogo: `pg_get_constraintdef` = `UNIQUE (consultorio_id, id)` con `conname = uq_sesion_consultorio_id_id` (`test_la_subida_crea_uq_sesion_consultorio_id_id`).
3. Modelo igual al esquema: `tests/integration/test_migraciones.py` (`compare_metadata` sin diferencias) en verde. Sin el UNIQUE en el modelo esa prueba habria detectado la diferencia.
4. Filas: `test_subida_desde_0003_con_datos_previos_no_modifica_ninguna_fila` (huella de las 4 tablas igual tras subir).
5. Las 3 pruebas ex-xfail pasan sin marca.
6. Integracion completa: **446 passed**; aislamiento: **8 passed**; unitarias: **580 passed**.
7. Bajada 0004 -> 0003 y nueva subida: `test_la_bajada_a_0003_restaura_el_catalogo_y_conserva_los_roles` (catalogo igual al de 0003, roles presentes, resubida identica al catalogo de la primera subida).
8. Bajada conserva filas (`test_la_bajada_conserva_las_filas`) y la restriccion nueva no queda (`test_la_bajada_elimina_uq_sesion_y_conserva_la_unicidad_del_token`).

Ajuste justificado a una prueba existente: `tests/integration/test_migraciones.py::test_nombres_de_restricciones_segun_la_convencion` incorpora `("sesion", "uq_sesion_consultorio_id_id")` al conjunto esperado (consecuencia directa de la decision del autor; el resto del conjunto y la convencion de nombres no cambian). Ese fallo lo detecto la suite en la primera corrida completa tras el cambio.

Cuentas actualizadas: integracion 446 passed (441 + 3 antes xfail + 2 nuevas); sin xfail restantes.

## Diferencia entre 934 y 936 pruebas

No es una diferencia de resultados sino de lo que se cuenta. La verificacion archivada de C-03 (`openspec/changes/archive/2026-11-09-autenticacion-sesion/verify.md`, linea 56) dice: 516 unitarias + 418 de integracion + 2 de Vitest = **936**, y en la misma linea aclara que en la salida de pytest hay **934** lineas `PASSED`. Por lo tanto: **934 son pruebas de backend (pytest)** y **936 es el total que suma las 2 de Vitest** del frontend. La medida de este Apply (516 + 418 = 934, Vitest 2) coincide exactamente con la de C-03. El texto de las tareas 0.1 y de DD-24 ("936 pruebas de backend") mezcla ambos conceptos; la cifra correcta de backend es 934. `CHANGES.md` no contiene la cifra (busqueda de solo lectura).

## Desvio de TDD en las tareas 2.1 a 2.4 (registro honesto)

No hubo una corrida en rojo separada en 2.1 a 2.4:
- 2.1 (`roles_bd`): las pruebas se escribieron antes que el modulo, pero las ejecute por primera vez junto con la implementacion (32 verdes); no existe una ejecucion roja registrada.
- 2.2, 2.3 y 2.4 (funcion de contrasenas, script y compose, runner y autoprueba): escribi los casos de `autoprueba.ps1` y la implementacion en la misma etapa y ejecute la autoprueba completa una sola vez, ya con todo implementado (22 casos OK). No ejecute la autoprueba contra el estado anterior para observar los casos en rojo, de modo que la falla esperada (funcion y script inexistentes) es inferida, no observada.
- 2.5: el arnes y sus pruebas se crearon juntos; no hubo corrida roja previa de esas pruebas (la ausencia de `tests/isolation` era el unico rojo, que tampoco ejecute como tal).
Las tareas de los grupos 1 y 3 si tienen corrida roja observada (33 fallas en 1.1 a 1.3, 4 en 1.5, ImportError en 1.4, 19 en 3.1).


## Segunda sesion de Apply: tareas 3.5 a 5.8 (solo db-test)

Convencion: unitarias con `docker compose run --rm --no-deps api python -m pytest` (sin base); integracion y aislamiento contra `db-test` efimera (mismo flujo del runner: contrasenas efimeras por nombre, `db-test` eliminada al terminar). Ninguna conexion toco `db`, `api` ni `frontend` de desarrollo. Sin `.env*`. Sin `git add`/`commit`.

### Orden real de ejecucion (desvio de secuencia, por dependencia)

La tarea 4.4 (guardias de rol de los motores de la API) NO se pudo probar en su posicion: "configuracion correcta -> 200" exige que `GET /api/auth/me` y el login funcionen con los roles reales, y eso depende de las funciones `acceso` (5.2), los modulos de acceso (5.4) y el servicio en dos transacciones (5.6). Orden seguido: 3.5, 3.6, 4.1, 4.2, 4.3, 4.5, 5.1, 5.2, 5.3 (catalogo), 5.4, 5.6 (servicio), 4.4 + 5.5 (motores con guardia y pools), 4.6, 5.3 (HTTP), 5.6 (aislamiento), 5.7, 5.8. Las funciones de 5.2 existen antes que las guardias de 4.4, de modo que la comprobacion de `EXECUTE` sobre `acceso.buscar_cuenta` de DD-29 si quedo en 4.4. Ninguna decision de diseno cambio.

### Grupo 3 (continuacion)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.5 | `tests/isolation/test_catalogo_roles.py`, `test_privilegios.py`, `test_rls.py` | Isolation | 8 isolation, 446 integracion | NO hubo rojo separado: las pruebas verifican la migracion `0004` ya existente (3.2) con conexiones reales; la unica falla de la primera corrida (2 de 91) fue un defecto de la prueba (`SET ROLE` al propio rol siempre se permite) y se corrigio la prueba | 91 verdes | matriz exacta por rol, tabla y columna con `has_*_privilege` (cuatro roles); 42501 reales en lo denegado (14 sentencias de `turnos_app`, 9 de `turnos_login`); sin contexto / vacio / `abc` (22P02) / A solo A / B solo B / inexistente; revocar sesion de B por `id` con contexto A afecta 0 filas; insertar sesion de B rechazado (42501); RLS habilitada y forzada en las 4 tablas; complemento con `SET LOCAL ROLE` | constantes `FUNCIONES_DE_SESION`/`FUNCIONES_DE_LOGIN` en `roles_bd.py` |
| 3.6 | - | - | - | - | grupos 2 y 3 en verde | - | la migracion ya usaba las constantes de `roles_bd`; el bloque de funciones (5.2) se agrego con el mismo orden |

### Grupo 4

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 4.1 | `tests/unit/test_contexto_bd.py` | Unit | 580 unitarias | ImportError observado (`app.core.contexto_bd` inexistente) | 15 verdes | `after_begin` con y sin contexto y con contextos sucesivos; `aplicar_contexto` fuera y dentro de transaccion; tipado; `fijar_consultorio_de_login` sin tocar `info`; la fabrica de la API registra siempre el evento y la de login no; evento `reset` del pool (revierte, `RESET` confirmado, no toca conexiones descartadas) | `crear_fabrica_de_sesiones` se movio de `database.py` a `contexto_bd.py` (las dos pruebas de `test_database.py` solo cambian el import: mismas aserciones) |
| 4.2 | `tests/isolation/test_contexto_transaccional.py` (10), `tests/integration/test_contexto_fixture.py` (3) | Isolation / Integration | 8 / 446 | NO hubo rojo separado (4.1 ya implementaba el comportamiento) | 10 y 3 verdes | commit, rollback, `ROLLBACK TO SAVEPOINT`, savepoint liberado, sin identidad (vacio y cero filas), pool de una conexion reutilizada, `RESET` ante una fuga simulada y control negativo (sin `RESET` la fuga persiste) | - |
| 4.3 | `tests/integration/app_auth.py` | Integration | 446 | - | integracion completa verde | `fabrica_sesiones` con `crear_fabrica_de_sesiones(..., create_savepoint)` y `fabrica_sesiones_login` sobre la misma conexion; ninguna asercion cambio | - |
| 4.4 | `tests/unit/test_roles_bd_conexion.py`, `tests/unit/test_pools_y_guardias.py`, `tests/isolation/test_guardia_rol_api.py` (8) | Unit / Isolation | 580 / 8 | ImportError observado (`RolDeConexionInvalido`, `violaciones_de_conexion`); en aislamiento la primera corrida fallo 3 de 8 por mi propio diseno de prueba (la validacion de `Settings` ya impide URLs iguales; se agrego `motor_*_con` para simular una configuracion que `Settings` no detecta) | todas verdes | `current_user` exacto (rol clon con los mismos privilegios y otro nombre -> `ROL_INESPERADO`), `DATABASE_URL` como `app` y como `turnos_login` -> `/me` 500 sin consultar sesion, `DATABASE_LOGIN_URL` como `turnos_app` y como `app` -> login 500 sin buscar cuenta ni crear sesion ni intentos, configuracion correcta -> 200, motores de administracion sin guardia | - |
| 4.5 | `tests/integration/test_modelo_base.py` (+4), `test_repositorios_acotados.py` (+1), `tests/isolation/test_rls.py` (+1) | Integration / Isolation | 446 | 4 fallas observadas antes de implementar (columnas sin diferir) | verdes; metadatos sin diferencias | `select(Usuario)` y `select(Sesion)` no incluyen `credencial` ni `token_hmac`; acceder lanza `InvalidRequestError`; `undefer` explicito la carga; `select(Usuario)` real como `turnos_app` con contexto devuelve 3 usuarios | - |
| 4.6 | `tests/unit/test_contexto_y_repositorios.py` (+4) | Unit | 17 | NO hubo rojo separado (el codigo ya cumplia) | 21 verdes | unica aparicion de `app.consultorio_id`; `aplicar_contexto` solo desde `auth/dependencias.py`; `fijar_consultorio_de_login` solo desde `auth/servicio.py`; sin `SET` de sesion | - |
| 4.7 | - | - | - | - | grupos 3 y 4 en verde | - | sin cambios adicionales |

Ajuste justificado de pruebas existentes en el grupo 4: `tests/integration/test_repositorios_acotados.py::test_alta_con_el_consultorio_del_contexto` lee `credencial` con SQL en lugar de `usuario.credencial` porque la columna ahora es diferida con raiseload (4.5): misma intencion (la credencial nace nula).

### Grupo 5

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 5.1 | `tests/isolation/test_funciones_acceso.py` (69) | Isolation | 102 | 54 fallas observadas (las funciones no existian) | 69 verdes tras 5.2 | conjunto exacto de 10; dueno, `prosecdef`, `proconfig`, ACL de un unico rol sin `PUBLIC`, `plpgsql`, `proretset` falso, sin `EXECUTE` en `prosrc`; ningun parametro `uuid`; rol sin concesion (creado y eliminado por la prueba); `CREATE FUNCTION acceso.x` denegado; `turnos_app` no ejecuta las 6 de login y `turnos_login` no ejecuta las 4 de sesion (42501, sin filas nuevas); HMAC de 31 y 33 bytes (22023); instante +1 h (22023, sin borrar); +4 min aceptado; conteo de cuenta <= 5 y de IP <= 30 acotados a la clave; descartados; limpieza de intentos = 100 de 150 y 0 de recientes | - |
| 5.2 | `alembic/versions/0004_aislamiento_roles_rbac.py` | Integration | idem | idem | 5.1 y 3.1 en verde; migracion/bajada verdes | `downgrade` elimina las 10 funciones antes del esquema, sin `CASCADE` | - |
| 5.3 | `tests/isolation/test_login_sin_escritura.py` (13) | Isolation | 61 | NO hubo rojo separado (las garantias las aporta 5.2) | 13 verdes | `reemplazar_credencial_por_rehash` inexistente (42883) sin cambios; todas las funciones de `turnos_login` pertenecen a `turnos_acceso_login`, sin escritura en `usuario`; ningun rol escribe `usuario`; sin politica `FOR UPDATE/DELETE` en `usuario`; `UPDATE credencial` falla (42501) como `turnos_login` y `turnos_app` con `xmin` igual; longitudes de `buscar_cuenta` con `MAXIMO_CODIGO`/`MAXIMO_EMAIL`; credencial solo de cuentas utilizables; HTTP: hash `t=2` real, hash vigente y rechazado -> credencial byte a byte y `xmin` iguales, y ninguna sentencia de escritura sobre `usuario` | - |
| 5.4 | `tests/integration/test_acceso_previo.py` (adaptado), `tests/unit/test_acceso_modulos.py` (10) | Integration / Unit | 446 | las pruebas viejas fallaban con las firmas nuevas (no se ejecuto una corrida roja aparte: reescribi los modulos antes de adaptar las pruebas) | 459 integracion; 10 unitarias | `acceso_login` solo desde `servicio` e `intentos`; `acceso_previo` solo desde `servicio`; `acceso_admin` solo desde comandos; el unico `UPDATE usuario SET credencial` de `app/` esta en `acceso_admin`; ninguna ruta ni modulo de `app/auth` lo importa; el login no hashea; los modulos no se importan entre si | `app/auth/cuenta.py` (dataclasses compartidas) |
| 5.5 | `tests/unit/test_pools_y_guardias.py`, `tests/unit/test_conexion_login.py` (7), `tests/unit/test_servicio_login_dos_transacciones.py` | Unit | 580 | ImportError observado | verdes | pool login 4/11/30/pre_ping, app 5/10/30/pre_ping, `connect_timeout` 5 y constantes nombradas; `TimeoutError` del pool de login -> `ServicioOcupado` (503) con `rollback`; el mismo error en `turnos_app` durante T2 sigue siendo generico; recorrido: unica ruta con `obtener_sesion_login` = `POST /api/auth/login` y una ruta extra se detecta; estaticas de DD-28 | `tests/rutas.py` (9.1 adelantada, ver abajo) |
| 5.6 | `tests/unit/test_servicio_login_dos_transacciones.py`, `tests/isolation/test_conexiones_login.py` (6), `tests/isolation/test_regresion_auth.py` (5), `tests/integration/test_servicio_auth.py`, `test_argon2_real.py` | Unit / Isolation / Integration | 580 / 446 | 10 fallas observadas de integracion al cambiar el servicio: 3 por un defecto mio (omitia la verificacion ficticia con cuenta inexistente) y 3 de concurrencia por usar solo `fabrica_sesiones` | verdes | orden T1 -> T2, T1 confirmada antes de abrir T2, verificador una vez, sin T2 en 401/429/503, T2 que falla revierte T2 y conserva T1; con roles reales: rol de cada transaccion, fallo al crear la sesion con 4 fallos previos (descartados, credencial y `xmin` intactos, login posterior 200), pools de una conexion sin contaminacion, verificacion con 2 locks consultivos tomados y ninguna transaccion de `turnos_app`, 10 concurrentes -> 5 x 401 y 5 x 429, sesion en el consultorio de la cuenta, login rechazado sin contexto y sin T2, revocacion de la sesion entrante de B | - |
| 5.7 | `tests/isolation/test_pool_login.py` (8), `tests/unit/test_presupuesto_conexiones.py` (5) | Isolation / Unit | 211 | NO hubo rojo separado: las condiciones se verifican sobre codigo ya construido en 5.5 y 5.6; no se cambio ningun parametro ni expectativa | 8 + 5 verdes, 3 corridas seguidas estables | ver "Validacion de PD-04" | - |
| 5.8 | - | - | - | - | unitarias 660, integracion + aislamiento 670 | - | modulos y servicio ya separados; sin cambios adicionales |

### Ajustes justificados de pruebas de C-03 (grupos 4 y 5)

- `tests/integration/test_acceso_previo.py`: importa `acceso_login`/`acceso_previo`/`acceso_admin` segun el modulo nuevo; `renovar_sesion` pasa a recibir el HMAC del token (la funcion `acceso.renovar_sesion` es por HMAC); `fallos_de_cuenta`/`fallos_de_ip` ya no reciben `limite` (5 y 30 viven en la base; se agregan pruebas de maximo 5 y 30 y la equivalencia con `POLITICA_CUENTA.umbral == 5` y `POLITICA_IP.umbral == 30`); el limite configurable de lotes del mantenimiento local se prueba con `acceso_admin.limpiar_intentos(limite=...)`; `buscar_cuenta` oculta la credencial de cuentas inactivas (nueva prueba) y la busqueda del comando local (`acceso_admin.buscar_cuenta`) si la ve.
- `tests/integration/test_servicio_auth.py::test_rehash_al_iniciar_sesion_con_parametros_desactualizados` y `tests/integration/test_argon2_real.py::test_login_http_con_hash_de_t2_responde_200_y_la_credencial_pasa_a_los_parametros_vigentes`: renombradas y adaptadas por R2-01 (REMOVED "Contrasenas con Argon2id y rehash"); esperan la credencial IDENTICA tras dos logins exitosos. Las demas aserciones de esos archivos no cambian.
- `tests/integration/datos_auth.py` (`Entorno.login`), `app_auth.py` (ruta `/prueba/login`), `test_concurrencia_login.py`: `iniciar_sesion(db_login, db, ...)` (firma de DD-27) y `app.state.fabrica_sesiones_login` en las apps de prueba. Las aserciones de concurrencia (5 x 401 / 5 x 429, 30 / 10, a lo sumo 4 verificaciones) no cambian; las 3 fallas iniciales de esa suite eran solo que la fabrica de login apuntaba al host `db` de la configuracion.
- `tests/unit/test_credenciales.py`, `test_mantenimiento.py`, `tests/integration/test_direccion_cliente.py`, `test_alta_consultorio.py`: solo cambian los modulos importados o sustituidos (`acceso_admin`, `acceso_login`, `app.auth.cuenta.Cuenta`).
- `tests/integration/test_rutas_protegidas.py`: el recorrido de rutas se extrajo a `tests/rutas.py` sin cambiar ninguna asercion (tarea 9.1, adelantada porque 5.5 la reutiliza).

### Validacion de PD-04 (5.7), configuracion real de los pools

Pools: login `pool_size=4`, `max_overflow=11`, `pool_timeout=30`, `pre_ping`; app `5/10/30`, `pre_ping`; `connect_timeout=5`. `db-test` efimera, app real de `crear_app`, conexiones reales de `turnos_login` y `turnos_app`, verificador de prueba rapido de C-03. Tres corridas consecutivas de las 14 pruebas de aislamiento de pools y login: 14 verdes cada una.

| Condicion | Prueba | Resultado |
|---|---|---|
| 1. 40 intentos, misma IP, 40 pares | `test_1_cuarenta_intentos_...` | 30 x 401 y 10 x 429; 30 fallos registrados |
| 2. 10 de la misma cuenta | `test_2_diez_intentos_...` | 5 x 401 y 5 x 429; 5 fallos |
| 3. 8 cuentas, IP distintas | `test_3_ocho_cuentas_...` | 8 x 401 |
| 4. maximo 4 Argon2 simultaneos | `test_4_a_lo_sumo_cuatro_...` | maximo = 4 con 8 solicitudes; 8 x 401 |
| 5. agotamiento forzado | `test_5_y_7_pool_de_login_agotado_...` | 503, cuerpo de servicio ocupado, `Retry-After: 5`, `Cache-Control: no-store`; verificador 0 veces; sin sesion; liberada la conexion, el login siguiente da 401 |
| 6. sin contaminacion de contexto | `test_6_las_conexiones_reutilizadas_...` | todas las conexiones libres del pool de `turnos_app` empiezan con contexto vacio |
| 7. 503 no registra intento | `test_5_y_7...`, `test_7_el_503_por_cupo...` | filas de `intento_login` iguales antes y despues (pool y cupo) |
| 8. sin conexiones ni locks | fixture `api` y `_sin_residuos` | `checkedout() == 0` en ambos pools y 0 locks consultivos de los dos roles |
| 9. presupuesto | `tests/unit/test_presupuesto_conexiones.py` | (15 + 15) x 1 + 3 comandos = 33 <= 100 - 3 - 10 = 87; 2 procesos = 63 <= 87; 3 procesos = 93 > 87. Margen: `MARGEN_DE_CONEXIONES = 10`; comandos locales simultaneos: 3 |

Observacion para el autor (no es un fallo): el presupuesto admite hasta DOS procesos de la API; un tercero exigiria revisar PD-04 (los pools y el cupo de Argon2 son por proceso).

### Desvios de TDD de esta sesion (registro honesto)

- Sin corrida roja separada: 3.5, 4.2, 4.6, 5.3, 5.7 (las pruebas verifican codigo ya construido en tareas previas). 5.4 y 5.6: reescribi los modulos antes de adaptar las pruebas existentes; la "falla" observada fueron las pruebas viejas contra las firmas nuevas.
- 4.4 se ejecuto despues de 5.2 a 5.6 (dependencia real, ver arriba).
- La tarea 9.1 (extraer `tests/rutas.py`) se adelanto porque 5.5 la reutiliza.
- La tarea 1.6 sigue sin ejecutarse (sin autorizacion): `.env.example` no se toco.


## Tercera sesion de Apply: tareas 6.1 a 8.4 (solo db-test)

Convencion: unitarias con `docker compose run --rm --no-deps api python -m pytest` (sin base); integracion y aislamiento contra `db-test` efimera con el mismo flujo del runner (contrasenas efimeras de rol por nombre, `db-test` eliminada al terminar). Ninguna conexion toco `db`, `api` ni `frontend` de desarrollo; ningun comando con `getpass` se ejecuto de verdad (lecturas inyectadas); sin `.env*`; sin `git add`/`commit`.

### Grupo 6: comandos locales

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 6.1 | `tests/unit/test_roles_postgres.py` | Unit | 660 unit (linea base de la sesion) | `ModuleNotFoundError` (`app.roles_postgres.__main__`) observado antes de escribir el modulo | 18 verdes (tras corregir una costura de mi doble de prueba: `Session.connection().exec_driver_sql`) | argumentos invalidos (6 formas), `APP_ENV=test`, sin TTY, sin `DATABASE_MIGRATION_URL`, rol sin permiso de crear roles, doble ingreso distinto, misma clave para ambos roles, clave vacia, creacion completa, existentes correctos, atributo y membresia indebidos, rotacion de un solo rol | docstring de uso (6.3) |
| 6.2 | `tests/integration/test_roles_postgres.py` | Integration | 459 integracion | **Sin corrida roja separada**: el codigo de 6.1 ya existia; las pruebas con `db-test` se escribieron despues. La primera corrida fallo 11/12 por un defecto real del codigo (`Session` no tiene `exec_driver_sql`; se uso `Session.connection()`) y 8 por un defecto de mi prueba (los `SAVEPOINT` capturados no son lecturas) | 12 verdes | creacion de los 4 roles con atributos reales de `pg_authid`; sentencias solo con verificador `SCRAM-SHA-256` y sin contrasenas en sentencias, parametros ni salida; segunda ejecucion sin cambios ni escrituras; roles reales de `db-test` verificados sin cambios; 5 atributos indebidos y 1 membresia indebida fallan sin corregir; claves iguales no crean ni el segundo rol; rotacion cambia solo el verificador indicado | los roles de prueba (`tt_c04_`) viven en la transaccion revertible: un fixture comprueba con una conexion nueva que no queda ninguno |
| 6.3 | `app/roles_postgres/__main__.py` (docstring) | - | - | n/a | docstring con el uso `docker compose run --rm -it api python -m app.roles_postgres crear [--rotar-contrasena ROL]` | - | - |
| 6.4 | `tests/unit/test_auth_contrasenas.py` (+22) | Unit | 78 en el archivo | `ImportError` (`EstadoHash`, `clasificar_hash`) observado | 100 verdes en el archivo | 11 clases (vigente, `t=2`, `m=19456`, sal de otra longitud, otro paralelismo, `$argon2i$`, `$argon2d$`, texto, vacio, PHC truncado, nulo); para cada una la misma decision que `verificar` y `necesita_rehash` | - |
| 6.5 | `tests/unit/test_credenciales.py` (+9), `tests/integration/test_credenciales.py` (+3) | Unit / Integration | 41 unit, 13 integracion | `ImportError` (`CredencialParaRevision`) observado en unitarias; las de integracion se escribieron con el codigo ya implementado (**sin corrida roja separada**) | 50 unit y 16 integracion verdes | excluyentes antes de conectar; `APP_ENV`, TTY y `DATABASE_MIGRATION_URL` como el resto; 7 usuarios -> 1/2/3/1 y 5 lineas `restablecer`; transaccion `READ ONLY` comprobada con `SHOW transaction_read_only` = `on` y escritura rechazada (SQLSTATE 25006); solo la sentencia de la propia prueba modifica; credenciales y sesiones iguales; salida sin `$argon2`, `@`, `ficticio-a`, `postgresql`; caso sin cuentas a restablecer; fallo al listar con mensaje fijo y rollback | `acceso_admin.listar_credenciales_para_revision` aplica `SET TRANSACTION READ ONLY` como primera sentencia |
| 6.6 | `tests/integration/test_credenciales.py` (+2) | Integration | idem | **Sin corrida roja separada**: la escritura condicionada (`IS NOT DISTINCT FROM`) ya existia desde C-03; las pruebas nuevas usan conexiones reales con commit (fixture `base_confirmada`, borrado al terminar solo en `db-test`) | 2 verdes | otra transaccion confirmada entre la lectura y la escritura -> mensaje fijo, credencial de la otra transaccion, sesion sin revocar; restablecer un hash `t=2` -> `$argon2id$v=19$m=65536,t=3,p=4$`, sesiones revocadas, la revision ya no la lista | - |
| 6.7 | docstring de `app/credenciales/__main__.py` | - | - | n/a | unitarias 762 verdes | - | docstring con `--revisar-hashes` |

Hallazgo del grupo 6: `tests/unit/test_conexion_login.py::test_los_comandos_locales_no_usan_el_rol_de_login` (de la sesion anterior) prohibe el texto `acceso_login` en `roles_postgres/`; mis nombres de campo coincidian. Se renombraron a `duenio_previo` / `duenio_login` (la prueba no se toco).

### Grupo 7: RBAC

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 7.1 | `tests/integration/test_dependencias_auth.py` (+5), ruta `/prueba/rol` en `app_auth.py` | Integration | 13 en el archivo | 2 fallas observadas (rol sin tipo; rol desconocido daba 200) | 16 verdes | rol tipado para `secretaria`; `/me` con texto para los 3 roles; rol `auditor` inyectado -> 401 con cuerpo de no autenticado, cookie borrada y registro `rol_desconocido` sin rol, email, ids ni token | - |
| 7.2 | `tests/unit/test_autorizacion.py` | Unit | - | `ImportError` (`app.auth.autorizacion`) observado | 12 verdes | sin roles; 4 valores no `Rol`; un invalido junto a validos; rol admitido; 2 roles no admitidos con 403, cuerpo y `no-store`; varios roles | - |
| 7.3 | `tests/integration/test_autorizacion_roles.py`, rutas de prueba en `app_auth.py` | Integration | 16 | `ModuleNotFoundError` (`app.api.errores`) observado (la prueba y las rutas se escribieron antes que `errores.py`) | 13 verdes | matriz de 3 roles x 2 rutas; 401 sin sesion; 403 de CSRF antes que el del rol; orden `Origin` -> 401 -> CSRF -> rol con la ruta ejecutada solo por el administrador; 403 identico (estado, cuerpo, cabeceras) para propio, ajeno e inexistente con 0 sentencias sobre `usuario` y un control que SI las detecta; `/me` y logout para los 3 roles con la app real y solo la sesion propia revocada | - |
| 7.4 | `tests/integration/test_autorizacion_roles.py`, `tests/isolation/test_acceso_cruzado.py` (4) | Integration / Isolation | idem | idem | 3 de integracion y 4 de aislamiento verdes | usuario de B y UUID inexistente -> 404 identicos (estado, cuerpo, cabeceras); propio 200; el 404 no depende del rol; id mal formado -> 422 sin datos; con `turnos_app` y la RLS: repositorio acotado y consulta SIN filtro de consultorio dan el mismo 404; cada consultorio ve 3/3 propios y 0/3 ajenos | `app/api/errores.py` `no_encontrado()` |
| 7.5 | `tests/unit/test_comparaciones_de_rol.py` | Unit | - | **Sin corrida roja separada** (el codigo ya cumplia); el detector se valida con 6 fragmentos que DEBE marcar y 5 que NO debe marcar, mas un control sobre `autorizacion.py` | 13 verdes | - | - |
| 7.6 | - | - | - | - | unitarias 762 verdes; integracion y aislamiento verdes | - | sin cambios adicionales |

### Grupo 8: consultorio enviado por el cliente

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 8.1 | `tests/unit/test_consultorio_cliente.py` | Unit | - | `ImportError` (`rechazar_consultorio_del_cliente`) observado | 16 verdes | 4 variantes de `consultorio_id`; valor vacio y repetido; 3 mayusculas de `X-Consultorio-Id`; 7 casos no rechazados (`X-Consultorio`, `Consultorio-Id`, `X-Tenant-Id`, `X-Request-Id`, `otro=1`, `consultorio`, `consultorio_ids`); detalle con tipo, ubicacion y mensaje fijos (la ubicacion no refleja la variante enviada) y sin el valor; `no-store`; la ruta no se ejecuta | - |
| 8.2 | `tests/integration/test_consultorio_cliente.py` (15) | Integration | 459 + 54 | 10 fallas observadas con la app sin la dependencia global (5 pasaban: las cabeceras que no se rechazan y el login sin datos prohibidos) | 15 verdes | `/me` con query y con las 3 mayusculas de la cabecera -> 422 sin ejecutar la ruta ni renovar la sesion; otras 4 cabeceras -> 200 con la identidad de A; `/health?otro=1` -> 200 y `Consultorio_ID` -> 422; login correcto con la cabecera -> 422 sin sesion ni intento ni verificacion; el 422 precede al 403 de `Origin`; sin datos prohibidos el orden de C-03 se conserva; la app de pruebas tambien la registra | registro en `crear_app` y en `crear_app_de_prueba` |
| 8.3 | `tests/unit/test_lecturas_de_peticion.py` | Unit | - | **Sin corrida roja separada** (el codigo ya cumplia; el detector se valida con 7 accesos inyectados que rompen la verificacion y con cabeceras de respuesta que no cuentan) | 12 verdes | lista blanca exacta de 7 (modulo, coleccion, nombre); ninguna lectura fuera del rechazo usa `consultorio` ni `tenant` (tambien resuelve el valor de las constantes); solo el rechazo toca esos nombres | - |
| 8.4 | `tests/unit/test_esquemas_sin_consultorio.py` (sin cambios) | Unit | - | n/a | verde | - | - |

#### Ajustes justificados de pruebas de C-03 (grupo 8)

Tres pruebas de `tests/integration/test_dependencias_auth.py` enviaban `consultorio_id` en la query o `X-Consultorio-Id` y esperaban 200 con el contexto de la sesion. Por la delta explicita de `validacion-entrada` (PD-02) esas peticiones responden ahora 422:
- `test_el_consultorio_enviado_por_el_cliente_nunca_altera_el_contexto`: ahora comprueba el 422 con esos datos, que las otras cabeceras (`X-Consultorio`, `Consultorio-Id`, `X-Tenant-Id`) se ignoran y que sin ellas el contexto es el de A (el caso "sin ellos" que pedia la tarea 8.2).
- `test_cada_sesion_da_el_contexto_de_su_propio_consultorio` y `test_el_repositorio_de_usuarios_con_el_contexto_inyectado_lista_solo_a`: el intento de colar el consultorio usa ahora un portador NO rechazado (`X-Consultorio`, `X-Tenant-Id`, parametro `consultorio`); misma intencion y mismas aserciones sobre el resultado.

#### Desvios de TDD de esta sesion (registro honesto)

- Sin corrida roja separada: 6.2 y 6.6 (el codigo existia o se implemento en 6.1/C-03), las pruebas de integracion de 6.5, 7.5 y 8.3 (verifican codigo ya conforme; los detectores se validan con casos inyectados).
- En 6.2 el primer defecto (`Session.exec_driver_sql` inexistente) lo detectaron las pruebas de integracion, no las unitarias, porque el doble de la sesion lo aceptaba; el doble se corrigio para reflejar la API real (`Session.connection()`).
- Una depuracion temporal del codigo de `roles_postgres` (traza al capturar la excepcion) se agrego y se retiro en el mismo paso (copia de respaldo restaurada); no queda en el codigo.
- La tarea 1.6 sigue sin ejecutarse (sin autorizacion): `.env.example` no se toco.


### Grupo 9: registro de aislamiento y regresion de C-03 con los roles efectivos

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 9.1 | `tests/rutas.py` | - | - | (sesion anterior) | verde | - | - |
| 9.2 | `tests/isolation/test_registro.py` (5), `tests/isolation/registro.py` | Isolation (sin conexiones) | 211 aislamiento | error de coleccion (`tests.isolation.registro` inexistente) observado | 5 verdes | igualdad exacta con la app real; entradas con caso y justificacion o parametro; ruta extra no registrada nombra `GET /api/pacientes/{paciente_id}`; entrada sin ruta nombra `DELETE /api/fantasma`; app sin rutas falla por las dos entradas | - |
| 9.3 | `tests/isolation/test_acceso_cruzado.py` (+3) | Isolation | idem | **Sin corrida roja separada** (el comportamiento ya existia) | 3 verdes | `/me` de B devuelve solo B y A sigue viendo A; logout de B revoca solo la sesion de B y A sigue valida; un ejecutor por cada entrada del registro (el conjunto de ejecutores debe igualar al registro) | - |
| 9.4 | `tests/isolation/test_regresion_auth.py` (+10) | Isolation | idem | **Sin corrida roja separada** (los flujos de C-03 ya funcionaban con los roles; se verifica la regresion) | 15 verdes en el archivo | flujo login/me/renovacion tras 61 s/logout; 6 rechazos genericos con el mismo cuerpo y sin cookie; hash `t=2` sin cambios en credencial ni `xmin`; 5 x 401 y 429 con `Retry-After`; 30 x 401 y 429 por IP; descarte tras exito; logout sin CSRF 403; usuario desactivado 401; otra `AUTH_SECRET_KEY` 401 y la original 200; credencial reemplazada durante el login (agregada en 10.2) | - |
| 9.5 | paso 6 del runner | - | - | - | `scripts/test.ps1`: 232 pruebas de aislamiento verdes | - | sin cambios adicionales del arnes |

### Tarea 10.1: `scripts/test.ps1` completo (antes de 10.2 y 10.3)

Resultado: **codigo 0**. Autoprueba OK; unitarias **762 passed**; integracion **509 passed**; aislamiento **232 passed**; `tsc` OK; Vitest **2 passed**. Comparacion con la linea base de 0.1 (516 unit + 418 integracion + 2 Vitest): las 19 pruebas de `test_superposicion_turnos.py` siguen en verde y sin cambios de contenido (`git diff -w --ignore-cr-at-eol --quiet` sin diferencias: la modificacion local es solo de finales de linea, ajena al Change; `git diff --stat` de ese archivo no muestra lineas modificadas). Despues de esa corrida se agregaron 2 pruebas de aislamiento (contrasena de rol ausente; credencial reemplazada durante el login): 234 de aislamiento en la corrida final del grupo 12.

Pruebas previas modificadas y su justificacion (acumulado; el detalle de cada una esta en las secciones de cada grupo): `test_migraciones.py` (unit e integracion), `test_seed.py`, `test_credenciales.py`, `test_mantenimiento.py`, `conftest.py`, `test_documentacion.py`, `test_database.py`, `test_crear_app.py`, `test_repositorios_acotados.py`, `test_acceso_previo.py`, `test_servicio_auth.py`, `test_argon2_real.py`, `test_concurrencia_login.py`, `test_direccion_cliente.py`, `test_alta_consultorio.py`, `test_rutas_protegidas.py` (solo extraccion), `test_migracion_autenticacion.py`, `test_dependencias_auth.py` (3 casos por el 422 de `consultorio_id`), `datos_auth.py`, `app_auth.py`. Ninguna expectativa se debilito; sin `xfail` ni `skip`.

### Tarea 10.3: secretos y datos reales

- `git status --short`: sin `.env*` en el arbol de trabajo del Change; los archivos nuevos son del Change.
- `git diff --check`: sin errores de espacios (solo avisos de finales de linea CRLF/LF preexistentes del repositorio).
- Busqueda de `TURNOS_APP_TEST_PASSWORD=`, `TURNOS_LOGIN_TEST_PASSWORD=` y `PASSWORD '` en `backend/`, `scripts/`, `docker-compose.yml`, `db/` y el Change: las unicas apariciones son (a) las asercion y construccion de sentencias con verificadores `SCRAM-SHA-256` de `app/roles_postgres` y sus pruebas, (b) `CREATE ROLE ... PASSWORD '{clave}'` de dos pruebas de aislamiento con una clave generada por `secrets.token_urlsafe(24)` en `db-test`, y (c) el texto de la spec de `ejecucion-de-pruebas`. Ningun literal de contrasena real; datos solo ficticios.


## 10.2 Matriz escenario -> prueba (14 deltas, 194 escenarios)

Notacion: UNI = `backend/tests/unit/`, INT = `backend/tests/integration/`, AIS = `backend/tests/isolation/`, AUTO = `scripts/tests/autoprueba.ps1`, RUN = `scripts/test.ps1`. Los numeros son el orden de los escenarios (`#### Scenario`) en cada `spec.md`. Resultado de la ultima corrida completa: `scripts/test.ps1` codigo 0 (ver "Tarea 10.1").

### acceso-previo-al-contexto (37)

| # | Prueba |
|---|---|
| 1 | AIS `test_funciones_acceso::catalogo_de_cada_funcion` |
| 2 | AIS `test_funciones_acceso::el_conjunto_de_funciones_es_exactamente_el_de_las_convenciones` |
| 3 | AIS `test_funciones_acceso::un_rol_sin_concesion_no_ejecuta_ninguna_funcion` |
| 4 | AIS `test_funciones_acceso::los_roles_de_conexion_no_crean_funciones_en_acceso`; AIS `test_privilegios::uso_de_esquemas_y_nunca_creacion` |
| 5 | AIS `test_funciones_acceso::turnos_app_no_ejecuta_las_funciones_de_login_ni_cambia_filas` |
| 6 | AIS `test_funciones_acceso::turnos_login_no_ejecuta_las_funciones_de_sesion` |
| 7 | AIS `test_funciones_acceso::el_duenio_de_las_funciones_de_sesion_no_toca_credenciales_ni_intentos` |
| 8 | AIS `test_funciones_acceso::ninguna_funcion_recibe_parametros_uuid` |
| 9 | AIS `test_funciones_acceso::hmac_de_longitud_invalida_*` (4 pruebas) |
| 10, 11, 12, 14 | INT `test_acceso_previo::buscar_cuenta_*`; AIS `test_login_sin_escritura::buscar_cuenta_devuelve_la_credencial_solo_de_cuentas_utilizables` y `buscar_cuenta_inexistente_no_devuelve_cuenta` |
| 13 | INT `test_servicio_auth::todo_rechazo_es_generico_ejecuta_una_verificacion_y_registra_un_fallo`; AIS `test_regresion_auth::rechazos_genericos_con_el_mismo_cuerpo_y_sin_cookie` |
| 15 | AIS `test_login_sin_escritura::ninguna_funcion_ejecutable_por_turnos_login_pertenece_a_un_rol_con_escritura_en_usuario` |
| 16 | AIS `test_login_sin_escritura::ningun_rol_del_camino_de_la_api_escribe_usuario`, `ningun_rol_nuevo_tiene_politica_de_actualizacion_sobre_usuario`, `update_de_credencial_falla_para_los_roles_de_conexion` |
| 17 | AIS `test_login_sin_escritura::la_funcion_de_rehash_no_existe_y_su_llamada_falla_sin_cambios`; `test_funciones_acceso::la_funcion_de_rehash_de_la_primera_revision_no_existe` |
| 18 | UNI `test_acceso_modulos::acceso_admin_solo_lo_importan_los_comandos_locales`, `el_unico_update_de_credencial_de_la_aplicacion_esta_en_acceso_admin`, `ninguna_ruta_ni_modulo_de_autenticacion_importa_acceso_admin` |
| 19 | AIS `test_login_sin_escritura::login_http_con_hash_anterior_vigente_y_rechazado_deja_la_credencial_y_el_xmin_intactos` |
| 20, 21 | INT `test_acceso_previo::resolver_sesion_por_hmac_con_usuario_y_consultorio`, `resolver_sesion_con_hmac_desconocido_devuelve_none` |
| 22 | AIS `test_regresion_auth::revocacion_de_la_sesion_entrante_de_otro_consultorio` |
| 23 | AIS `test_privilegios::turnos_app_recibe_42501_en_lo_denegado`, `nadie_lee_token_hmac_ni_alembic_version_fuera_de_la_administracion` |
| 24 | AIS `test_funciones_acceso::conteo_de_cuenta_limitado_a_la_clave_y_a_cinco`, `conteo_de_ip_limitado_a_treinta` |
| 25 | INT `test_acceso_previo::fallos_de_cuenta_*`, `fallos_de_ip_*`, `descartar_fallos_de_cuenta_*`; UNI `test_auth_intentos.py` |
| 26 | AIS `test_funciones_acceso::instante_una_hora_en_el_futuro_rechazado_en_funciones_de_escritura`, `el_instante_dentro_de_los_cinco_minutos_se_acepta` |
| 27 | AIS `test_funciones_acceso::limpiar_intentos_borra_exactamente_cien_de_ciento_cincuenta`, `limpiar_intentos_no_borra_fallos_recientes` |
| 28 | AIS `test_regresion_auth::sesion_creada_en_el_consultorio_de_la_cuenta` |
| 29 | AIS `test_regresion_auth::login_rechazado_sin_contexto_y_sin_abrir_la_transaccion_de_sesion` |
| 30 | AIS `test_conexiones_login::rol_de_cada_transaccion_y_t1_termina_antes_de_que_empiece_t2` |
| 31 | AIS `test_conexiones_login::fallo_al_crear_la_sesion_deja_los_fallos_descartados_y_la_credencial_intacta` |
| 32 | AIS `test_conexiones_login::pools_de_una_conexion_no_conservan_contexto_entre_logins_de_a_y_b` |
| 33 | AIS `test_conexiones_login::la_verificacion_corre_con_los_locks_tomados_y_sin_conexion_de_app` |
| 34 | AIS `test_conexiones_login::diez_logins_concurrentes_del_mismo_par_dan_cinco_401_y_cinco_429` |
| 35 | AIS `test_pool_login::test_5_y_7_pool_de_login_agotado_responde_503_sin_verificar_ni_registrar_intento` |
| 36 | AIS `test_pool_login::test_1_cuarenta_intentos_...`; UNI `test_pools_y_guardias`, `test_presupuesto_conexiones` |
| 37 | AIS `test_pool_login::test_8_el_pool_de_login_cierra_cada_transaccion_y_sus_locks` |

### aislamiento-base-de-datos (44)

| # | Prueba |
|---|---|
| 1, 2, 3 | AIS `test_catalogo_roles::cada_rol_existe_sin_atributos_indebidos`, `los_roles_de_conexion_tienen_login`, `los_duenos_de_funciones_no_tienen_login`, `ningun_rol_es_miembro_de_otro_ni_tiene_miembros`; UNI `test_roles_bd.py` |
| 4, 9 | UNI `test_roles_bd_conexion.py`, `test_pools_y_guardias::la_guardia_cierra_la_conexion_y_falla_con_mensaje_fijo_sin_valores`; AIS `test_guardia_rol_api::database_login_url_como_app_o_admin_hace_fallar_el_login_sin_cuenta_ni_sesion` y `database_url_con_otro_rol_hace_fallar_me_sin_consultar_sesion` |
| 5 | AIS `test_guardia_rol_api::configuracion_correcta_login_me_y_logout_responden_200` |
| 6 | AIS `test_guardia_rol_api::database_login_url_como_app_o_admin_...`; UNI `test_config.py` (usuarios iguales rechazados) |
| 7 | AIS `test_guardia_rol_api::database_url_con_otro_rol_hace_fallar_me_sin_consultar_sesion` |
| 8 | AIS `test_guardia_rol_api::un_rol_con_los_mismos_privilegios_y_otro_nombre_falla_por_current_user`, `database_url_con_un_rol_clonado_hace_fallar_me`; UNI `test_roles_bd_conexion::un_rol_con_los_mismos_privilegios_pero_otro_nombre_se_rechaza` |
| 10 | UNI `test_conexion_login::en_la_app_real_solo_el_login_declara_la_sesion_de_login` |
| 11 | UNI `test_conexion_login::una_ruta_extra_con_la_sesion_de_login_hace_fallar_la_verificacion` |
| 12 | UNI `test_conexion_login::el_motor_y_la_fabrica_de_login_solo_se_mencionan_en_main_y_dependencias`, `crear_engine_login_solo_se_llama_desde_main`, `obtener_sesion_login_solo_se_importa_en_la_ruta_de_login`, `database_login_url_solo_la_leen_...` |
| 13, 14, 15 | AIS `test_rls::sin_contexto_cero_filas`, `contexto_vacio_cero_filas`, `contexto_no_uuid_falla_cerrado_con_error_de_conversion` |
| 16 | AIS `test_rls::rls_habilitada_y_forzada_en_las_cuatro_tablas` |
| 17 | AIS `test_rls::contexto_a_solo_ve_a`, `contexto_b_solo_ve_b_y_a_la_inversa`, `select_de_usuario_del_orm_funciona_como_turnos_app_con_contexto` |
| 18 | AIS `test_rls::revocar_la_sesion_de_b_por_id_con_contexto_a_afecta_cero_filas` |
| 19 | AIS `test_rls::insertar_una_sesion_de_b_con_contexto_a_es_rechazado` |
| 20, 21 | AIS `test_contexto_transaccional::el_contexto_se_recupera_tras_commit`, `..._tras_rollback`, `rollback_to_savepoint_...` |
| 22 | AIS `test_contexto_transaccional::conexion_reutilizada_del_pool_empieza_sin_contexto`, `el_reset_del_pool_limpia_un_valor_de_sesion_filtrado`; `test_pool_login::test_6_...` |
| 23 | UNI `test_contexto_y_repositorios::nunca_se_fija_el_contexto_con_set_de_sesion` |
| 24 | AIS `test_privilegios::privilegios_efectivos_exactamente_iguales_a_la_matriz`, `ejecucion_de_funciones_exactamente_la_de_la_matriz` |
| 25 | AIS `test_privilegios::nadie_lee_token_hmac_ni_alembic_version_fuera_de_la_administracion`; INT `test_modelo_base::select_de_sesion_no_trae_token_hmac_y_acceder_lanza_error` |
| 26 | AIS `test_privilegios::ningun_rol_de_la_api_puede_escribir_la_credencial`, `solo_turnos_acceso_login_lee_la_credencial`; INT `test_modelo_base::select_de_usuario_no_trae_la_credencial` |
| 27 | AIS `test_privilegios::turnos_app_recibe_42501_en_lo_denegado` |
| 28, 29 | AIS `test_privilegios::turnos_login_no_tiene_acceso_a_ninguna_tabla`, `turnos_login_si_puede_consultar_sin_tablas` |
| 30 | AIS `test_catalogo_roles::los_roles_de_conexion_no_pueden_cambiar_de_rol`, `los_roles_de_conexion_no_pueden_crear_roles_ni_tablas` |
| 31, 34 | INT `test_convenciones_esquema::el_esquema_actual_cumple_las_convenciones`, `las_tablas_con_consultorio_son_las_esperadas` |
| 32, 35 | INT `test_convenciones_esquema::una_tabla_sin_clave_compuesta_ni_rls_se_detecta`, `una_fk_sin_consultorio_id_hacia_usuario_se_detecta`, `una_politica_distinta_de_la_exacta_se_detecta` |
| 33 | INT `test_convenciones_esquema::una_referencia_cruzada_entre_consultorios_la_rechaza_la_fk_compuesta` |
| 36, 37, 38 | INT `test_migracion_aislamiento::roles_ausentes_la_subida_falla_nombrando_el_rol_y_deja_0003`, `atributos_indebidos_...`, `membresias_indebidas_...`, `un_rol_dueno_de_objetos_impide_la_subida` |
| 39 | INT `test_migracion_aislamiento::subida_desde_0003_con_datos_previos_no_modifica_ninguna_fila` |
| 40 | INT `test_migracion_aislamiento::la_bajada_a_0003_restaura_el_catalogo_y_conserva_los_roles`, `la_bajada_conserva_las_filas` |
| 41 | UNI `test_roles_postgres::app_env_test_se_rechaza_sin_conectar_ni_pedir_contrasenas` |
| 42 | UNI `test_roles_postgres::roles_existentes_correctos_no_cambian_nada_ni_piden_contrasenas`; INT `test_roles_postgres::segunda_ejecucion_no_cambia_atributos_ni_contrasenas`, `los_roles_reales_de_db_test_se_verifican_sin_cambios` |
| 43 | INT `test_roles_postgres::las_sentencias_solo_llevan_verificadores_scram_nunca_la_contrasena`; UNI `creacion_completa_imprime_solo_textos_fijos_y_confirma` |
| 44 | UNI `test_roles_postgres::la_misma_contrasena_para_ambos_roles_se_rechaza_sin_crear_ninguno`; INT `contrasenas_iguales_no_crean_ni_el_segundo_rol` |

### autenticacion-sesion (19)

| # | Prueba |
|---|---|
| 1 | INT `test_servicio_auth::aislamiento_de_cuentas_la_contrasena_de_b_no_autentica_en_a`; INT `test_api_auth::la_cuenta_es_la_del_par_codigo_email_y_no_la_de_otro_consultorio` |
| 2 | INT `test_dependencias_auth::cada_sesion_da_el_contexto_de_su_propio_consultorio`; AIS `test_regresion_auth::la_cookie_de_un_consultorio_nunca_da_la_identidad_del_otro` |
| 3 | INT `test_dependencias_auth::la_identidad_sale_de_la_sesion_y_el_contexto_es_el_de_su_consultorio` |
| 4, 5 | INT `test_dependencias_auth::sin_sesion_valida_responde_401_y_borra_la_cookie` |
| 6 | INT `test_contexto_fixture.py`; AIS `test_contexto_transaccional::con_identidad_la_misma_session_ve_solo_su_consultorio` |
| 7, 8, 9, 10 | UNI `test_auth_concurrencia.py` (cupos, saturacion, liberacion ante errores y cancelacion); AIS `test_pool_login::test_4_a_lo_sumo_cuatro_verificaciones_argon2_simultaneas` |
| 11, 12, 13 | INT `test_migracion_autenticacion::la_revision_0003_depende_de_0002_y_head_es_0004`, `subida_desde_0002_con_datos_previos_...`, `bajada_a_0002_...` |
| 14 | INT `test_argon2_real::el_hasher_de_produccion_produce_el_prefijo_de_la_spec_con_sal_distinta`, `el_comando_local_guarda_un_hash_con_los_parametros_reales_de_la_spec` |
| 15 | INT `test_argon2_real::login_http_con_hash_de_t2_responde_200_y_la_credencial_queda_identica`; AIS `test_regresion_auth::login_con_credencial_de_parametros_anteriores_responde_200_sin_cambiar_la_fila` |
| 16 | INT `test_argon2_real::login_http_con_hash_vigente_no_cambia_la_credencial` |
| 17 | INT `test_argon2_real::login_http_fallido_con_hash_de_t2_no_reescribe_la_credencial`; AIS `test_login_sin_escritura::login_http_con_hash_anterior_vigente_y_rechazado...` |
| 18 | AIS `test_login_sin_escritura::login_http_con_hash_anterior_vigente_y_rechazado_deja_la_credencial_y_el_xmin_intactos` (ninguna sentencia de escritura sobre `usuario`) |
| 19 | AIS `test_regresion_auth::credencial_reemplazada_durante_el_login_queda_la_del_comando_y_el_login_no_la_modifica` (agregada en 10.2: faltaba la prueba) |

### autorizacion-roles (14)

| # | Prueba |
|---|---|
| 1 | INT `test_dependencias_auth::el_rol_de_la_identidad_es_el_tipo_cerrado_rol` |
| 2 | INT `test_dependencias_auth::me_muestra_el_rol_como_texto_para_cada_rol` |
| 3 | INT `test_dependencias_auth::un_rol_desconocido_no_autentica_responde_401_y_registra_un_codigo_fijo` |
| 4, 5 | INT `test_autorizacion_roles::matriz_de_los_tres_roles` (2 rutas); UNI `test_autorizacion::el_rol_admitido_pasa`, `varios_roles_admitidos` |
| 6 | UNI `test_autorizacion::sin_roles_falla_al_declararse`, `un_valor_que_no_es_rol_falla_al_declararse` |
| 7 | INT `test_autorizacion_roles::el_403_por_rol_es_identico_para_propio_ajeno_e_inexistente_y_no_toca_usuario` |
| 8 | INT `test_autorizacion_roles::sin_sesion_responde_401_antes_de_evaluar_el_rol` |
| 9 | INT `test_autorizacion_roles::sin_token_csrf_la_secretaria_recibe_el_403_de_csrf_antes_que_el_del_rol`, `orden_origen_identidad_csrf_rol_...` |
| 10, 11 | INT `test_autorizacion_roles::usuario_de_b_y_uuid_inexistente_responden_404_identicos_y_el_propio_200`; AIS `test_acceso_cruzado::usuario_de_b_y_uuid_inexistente_dan_404_identicos_con_turnos_app` |
| 12, 13 | INT `test_autorizacion_roles::me_y_logout_estan_disponibles_para_cada_rol` |
| 14 | UNI `test_comparaciones_de_rol.py` |

### base-de-datos-local (17)

| # | Prueba |
|---|---|
| 1 | INT `test_migraciones::el_comando_explicito_deja_la_base_al_dia` |
| 2 | AUTO "El arranque de la API no migra" |
| 3 | INT `test_migraciones::sin_tablas_de_dominio` |
| 4 | INT `test_migraciones::tablas_del_modelo_base_vacias_tras_migrar` |
| 5, 6, 7 | UNI `test_database::guardia_rechaza_la_misma_base_que_desarrollo`, `guardia_rechaza_url_de_pruebas_ausente`, `guardia_rechaza_nombre_de_base_que_no_termina_en_test` |
| 8 | AUTO "Base de pruebas separada y efimera" |
| 9 | INT `test_base_de_datos::la_suite_corre_sobre_la_base_de_pruebas` |
| 10 | UNI `test_database::guardia_rechaza_pruebas_iguales_en_destino_a_login_o_migracion`, `test_migraciones::la_guardia_de_pruebas_tambien_compara_con_la_url_de_migracion` |
| 11, 12, 13, 14 | UNI `test_migraciones::destino_test_*`, `url_explicita_*`, `env_py_*` |
| 15 | UNI `test_migraciones::destino_desarrollo_explicito_resuelve_la_base_de_desarrollo`, `desarrollo_usa_la_url_de_migracion_y_nunca_la_de_la_api` (la delta MODIFICA el destino: ahora `DATABASE_MIGRATION_URL`) |
| 16 | UNI `test_migraciones::destino_desconocido_se_rechaza_listando_los_valores_admitidos` |
| 17 | UNI `test_migraciones::desarrollo_sin_url_de_migracion_falla_mencionandola_sin_valores` |

### configuracion-backend (12)

| # | Prueba |
|---|---|
| 1, 2, 3, 4 | UNI `test_config::carga_de_valores_validos`, `falta_database_url_menciona_la_variable`, `app_env_no_admitido_menciona_la_variable`, `el_error_no_revela_la_contrasena` |
| 5, 6 | UNI `test_config.py` (URLs de migracion y de login opcionales y secretas; tarea 1.1) |
| 7 | AUTO ".env ignorado por Git" |
| 8 | AUTO "Plantilla completa con valores ficticios" (las tres URLs de rol y sus usuarios); UNI `test_plantilla_env::test_la_plantilla_declara_exactamente_las_14_variables`, `test_las_tres_urls_de_base_usan_el_usuario_de_su_rol`, `test_la_plantilla_usa_valores_ficticios_para_las_contrasenas_de_los_roles` (tarea 1.6, GREEN registrado abajo) |
| 9, 10 | UNI `test_config.py` (mismo rol rechazado; mismo servidor con roles distintos admitido) |
| 11 | UNI `test_crear_app::ningun_motor_de_la_app_apunta_a_database_migration_url` |
| 12 | UNI `test_crear_app::crear_app_sin_database_login_url_falla_con_mensaje_fijo_sin_abrir_conexiones` |

### credenciales-locales (9)

| # | Prueba |
|---|---|
| 1 | UNI `test_credenciales::app_env_test_se_rechaza_sin_conectar_ni_leer`; `test_comandos_administracion::cada_comando_con_app_env_test_se_rechaza_sin_conectar` |
| 2 | UNI `test_comandos_administracion::cada_comando_sin_la_url_de_administracion_la_menciona_sin_conectar` |
| 3 | UNI `test_comandos_administracion::la_sesion_por_defecto_de_cada_comando_apunta_al_host_de_administracion` |
| 4, 6 | UNI `test_auth_contrasenas::test_clasificar_hash` (11 clases); INT `test_credenciales::la_revision_clasifica_los_siete_usuarios_y_lista_las_cinco_cuentas`, `la_salida_de_la_revision_no_contiene_datos_sensibles` |
| 5 | INT `test_credenciales::la_revision_no_envia_escrituras_corre_en_solo_lectura_y_no_cambia_nada` |
| 7 | UNI `test_credenciales::revisar_y_reemplazar_son_excluyentes_y_fallan_antes_de_conectar` |
| 8 | INT `test_credenciales::una_transaccion_confirmada_entre_la_lectura_y_la_escritura_hace_fallar_el_comando` |
| 9 | INT `test_credenciales::restablecer_un_hash_de_t2_deja_el_hash_vigente_revoca_sesiones_y_sale_de_la_revision` |

### ejecucion-de-pruebas (5)

| # | Prueba |
|---|---|
| 1 | RUN `scripts/test.ps1` completo (codigo 0) |
| 2 | AUTO "Paso de aislamiento despues de integracion" |
| 3 | AUTO "Contrasena efimera de rol de prueba: formato y unicidad" |
| 4 | AUTO "test.ps1: contrasenas de los roles por nombre, sin literal y retiradas" |
| 5 | AUTO "db-test sin contrasenas no arranca (proyecto aislado)" |

### mantenimiento-local (4)

| # | Prueba |
|---|---|
| 1 | UNI `test_mantenimiento::app_env_test_se_rechaza_sin_abrir_sesion_ni_conectar` |
| 2 | UNI `test_mantenimiento::los_argumentos_invalidos_se_rechazan_antes_de_conectar`, `analizar_lanza_argumentos_invalidos_sin_repetir_el_valor` |
| 3 | UNI `test_mantenimiento::el_maximo_de_lotes_por_defecto_y_los_limites_se_aceptan` |
| 4 | UNI `test_comandos_administracion::cada_comando_sin_la_url_de_administracion_la_menciona_sin_conectar` (mantenimiento), `la_sesion_por_defecto_de_cada_comando_apunta_al_host_de_administracion` |

### modelo-consultorios-usuarios (3)

| # | Prueba |
|---|---|
| 1 | INT `test_modelo_base::usuario_sin_credencial_aceptado` |
| 2 | INT `test_modelo_base::credencial_vacia_rechazada` |
| 3 | INT `test_modelo_autenticacion::ninguna_restriccion_check_de_usuario_menciona_argon2` |

### pruebas-aislamiento (15)

| # | Prueba |
|---|---|
| 1 | AIS `test_arnes::motor_app_conecta_como_turnos_app_no_superusuario_en_base_de_pruebas`, `motor_login_conecta_como_turnos_login_...` |
| 2 | AIS `test_arnes::una_contrasena_de_rol_ausente_hace_fallar_el_arnes_sin_revelar_valores` (agregada en 10.2: faltaba la prueba) |
| 3 | UNI `test_database::guardia_rechaza_pruebas_iguales_en_destino_a_login_o_migracion` |
| 4 | AIS `test_arnes::limpieza_deja_todas_las_tablas_vacias`, `limpieza_al_terminar_la_prueba_anterior` |
| 5 | AIS `test_registro::el_registro_coincide_exactamente_con_las_rutas_protegidas_de_la_app_real` |
| 6 | AIS `test_registro::una_ruta_protegida_extra_no_registrada_hace_fallar_la_verificacion` |
| 7, 8 | AIS `test_acceso_cruzado::acceso_cruzado_por_entrada_del_registro[GET /api/auth/me]` y `[POST /api/auth/logout]` |
| 9 | AIS `test_acceso_cruzado::usuario_de_b_y_uuid_inexistente_dan_404_identicos_con_turnos_app` |
| 10 | AIS `test_regresion_auth::flujo_login_me_renovacion_tras_61_segundos_y_logout` |
| 11 | AIS `test_regresion_auth::login_con_credencial_de_parametros_anteriores_responde_200_sin_cambiar_la_fila` |
| 12 | AIS `test_regresion_auth::cinco_fallos_del_mismo_par_dan_401_y_el_sexto_429_con_retry_after` (y `el_limite_por_direccion_...`) |
| 13 | AIS `test_regresion_auth::rechazos_genericos_con_el_mismo_cuerpo_y_sin_cookie` |
| 14 | AIS `test_regresion_auth::un_exito_descarta_los_fallos_previos_de_la_cuenta` |
| 15 | AIS `test_regresion_auth::logout_sin_token_csrf_responde_403_y_la_sesion_sigue_valida` |

### repositorios-acotados (4)

| # | Prueba |
|---|---|
| 1 | UNI `test_contexto_y_repositorios::las_construcciones_de_contexto_fuera_de_pruebas_solo_estan_en_la_dependencia_de_identidad` |
| 2 | INT `test_dependencias_auth::la_identidad_sale_de_la_sesion_y_el_contexto_es_el_de_su_consultorio` |
| 3 | UNI `test_contexto_y_repositorios::la_unica_aparicion_del_parametro_de_contexto_esta_en_contexto_bd`, `aplicar_contexto_solo_se_llama_desde_dependencias`, `fijar_consultorio_de_login_solo_se_llama_desde_el_servicio` |
| 4 | AIS `test_acceso_cruzado::usuario_de_b_y_uuid_inexistente_dan_404_identicos_con_turnos_app[/prueba/sin-filtro/usuarios]`, `cada_consultorio_ve_solo_los_suyos_y_el_otro_le_da_404`; AIS `test_rls.py` |

### seed-ficticio (3)

| # | Prueba |
|---|---|
| 1, 2 | UNI `test_seed::entorno_de_pruebas_rechazado_con_mensaje_que_menciona_app_env`, `entorno_local_admitido` |
| 3 | UNI `test_comandos_administracion::la_sesion_por_defecto_de_cada_comando_apunta_al_host_de_administracion` (seed) |

### validacion-entrada (8)

| # | Prueba |
|---|---|
| 1 | INT `test_consultorio_cliente::me_con_consultorio_id_en_la_query_responde_422_sin_ejecutar_la_ruta`; UNI `test_consultorio_cliente::la_query_consultorio_id_se_rechaza_con_422_en_cualquier_variante` |
| 2 | INT `test_consultorio_cliente::health_con_un_parametro_cualquiera_responde_200_y_con_consultorio_id_422` |
| 3 | INT `test_consultorio_cliente::health_con_un_parametro_cualquiera_responde_200_...`; UNI `otras_cabeceras_y_parametros_no_se_rechazan` |
| 4 | INT `test_consultorio_cliente::me_con_la_cabecera_x_consultorio_id_responde_422_sin_el_valor` |
| 5 | INT `test_consultorio_cliente::health_con_la_cabecera_en_cualquier_mayuscula_responde_422`; UNI `la_cabecera_x_consultorio_id_se_rechaza_con_422_en_cualquier_variante` |
| 6 | INT `test_consultorio_cliente::login_correcto_con_la_cabecera_prohibida_responde_422_sin_sesion_ni_intento` |
| 7 | INT `test_consultorio_cliente::otras_cabeceras_se_ignoran_y_la_identidad_es_la_de_a` |
| 8 | UNI `test_lecturas_de_peticion::las_lecturas_de_la_peticion_coinciden_exactamente_con_la_lista_blanca`, `ninguna_lectura_fuera_del_rechazo_usa_un_nombre_de_consultorio_o_tenant` |

Resultado: **194 de 194 escenarios cubiertos por pruebas automatizadas** (verificado en la sesion de 12.7: las 167 referencias `archivo::funcion` de la matriz existen en `backend/tests/` y los 8 casos AUTO existen en `scripts/tests/autoprueba.ps1`). El escenario configuracion-backend #8 quedo cubierto al completarse la tarea 1.6. Dos escenarios sin prueba al empezar 10.2 (autenticacion-sesion #19 y pruebas-aislamiento #2) se cubrieron con pruebas nuevas.

## 1.6 Plantilla de variables (RED)

Fase RED de la tarea 1.6 (requisito "Plantilla de variables sin secretos y .env fuera de Git", escenario "Plantilla completa con valores ficticios"). No se leyo ni se modifico `.env.example`; la plantilla solo la leen las pruebas dentro del contenedor.

Pruebas agregadas o modificadas (ninguna asercion preexistente se quito ni relajo):
- `backend/tests/unit/test_plantilla_env.py`: `test_la_plantilla_declara_exactamente_las_14_variables` (conjunto de nombres, sin faltantes ni sobrantes), `test_las_tres_urls_de_base_usan_el_usuario_de_su_rol` (usuario via urlsplit: DATABASE_URL=turnos_app, DATABASE_LOGIN_URL=turnos_login, DATABASE_MIGRATION_URL=app), `test_la_plantilla_usa_valores_ficticios_para_las_contrasenas_de_los_roles` (POSTGRES_PASSWORD=app, migracion=app, contrasenas de turnos_app y turnos_login con prefijo `REEMPLAZAR_` y distintas entre si; solo booleanos en el mensaje).
- `backend/tests/unit/test_plantilla_ausente.py`: las tres pruebas nuevas se agregan a `PRUEBAS_QUE_DEPENDEN_DE_LA_PLANTILLA` (leen el archivo, deben fallar con la plantilla ausente).
- `scripts/tests/autoprueba.ps1`, caso 'Plantilla completa con valores ficticios': `$requeridas` suma DATABASE_LOGIN_URL y DATABASE_MIGRATION_URL; se exige el usuario de cada URL.

Comando: `docker compose run --rm --no-deps -e AUTH_SECRET_KEY api python -m pytest -p no:cacheprovider tests/unit/test_plantilla_env.py tests/unit/test_plantilla_ausente.py -v`
Resultado RED: 4 failed, 19 passed.
- FAILED `test_la_plantilla_declara_exactamente_las_14_variables`: faltan `DATABASE_LOGIN_URL` y `DATABASE_MIGRATION_URL`.
- FAILED `test_las_tres_urls_de_base_usan_el_usuario_de_su_rol`: usuario de DATABASE_URL es `app` (esperado `turnos_app`); las otras dos URL no existen (usuario None).
- FAILED `test_la_plantilla_usa_valores_ficticios_para_las_contrasenas_de_los_roles`: la contrasena de DATABASE_MIGRATION_URL esta vacia porque la variable no existe (primera asercion que falla).
- FAILED `test_con_la_plantilla_presente_el_mismo_subproceso_pasa` (preexistente, de control): el subproceso ejecuta test_plantilla_env.py completo y hereda las 3 fallas anteriores; pasara en GREEN.
Las 18 pruebas restantes siguen en verde, incluida `test_con_la_plantilla_ausente_...`.

Autoprueba (solo el caso afectado, extraido a un script temporal para no ejecutar `docker compose config`): `[FALLA] Plantilla completa con valores ficticios -> falta la variable DATABASE_LOGIN_URL`.

## 1.6 Plantilla de variables (GREEN)

La edicion de `.env.example` la hizo el autor a mano (tres conexiones de C-04); el agente no leyo ni modifico la plantilla.

Comando: `docker compose run --rm --no-deps -e AUTH_SECRET_KEY api python -m pytest -p no:cacheprovider tests/unit/test_plantilla_env.py tests/unit/test_plantilla_ausente.py -v` (imagen `api` reconstruida antes; `AUTH_SECRET_KEY` efimera generada con `New-ClaveAuthEfimera`, como `scripts/test.ps1`).
Resultado GREEN: **23 passed** (RED fue 4 failed, 19 passed). Autoprueba, caso 'Plantilla completa con valores ficticios' (script aislado): `[OK]`, codigo 0.
REFACTOR: no corresponde (solo cambio la plantilla, sin cambios de codigo). Sin expectativas relajadas.

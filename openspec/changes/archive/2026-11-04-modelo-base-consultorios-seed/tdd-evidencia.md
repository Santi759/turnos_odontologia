# Evidencia TDD: modelo-base-consultorios-seed

Entorno: Windows 11, Docker Desktop, contenedor `api` (Python 3.14.10, pytest 9.1.1, SQLAlchemy 2.1, Alembic) y `db-test` (PostgreSQL 18.6, efimera). Todo contra `db-test`; la base de desarrollo no se modifico (`alembic current` sobre desarrollo sigue en `0001`). Solo datos ficticios (`@example.test`).

## Decisiones del autor registradas (tarea 1.1)

Aprobadas por el autor el 2026-11-04 y reflejadas en `design.md` (tabla "Decisiones pendientes para el autor", ahora resueltas). Ninguna difiere de la propuesta del diseno, salvo DP-05, que fue negativa:

| Id | Respuesta |
|---|---|
| DP-01 | `consultorio.nombre` NO es unico; se identifica por UUIDv7; el login futuro usara un identificador inequivoco, no el nombre visible |
| DP-02 | `credencial` nullable (NULL = cuenta sin credenciales); cadena vacia prohibida por CHECK; C-03 debe garantizar que NULL nunca inicia sesion |
| DP-03 | Comportamiento de consultorio inactivo se decide en C-03; C-02 solo persiste `activo` |
| DP-04 | Seed con UUIDv7 literales fijos y validos; prueba de `version == 7` para cada id del seed (tarea 4.1/4.3) |
| DP-05 | Migracion `0002` y seed SOLO en `db-test`. NO se autoriza ejecutarlos sobre desarrollo: la tarea 4.8 queda sin marcar |
| DP-06 | Validacion completa de formato de email diferida a C-05; en C-02 normalizacion, no vacio y unico por consultorio |

## Linea base (tarea 1.2)

Comando: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1` (antes de cualquier cambio de codigo). Codigo de salida: 0.

- Unitarias: `86 passed, 1 warning` (incluye las 19 de `test_superposicion_turnos.py`).
- Integracion (`db-test`): `9 passed`.
- Vitest: `Tests 2 passed`.
- Total: 97. Mensaje final: `Todas las suites pasaron.`

## Tabla de evidencia (tarea 1.3)

| Tarea | Archivo de prueba | Capa | Red de seguridad | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 2.1-2.3 | `backend/tests/unit/test_modelos.py` | Unitaria | 97/97 (1.2) | `ModuleNotFoundError: No module named 'app.models.usuario'`, `1 error` en la coleccion | `6 passed` | 3 casos de `normalizar_email` (extremos, ya normalizado, espacios internos) + 5 restricciones nombradas | Sin cambios necesarios |
| 2.4 | `backend/tests/integration/conftest.py` (fixtures `config_alembic`, `revision_actual`, `base_migrada`, `sesion`), `test_migraciones.py` | Integracion | 9/9 | n/a (movimiento de fixtures, sin comportamiento nuevo) | `9 passed` tras mover los fixtures (con `0002` aun inexistente) | n/a | n/a |
| 2.5 | `backend/tests/integration/test_modelo_base.py` | Integracion | 9/9 | `relation "consultorio" does not exist` (`UndefinedTable`) en las pruebas nuevas; 31 fallos en total junto a 2.6 | `22 passed` (con 2.6: `39 passed`) tras `0002` | Varios casos por escenario (3 roles invalidos, 3 emails no normalizados, 2 consultorios, etc.) | Ver 2.9 |
| 2.6 | `backend/tests/integration/test_migraciones.py` | Integracion | 9/9 | `31 failed, 8 passed` (8 pruebas de migracion nuevas/actualizadas fallan antes de `0002`) | `39 passed, 0 failed` | subida/bajada/vuelta a head, `compare_metadata`, nombres en `pg_constraint` | Ver 2.9 |
| 2.7 | `alembic/versions/0002_modelo_base_consultorios.py` | Integracion | 9/9 | (de 2.5/2.6) | `alembic -x target=test upgrade head`: `Running upgrade 0001 -> 0002`; `39 passed` | n/a | n/a |
| 2.8 | (revision manual de SQL offline) | n/a | n/a | n/a | SQL generado coincide con DM-01; ver mas abajo | n/a | n/a |
| 2.9 | todas las anteriores | Unit+Integ | n/a | n/a | `92 passed` unitarias, `39 passed` integracion, Vitest `2 passed` en `scripts/test.ps1` (codigo 0) | n/a | Ajuste de formato de lineas largas en pruebas; sin linter configurado en el proyecto |

### Hallazgos durante GREEN (correcciones de las pruebas, no del diseno)

1. PostgreSQL 18 lista tambien las restricciones `NOT NULL` en `pg_constraint` (`contype = 'n'`, nombres como `usuario_id_not_null`) y `alembic_version` tiene su `PRIMARY KEY` (`alembic_version_pkc`). La prueba "Nombres de restricciones segun la convencion" se acoto a `contype IN ('p','f','u','c')` y a las tablas `consultorio` y `usuario`. RED->GREEN: fallo con `Extra items in the left set` -> `39 passed`.
2. `ON DELETE RESTRICT` falla con SQLSTATE `23001` (`restrict_violation`, clase 23 de integridad), no `23503` (`foreign_key_violation`), que es el que produce `NO ACTION`/inserciones con referencia inexistente. La prueba "Borrado de consultorio con usuarios restringido" exige `23001`. La spec dice "violacion de clave foranea" en sentido amplio; el diseno ya eligio `RESTRICT` explicitamente (DM-01). No cambia el comportamiento aprobado. RED->GREEN: `assert '23001' == '23503'` -> `39 passed`.

### Justificacion del cambio de `test_sin_tablas_de_dominio` (tarea 2.6)

El test de C-01 exigia `tablas == ["alembic_version"]`. Con la migracion `0002` (capacidad `modelo-consultorios-usuarios`) ese contrato deja de ser verdadero por diseno. Se actualizo a `sorted(tablas) == ["alembic_version", "consultorio", "usuario"]` conservando el nombre, segun la delta MODIFIED de `base-de-datos-local` (escenario "Sin tablas de dominio" con contenido actualizado) y DM-11. Se agrego `test_tablas_del_modelo_base_vacias_tras_migrar` (escenario "Tablas del modelo base vacias tras migrar"). Antes de `0002` la prueba actualizada fallaba (RED) y paso despues (GREEN). Sin esa justificacion no se modifica ningun otro test de C-01.

### SQL offline de la migracion (tarea 2.8)

Comando: `docker compose run --rm --no-deps api alembic -x target=test upgrade 0001:0002 --sql`. Salida: `BEGIN;` + `CREATE TABLE consultorio (...)` + `CREATE TABLE usuario (...)` + `UPDATE alembic_version SET version_num='0002' WHERE alembic_version.version_num = '0001';` + `COMMIT;`. Los `CREATE TABLE` coinciden con el boceto de DM-01 (mismas columnas, tipos, defaults, `pk_*`, `fk_usuario_consultorio_id_consultorio ... ON DELETE RESTRICT`, `uq_usuario_consultorio_id_id`, `uq_usuario_consultorio_id_email`, `ck_*`). No hay `INSERT` (`grep -ci insert` = 0); el unico `UPDATE` es el registro de la revision de Alembic.

## Regresion al cierre del Bloque 1

`scripts/test.ps1`: codigo 0, `92 passed` unitarias (86 + 6 nuevas; incluyen las 19 de superposicion), `39 passed` integracion (9 + 30 nuevas), Vitest `2 passed` = 133. `alembic current` sobre desarrollo: `0001` (sin cambios).

## Bloque 2: repositorios acotados (tareas 3.1 a 3.8)

Seguridad: `ContextoConsultorio` es inmutable, tipado (UUID) y solo se construye en codigo del servidor; no se inventa autenticacion (sin tokens, encabezados ni parseo de peticiones). En C-03 lo construira la dependencia `contexto_consultorio` desde la identidad autenticada. Los filtros por consultorio y los UUIDv7 NO reemplazan la autorizacion ni RLS de C-04 (RN-MT-06); la advertencia esta en los docstrings de `contexto.py`, `base.py` y `consultorios.py`.

Linea base de entrada del bloque: unitarias 92, integracion 39 (cierre del Bloque 1).

| Tarea | Archivo de prueba | Capa | Red de seguridad | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 3.1 | `backend/tests/unit/test_contexto_y_repositorios.py` | Unitaria | 92/92 + 39/39 | `ModuleNotFoundError: No module named 'app.repositories.consultorios'` (coleccion) | tras 3.2/3.3: `15 passed` | contexto con `"1"`, `1`, `str(UUID)`, `None`; dos repositorios sin contexto; dos contextos A y B | n/a |
| 3.2 | idem | Unitaria | idem | (de 3.1) | `contexto.py`, `base.py` (`RepositorioAcotado`), `NuevoUsuario` en `usuarios.py` | n/a | n/a |
| 3.3 | idem | Unitaria | idem | (de 3.1) | SQL compilado de `listar`, `obtener_por_id`, `buscar_por_email` contiene `usuario.consultorio_id = '<UUID del contexto>'` para A y para B; `ConsultorioRepositorio` solo expone `obtener_actual` (superficie publica == `{"obtener_actual"}`) y su SQL filtra por `consultorio.id` del contexto | contextos A/B; email normalizado en el SQL | n/a |
| 3.4 | `backend/tests/unit/test_esquemas_sin_consultorio.py` | Unitaria | idem | Con `app/schemas/temporal_red.py` (subclase temporal de `EsquemaEntrada` con `consultorio_id`): `AssertionError: assert ['EsquemaTemporalConConsultorio'] == []`, `1 failed, 1 passed`. Archivo temporal eliminado; `git status --short` no lista `app/schemas` | sin la subclase: `2 passed`; luego `3 passed` con el control de `extra="forbid"` | prueba adicional de `extra="forbid"` (hoy sin esquemas de dominio, con control sobre la base comun) | n/a |
| 3.5 | `backend/tests/integration/test_repositorios_acotados.py` (14 pruebas, A/B ficticios en `db-test`, sesion con savepoint revertida) | Integracion | 39/39 | Los metodos ya existian desde 3.3 (se implementaron junto con sus consultas), asi que la RED se obtuvo por MUTACION: se reemplazo temporalmente la condicion de consultorio de `RepositorioAcotado` por `true()`; resultado `9 failed, 20 passed` (7 de integracion: listado, get ajeno, email propio y ajeno, alta en contexto, alta repetida, desactivar ajeno; 2 unitarias del SQL). Archivo restaurado de copia y `29 passed` | `53 passed` integracion | mismo email en A y B; email repetido en A con otra capitalizacion (SQLSTATE 23505); alta en B queda en B | n/a |
| 3.6 | `test_database.py` (unitaria, 2 pruebas nuevas) + integracion | Unit+Integ | 12/12 de `test_database.py` | `ImportError: cannot import name 'crear_fabrica_de_sesiones'` (2 failed) | `crear_fabrica_de_sesiones` en `app/core/database.py` (`expire_on_commit=False`, sin instancia global): `14 passed` | sesiones independientes; sin conexion al crearlas | n/a |
| 3.7 | `test_repositorios_acotados.py` | Integracion | idem | cubierta por la mutacion de 3.5 (`test_obtener_por_id_de_otro_...` y `test_desactivar_..._igual_que_inexistente` fallan con el filtro anulado) | obtener por id y email ajenos == inexistentes (`None`); `desactivar` ajeno == inexistente (`False`) y ninguna fila cambia | `desactivar` propio True y fila `activo=False`; no afecta a otros propios ni ajenos | n/a |
| 3.8 | todas | Unit+Integ | n/a | n/a | el filtro vive solo en `_condicion_de_consultorio`/`_seleccionar`; unitarias `112 passed`, integracion `53 passed` | n/a | Sin duplicacion: lecturas parten de `_seleccionar()`, `desactivar` usa `_condicion_de_consultorio()` |

Hallazgo de proceso: `crear()` toma `consultorio_id` solo del contexto; `NuevoUsuario` no tiene ese campo (`TypeError` si se pasa), y `credencial` nunca se escribe (queda nula).

### Regresion al cierre del Bloque 2

`scripts/test.ps1`: codigo 0, `112 passed` unitarias (86 + 6 + 20 nuevas), `53 passed` integracion (9 + 30 + 14), Vitest `2 passed` = 167. Las 19 de superposicion: `19 passed` en el venv del host (`backend/.venv`) y dentro del total del contenedor. `alembic current` sobre desarrollo: `0001`.

## Bloque 3: seed ficticio (tareas 4.1 a 4.6; 4.7 y 4.8 NO se hacen aqui)

Seguridad: el seed solo corre con `APP_ENV=local` y solo contra `DATABASE_URL`; el comando real (`python -m app.seed`) NO se ejecuto contra ninguna base en este bloque. Las pruebas de integracion usan `aplicar_seed` con el fixture `sesion` (transaccion revertida de `db-test`) y `main(abrir_sesion=...)` con esa misma sesion inyectada (costura de pruebas; el valor por defecto crea motor y sesion desde `DATABASE_URL`). Datos: 2 consultorios "Consultorio Demo A/B", 6 usuarios `@example.test` con `Demo` en el nombre, `credencial` nula (sin hashing), UUIDv7 literales generados una vez con `uuid.uuid7()` del contenedor (DP-04). Solo `INSERT ... ON CONFLICT DO NOTHING` sin destino de conflicto, sin UPDATE/DELETE.

Linea base de entrada: unitarias 112, integracion 53.

| Tarea | Archivo de prueba | Capa | Red de seguridad | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 4.1 | `backend/tests/unit/test_seed.py` | Unitaria | 112/112 + 53/53 | `ModuleNotFoundError: No module named 'app.seed'` (1 error de coleccion) | `13 passed` | ids: version 7, variante RFC 4122, 8 unicos; roles por consultorio; sin campo de credencial; guardia local/test; `main` con `APP_ENV=test`: codigo != 0, texto con `APP_ENV`, sin `host-inexistente`/`postgresql`/`secreto`/`@`, listener `do_connect` sin intentos; control: con `APP_ENV=local` el listener SI detecta `host-inexistente.invalid`; errores con tabla inexistente (42P01) y generico sin detalles, con rollback; resumen con cantidades distintas | n/a |
| 4.2 | idem | Unitaria | idem | (de 4.1) | `app/seed/{datos,entorno,aplicar,__main__}.py` | n/a | n/a |
| 4.3 | `backend/tests/integration/test_seed.py` (9 pruebas, `db-test`, savepoint revertido) | Integracion | 53/53 | `aplicar_seed` ya existia (requerido por el import de 4.1), asi que la RED se obtuvo por MUTACION: se cambio temporalmente `on_conflict_do_nothing` por `on_conflict_do_update` en consultorios: `2 failed, 7 passed` (`test_dos_ejecuciones_no_duplican`, `test_una_fila_del_seed_modificada_no_se_sobrescribe`). Restaurado desde copia | `9 passed` | dos ejecuciones (2da: 0 insertadas, 8 omitidas); ids fijos tras rollback y reaplicacion; consultorio y usuario del seed renombrados no se sobrescriben; fila ajena con el mismo email (tras borrar el administrador del seed) conserva id y nombre, omitidas >= 1; `main` inyectado imprime solo cantidades (sin `@`, `postgresql` ni nombres) y carga 6 usuarios | n/a |
| 4.4 | `test_seed.py` (unitaria) | Unitaria | idem | n/a | Prueba que escanea `app/seed/*.py` y exige cero coincidencias con `update|delete|truncate|drop`; control: el patron detecta `update(Usuario)...` y no detecta `insert(...).on_conflict_do_nothing()`. `15 passed` en `test_seed.py` | n/a | n/a |
| 4.5 | `scripts/tests/autoprueba.ps1` (caso "El arranque de la API no ejecuta el seed") | Autoprueba | autoprueba previa verde | Control del patron en PowerShell: `-notlike '*app.seed*'` sobre `python -m app.seed` -> `DETECTA` (el caso fallaria); sobre el comando `uvicorn ...` -> no detecta | `[OK] El arranque de la API no ejecuta el seed`, `Autoprueba: todos los casos pasan`, exit 0 | ASCII, PowerShell 5.1 | n/a |
| 4.6 | todas | Unit+Integ | n/a | n/a | salida y errores revisados: solo cantidades o mensajes fijos, sin emails, nombres ni URLs (verificado por las pruebas de salida) | n/a | Guardia en `entorno.py` (pura), aplicacion en `aplicar.py`, comando en `__main__.py` |

"Migrar no carga datos" ya esta cubierta por `test_migrar_desde_base_no_carga_datos` y `test_tablas_del_modelo_base_vacias_tras_migrar` (Bloque 1).

### Regresion al cierre del Bloque 3

`scripts/test.ps1`: codigo 0 (incluye la autoprueba ampliada), `127 passed` unitarias (112 + 15), `62 passed` integracion (53 + 9), Vitest `2 passed` = 191. Las 19 de superposicion: `19 passed` en el venv del host. Desarrollo: `alembic current` = `0001`; consulta de solo lectura `pg_tables` (esquema `public`) = solo `alembic_version`.

## Bloque 4: integracion y regresion (ejecuciones; NO es el Verify formal)

Este bloque solo registra ejecuciones y una pre-verificacion de trazabilidad. No existe `verify.md` ni se emite conclusion de Verify (O2): lo aprobara el autor por separado.

### Ejecuciones (salida real)

| Comando | Resultado |
|---|---|
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1` | codigo de salida 0; pasos 0 a 7 ejecutados (autoprueba con "Autoprueba: todos los casos pasan"; build; unitarias `127 passed, 1 warning`; db-test; `alembic upgrade head`; integracion `62 passed`; `tsc --noEmit`; Vitest `2 passed`); "Todas las suites pasaron." Total 191 (97 previas + 94 nuevas) |
| `backend/.venv/Scripts/python.exe -m pytest -p no:cacheprovider tests/unit/test_superposicion_turnos.py -q` (venv del host) | `19 passed in 0.03s` |
| `git diff --quiet f13f0ba -- backend/app/domain/superposicion_turnos.py backend/tests/unit/test_superposicion_turnos.py` | codigo de salida 0 (sin cambios); `git diff --quiet HEAD -- ...` tambien 0 |
| `openspec validate modelo-base-consultorios-seed --strict` | `Change 'modelo-base-consultorios-seed' is valid`; codigo de salida 0 |
| `docker compose run --rm --no-deps api alembic current` (desarrollo, solo lectura) | `0001` |

### Las 97 pruebas previas

Las 97 de la linea base siguen existiendo y pasando (todas dentro de las 191): 86 unitarias previas (incluidas las 19 de superposicion), 9 de integracion y 2 de Vitest. Archivos previos modificados (`git diff HEAD --numstat`):

- `backend/tests/integration/conftest.py` (+51/-1): se agregaron los fixtures `config_alembic`, `revision_actual`, `base_migrada` (movido desde `test_migraciones.py`) y `sesion`. El fixture `motor` no cambia.
- `backend/tests/integration/test_migraciones.py` (+126/-36): el helper `_configuracion_alembic`, `_revision_actual` y el fixture `base_migrada` pasaron a fixtures de `conftest.py` (sin cambio de logica); `test_el_comando_explicito_deja_la_base_al_dia` usa esos fixtures con las mismas aserciones; `test_sin_tablas_de_dominio` es el UNICO cambio de contrato (justificado en la tarea 2.6). Las otras 3 pruebas previas del archivo no se tocaron.
- `backend/tests/unit/test_database.py` (+27/-0): solo 2 pruebas nuevas de `crear_fabrica_de_sesiones`; las previas intactas.
- `backend/tests/integration/test_base_de_datos.py` y `backend/tests/unit/test_superposicion_turnos.py`: sin cambios.
- Comprobacion automatica: todos los nombres `def test_*` de `test_migraciones.py` (integracion), `test_database.py` y `test_base_de_datos.py` en `HEAD` siguen presentes en la coleccion actual (0 ausentes). La coleccion actual tiene 189 pruebas de backend (127 + 62).

### Pre-verificacion de trazabilidad escenario -> prueba (59 escenarios: 4 + 24 + 18 + 13)

Resultado: 59 de 59 con prueba automatizada existente y en verde; sin brechas. No hizo falta agregar pruebas.

| N | Capacidad | Escenario | Prueba (`archivo::prueba`, bajo `backend/tests/` salvo la autoprueba) |
|---|---|---|---|
| 1 | base-de-datos-local | El comando explícito deja la base al día | `integration/test_migraciones.py::test_el_comando_explicito_deja_la_base_al_dia` |
| 2 | base-de-datos-local | El arranque de la API no migra | `scripts/tests/autoprueba.ps1: caso 'El arranque de la API no migra'` |
| 3 | base-de-datos-local | Sin tablas de dominio | `integration/test_migraciones.py::test_sin_tablas_de_dominio` |
| 4 | base-de-datos-local | Tablas del modelo base vacías tras migrar | `integration/test_migraciones.py::test_tablas_del_modelo_base_vacias_tras_migrar` |
| 5 | modelo-consultorios-usuarios | Valores por defecto al insertar solo el nombre | `integration/test_modelo_base.py::test_valores_por_defecto_al_insertar_solo_el_nombre` |
| 6 | modelo-consultorios-usuarios | La zona horaria por defecto es válida para PostgreSQL | `integration/test_modelo_base.py::test_la_zona_horaria_por_defecto_existe_una_vez_en_pg_timezone_names` |
| 7 | modelo-consultorios-usuarios | Nombre obligatorio | `integration/test_modelo_base.py::test_nombre_de_consultorio_obligatorio` |
| 8 | modelo-consultorios-usuarios | Anticipación negativa rechazada | `integration/test_modelo_base.py::test_anticipacion_negativa_rechazada` |
| 9 | modelo-consultorios-usuarios | Anticipación cero aceptada | `integration/test_modelo_base.py::test_anticipacion_cero_aceptada` |
| 10 | modelo-consultorios-usuarios | Id de consultorio generado por el servidor | `integration/test_modelo_base.py::test_id_de_consultorio_generado_como_uuid_v7` |
| 11 | modelo-consultorios-usuarios | Id de usuario generado por el servidor | `integration/test_modelo_base.py::test_id_de_usuario_generado_como_uuid_v7_y_distinto_del_consultorio` |
| 12 | modelo-consultorios-usuarios | Usuario con consultorio inexistente rechazado | `integration/test_modelo_base.py::test_usuario_con_consultorio_inexistente_rechazado` |
| 13 | modelo-consultorios-usuarios | Usuario sin consultorio rechazado | `integration/test_modelo_base.py::test_usuario_sin_consultorio_rechazado` |
| 14 | modelo-consultorios-usuarios | Borrado de consultorio con usuarios restringido | `integration/test_modelo_base.py::test_borrado_de_consultorio_con_usuarios_restringido` |
| 15 | modelo-consultorios-usuarios | Valores por defecto del usuario | `integration/test_modelo_base.py::test_valores_por_defecto_del_usuario` |
| 16 | modelo-consultorios-usuarios | Restricción de unicidad compuesta presente | `integration/test_modelo_base.py::test_restriccion_unica_compuesta_consultorio_id_e_id_presente` |
| 17 | modelo-consultorios-usuarios | Roles admitidos aceptados | `integration/test_modelo_base.py::test_roles_admitidos_aceptados` |
| 18 | modelo-consultorios-usuarios | Rol no admitido rechazado | `integration/test_modelo_base.py::test_rol_no_admitido_rechazado (3 casos)` |
| 19 | modelo-consultorios-usuarios | Mismo email en dos consultorios | `integration/test_modelo_base.py::test_mismo_email_en_dos_consultorios_aceptado` |
| 20 | modelo-consultorios-usuarios | Email repetido en el mismo consultorio rechazado | `integration/test_modelo_base.py::test_email_repetido_en_el_mismo_consultorio_rechazado` |
| 21 | modelo-consultorios-usuarios | Email no normalizado rechazado por la base | `integration/test_modelo_base.py::test_email_no_normalizado_rechazado_por_la_base (3 casos)` |
| 22 | modelo-consultorios-usuarios | Usuario sin credencial aceptado | `integration/test_modelo_base.py::test_usuario_sin_credencial_aceptado` |
| 23 | modelo-consultorios-usuarios | Credencial vacía rechazada | `integration/test_modelo_base.py::test_credencial_vacia_rechazada` |
| 24 | modelo-consultorios-usuarios | Cadena de revisiones | `integration/test_migraciones.py::test_cadena_de_revisiones_head_0002_sobre_0001` |
| 25 | modelo-consultorios-usuarios | Subida desde 0001 crea las tablas vacías | `integration/test_migraciones.py::test_subida_desde_0001_crea_las_tablas_vacias` |
| 26 | modelo-consultorios-usuarios | Bajada a 0001 elimina las tablas y conserva la extensión | `integration/test_migraciones.py::test_bajada_a_0001_elimina_las_tablas_y_conserva_btree_gist` |
| 27 | modelo-consultorios-usuarios | Sin diferencias entre modelos y base migrada | `integration/test_migraciones.py::test_los_modelos_coinciden_con_la_base_migrada` |
| 28 | modelo-consultorios-usuarios | Nombres de restricciones según la convención | `integration/test_migraciones.py::test_nombres_de_restricciones_segun_la_convencion (y unit/test_modelos.py::test_usuario_declara_las_restricciones_con_nombre_de_la_convencion)` |
| 29 | repositorios-acotados | Contexto con identificador válido | `unit/test_contexto_y_repositorios.py::test_contexto_expone_el_identificador_y_es_inmutable` |
| 30 | repositorios-acotados | Contexto con identificador no UUID rechazado | `unit/test_contexto_y_repositorios.py::test_contexto_con_identificador_no_uuid_rechazado (4 casos)` |
| 31 | repositorios-acotados | Repositorio sin contexto rechazado | `unit/test_contexto_y_repositorios.py::test_repositorio_sin_contexto_rechazado (2 casos)` |
| 32 | repositorios-acotados | Ningún esquema de entrada declara consultorio_id | `unit/test_esquemas_sin_consultorio.py::test_ningun_esquema_de_entrada_declara_consultorio_id` |
| 33 | repositorios-acotados | Datos de alta de usuario sin consultorio_id | `unit/test_contexto_y_repositorios.py::test_datos_de_alta_de_usuario_sin_consultorio_id` |
| 34 | repositorios-acotados | Listado solo del consultorio propio | `integration/test_repositorios_acotados.py::test_listado_solo_del_consultorio_propio` |
| 35 | repositorios-acotados | Obtener por id un usuario de otro consultorio | `integration/test_repositorios_acotados.py::test_obtener_por_id_de_otro_consultorio_igual_que_inexistente` |
| 36 | repositorios-acotados | Obtener por id un usuario propio | `integration/test_repositorios_acotados.py::test_obtener_por_id_propio_devuelve_el_usuario` |
| 37 | repositorios-acotados | Buscar por email dentro del consultorio | `integration/test_repositorios_acotados.py::test_buscar_por_email_dentro_del_consultorio_sin_distinguir_mayusculas` |
| 38 | repositorios-acotados | Buscar por email de otro consultorio | `integration/test_repositorios_acotados.py::test_buscar_por_email_de_otro_consultorio_igual_que_inexistente` |
| 39 | repositorios-acotados | Toda consulta generada incluye el filtro por consultorio | `unit/test_contexto_y_repositorios.py::test_toda_consulta_generada_incluye_el_filtro_por_consultorio (2 casos)` |
| 40 | repositorios-acotados | Alta con el consultorio del contexto | `integration/test_repositorios_acotados.py::test_alta_con_el_consultorio_del_contexto` |
| 41 | repositorios-acotados | Alta con email repetido en el consultorio, sin distinguir mayúsculas | `integration/test_repositorios_acotados.py::test_alta_con_email_repetido_sin_distinguir_mayusculas_rechazada` |
| 42 | repositorios-acotados | Desactivar un usuario de otro consultorio | `integration/test_repositorios_acotados.py::test_desactivar_un_usuario_de_otro_consultorio_igual_que_inexistente` |
| 43 | repositorios-acotados | Desactivar un usuario propio | `integration/test_repositorios_acotados.py::test_desactivar_un_usuario_propio` |
| 44 | repositorios-acotados | Obtener el consultorio actual | `integration/test_repositorios_acotados.py::test_obtener_el_consultorio_actual` |
| 45 | repositorios-acotados | Contexto de un consultorio inexistente | `integration/test_repositorios_acotados.py::test_contexto_de_un_consultorio_inexistente_no_devuelve_resultado` |
| 46 | repositorios-acotados | Sin operaciones sobre otros consultorios | `unit/test_contexto_y_repositorios.py::test_consultorio_repositorio_solo_expone_obtener_actual` |
| 47 | seed-ficticio | Migrar no carga datos | `integration/test_migraciones.py::test_migrar_desde_base_no_carga_datos` |
| 48 | seed-ficticio | El arranque de la API no ejecuta el seed | `scripts/tests/autoprueba.ps1: caso 'El arranque de la API no ejecuta el seed'` |
| 49 | seed-ficticio | Dos consultorios y seis usuarios | `integration/test_seed.py::test_dos_consultorios_y_seis_usuarios` |
| 50 | seed-ficticio | Datos evidentemente ficticios | `integration/test_seed.py::test_datos_evidentemente_ficticios` |
| 51 | seed-ficticio | Valores de consultorio del seed | `integration/test_seed.py::test_valores_de_consultorio_del_seed` |
| 52 | seed-ficticio | Seis usuarios sin credencial | `integration/test_seed.py::test_seis_usuarios_sin_credencial` |
| 53 | seed-ficticio | Dos ejecuciones no duplican | `integration/test_seed.py::test_dos_ejecuciones_no_duplican` |
| 54 | seed-ficticio | Identificadores fijos | `integration/test_seed.py::test_identificadores_fijos_entre_aplicaciones` |
| 55 | seed-ficticio | Una fila del seed modificada no se sobrescribe | `integration/test_seed.py::test_una_fila_del_seed_modificada_no_se_sobrescribe` |
| 56 | seed-ficticio | Una fila ajena con el mismo email se respeta | `integration/test_seed.py::test_una_fila_ajena_con_el_mismo_email_se_respeta` |
| 57 | seed-ficticio | Entorno de pruebas rechazado | `unit/test_seed.py::test_main_con_app_env_test_no_abre_conexion_y_termina_con_error` |
| 58 | seed-ficticio | Entorno local admitido | `unit/test_seed.py::test_entorno_local_admitido` |
| 59 | seed-ficticio | Resumen solo con cantidades | `unit/test_seed.py::test_resumen_solo_informa_cantidades (y integration/test_seed.py::test_el_comando_principal_informa_solo_cantidades_y_carga_el_seed)` |

Los escenarios "El arranque de la API no migra" y "El arranque de la API no ejecuta el seed" se cubren con la autoprueba (`scripts/tests/autoprueba.ps1`), paso 0 de `scripts/test.ps1`.

## Tarea 4.8: ejecución sobre la base de desarrollo (2026-11-04, orquestador)

El autor autorizó expresamente OP-1, OP-2 y OP-3 (DP-05), solo sobre la base local de desarrollo. Se ejecutaron en orden, con verificaciones entre cada paso. No hubo downgrade, DROP, DELETE, TRUNCATE ni `down -v`.

### Comprobaciones previas

| Comprobación | Resultado |
|---|---|
| Directorio y rama | `C:\dev\turnos_odontologia`, `main` |
| PostgreSQL | `pg_isready`: `accepting connections`; `db` Up (healthy); PostgreSQL 18.6 |
| Destino de `DATABASE_URL` (sin credenciales) | `postgresql+psycopg`, host `db` (servicio local de Docker Compose), puerto 5432, base `turnos`, `APP_ENV=local` |
| Revisión de Alembic | `0001` |
| Tablas en `public` | Solo `alembic_version`; 0 tablas de dominio, así que no había datos preexistentes que modificar |

### OP-1: `docker compose run --rm api alembic upgrade head`

```
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, modelo base: tablas consultorio y usuario (sin datos)
OP1_EXIT=0
```

Verificación posterior:
- `alembic current`: `0002 (head)`.
- Tablas: `alembic_version, consultorio, usuario`.
- `consultorio`: 0 filas. `usuario`: 0 filas.
- Extensiones: `btree_gist` y `plpgsql`.
- Restricciones de `pg_constraint`: coinciden con DM-01.
  - `pk_consultorio` y `pk_usuario`.
  - `ck_consultorio_anticipacion_no_negativa`.
  - `ck_usuario_credencial_no_vacia`, `ck_usuario_email_normalizado` y `ck_usuario_rol_valido` (`administrador`, `secretaria`, `odontologo`).
  - `fk_usuario_consultorio_id_consultorio ... ON DELETE RESTRICT`.
  - `uq_usuario_consultorio_id_email` y `uq_usuario_consultorio_id_id`.
- Columnas:
  - `id uuid` con default `uuidv7()` en las dos tablas.
  - `zona_horaria` con default `'America/Argentina/Buenos_Aires'`.
  - `anticipacion_cancelacion_horas` con default 24.
  - `activo` con default `true`.
  - `creado_en timestamptz` con default `now()`.
  - `credencial` admite NULL; el resto de las columnas son NOT NULL.

### OP-2: `docker compose run --rm api python -m app.seed` (primera carga)

```
consultorios: 2 insertados, 0 omitidos; usuarios: 6 insertados, 0 omitidos
OP2_EXIT=0
```

Verificación posterior:
- 2 consultorios, "Consultorio Demo A" y "Consultorio Demo B".
- 6 usuarios: 3 por consultorio, uno por rol.
- 6 de 6 emails en `@example.test`.
- 6 de 6 con `credencial IS NULL`.
- Los 8 `id` (2 consultorios y 6 usuarios) tienen versión `7`, según el dígito de versión del UUID.
- No hay datos personales reales.

Huella del contenido antes de OP-3 (`md5(string_agg(row(t.*)::text, '|' order by id))`):
- `consultorio`: `9d0059bb42915baa8fa2d7b94265725e`
- `usuario`: `84a7a3e1fa420f80bfa2818c81a8fccc`

### OP-3: `docker compose run --rm api python -m app.seed` (segunda carga)

```
consultorios: 0 insertados, 2 omitidos; usuarios: 0 insertados, 6 omitidos
OP3_EXIT=0
```

Verificación posterior:
- Huellas idénticas a las de antes de OP-3: ningún dato se sobrescribió.
- `SELECT count(*)`: `consultorio` = 2, `usuario` = 6.

### Consultas de solo lectura del README

| Consultorio | Zona horaria | Anticipación | Activo | Usuarios |
|---|---|---|---|---|
| Consultorio Demo A | America/Argentina/Buenos_Aires | 24 | t | 3 (administrador, odontologo, secretaria) |
| Consultorio Demo B | America/Argentina/Buenos_Aires | 24 | t | 3 (administrador, odontologo, secretaria) |

Los 6 usuarios tienen `activo = t` y `sin_credencial = t`.

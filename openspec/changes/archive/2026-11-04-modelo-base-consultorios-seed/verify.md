# Verify: modelo-base-consultorios-seed (C-02)

Verificación formal (tareas 5.3 a 5.6) del Change `modelo-base-consultorios-seed`, ejecutada el 2026-11-04 en Windows 11 con Docker Desktop y PowerShell, sobre la rama `main` (HEAD `188f064`, con los cambios de C-02 sin commitear). Todos los datos son ficticios. **Este documento no archiva el Change**: el Archive solo se ejecuta con indicación del autor (AGENTS.md O2) y marca C-02 `[x]` en `CHANGES.md` en ese momento.

## Entorno

```
Docker 29.9.2 / Docker Compose v5.6.1
openspec CLI: 1.14.1
Imagen api: Python 3.14.10, pytest 9.1.1, SQLAlchemy 2.1.6, Alembic 1.20.1 (ver verify de foundation-setup)
PostgreSQL: 18.6 (servicios db de desarrollo y db-test efímero)
Host: backend/.venv (solo para las 19 pruebas de superposición)
```

Restricciones respetadas en esta verificación: sin migraciones adicionales sobre desarrollo, sin volver a ejecutar el seed, sin `downgrade`/`DROP`/`DELETE`/`TRUNCATE`/`down -v`; acceso a desarrollo solo de lectura (`SELECT` y `alembic current`). `scripts/test.ps1` migra únicamente `db-test`.

## Comandos ejecutados y resultados

### 1. `openspec validate modelo-base-consultorios-seed --strict`

```
Change 'modelo-base-consultorios-seed' is valid
rc=0
```

### 2. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1`

Código de salida: **0**. Resumen real por paso (salida completa guardada fuera del repositorio; las pruebas corrieron con `-v`):

```
==> 0. autoprueba del runner y de la higiene del repositorio
[OK]    Un paso falla
[OK]    Todos los pasos de la secuencia pasan
[OK]    Falta el archivo .env
[OK]    .env ignorado por Git
[OK]    Plantilla completa con valores ficticios
[OK]    El arranque de la API no migra
[OK]    El arranque de la API no ejecuta el seed
[OK]    Base de pruebas separada y efimera
[OK]    Verificacion de tipos estricta
[OK]    Sin any en el codigo del frontend
[OK]    Pruebas existentes en verde (archivo sin cambios)
[OK]    test.ps1 sin .env termina con error antes de cualquier suite
[OK]    Scripts en ASCII y sin redireccion de stderr de comandos nativos
Autoprueba: todos los casos pasan
==> 1. construir imagenes (api, frontend)
==> 2. pruebas unitarias del backend (incluye las 19 de superposicion)
======================== 127 passed, 1 warning in 2.96s ========================
==> 3. levantar la base de pruebas efimera (db-test)
==> 4. migraciones sobre la base de pruebas (alembic upgrade head)
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, habilitar btree_gist (infraestructura, sin tablas de dominio)
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, modelo base: tablas consultorio y usuario (sin datos)
==> 5. pruebas de integracion contra PostgreSQL real (db-test)
============================== 62 passed in 6.23s ==============================
==> 6. verificacion de tipos del frontend (tsc --noEmit)
==> 7. pruebas del frontend (Vitest)
 Test Files  1 passed (1)
      Tests  2 passed (2)
Todas las suites pasaron.
```

Totales: 127 unitarias + 62 de integración + 2 de Vitest = **191** (línea base 97 + 94 nuevas). En la salida `-v` hay 189 líneas `PASSED` y 0 `FAILED`/`ERROR`/`SKIPPED`/`xfail`. La única advertencia es `StarletteDeprecationWarning` por `httpx` en `starlette.testclient` (DT-01 de C-01, preexistente).

### 3. Las 19 pruebas de superposición en el host y archivos sin cambios

```
$ backend/.venv/Scripts/python -m pytest -p no:cacheprovider backend/tests/unit/test_superposicion_turnos.py -q
...................                                                      [100%]
19 passed in 0.03s

$ git diff --quiet f13f0ba -- backend/app/domain/superposicion_turnos.py backend/tests/unit/test_superposicion_turnos.py
rc=0
```

Las 19 también están dentro de las 127 del contenedor.

## Trazabilidad formal escenario → prueba (tarea 5.3)

Los 59 escenarios de las cuatro specs (4 `base-de-datos-local`, 24 `modelo-consultorios-usuarios`, 18 `repositorios-acotados`, 13 `seed-ficticio`) se contaron con `grep` sobre los encabezados `#### Scenario:` (59) y se compararon por nombre exacto con la tabla (sin diferencias en ningún sentido). Cada prueba citada existe como `def <nombre>` en el archivo indicado y figura como `PASSED` en la salida `-v` de la ejecución 2 (columna entre paréntesis: casos parametrizados ejecutados). Los dos escenarios sobre el arranque de la API se cubren con la autoprueba, cuyos casos figuran `[OK]` arriba.

**Resultado: 59 de 59 escenarios con prueba automatizada ejecutada y en verde; sin brechas.**

| N | Capacidad | Escenario | Prueba(s) (`archivo::prueba`, bajo `backend/tests/` salvo la autoprueba) | Resultado |
|---|---|---|---|---|
| 1 | base-de-datos-local | El comando explícito deja la base al día | `integration/test_migraciones.py::test_el_comando_explicito_deja_la_base_al_dia` (1 PASSED) | Ejecutada y pasó |
| 2 | base-de-datos-local | El arranque de la API no migra | `scripts/tests/autoprueba.ps1`, caso `El arranque de la API no migra` | Autoprueba (paso 0 de `test.ps1`): `[OK]` |
| 3 | base-de-datos-local | Sin tablas de dominio | `integration/test_migraciones.py::test_sin_tablas_de_dominio` (1 PASSED) | Ejecutada y pasó |
| 4 | base-de-datos-local | Tablas del modelo base vacías tras migrar | `integration/test_migraciones.py::test_tablas_del_modelo_base_vacias_tras_migrar` (1 PASSED) | Ejecutada y pasó |
| 5 | modelo-consultorios-usuarios | Valores por defecto al insertar solo el nombre | `integration/test_modelo_base.py::test_valores_por_defecto_al_insertar_solo_el_nombre` (1 PASSED) | Ejecutada y pasó |
| 6 | modelo-consultorios-usuarios | La zona horaria por defecto es válida para PostgreSQL | `integration/test_modelo_base.py::test_la_zona_horaria_por_defecto_existe_una_vez_en_pg_timezone_names` (1 PASSED) | Ejecutada y pasó |
| 7 | modelo-consultorios-usuarios | Nombre obligatorio | `integration/test_modelo_base.py::test_nombre_de_consultorio_obligatorio` (1 PASSED) | Ejecutada y pasó |
| 8 | modelo-consultorios-usuarios | Anticipación negativa rechazada | `integration/test_modelo_base.py::test_anticipacion_negativa_rechazada` (1 PASSED) | Ejecutada y pasó |
| 9 | modelo-consultorios-usuarios | Anticipación cero aceptada | `integration/test_modelo_base.py::test_anticipacion_cero_aceptada` (1 PASSED) | Ejecutada y pasó |
| 10 | modelo-consultorios-usuarios | Id de consultorio generado por el servidor | `integration/test_modelo_base.py::test_id_de_consultorio_generado_como_uuid_v7` (1 PASSED) | Ejecutada y pasó |
| 11 | modelo-consultorios-usuarios | Id de usuario generado por el servidor | `integration/test_modelo_base.py::test_id_de_usuario_generado_como_uuid_v7_y_distinto_del_consultorio` (1 PASSED) | Ejecutada y pasó |
| 12 | modelo-consultorios-usuarios | Usuario con consultorio inexistente rechazado | `integration/test_modelo_base.py::test_usuario_con_consultorio_inexistente_rechazado` (1 PASSED) | Ejecutada y pasó |
| 13 | modelo-consultorios-usuarios | Usuario sin consultorio rechazado | `integration/test_modelo_base.py::test_usuario_sin_consultorio_rechazado` (1 PASSED) | Ejecutada y pasó |
| 14 | modelo-consultorios-usuarios | Borrado de consultorio con usuarios restringido | `integration/test_modelo_base.py::test_borrado_de_consultorio_con_usuarios_restringido` (1 PASSED) | Ejecutada y pasó |
| 15 | modelo-consultorios-usuarios | Valores por defecto del usuario | `integration/test_modelo_base.py::test_valores_por_defecto_del_usuario` (1 PASSED) | Ejecutada y pasó |
| 16 | modelo-consultorios-usuarios | Restricción de unicidad compuesta presente | `integration/test_modelo_base.py::test_restriccion_unica_compuesta_consultorio_id_e_id_presente` (1 PASSED) | Ejecutada y pasó |
| 17 | modelo-consultorios-usuarios | Roles admitidos aceptados | `integration/test_modelo_base.py::test_roles_admitidos_aceptados` (1 PASSED) | Ejecutada y pasó |
| 18 | modelo-consultorios-usuarios | Rol no admitido rechazado | `integration/test_modelo_base.py::test_rol_no_admitido_rechazado` (3 PASSED) | Ejecutada y pasó |
| 19 | modelo-consultorios-usuarios | Mismo email en dos consultorios | `integration/test_modelo_base.py::test_mismo_email_en_dos_consultorios_aceptado` (1 PASSED) | Ejecutada y pasó |
| 20 | modelo-consultorios-usuarios | Email repetido en el mismo consultorio rechazado | `integration/test_modelo_base.py::test_email_repetido_en_el_mismo_consultorio_rechazado` (1 PASSED) | Ejecutada y pasó |
| 21 | modelo-consultorios-usuarios | Email no normalizado rechazado por la base | `integration/test_modelo_base.py::test_email_no_normalizado_rechazado_por_la_base` (3 PASSED) | Ejecutada y pasó |
| 22 | modelo-consultorios-usuarios | Usuario sin credencial aceptado | `integration/test_modelo_base.py::test_usuario_sin_credencial_aceptado` (1 PASSED) | Ejecutada y pasó |
| 23 | modelo-consultorios-usuarios | Credencial vacía rechazada | `integration/test_modelo_base.py::test_credencial_vacia_rechazada` (1 PASSED) | Ejecutada y pasó |
| 24 | modelo-consultorios-usuarios | Cadena de revisiones | `integration/test_migraciones.py::test_cadena_de_revisiones_head_0002_sobre_0001` (1 PASSED) | Ejecutada y pasó |
| 25 | modelo-consultorios-usuarios | Subida desde 0001 crea las tablas vacías | `integration/test_migraciones.py::test_subida_desde_0001_crea_las_tablas_vacias` (1 PASSED) | Ejecutada y pasó |
| 26 | modelo-consultorios-usuarios | Bajada a 0001 elimina las tablas y conserva la extensión | `integration/test_migraciones.py::test_bajada_a_0001_elimina_las_tablas_y_conserva_btree_gist` (1 PASSED) | Ejecutada y pasó |
| 27 | modelo-consultorios-usuarios | Sin diferencias entre modelos y base migrada | `integration/test_migraciones.py::test_los_modelos_coinciden_con_la_base_migrada` (1 PASSED) | Ejecutada y pasó |
| 28 | modelo-consultorios-usuarios | Nombres de restricciones según la convención | `integration/test_migraciones.py::test_nombres_de_restricciones_segun_la_convencion` (1 PASSED) + `unit/test_modelos.py::test_usuario_declara_las_restricciones_con_nombre_de_la_convencion` (1 PASSED) | Ejecutada y pasó |
| 29 | repositorios-acotados | Contexto con identificador válido | `unit/test_contexto_y_repositorios.py::test_contexto_expone_el_identificador_y_es_inmutable` (1 PASSED) | Ejecutada y pasó |
| 30 | repositorios-acotados | Contexto con identificador no UUID rechazado | `unit/test_contexto_y_repositorios.py::test_contexto_con_identificador_no_uuid_rechazado` (4 PASSED) | Ejecutada y pasó |
| 31 | repositorios-acotados | Repositorio sin contexto rechazado | `unit/test_contexto_y_repositorios.py::test_repositorio_sin_contexto_rechazado` (2 PASSED) | Ejecutada y pasó |
| 32 | repositorios-acotados | Ningún esquema de entrada declara consultorio_id | `unit/test_esquemas_sin_consultorio.py::test_ningun_esquema_de_entrada_declara_consultorio_id` (1 PASSED) | Ejecutada y pasó |
| 33 | repositorios-acotados | Datos de alta de usuario sin consultorio_id | `unit/test_contexto_y_repositorios.py::test_datos_de_alta_de_usuario_sin_consultorio_id` (1 PASSED) | Ejecutada y pasó |
| 34 | repositorios-acotados | Listado solo del consultorio propio | `integration/test_repositorios_acotados.py::test_listado_solo_del_consultorio_propio` (1 PASSED) | Ejecutada y pasó |
| 35 | repositorios-acotados | Obtener por id un usuario de otro consultorio | `integration/test_repositorios_acotados.py::test_obtener_por_id_de_otro_consultorio_igual_que_inexistente` (1 PASSED) | Ejecutada y pasó |
| 36 | repositorios-acotados | Obtener por id un usuario propio | `integration/test_repositorios_acotados.py::test_obtener_por_id_propio_devuelve_el_usuario` (1 PASSED) | Ejecutada y pasó |
| 37 | repositorios-acotados | Buscar por email dentro del consultorio | `integration/test_repositorios_acotados.py::test_buscar_por_email_dentro_del_consultorio_sin_distinguir_mayusculas` (1 PASSED) | Ejecutada y pasó |
| 38 | repositorios-acotados | Buscar por email de otro consultorio | `integration/test_repositorios_acotados.py::test_buscar_por_email_de_otro_consultorio_igual_que_inexistente` (1 PASSED) | Ejecutada y pasó |
| 39 | repositorios-acotados | Toda consulta generada incluye el filtro por consultorio | `unit/test_contexto_y_repositorios.py::test_toda_consulta_generada_incluye_el_filtro_por_consultorio` (2 PASSED) | Ejecutada y pasó |
| 40 | repositorios-acotados | Alta con el consultorio del contexto | `integration/test_repositorios_acotados.py::test_alta_con_el_consultorio_del_contexto` (1 PASSED) | Ejecutada y pasó |
| 41 | repositorios-acotados | Alta con email repetido en el consultorio, sin distinguir mayúsculas | `integration/test_repositorios_acotados.py::test_alta_con_email_repetido_sin_distinguir_mayusculas_rechazada` (1 PASSED) | Ejecutada y pasó |
| 42 | repositorios-acotados | Desactivar un usuario de otro consultorio | `integration/test_repositorios_acotados.py::test_desactivar_un_usuario_de_otro_consultorio_igual_que_inexistente` (1 PASSED) | Ejecutada y pasó |
| 43 | repositorios-acotados | Desactivar un usuario propio | `integration/test_repositorios_acotados.py::test_desactivar_un_usuario_propio` (1 PASSED) | Ejecutada y pasó |
| 44 | repositorios-acotados | Obtener el consultorio actual | `integration/test_repositorios_acotados.py::test_obtener_el_consultorio_actual` (1 PASSED) | Ejecutada y pasó |
| 45 | repositorios-acotados | Contexto de un consultorio inexistente | `integration/test_repositorios_acotados.py::test_contexto_de_un_consultorio_inexistente_no_devuelve_resultado` (1 PASSED) | Ejecutada y pasó |
| 46 | repositorios-acotados | Sin operaciones sobre otros consultorios | `unit/test_contexto_y_repositorios.py::test_consultorio_repositorio_solo_expone_obtener_actual` (1 PASSED) | Ejecutada y pasó |
| 47 | seed-ficticio | Migrar no carga datos | `integration/test_migraciones.py::test_migrar_desde_base_no_carga_datos` (1 PASSED) | Ejecutada y pasó |
| 48 | seed-ficticio | El arranque de la API no ejecuta el seed | `scripts/tests/autoprueba.ps1`, caso `El arranque de la API no ejecuta el seed` | Autoprueba (paso 0 de `test.ps1`): `[OK]` |
| 49 | seed-ficticio | Dos consultorios y seis usuarios | `integration/test_seed.py::test_dos_consultorios_y_seis_usuarios` (1 PASSED) | Ejecutada y pasó |
| 50 | seed-ficticio | Datos evidentemente ficticios | `integration/test_seed.py::test_datos_evidentemente_ficticios` (1 PASSED) | Ejecutada y pasó |
| 51 | seed-ficticio | Valores de consultorio del seed | `integration/test_seed.py::test_valores_de_consultorio_del_seed` (1 PASSED) | Ejecutada y pasó |
| 52 | seed-ficticio | Seis usuarios sin credencial | `integration/test_seed.py::test_seis_usuarios_sin_credencial` (1 PASSED) | Ejecutada y pasó |
| 53 | seed-ficticio | Dos ejecuciones no duplican | `integration/test_seed.py::test_dos_ejecuciones_no_duplican` (1 PASSED) | Ejecutada y pasó |
| 54 | seed-ficticio | Identificadores fijos | `integration/test_seed.py::test_identificadores_fijos_entre_aplicaciones` (1 PASSED) | Ejecutada y pasó |
| 55 | seed-ficticio | Una fila del seed modificada no se sobrescribe | `integration/test_seed.py::test_una_fila_del_seed_modificada_no_se_sobrescribe` (1 PASSED) | Ejecutada y pasó |
| 56 | seed-ficticio | Una fila ajena con el mismo email se respeta | `integration/test_seed.py::test_una_fila_ajena_con_el_mismo_email_se_respeta` (1 PASSED) | Ejecutada y pasó |
| 57 | seed-ficticio | Entorno de pruebas rechazado | `unit/test_seed.py::test_main_con_app_env_test_no_abre_conexion_y_termina_con_error` (1 PASSED) | Ejecutada y pasó |
| 58 | seed-ficticio | Entorno local admitido | `unit/test_seed.py::test_entorno_local_admitido` (1 PASSED) | Ejecutada y pasó |
| 59 | seed-ficticio | Resumen solo con cantidades | `unit/test_seed.py::test_resumen_solo_informa_cantidades` (1 PASSED) + `integration/test_seed.py::test_el_comando_principal_informa_solo_cantidades_y_carga_el_seed` (1 PASSED) | Ejecutada y pasó |

## Verificación de la base de desarrollo (solo lectura)

Consultas con `docker compose exec -T db psql -U app -d turnos -tAc "SELECT ..."` y `docker compose exec -T api alembic current`. Se midió **antes** y **después** de ejecutar `scripts/test.ps1` para demostrar que las pruebas de integración (que usan `db-test`) no afectan a desarrollo.

| Comprobación | Antes de `test.ps1` | Después de `test.ps1` |
|---|---|---|
| `alembic current` | `0002 (head)` | `0002 (head)` |
| Tablas en `public` | `alembic_version, consultorio, usuario` | sin cambios (solo se recontaron filas y huellas) |
| `count(*)` consultorio | 2 | 2 |
| `count(*)` usuario | 6 | 6 |
| Emails `@example.test` | 6 de 6 | n/a (huellas idénticas) |
| `credencial IS NULL` | 6 de 6 | n/a (huellas idénticas) |
| Ids con dígito de versión `7` (consultorio + usuario) | 8 de 8 | n/a (huellas idénticas) |
| Huella `consultorio` (`md5(string_agg(row(t.*)::text, '\|' order by id))`) | `9d0059bb42915baa8fa2d7b94265725e` | `9d0059bb42915baa8fa2d7b94265725e` |
| Huella `usuario` | `84a7a3e1fa420f80bfa2818c81a8fccc` | `84a7a3e1fa420f80bfa2818c81a8fccc` |

Las huellas coinciden con las registradas en `tdd-evidencia.md` (sección de la tarea 4.8). Conclusión: el contenido de desarrollo es exactamente el sembrado en 4.8 y la suite completa no lo modificó.

## Idempotencia y no destrucción del seed

No se volvió a ejecutar el seed. La evidencia es:

- **Pruebas automatizadas sobre `db-test`** (todas `PASSED` arriba): `integration/test_seed.py::test_dos_ejecuciones_no_duplican` (escenario 53), `::test_identificadores_fijos_entre_aplicaciones` (54), `::test_una_fila_del_seed_modificada_no_se_sobrescribe` (55) y `::test_una_fila_ajena_con_el_mismo_email_se_respeta` (56). Además `unit/test_seed.py` escanea `app/seed/*.py` y exige cero `update|delete|truncate|drop` (el seed solo usa `INSERT ... ON CONFLICT DO NOTHING`). La RED de estas pruebas se obtuvo por mutación (`on_conflict_do_update`); ver `tdd-evidencia.md` 4.3.
- **Ejecución real en desarrollo (tarea 4.8, orquestador, con autorización expresa del autor, DP-05)**, registrada en `tdd-evidencia.md`: OP-1 `alembic upgrade head` (`0001 -> 0002`, rc 0, tablas vacías); OP-2 primera carga `consultorios: 2 insertados, 0 omitidos; usuarios: 6 insertados, 0 omitidos` (rc 0); OP-3 segunda carga `consultorios: 0 insertados, 2 omitidos; usuarios: 0 insertados, 6 omitidos` (rc 0), con huellas idénticas antes y después de OP-3 (nada sobrescrito) y `count(*)` 2 y 6. La salida del comando contiene solo cantidades (X1). Sin `downgrade`, `DROP`, `DELETE`, `TRUNCATE` ni `down -v`.
- Verificación manual 2.8 (SQL offline de `0001:0002`, sin `INSERT`): registrada en `tdd-evidencia.md`.

## Revisión de reglas duras (tarea 5.4)

| Regla | Resultado | Evidencia |
|---|---|---|
| D1 Datos ficticios | Cumple | Seed y pruebas usan solo `@example.test` y nombres "Demo"/"Persona Ficticia"; en desarrollo 6 de 6 emails `@example.test`; el escaneo de secretos solo encontró URLs de prueba ficticias (`app:app`, `host-inexistente.invalid`) |
| D2 Sin datos clínicos | Cumple | `grep -i` de diagnóstico, odontograma, historia, tratamiento, clínic*, alergia en `app/models`, `app/seed`, `app/repositories` y la migración: 0 coincidencias; `usuario` solo tiene id, consultorio, email, nombre, rol, activo, credencial, creado_en |
| D3 Sin solapamientos | N/A | C-02 no toca turnos; `superposicion_turnos.py` y su prueba sin cambios respecto de `f13f0ba` |
| D4 Sillones y boxes | N/A | No se modelan |
| D5 Aislamiento | Cumple (alcance C-02) | `app/schemas` no contiene `consultorio_id` (prueba `test_ningun_esquema_de_entrada_declara_consultorio_id`, escenario 32); `EsquemaEntrada` con `extra="forbid"`; los repositorios toman `consultorio_id` solo de `ContextoConsultorio` (`base.py`, `consultorios.py`, `usuarios.py`); `NuevoUsuario` no tiene ese campo; sin endpoints ni autenticación. RLS y autorización quedan para C-03/C-04 y no se declaran completas aquí |
| D6 Decisiones abiertas | Cumple | Todas las decisiones del Change fueron aprobadas por el autor el 2026-11-04: DP-01 (`nombre` sin UNIQUE), DP-02 (`credencial` nullable, NULL = sin credencial), DP-03 (consultorio inactivo se decide en C-03), DP-04 (UUIDv7 literales fijos), DP-05 (migración y seed en desarrollo solo con autorización expresa; luego autorizado y ejecutado como 4.8), DP-06 (formato de email diferido a C-05); DC-01 a DC-12 aprobadas en Explore/Propose. PA-03, PA-04 y PA-11 no se resolvieron: se difieren a C-03/C-04/C-05 |
| X1 Datos sensibles fuera de logs | Cumple | En `app/seed`, `app/repositories`, `app/models` y `app/core/database.py` no hay `logging`/`logger`; los únicos `print` están en `app/seed/__main__.py` (mensajes fijos de error a stderr y el resumen con cantidades, `ResumenSeed.texto()`); `test_resumen_solo_informa_cantidades` y la prueba de `main` con `APP_ENV=test` verifican que la salida no contiene emails, nombres ni URLs |
| X2 Pruebas y base de datos | Cumple | Integración contra PostgreSQL 18.6 real (`db-test`, efímera, paso 5 de `test.ps1`); sin simulación de la base para restricciones, aislamiento ni seed; las unitarias del módulo puro no requieren base |
| X3 Servicios externos | Cumple | `grep` de `http(s)://`, `requests`, `httpx`, `boto`, `smtp` en código nuevo: 0 coincidencias; `docker-compose.yml` y `.env.example` sin cambios |
| S1 Python | Cumple | Revisión AST de 19 funciones públicas del código nuevo (`app/seed`, `app/repositories`, modelos, `database.py`): todas con anotaciones de parámetros y retorno y nombres `snake_case`; `EsquemaEntrada` con `extra="forbid"` y sin esquemas de entrada nuevos |
| S2 TypeScript | N/A | No se tocó el frontend (`tsc --noEmit` y Vitest en verde en `test.ps1`) |
| X4 Idioma | Cumple | Documentación y artefactos en español; identificadores de dominio según la KB (`Consultorio`, `Usuario`) |
| O1 Alcance | Cumple | Implementado dentro de las 4 specs; `grep -i` de router, APIRouter, ROW LEVEL SECURITY, CREATE POLICY, jwt, bcrypt, argon, passlib en código nuevo: 0 coincidencias. Sin cambios en `docker-compose.yml`, `.env.example`, `Settings`, `scripts/test.ps1`, `alembic/env.py`, `app/models/base.py`, `superposicion_turnos.py` ni su prueba. `CHANGES.md` sin modificar |
| G1 Git | Cumple hasta ahora | Sin `git add`, commit ni push durante Apply y Verify |

## Git e higiene (tarea 5.6)

**Modificados (7):**

| Archivo | Propósito |
|---|---|
| `README.md` | +46 líneas / 0 eliminadas: sección del seed (conserva el contenido existente) |
| `backend/app/core/database.py` | Agrega `crear_fabrica_de_sesiones` (DM-09) |
| `backend/app/models/__init__.py` | Registra los modelos `Consultorio` y `Usuario` |
| `backend/tests/integration/conftest.py` | Fixtures `config_alembic`, `revision_actual`, `base_migrada` (movido) y `sesion` |
| `backend/tests/integration/test_migraciones.py` | Pruebas de la migración `0002`; actualiza `test_sin_tablas_de_dominio` (delta MODIFIED) |
| `backend/tests/unit/test_database.py` | 2 pruebas nuevas de `crear_fabrica_de_sesiones` |
| `scripts/tests/autoprueba.ps1` | Caso "El arranque de la API no ejecuta el seed" |

**Nuevos (código y pruebas, 18):** `backend/alembic/versions/0002_modelo_base_consultorios.py` (migración); `backend/app/models/consultorio.py` y `usuario.py` (modelos); `backend/app/repositories/base.py`, `consultorios.py`, `contexto.py`, `usuarios.py` (repositorios acotados); `backend/app/seed/__init__.py`, `__main__.py`, `aplicar.py`, `datos.py`, `entorno.py` (seed); `backend/tests/integration/test_modelo_base.py`, `test_repositorios_acotados.py`, `test_seed.py` y `backend/tests/unit/test_contexto_y_repositorios.py`, `test_esquemas_sin_consultorio.py`, `test_modelos.py`, `test_seed.py` (pruebas).

**Nuevos (carpeta del Change):** `openspec/changes/modelo-base-consultorios-seed/` con `.openspec.yaml`, `proposal.md`, `design.md`, `tasks.md`, `tdd-evidencia.md`, `verify.md` (este) y `specs/*/spec.md` (4).

Comprobaciones:

- `git diff --check` (archivos rastreados modificados): sin errores de espacios en blanco, rc 0 (solo avisos de fin de línea por `.gitattributes`: `README.md` tiene CRLF en la copia de trabajo y Git lo normaliza a LF; `autoprueba.ps1` tiene LF y `.gitattributes` fuerza CRLF; no son errores).
- `git diff --no-index --check /dev/null <archivo>` sobre **cada** archivo no rastreado (previo a crear `verify.md`): sin ninguna salida, es decir sin espacios finales.
- Escaneo de CR en archivos nuevos: ninguno contiene CRLF (todos LF).
- Escaneo de secretos (claves privadas, tokens, contraseñas): solo las URLs ficticias de prueba (`app:app`, `otra-clave-ficticia`, `secreto` como valor de control) y la palabra "secretaria"; ningún secreto real.
- Higiene: no hay `.env`, `.venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `dist`, logs ni scripts temporales (`backend/_tmp*`, `app/schemas/temporal*`) entre los candidatos; `git check-ignore -q .env` rc 0 (ignorado); `CHANGES.md`, `AGENTS.md`, `CLAUDE.md`, KB y `docker-compose.yml` sin modificar.

## Observaciones para Archive

1. `README.md` todavía indica el estado de C-02 como "en implementación": actualizarlo al archivar (con autorización del autor).
2. Al archivar, marcar C-02 `[x]` en `CHANGES.md` y corregir la numeración histórica de migraciones: C-02 es `0002` y C-04 será `0003` (DC-11); `CHANGES.md` todavía dice "001" y "002".
3. DT-01 (advertencia de `httpx` en `starlette.testclient`) persiste, sin impacto funcional.
4. La base de desarrollo ya contiene las tablas de C-02 y el seed ficticio; hacer `downgrade` sobre desarrollo está prohibido (la `downgrade` de `0002` es solo para `db-test`).
5. Para C-03: respetar el contrato de `credencial` NULL (nunca inicia sesión) y definir el comportamiento ante consultorio inactivo (DP-03). Los filtros y los UUIDv7 no reemplazan RLS ni autorización de C-04 (RN-MT-06).
6. Git emite un aviso inocuo de fin de línea sobre `autoprueba.ps1` (LF en la copia de trabajo, `eol=crlf` en `.gitattributes`).

## Condiciones de O2

| Condición | Estado | Evidencia |
|---|---|---|
| `openspec validate modelo-base-consultorios-seed --strict` sin errores | Cumple | Comando 1: valid, rc 0 |
| pytest exitoso | Cumple | Comando 2: 127 unitarias y 62 de integración, rc 0; 19 de superposición en el host |
| Todos los escenarios cubiertos por pruebas automatizadas | Cumple | Trazabilidad: 59 de 59, ejecutadas y en verde |
| Registro de comandos, resultados y evidencia en el Change | Cumple | Este documento y `tdd-evidencia.md` (incluye 2.8 y 4.8) |

## Conclusión

La implementación de `modelo-base-consultorios-seed` (C-02) cumple las cuatro condiciones de O2 y las reglas duras aplicables: validación estricta en verde, 191 pruebas en verde (127 unitarias, 62 de integración contra PostgreSQL real, 2 de Vitest), 59 de 59 escenarios con prueba automatizada, base de desarrollo en `0002 (head)` con 2 consultorios y 6 usuarios ficticios y huellas sin variación antes y después de la suite, y sin secretos ni archivos temporales entre los candidatos a commit. No se detectaron fallas. Quedan pendientes, por indicación del autor, el Archive (con las correcciones de `README.md` y `CHANGES.md` indicadas) y el commit (G1). **Verify superado; el Change está listo para Archive cuando el autor lo indique.**

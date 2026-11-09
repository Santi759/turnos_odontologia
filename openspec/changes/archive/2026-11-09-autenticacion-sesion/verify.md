# Verify: autenticacion-sesion (C-03)

Verificación formal (tareas 14.1, 14.2 y 14.3) del Change `autenticacion-sesion`, ejecutada el 2026-11-09 en Windows 11 con Docker Desktop, PowerShell 5.1 y Git Bash, sobre la rama `main` (HEAD `6258bbc`, con los cambios de C-03 sin commitear). Dominio **CRITICAL** (autenticación). Todos los datos son ficticios. **Este documento no archiva el Change**: el Archive solo se ejecuta con indicación del autor (AGENTS.md O2) y, en ese momento, se corrige `CHANGES.md` (migración de C-04 `0003` a `0004`) y se marca C-03 `[x]`.

## Entorno

```
Docker 29.9.2 / Docker Compose v5.6.1
openspec CLI: 1.14.1
Imagen api: Python 3.14.10, pytest 9.1.1, SQLAlchemy 2.1.6, Alembic 1.20.1, argon2-cffi 25.1.0, FastAPI 0.162.0
PostgreSQL: 18.6 (servicio db de desarrollo y db-test efímero)
Host: el `python` del host es un stub roto de Windows Store; todo Python corre dentro de contenedores
```

Restricciones respetadas: la base de desarrollo se consultó solo con `SELECT` (sin migraciones, mantenimiento, seed, credenciales, `downgrade`/`DROP`/`TRUNCATE`/`down -v`); no se reconstruyó ni reinició la API de desarrollo (el paso de construcción de imágenes lo hace el propio `test.ps1`); no se modificó `.env` ni ningún archivo de producción o de pruebas; sin `git add`, commit ni push. El runner usa `db-test` efímera (tmpfs) y una `AUTH_SECRET_KEY` efímera pasada por nombre (`-e AUTH_SECRET_KEY`); la clave nunca se imprimió.

## Comandos ejecutados y resultados

### 1. Tarea 14.1: `openspec --version` y `openspec validate autenticacion-sesion --strict`

```
$ openspec --version
1.14.1
$ openspec validate autenticacion-sesion --strict
Change 'autenticacion-sesion' is valid
rc=0
```

Se repitió al final de la verificación (tras marcar las tareas) con el mismo resultado.

### 2. Tarea 14.2: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1`

Corrida **nueva** (no se reutilizó ninguna anterior). Código de salida: **0**. Resumen real por paso (salida completa guardada fuera del repositorio, en el scratchpad de la sesión, `verify_test.log`; las suites corrieron con `-v`):

```
==> 0. autoprueba del runner y de la higiene del repositorio
Autoprueba: todos los casos pasan                      (18 casos [OK])
==> 1. construir imagenes (api, frontend)
==> 2. pruebas unitarias del backend (incluye las 19 de superposicion)
======================= 516 passed, 1 warning in 27.50s ========================
==> 3. levantar la base de pruebas efimera (db-test)
==> 4. migraciones sobre la base de pruebas (alembic upgrade head)
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, habilitar btree_gist (infraestructura, sin tablas de dominio)
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, modelo base: tablas consultorio y usuario (sin datos)
INFO  [alembic.runtime.migration] Running upgrade 0002 -> 0003, autenticacion: codigo de consultorio, sesion e intento_login
==> 5. pruebas de integracion contra PostgreSQL real (db-test)
================== 418 passed, 1 warning in 98.37s (0:01:38) ===================
==> 6. verificacion de tipos del frontend (tsc --noEmit)      (sin errores)
==> 7. pruebas del frontend (Vitest)
 Test Files  1 passed (1)
      Tests  2 passed (2)
Todas las suites pasaron.
EXIT=0
```

Totales: 516 unitarias + 418 de integración + 2 de Vitest = **936** pruebas (más 18 casos de autoprueba). En la salida `-v` hay **934 líneas `PASSED`** de pytest y **0** `FAILED`/`ERROR`/`SKIPPED`/`XFAIL`/`XPASS`. La única advertencia es `StarletteDeprecationWarning` por `httpx` en `starlette.testclient` (DT-01 de C-01, preexistente, sin impacto funcional). Al terminar, el `finally` del runner retiró la variable de entorno y eliminó `db-test`.

### 3. Las 19 pruebas de superposición y archivos sin cambios

```
$ docker compose run --rm --no-deps api python -m pytest -p no:cacheprovider tests/unit/test_superposicion_turnos.py -q
...................                                                      [100%]
19 passed in 0.40s

$ git diff --quiet f13f0ba -- backend/tests/unit/test_superposicion_turnos.py backend/app/domain/superposicion_turnos.py
rc=0
$ git rev-parse f13f0ba:backend/tests/unit/test_superposicion_turnos.py   -> 2fe1a9f4fd9cf2e7726b12a968a2dfce4035b3d2
$ git hash-object backend/tests/unit/test_superposicion_turnos.py        -> 2fe1a9f4fd9cf2e7726b12a968a2dfce4035b3d2
$ git rev-parse f13f0ba:backend/app/domain/superposicion_turnos.py       -> 2a2f8c64d8b8d7eea3c5ebf348e91cf65c0661c7
$ git hash-object backend/app/domain/superposicion_turnos.py             -> 2a2f8c64d8b8d7eea3c5ebf348e91cf65c0661c7
```

Las 19 también están dentro de las 516 del paso 2. Contenido idéntico al de `f13f0ba`; `git status` puede mostrar la prueba como `M` solo por fin de línea.

## Trazabilidad formal escenario → prueba (tarea 14.3)

Se partió de la matriz definitiva de `tdd-evidencia.md` (sección "Matriz de trazabilidad (grupo 12.2) - DEFINITIVA"). Comprobaciones:

- **Conteo de escenarios**: `grep -c '#### Scenario:'` sobre las 11 specs delta = **229**; la matriz tiene **229 filas** (autenticacion-sesion 68, control-intentos-login 33, modelo-consultorios-usuarios 27, credenciales-locales 26, configuracion-backend 25, proteccion-csrf 18, mantenimiento-local 9, base-de-datos-local 7, seed-ficticio 7, repositorios-acotados 5, ejecucion-de-pruebas 4).
- **Existencia y ejecución (programática, sobre la salida de la corrida del punto 2)**: se extrajeron de la columna "Prueba(s)" **335 identificadores `archivo::prueba` distintos**; **335 de 335 figuran como `PASSED`** en la corrida nueva (uno, `test_vencimientos_incoherentes_rechazados[vencimiento ...]`, contiene espacios en el identificador parametrizado y se confirmó aparte con sus 2 casos `PASSED`). 0 faltantes, 0 omitidos. Las **7 filas restantes** no usan pytest sino la autoprueba; los casos citados figuran `[OK]` en la corrida nueva (`El arranque de la API no procesa cabeceras de proxy`, `.env ignorado por Git`, `El arranque de la API no migra`, `Compose monta solo .env.example de solo lectura en api`, `test.ps1: clave por nombre, sin literal y retirada del entorno` (2 filas), `Clave efimera de autenticacion: formato, diversidad y unicidad`, `Funciona sin clave en .env ...`).
- **Revisión por muestreo del contenido de las pruebas** (se leyó el cuerpo y se confirmó que afirma el comportamiento del escenario, no una tautología): unas 35 pruebas, priorizando autenticación, CSRF, aislamiento, control de intentos, HTTP y las brechas cerradas en 12.2:
  - Autenticación/HTTP: `test_api_auth.py::test_login_exitoso_responde_200_emite_la_cookie_y_crea_una_sesion`, `::test_el_cuerpo_del_login_es_exactamente_la_identidad_minima`, `::test_la_cookie_de_sesion_tiene_los_atributos_por_defecto` (HttpOnly, SameSite=Lax, Secure); `test_api_login_rechazos.py::test_la_contrasena_correcta_en_mayusculas_o_con_espacio_final_responde_el_rechazo_generico` (401, cuerpo exacto, `no-store`, sin cookie, 0 sesiones, 1 fallo y luego 200 con la exacta).
  - Sesión: `test_servicio_auth.py::test_login_con_cookie_de_sesion_valida_la_revoca_y_emite_un_token_distinto` (rotación), `::test_sesion_inactiva_31_minutos_vencida`; `test_dependencias_auth.py::test_una_sesion_revocada_vencida_o_de_usuario_inactivo_responde_401`.
  - Aislamiento: `test_dependencias_auth.py::test_el_consultorio_enviado_por_el_cliente_nunca_altera_el_contexto` (parámetro y cabecera con el consultorio B; el contexto sigue siendo A), `::test_el_repositorio_de_usuarios_con_el_contexto_inyectado_lista_solo_a`; `test_modelo_autenticacion.py::test_sesion_con_consultorio_distinto_del_usuario_rechazada` (FK compuesta `fk_sesion_consultorio_id_usuario`); `test_rutas_protegidas.py::test_toda_ruta_fuera_de_la_lista_blanca_responde_401_sin_cookie`.
  - CSRF: `test_rutas_protegidas.py::test_toda_ruta_que_cambia_estado_responde_403_sin_origin` y `::test_toda_ruta_con_sesion_que_cambia_estado_responde_403_sin_token_csrf` (recorren todas las rutas registradas); `test_origen_csrf.py::test_cambiar_estado_sin_token_o_con_token_incorrecto_responde_403_sin_cambios` (sin token, vacío, alterado, de otra sesión y de sesión revocada; 0 cambios).
  - Control de intentos y concurrencia: `test_api_control_intentos.py::test_sexto_intento_responde_429_con_retry_after_840_sin_verificar_ni_crear_sesion`; `test_api_login_rechazos.py::test_el_bloqueo_de_ip_deja_intactas_las_sesiones_abiertas_me_200_y_logout_204`, `::test_diez_rechazos_previos_de_cada_tipo_no_registran_fallos_y_el_login_correcto_responde_200`; `test_concurrencia_login.py::test_ocho_logins_http_concurrentes_ejecutan_a_lo_sumo_cuatro_verificaciones_a_la_vez` (hilos reales) y `::test_cuarenta_logins_http_concurrentes_desde_la_misma_ip_dan_exactamente_30_401_y_10_429`.
  - Secretos y registros: `test_api_registros.py::test_ningun_registro_ni_respuesta_contiene_datos_sensibles`; `test_direccion_cliente.py::test_login_real_sin_cliente_registra_solo_el_codigo_fijo`.
  - CORS y documentación: `test_cors.py::test_el_origen_ajeno_no_recibe_credenciales_ni_cabeceras_cors`; `test_documentacion.py::test_con_app_env_test_la_documentacion_responde_404` (y la variante `local` con 200, por nombre).
  - Brechas 12.2 (las 13): leídos los cuerpos de la 1 (`test_el_montaje_de_la_plantilla_en_el_contenedor_rechaza_la_escritura`, `errno.EROFS`), 2, 4 (`test_argon2_real.py::test_login_http_con_hash_de_t2_responde_200_y_la_credencial_pasa_a_los_parametros_vigentes`), 5, 6 (`test_login_real_sin_cliente_registra_solo_el_codigo_fijo`), 7, 8, 9 (`test_la_lista_generica_incluye_los_terminos_de_la_spec_y_excluye_turnos_y_odontologia`), 10 (`test_nombre_de_consultorio_obligatorio`, SQLSTATE 23502 y columna `nombre`), 11 (`test_equivalencia_del_codigo_largo_con_la_expresion_real_de_la_migracion_0003`, 1000 pares con migración real) y 13 (`test_plantilla_ausente.py`, con subproceso y control de ruta presente); la 3 (hasher real) se revisó por su nombre y por la prueba 4; la 12 es la autoprueba descrita abajo.
  - No se detectaron filas débiles en el muestreo. La RED por mutación de cada brecha está registrada en `tdd-evidencia.md` ("Cierre de brechas 12.2").

**Resultado: 229 de 229 escenarios con prueba automatizada (pytest o autoprueba) ejecutada y en verde en la corrida nueva; sin brechas.**

**Limitación aceptada del escenario 12 ("Funciona sin clave en .env", `ejecucion-de-pruebas`)**: la cobertura es el caso de autoprueba `Funciona sin clave en .env (entorno aislado, db-test propia, sin tocar .env ni desarrollo)` (`[OK]` en esta corrida), que verifica en un proyecto Compose aislado (`autoprueba-sinclave`) con un archivo de entorno ficticio sin `AUTH_SECRET_KEY` y la clave efímera del runner, solo los pasos de **migración e integración**. **No** se ejecutó el runner completo `test.ps1` en un entorno aislado sin la clave personal del autor: la corrida del punto 2 se hizo en el entorno normal del autor. Se mantiene como limitación documentada.

## Verificación de la base de desarrollo (solo lectura)

Consultas con `docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At'` (SQL por entrada estándar; no se imprimen credenciales ni hashes). Se midió **antes** y **después** de ejecutar `scripts/test.ps1`.

| Comprobación | Antes de `test.ps1` | Después de `test.ps1` |
|---|---|---|
| `alembic_version` | `0003` | `0003` |
| `count(*)` consultorio | 2 | 2 |
| `count(*)` usuario | 6 | 6 |
| Usuarios con credencial | `administracion.a@example.test`, `administracion.b@example.test` (ambas con prefijo `$argon2id$v=19$m=65536,t=3,p=4$`) | idéntico |
| Usuarios sin credencial (`NULL`) | 4 | 4 |
| `count(*)` sesion | 0 | 0 |
| `count(*)` intento_login | 0 | 0 |
| md5 consultorio (columnas base) | `1e231121339bde9fbd9eea082d93bee6` | `1e231121339bde9fbd9eea082d93bee6` |
| md5 consultorio (fila completa, incluye `codigo`) | `b74c6edfab8ba5d584e63210aa614e49` | `b74c6edfab8ba5d584e63210aa614e49` |
| md5 usuario (columnas base) | `e3b0b6c83c6930d6272f3b2d71d802bc` | `e3b0b6c83c6930d6272f3b2d71d802bc` |
| md5 usuarios sin credencial (fila completa) | `2a31e6314b3395fc2cd5b94ac8e5af05` | `2a31e6314b3395fc2cd5b94ac8e5af05` |
| md5 de las 2 credenciales | `602521e9ca6531c1863b03f339e4e9f8` | `602521e9ca6531c1863b03f339e4e9f8` |

Los valores coinciden con lo esperado y con lo registrado en 13.1/13.2; la comparación `diff` de las salidas antes/después es vacía. Conclusión: la suite completa no modificó la base de desarrollo.

Salud de la API de desarrollo tras la corrida (usa `--reload` sobre `./backend` montado): `GET /api/health` -> 200; `GET /api/auth/me` sin cookie -> 401 con `{"detail":"No autenticado."}`. Servicios `api`, `db` y `frontend` en ejecución.

## Revisión de reglas duras / seguridad

| Regla | Resultado | Evidencia |
|---|---|---|
| D1 Datos ficticios | Cumple | Dominios de correo en código y pruebas: `example.test`, `example.com` (reservado), `.invalid`; el seed y las pruebas usan nombres "Ficticio"/"Demo"; la base de desarrollo tiene solo `@example.test` |
| D2 Sin datos clínicos | Cumple | `grep -i` de diagnóstico, odontograma, historia clínica, tratamiento, alergia en `app/` y en la migración 0003: 0 coincidencias |
| D3 Sin solapamientos | N/A | C-03 no toca turnos; módulo y prueba de superposición idénticos a `f13f0ba` (blobs arriba) |
| D4 Sillones y boxes | N/A | No se modelan |
| D5 Aislamiento | Cumple (alcance C-03) | `ContextoConsultorio(...)` se construye en un único lugar, `app/auth/dependencias.py` (`identidad_actual`), a partir del `consultorio_id` de la sesión validada; `EntradaLogin` hereda de `EsquemaEntrada` (`extra="forbid"`) y no declara `consultorio_id`; el cliente solo envía `codigo_consultorio` (público, para el login). Tabla `sesion` con FK compuesta `(consultorio_id, usuario_id) -> usuario(consultorio_id, id)` (`fk_sesion_consultorio_id_usuario`, probada). Pruebas de contexto con parámetro/cabecera de otro consultorio (ver muestreo). La barrera en base (RLS) y la autorización por rol siguen **pendientes para C-04** y no se declaran completas aquí |
| D6 Decisiones abiertas | Cumple | Decisiones registradas en `design.md` y aprobadas por el autor; sin resolver PA-xx por cuenta propia |
| X1 Datos sensibles fuera de logs | Cumple | Solo 3 llamadas de registro en `app/auth` y `app/api`, con códigos fijos (`direccion_cliente_no_determinable`, `verificacion_saturada`, `login_rechazado`); `print` solo en los comandos `credenciales` y `mantenimiento` con mensajes fijos y cantidades; el 422 no refleja la entrada (`RutaAuth`); probado por `test_ningun_registro_ni_respuesta_contiene_datos_sensibles` y `test_login_real_sin_cliente_registra_solo_el_codigo_fijo` |
| Sesiones | Cumple | Cookie `turnos_session`: `HttpOnly`, `SameSite=Lax`, `Path=/`, sin `Domain`, `Secure` salvo `AUTH_COOKIE_SECURE=false` solo con `APP_ENV=local` (la configuración lo rechaza en otro caso); el servidor guarda solo el HMAC-SHA-256 del token (`token_hmac`, 32 bytes, único); inactividad 30 min y vencimiento absoluto 12 h (valores por defecto configurables); `logout` revoca al instante solo esa sesión; un login con cookie válida revoca la anterior y emite un token distinto (rotación) |
| CSRF | Cumple | Todo método que cambia estado exige un único `Origin` igual a uno permitido (403 en otro caso) y, con sesión, el `X-CSRF-Token` derivado de la sesión comparado en tiempo constante (`hmac.compare_digest`); `Content-Type: application/json` obligatorio en el login (415); probado sobre todas las rutas registradas |
| Control de intentos | Cumple | 5 fallos por par (código, email) y 30 por IP en 15 minutos -> 429 con `Retry-After`; el semáforo de Argon2 admite 4 verificaciones simultáneas y responde 503 `Retry-After: 5`; los bloqueos no se guardan sino que se calculan de los fallos; probado con concurrencia real (hilos y conexiones reales) |
| CORS | Cumple | `CORSMiddleware` con orígenes de `CORS_ALLOWED_ORIGINS`, métodos `GET`/`POST`; el middleware propio `CredencialesSoloConOrigenPermitido` elimina `Allow-Credentials` si no hay `Allow-Origin` (probado con origen ajeno y preflight) |
| Documentación de la API | Cumple | `/docs`, `/redoc` y `/openapi.json` solo con `APP_ENV=local` (404 en `test`); sin `/docs/oauth2-redirect` |
| S1 Python | Cumple | Esquema de entrada `extra="forbid"` (`EsquemaEntrada`; `EntradaLogin` lo hereda; los demás esquemas son de respuesta); código nuevo con nombres `snake_case` y anotaciones en funciones públicas (revisión de lectura de `app/auth`, `app/api`, `app/schemas`) |
| S2 TypeScript | N/A | No se tocó el frontend (`tsc --noEmit` y Vitest en verde) |
| X2 Pruebas y base de datos | Cumple | Integración contra PostgreSQL 18.6 real (`db-test`, efímera); concurrencia con conexiones reales; sin simulación de la base para restricciones ni aislamiento |
| X3 Servicios externos | Cumple | `grep` de `http(s)://`, `requests`, `httpx`, `boto`, `smtplib` en `app/`: 0 coincidencias; sin servicios externos |
| X4 Idioma | Cumple | Documentación y artefactos en español; identificadores de dominio según la KB |
| O1 Alcance | Cumple | Implementado dentro de las 11 specs (72 requisitos, 229 escenarios); no se tocó `CHANGES.md`, `AGENTS.md`, `CLAUDE.md`, la KB ni `openspec/specs/` |
| G1 Git | Cumple hasta ahora | Sin `git add`, commit ni push durante Apply y Verify |

**Escaneo de secretos** sobre los archivos nuevos y modificados (claves privadas, `AKIA`, `sk-`, `ghp_`, contraseñas literales, `AUTH_SECRET_KEY=` con valor): ninguna coincidencia real. `AUTH_SECRET_KEY` aparece solo como nombre de variable, como marcador de plantilla rechazado por la configuración (`REEMPLAZAR_generar_con_secrets_token_urlsafe_48`), como constantes de mensajes de error y generada en tiempo de ejecución (`secrets.token_urlsafe(48)` en pruebas, `New-ClaveAuthEfimera` en el runner). Los hashes que aparecen en mensajes de fallo de pruebas son de contraseñas ficticias.

## Git e higiene

`git status --short` (HEAD `6258bbc`): **25 archivos modificados** y **49 entradas no rastreadas** (78 archivos no rastreados al expandir directorios, incluida la carpeta del Change).

**Modificados (25):** `.env.example`, `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/models/__init__.py`, `backend/app/models/consultorio.py`, `backend/app/seed/aplicar.py`, `backend/app/seed/datos.py`, `backend/requirements.txt`, `docker-compose.yml`, `scripts/lib/Pasos.ps1`, `scripts/test.ps1`, `scripts/tests/autoprueba.ps1`, y 13 archivos de pruebas existentes en `backend/tests/` (integración: `conftest.py`, `test_migraciones.py`, `test_modelo_base.py`, `test_repositorios_acotados.py`, `test_seed.py`; unitarias: `conftest.py`, `test_config.py`, `test_contexto_y_repositorios.py`, `test_cors.py`, `test_migraciones.py`, `test_modelos.py`, `test_seed.py`, `test_superposicion_turnos.py`).

**Nuevos (código y pruebas):** migración `0003_autenticacion_sesion.py`; `app/api/auth.py`; `app/auth/` (`acceso_previo`, `claves`, `concurrencia`, `contrasenas`, `cookies`, `dependencias`, `intentos`, `reloj`, `servicio`, `recursos/`); `app/core/cors.py` y `linea_de_comandos.py`; `app/credenciales/`; `app/mantenimiento/`; modelos `codigo`, `intento_login`, `sesion`; `app/schemas/auth.py`; 19 archivos de pruebas de integración (más 2 auxiliares, `app_auth.py` y `datos_auth.py`) y 16 de pruebas unitarias; y la carpeta del Change (`.openspec.yaml`, `proposal.md`, `design.md`, `tasks.md`, `tdd-evidencia.md`, `verify.md`, 11 `specs/*/spec.md`).

Comprobaciones:

- `git diff --check` (rastreados): sin errores de espacios en blanco, rc 0. Solo avisos de fin de línea de los `.ps1` (LF en la copia de trabajo; `.gitattributes` los normaliza a CRLF): no son errores.
- `git diff --no-index --check /dev/null <archivo>` sobre cada uno de los archivos no rastreados: **una única observación menor**, `tdd-evidencia.md` línea 729, una línea de solo dos espacios dentro de una lista Markdown. No afecta a la validación ni a las pruebas; conviene limpiarla antes de commitear (este Verify no modifica otros documentos del Change).
- Fin de línea: ningún archivo nuevo, salvo los `.ps1`, contiene CR (todos LF).
- `git check-ignore -v .env` -> `.gitignore:2:.env`: `.env` ignorado y ausente de la lista de no rastreados.
- Entre los no rastreados no hay `.env`, copias de respaldo, `__pycache__`, `.pytest_cache`, `node_modules`, `.venv`, logs ni scripts temporales (`__pycache__` está ignorado). Las copias de respaldo viven fuera del repositorio (`C:\dev\respaldos_turnos`).
- Integridad de documentos protegidos: `AGENTS.md` y `CLAUDE.md` `3961cff0f8983e21fc2f1e617ab7a7f343da6bc0`, `CHANGES.md` `d2b71fdd8a8040fca071a27011177cbe28066f8f`; `git diff --quiet -- AGENTS.md CLAUDE.md CHANGES.md openspec/specs` rc 0 (sin cambios).

## Observaciones para Archive

1. En el Archive (solo con autorización del autor): corregir en `CHANGES.md` la numeración de migraciones (la migración de C-04 pasa de `0003` a `0004`, porque C-03 ya usa `0003`) y marcar C-03 `[x]`. No se hizo ahora.
2. Las copias de respaldo de la base de desarrollo están fuera del repositorio, en `C:\dev\respaldos_turnos`; no se versionan.
3. Nota menor de documentación para un Change futuro: el docstring del módulo `app/credenciales` menciona `docker compose run --rm -it`, pero Compose v5 no tiene la opción `-t` (usa TTY por defecto); corregir el texto.
4. La API de desarrollo corre con `--reload` sobre `./backend` montado; cualquier edición de código la recarga.
5. DT-01 (advertencia de `httpx` en `starlette.testclient`) persiste, sin impacto funcional.
6. Línea 729 de `tdd-evidencia.md` con espacios al final (ver Git e higiene); limpiarla antes del commit.
7. La base de desarrollo ya está en `0003` con credenciales en las dos cuentas de administración de demostración; `downgrade` sobre desarrollo sigue prohibido.
8. El commit es solo con autorización del autor (G1), presentando antes archivos y mensaje; nunca `git add .`.

## Riesgos residuales

- **Escenario 12 de `ejecucion-de-pruebas`**: limitación aceptada descrita en la trazabilidad (el runner completo no se ejecutó en un entorno aislado sin la clave personal; solo migración e integración se verificaron con clave efímera en un proyecto Compose aislado).
- **Mantenimiento manual (DT-02)**: la limpieza de sesiones e intentos antiguos se ejecuta a mano con `python -m app.mantenimiento limpiar`; además el login borra sesiones vencidas. No hay tarea programada.
- **Sin RLS ni autorización por rol**: el aislamiento por consultorio depende de la sesión, de la FK compuesta y de los repositorios acotados; la barrera en base (PA-04) y la autorización quedan para C-04.
- **Identidad del cliente**: el control por IP usa la conexión directa y nunca `X-Forwarded-For` (DD-19); detrás de un proxy inverso todos los clientes compartirían una IP y se requeriría un diseño explícito antes de producción.
- **Dependencia del entorno del autor**: `test.ps1` requiere Docker Desktop y el repositorio configurado; falla con error claro si faltan los requisitos previos.
- **Sin integración con el frontend**: el frontend todavía no consume la autenticación; la prueba manual de login, `/me` y logout de 13.2 quedó registrada en `tdd-evidencia.md`.

## Condiciones de O2

| Condición | Estado | Evidencia |
|---|---|---|
| `openspec validate autenticacion-sesion --strict` sin errores | Cumple | Comando 1: valid, rc 0 (versión 1.14.1) |
| pytest exitoso | Cumple | Comando 2: 516 unitarias y 418 de integración, rc 0; 19 de superposición aparte (19 passed) |
| Todos los escenarios cubiertos por pruebas automatizadas | Cumple | Trazabilidad: 229 de 229, ejecutadas y en verde (335 identificadores pytest `PASSED` + casos de autoprueba `[OK]`) |
| Registro de comandos, resultados y evidencia en el Change | Cumple | Este documento y `tdd-evidencia.md` |

## Conclusión

La implementación de `autenticacion-sesion` (C-03) cumple las cuatro condiciones de O2 y las reglas duras aplicables: validación estricta en verde, 936 pruebas en verde (516 unitarias, 418 de integración contra PostgreSQL real, 2 de Vitest) más 18 casos de autoprueba, `test.ps1` con código 0, 229 de 229 escenarios con prueba automatizada ejecutada en la corrida de esta verificación, base de desarrollo sin variación (alembic `0003`, 2 consultorios, 6 usuarios, credenciales solo en las 2 cuentas de demostración, 0 sesiones, 0 intentos, huellas idénticas antes y después), API de desarrollo sana y sin secretos ni archivos temporales entre los candidatos a commit. No se detectaron fallas; las únicas observaciones son menores (espacios al final en una línea de `tdd-evidencia.md`, nota de documentación sobre `-it`) y la limitación aceptada del escenario 12. **Verify superado; el Change queda listo para Archive cuando el autor lo indique**, con la corrección de `CHANGES.md` (C-04: `0004`) y el marcado de C-03 en ese momento, y el commit solo con autorización (G1).

## Revisión documental posterior al primer Archive (2026-11-09)

Esta sección se agregó después de la conclusión anterior y no la modifica. Los resultados de Verify registrados arriba siguen siendo los de su ejecución original.

- **Hallazgo.** El primer Archive (2026-11-09) sincronizó las specs, pero `openspec validate --specs --strict` falló en 5 specs principales. Siete requisitos modificados por C-03 superaban los 500 caracteres. `validate autenticacion-sesion --strict` no lo detectó porque en 1.14.1 solo mide los requisitos ADDED de un Change.
- **Reversión.** Se revirtió con autorización del autor, con respaldo completo en `C:\dev\respaldos_turnos\archive_c03_20261109\`.
- **Corrección documental (plan B).**
  - Los 7 requisitos se reorganizaron en 17: las deltas pasan de 72 a 82 requisitos.
  - Los 229 escenarios se conservan con títulos y cuerpos idénticos; 18 cambian de requisito.
  - Los escenarios que ya estaban en HEAD siguen en su requisito MODIFIED, como exige OpenSpec.
  - El plan A (18 requisitos y un renombre) se descartó porque fallaba esa regla. El detalle está en `tdd-evidencia.md`.
- **Sin cambios de código ni de comportamiento.** No se modificaron código, migraciones, pruebas ni la base de datos. Las 936 pruebas, la matriz y sus 335 identificadores siguen siendo la evidencia válida. En la matriz solo se actualizó la columna "Requisito" de 18 filas.
- **Validaciones tras la corrección.**
  - `openspec validate autenticacion-sesion --strict`: válido.
  - Archive simulado en una copia aislada de `openspec/`: termina correctamente (+72 ~9).
  - `openspec validate --specs --strict` en la copia: 15 de 15 specs pasan.
  - Las specs resultantes tienen 116 requisitos y 315 escenarios, idénticos en título y cuerpo a los del primer Archive.
  - Ningún requisito supera 500 caracteres.
- **Condición pendiente.** El Archive real queda sujeto a la autorización del autor.

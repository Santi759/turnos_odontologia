# Verify: foundation-setup (C-01)

Verificación de la implementación (Apply) del Change `foundation-setup`, ejecutada el 2026-11-03 en Windows 11 con Docker Desktop (WSL 2) y PowerShell 5.1. Todos los datos son ficticios. **Este documento no archiva el Change**: el Archive solo se ejecuta con indicación del autor (AGENTS.md O2) y marca C-01 `[x]` en `CHANGES.md` en ese momento.

## Entorno

```
Docker servidor 29.9.2 / cliente 29.9.2
Docker Compose version v5.6.1
Python (imagen api): Python 3.14.10
Node (imagen frontend): v22.23.1
openspec CLI: 1.14.1
Host: Python 3.14.5, Node v22.23.1, npm 10.9.8 (solo conveniencia; las suites corren en contenedores)
Imágenes: python:3.14.10-slim-trixie, postgres:18.6-trixie, node:22.23.1-trixie-slim
```

### `pip freeze` real dentro del contenedor `api`

```
alembic==1.20.1
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.16.0
certifi==2026.10.23
click==8.5.0
fastapi==0.162.0
h11==0.16.0
httpcore==1.0.9
httptools==0.9.0
httpx==0.28.1
idna==3.20
iniconfig==2.3.1
Mako==1.4.3
MarkupSafe==3.0.4
opentelemetry-api==1.45.2
packaging==26.3
pluggy==1.7.0
psycopg==3.3.6
psycopg-binary==3.3.6
pydantic==2.14.2
pydantic-settings==2.16.2
pydantic_core==2.50.2
Pygments==2.21.0
pytest==9.1.1
python-dotenv==1.2.4
PyYAML==6.0.3
SQLAlchemy==2.1.6
starlette==1.10.0
typing-inspection==0.4.4
typing_extensions==4.16.0
uvicorn==0.54.0
uvloop==0.23.0
watchfiles==1.3.0
websockets==17.4
```

### `npm ls --depth=0` real dentro del contenedor `frontend`

```
turnos-odontologia-frontend@0.0.0 /app
+-- @testing-library/dom@10.4.2
+-- @testing-library/jest-dom@7.0.1
+-- @testing-library/react@16.3.3
+-- @types/react-dom@19.3.0
+-- @types/react@19.3.0
+-- @vitejs/plugin-react@6.2.1
+-- jsdom@30.1.3
+-- react-dom@19.3.1
+-- react@19.3.1
+-- typescript@6.0.3
+-- vite@8.3.5
`-- vitest@5.1.0
```

Decisiones del autor (2026-11-03) confirmadas en ejecución: DP-01 (`btree_gist` por migración `0001`), DP-02 (`psycopg[binary]==3.3.6` se instaló sin compilar ruedas en Python 3.14.10), DP-03 (TypeScript 6.0.3: `typecheck`, `build` y `vitest` en verde con vite 8.3.5 y vitest 5.1.0) y DP-04 (base de pruebas `db-test` separada y efímera).

## Comandos ejecutados y resultados

### 1. `openspec validate foundation-setup --strict`

```
Change 'foundation-setup' is valid
rc=0
```

### 2. `.\scripts\test.ps1` (ejecución completa, comando documentado en el README)

Código de salida: **0**. Salida completa (sin colores ANSI):

```
==> 0. autoprueba del runner y de la higiene del repositorio
==> paso uno
==> paso dos
[OK]    Un paso falla
==> a
==> b
[OK]    Todos los pasos de la secuencia pasan
[OK]    Falta el archivo .env
[OK]    .env ignorado por Git
[OK]    Plantilla completa con valores ficticios
[OK]    El arranque de la API no migra
[OK]    Base de pruebas separada y efimera
[OK]    Verificacion de tipos estricta
[OK]    Sin any en el codigo del frontend
[OK]    Pruebas existentes en verde (archivo sin cambios)
[OK]    test.ps1 sin .env termina con error antes de cualquier suite
[OK]    Scripts en ASCII y sin redireccion de stderr de comandos nativos
Autoprueba: todos los casos pasan
==> 1. construir imagenes (api, frontend)
 Image turnos_odontologia-api Building
 Image turnos_odontologia-frontend Building
#1 [internal] load local bake definitions
#1 reading from stdin 1.00kB done
#1 DONE 0.0s
#2 [frontend internal] load build definition from Dockerfile
#2 transferring dockerfile: 145B 0.0s done
#2 DONE 0.0s
#3 [api internal] load build definition from Dockerfile
#3 transferring dockerfile: 256B 0.0s done
#3 DONE 0.0s
#4 [frontend internal] load metadata for docker.io/library/node:22.23.1-trixie-slim
#4 DONE 0.1s
#5 [frontend internal] load .dockerignore
#5 transferring context: 60B done
#5 DONE 0.0s
#6 [frontend 1/4] FROM docker.io/library/node:22.23.1-trixie-slim@sha256:e6d9a389d34ff9678438af985c9913fbd1eb6ed36e80fea56644f4b4f6dd70ba
#6 resolve docker.io/library/node:22.23.1-trixie-slim@sha256:e6d9a389d34ff9678438af985c9913fbd1eb6ed36e80fea56644f4b4f6dd70ba 0.0s done
#6 DONE 0.0s
#7 [frontend internal] load build context
#7 transferring context: 72B done
#7 DONE 0.0s
#8 [frontend 2/4] WORKDIR /app
#8 CACHED
#9 [frontend 3/4] COPY package.json package-lock.json ./
#9 CACHED
#10 [frontend 4/4] RUN npm ci
#10 CACHED
#11 [frontend] exporting to image
#11 exporting layers done
#11 exporting manifest sha256:af87b9ae0075d49d04537f533e2e65fbc20b37d248089c742da1c464e0131fc9 done
#11 exporting config sha256:11317ead2693db4573cd3dbbcdcf2f9852d3690ae5a4876eb02b9aef091d8b73 done
#11 exporting attestation manifest sha256:55edd0884b6081d273fcd921db150a1d6d9564f6ce399d5251ace1e99ed2cc9c 0.0s done
#11 exporting manifest list sha256:9646bfcb9b115d9ca73405bb481038a6f1ea485500d4a8050d069fd389ca74fa 0.0s done
#11 naming to docker.io/library/turnos_odontologia-frontend:latest done
#11 unpacking to docker.io/library/turnos_odontologia-frontend:latest
#11 unpacking to docker.io/library/turnos_odontologia-frontend:latest 0.0s done
#11 DONE 0.2s
#12 [api internal] load metadata for docker.io/library/python:3.14.10-slim-trixie
#12 DONE 0.4s
#13 [api internal] load .dockerignore
#13 transferring context: 2B done
#13 DONE 0.0s
#14 [api 1/4] FROM docker.io/library/python:3.14.10-slim-trixie@sha256:930e1abba7c4e8f96ed93e8012c35d174d7732752731bbd5e8e757d7ec6f3966
#14 resolve docker.io/library/python:3.14.10-slim-trixie@sha256:930e1abba7c4e8f96ed93e8012c35d174d7732752731bbd5e8e757d7ec6f3966 0.1s done
#14 DONE 0.1s
#15 [api internal] load build context
#15 transferring context: 77B done
#15 DONE 0.0s
#16 [frontend] resolving provenance for metadata file
#16 DONE 0.0s
#17 [api 2/4] WORKDIR /app
#17 CACHED
#18 [api 3/4] COPY requirements.txt requirements-dev.txt ./
#18 CACHED
#19 [api 4/4] RUN pip install --no-cache-dir -r requirements-dev.txt
#19 CACHED
#20 [api] exporting to image
#20 exporting layers done
#20 exporting manifest sha256:63b4a4ad25c198625c38c95307a008584c7a816d91ab705d737a5d0eb5a1148c done
#20 exporting config sha256:a665f0c778e71a231f85c01d15fea7fb2882ad294bc45a8bde8c44f613bf4035 done
#20 exporting attestation manifest sha256:2602994174d0373b119e210943a74cfe9891239b2e09e342842abcabe5e94b61 0.0s done
#20 exporting manifest list sha256:19f9aacebf03e01663815df63ec4d85fb8445290ee295231ea6d0bf1320fe87d 0.0s done
#20 naming to docker.io/library/turnos_odontologia-api:latest done
#20 unpacking to docker.io/library/turnos_odontologia-api:latest 0.0s done
#20 DONE 0.2s
#21 [api] resolving provenance for metadata file
#21 DONE 0.0s
 Image turnos_odontologia-api Built
 Image turnos_odontologia-frontend Built
==> 2. pruebas unitarias del backend (incluye las 19 de superposicion)
 Container turnos_odontologia-api-run-2946b392219e Creating
 Container turnos_odontologia-api-run-2946b392219e Created
============================= test session starts ==============================
platform linux -- Python 3.14.10, pytest-9.1.1, pluggy-1.7.0 -- /usr/local/bin/python
rootdir: /app
configfile: pyproject.toml
plugins: anyio-4.16.0
collecting ... collected 57 items
tests/unit/test_config.py::test_carga_de_valores_validos PASSED          [  1%]
tests/unit/test_config.py::test_falta_database_url_menciona_la_variable PASSED [  3%]
tests/unit/test_config.py::test_falta_app_env_menciona_la_variable PASSED [  5%]
tests/unit/test_config.py::test_app_env_no_admitido_menciona_la_variable PASSED [  7%]
tests/unit/test_config.py::test_el_error_no_revela_la_contrasena PASSED  [  8%]
tests/unit/test_config.py::test_el_error_no_muestra_el_valor_recibido PASSED [ 10%]
tests/unit/test_config.py::test_varios_origenes_separados_por_comas PASSED [ 12%]
tests/unit/test_config.py::test_origenes_con_espacios_se_recortan PASSED [ 14%]
tests/unit/test_config.py::test_origenes_invalidos_se_rechazan[*] PASSED [ 15%]
tests/unit/test_config.py::test_origenes_invalidos_se_rechazan[http://localhost:5173,*] PASSED [ 17%]
tests/unit/test_config.py::test_origenes_invalidos_se_rechazan[] PASSED  [ 19%]
tests/unit/test_config.py::test_origenes_invalidos_se_rechazan[ , ] PASSED [ 21%]
tests/unit/test_config.py::test_test_database_url_ausente_es_none PASSED [ 22%]
tests/unit/test_config.py::test_test_database_url_presente_se_carga_como_secreto PASSED [ 24%]
tests/unit/test_cors.py::test_origen_permitido_recibe_la_cabecera_cors PASSED [ 26%]
tests/unit/test_cors.py::test_origen_no_permitido_no_recibe_la_cabecera_cors PASSED [ 28%]
tests/unit/test_cors.py::test_cada_origen_configurado_es_permitido[http://localhost:5173] PASSED [ 29%]
tests/unit/test_cors.py::test_cada_origen_configurado_es_permitido[http://127.0.0.1:5173] PASSED [ 31%]
tests/unit/test_cors.py::test_no_se_habilitan_credenciales PASSED        [ 33%]
tests/unit/test_database.py::test_verificar_conexion_falla_con_error_de_conexion_si_la_base_es_inaccesible PASSED [ 35%]
tests/unit/test_database.py::test_crear_engine_no_conecta_al_crearse PASSED [ 36%]
tests/unit/test_database.py::test_guardia_acepta_una_base_de_pruebas_separada PASSED [ 38%]
tests/unit/test_database.py::test_guardia_rechaza_url_de_pruebas_ausente PASSED [ 40%]
tests/unit/test_database.py::test_guardia_rechaza_url_de_pruebas_vacia PASSED [ 42%]
tests/unit/test_database.py::test_guardia_rechaza_la_misma_base_que_desarrollo[postgresql+psycopg://app:app@db:5432/turnos] PASSED [ 43%]
tests/unit/test_database.py::test_guardia_rechaza_la_misma_base_que_desarrollo[postgresql+psycopg://otro:otra-clave-ficticia@db:5432/turnos] PASSED [ 45%]
tests/unit/test_database.py::test_guardia_rechaza_la_misma_base_que_desarrollo[postgresql+psycopg://app:app@db/turnos] PASSED [ 47%]
tests/unit/test_database.py::test_guardia_rechaza_nombre_de_base_que_no_termina_en_test[postgresql+psycopg://app:app@db-test:5432/turnos] PASSED [ 49%]
tests/unit/test_database.py::test_guardia_rechaza_nombre_de_base_que_no_termina_en_test[postgresql+psycopg://app:app@db-test:5432/turnos_test_copia] PASSED [ 50%]
tests/unit/test_database.py::test_guardia_rechaza_nombre_de_base_que_no_termina_en_test[postgresql+psycopg://app:app@db-test:5432/test] PASSED [ 52%]
tests/unit/test_database.py::test_guardia_acepta_mismo_nombre_de_base_en_otro_host PASSED [ 54%]
tests/unit/test_esquemas.py::test_campo_no_declarado_es_rechazado PASSED [ 56%]
tests/unit/test_esquemas.py::test_solo_campos_declarados_se_validan PASSED [ 57%]
tests/unit/test_esquemas.py::test_cualquier_campo_extra_se_rechaza_no_solo_consultorio_id PASSED [ 59%]
tests/unit/test_salud.py::test_health_responde_ok PASSED                 [ 61%]
tests/unit/test_salud.py::test_health_responde_ok_con_la_base_inaccesible PASSED [ 63%]
tests/unit/test_salud.py::test_ruta_no_declarada_bajo_api_responde_404 PASSED [ 64%]
tests/unit/test_salud.py::test_el_instrumento_detecta_intentos_de_conexion PASSED [ 66%]
tests/unit/test_superposicion_turnos.py::test_exitoso_sin_turnos_existentes PASSED [ 68%]
tests/unit/test_superposicion_turnos.py::test_exitoso_con_un_turno_existente_que_no_se_cruza PASSED [ 70%]
tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[parcial_izquierda] PASSED [ 71%]
tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[parcial_derecha] PASSED [ 73%]
tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[contenido] PASSED [ 75%]
tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[contenedor] PASSED [ 77%]
tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[identico] PASSED [ 78%]
tests/unit/test_superposicion_turnos.py::test_turnos_consecutivos_se_aceptan[consecutivo_posterior] PASSED [ 80%]
tests/unit/test_superposicion_turnos.py::test_turnos_consecutivos_se_aceptan[consecutivo_anterior] PASSED [ 82%]
tests/unit/test_superposicion_turnos.py::test_turnos_simultaneos_de_profesionales_distintos_se_aceptan PASSED [ 84%]
tests/unit/test_superposicion_turnos.py::test_rechazo_con_turno_de_otro_profesional_en_la_entrada PASSED [ 85%]
tests/unit/test_superposicion_turnos.py::test_candidato_con_intervalo_no_positivo_es_invalido[duracion_cero] PASSED [ 87%]
tests/unit/test_superposicion_turnos.py::test_candidato_con_intervalo_no_positivo_es_invalido[fin_anterior_al_inicio] PASSED [ 89%]
tests/unit/test_superposicion_turnos.py::test_candidato_sin_zona_horaria_es_invalido[instantes_sin_zona_horaria] PASSED [ 91%]
tests/unit/test_superposicion_turnos.py::test_candidato_sin_zona_horaria_es_invalido[mezcla_con_y_sin_zona_horaria] PASSED [ 92%]
tests/unit/test_superposicion_turnos.py::test_turno_existente_sin_zona_horaria_es_invalido PASSED [ 94%]
tests/unit/test_superposicion_turnos.py::test_turno_existente_con_intervalo_invalido_es_invalido PASSED [ 96%]
tests/unit/test_superposicion_turnos.py::test_turno_existente_invalido_de_otro_profesional_es_invalido PASSED [ 98%]
tests/unit/test_superposicion_turnos.py::test_candidato_invalido_tiene_precedencia_sobre_la_superposicion PASSED [100%]
=============================== warnings summary ===============================
../usr/local/lib/python3.14/site-packages/fastapi/testclient.py:1
  /usr/local/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 57 passed, 1 warning in 1.70s =========================
==> 3. levantar la base de pruebas efimera (db-test)
 Container turnos_odontologia-db-test-1 Creating
 Container turnos_odontologia-db-test-1 Created
 Container turnos_odontologia-db-test-1 Starting
 Container turnos_odontologia-db-test-1 Started
 Container turnos_odontologia-db-test-1 Waiting
 Container turnos_odontologia-db-test-1 Healthy
==> 4. migraciones sobre la base de pruebas (alembic upgrade head)
 Container turnos_odontologia-api-run-a419737eeb2e Creating
 Container turnos_odontologia-api-run-a419737eeb2e Created
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, habilitar btree_gist (infraestructura, sin tablas de dominio)
==> 5. pruebas de integracion contra PostgreSQL real (db-test)
 Container turnos_odontologia-api-run-f5e622081079 Creating
 Container turnos_odontologia-api-run-f5e622081079 Created
============================= test session starts ==============================
platform linux -- Python 3.14.10, pytest-9.1.1, pluggy-1.7.0 -- /usr/local/bin/python
rootdir: /app
configfile: pyproject.toml
plugins: anyio-4.16.0
collecting ... collected 9 items
tests/integration/test_base_de_datos.py::test_consulta_trivial PASSED    [ 11%]
tests/integration/test_base_de_datos.py::test_version_mayor_del_servidor_es_18 PASSED [ 22%]
tests/integration/test_base_de_datos.py::test_btree_gist_figura_como_extension_disponible PASSED [ 33%]
tests/integration/test_base_de_datos.py::test_la_suite_corre_sobre_la_base_de_pruebas PASSED [ 44%]
tests/integration/test_migraciones.py::test_extension_btree_gist_instalada_tras_migrar PASSED [ 55%]
tests/integration/test_migraciones.py::test_restriccion_de_exclusion_utilizable_y_sin_residuos PASSED [ 66%]
tests/integration/test_migraciones.py::test_la_restriccion_acepta_periodos_consecutivos_y_otro_recurso PASSED [ 77%]
tests/integration/test_migraciones.py::test_el_comando_explicito_deja_la_base_al_dia PASSED [ 88%]
tests/integration/test_migraciones.py::test_sin_tablas_de_dominio PASSED [100%]
============================== 9 passed in 1.18s ===============================
==> 6. verificacion de tipos del frontend (tsc --noEmit)
 Container turnos_odontologia-frontend-run-938d634319f1 Creating
 Container turnos_odontologia-frontend-run-938d634319f1 Created
> turnos-odontologia-frontend@0.0.0 typecheck
> tsc --noEmit -p tsconfig.json
==> 7. pruebas del frontend (Vitest)
 Container turnos_odontologia-frontend-run-e0213954d145 Creating
 Container turnos_odontologia-frontend-run-e0213954d145 Created
> turnos-odontologia-frontend@0.0.0 test
> vitest run
 RUN  v5.1.0 /app
 ✓ src/App.test.tsx (2 tests) 164ms
 Test Files  1 passed (1)
      Tests  2 passed (2)
   Start at  15:28:50
   Duration  1.30s (environment 67%, tests 14%, setup 13%, transform 4%, import 1%)
Todas las suites pasaron.
 Container turnos_odontologia-db-test-1 Stopping
 Container turnos_odontologia-db-test-1 Stopped
 Container turnos_odontologia-db-test-1 Removing
 Container turnos_odontologia-db-test-1 Removed
```

Resumen: autoprueba (código 0), unitarias `57 passed` (incluye las 19 de `test_superposicion_turnos.py`), migraciones sobre `db-test` (`Running upgrade -> 0001`), integración `9 passed` contra PostgreSQL 18.6 real, `tsc --noEmit` código 0 y Vitest `2 passed`. `db-test` se elimina al terminar (bloque `finally`); la base de desarrollo `db` y el volumen `pgdata` no se tocan.

### 3. Fallo de extremo a extremo (tarea 12.2)

Cambio temporal (sin commitear) del valor esperado en `backend/tests/unit/test_salud.py` (`{"status": "ok"}` por `{"status": "roto"}`); salida relevante de `scripts/test.ps1`:

```
==> 0. autoprueba del runner y de la higiene del repositorio
==> 1. construir imagenes (api, frontend)
==> 2. pruebas unitarias del backend (incluye las 19 de superposicion)
tests/unit/test_salud.py::test_health_responde_ok FAILED                 [ 61%]
FAILED tests/unit/test_salud.py::test_health_responde_ok - AssertionError: as...
=================== 1 failed, 56 passed, 1 warning in 1.83s ====================
ERROR: Paso fallido: 2. pruebas unitarias del backend (incluye las 19 de superposicion) (codigo de salida 1)
```

Código de salida: **1**. Nombra el paso 2 y no ejecuta los pasos 3 a 7 (no aparece ninguna línea `==> 3.` en adelante). El archivo se restauró desde una copia y `sha256sum` coincide con el original (byte a byte idéntico; el archivo no está versionado, por eso se comparó por hash y no con `git diff`).

### 4. Otras suites ejecutadas durante Apply (resumen)

| Comando | Resultado |
|---|---|
| `docker compose run --rm --no-deps api python -m pytest -p no:cacheprovider tests/unit -q` | `57 passed, 1 warning` |
| `backend/.venv/Scripts/python.exe -m pytest -p no:cacheprovider tests/unit/test_superposicion_turnos.py -v` (host) | `19 passed` |
| `docker compose run --rm --no-deps api python -m pytest -p no:cacheprovider tests/integration -v` | `9 passed` |
| `docker compose run --rm --no-deps frontend npm run typecheck` / `npm run build` / `npm test` | código 0 / `built in 249ms` / `2 passed` |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/tests/autoprueba.ps1` | código 0 (12 casos) |
| `git diff --quiet f13f0ba -- backend/tests/unit/test_superposicion_turnos.py backend/app/domain/superposicion_turnos.py` | código 0 (sin cambios) |

La única advertencia de pytest es `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead` (sin impacto funcional; queda como observación para el autor).

## Trazabilidad escenario -> prueba (44 de 44)

Pruebas automatizadas: `U` = `backend/tests/unit/`, `I` = `backend/tests/integration/`, `A` = caso de `scripts/tests/autoprueba.ps1`, `F` = `frontend/src/App.test.tsx`.

| # | Capacidad | Escenario | Prueba |
|---|---|---|---|
| 1 | salud-api | Health responde ok | `U/test_salud.py::test_health_responde_ok` |
| 2 | salud-api | Health responde ok con la base inaccesible | `U/test_salud.py::test_health_responde_ok_con_la_base_inaccesible` (+ control `test_el_instrumento_detecta_intentos_de_conexion`) |
| 3 | salud-api | Ruta no declarada | `U/test_salud.py::test_ruta_no_declarada_bajo_api_responde_404` |
| 4 | configuracion-backend | Carga de valores válidos | `U/test_config.py::test_carga_de_valores_validos` |
| 5 | configuracion-backend | Falta DATABASE_URL | `U/test_config.py::test_falta_database_url_menciona_la_variable` |
| 6 | configuracion-backend | APP_ENV con valor no admitido | `U/test_config.py::test_app_env_no_admitido_menciona_la_variable` |
| 7 | configuracion-backend | El error no revela la contraseña | `U/test_config.py::test_el_error_no_revela_la_contrasena`, `test_el_error_no_muestra_el_valor_recibido` |
| 8 | configuracion-backend | Origen permitido | `U/test_cors.py::test_origen_permitido_recibe_la_cabecera_cors` (+ preflight real, ver manuales) |
| 9 | configuracion-backend | Origen no permitido | `U/test_cors.py::test_origen_no_permitido_no_recibe_la_cabecera_cors` |
| 10 | configuracion-backend | Varios orígenes separados por comas | `U/test_config.py::test_varios_origenes_separados_por_comas`, `U/test_cors.py::test_cada_origen_configurado_es_permitido` |
| 11 | configuracion-backend | Comodín rechazado | `U/test_config.py::test_origenes_invalidos_se_rechazan[*]` |
| 12 | configuracion-backend | Lista vacía rechazada | `U/test_config.py::test_origenes_invalidos_se_rechazan[]` |
| 13 | configuracion-backend | .env ignorado por Git | `A/.env ignorado por Git` |
| 14 | configuracion-backend | Plantilla completa con valores ficticios | `A/Plantilla completa con valores ficticios` |
| 15 | validacion-entrada | Campo no declarado rechazado | `U/test_esquemas.py::test_campo_no_declarado_es_rechazado` |
| 16 | validacion-entrada | Solo campos declarados | `U/test_esquemas.py::test_solo_campos_declarados_se_validan` |
| 17 | base-de-datos-local | Consulta trivial | `I/test_base_de_datos.py::test_consulta_trivial` |
| 18 | base-de-datos-local | Versión mayor del servidor | `I/test_base_de_datos.py::test_version_mayor_del_servidor_es_18` |
| 19 | base-de-datos-local | Extensión disponible en el servidor | `I/test_base_de_datos.py::test_btree_gist_figura_como_extension_disponible` |
| 20 | base-de-datos-local | Extensión instalada tras migrar | `I/test_migraciones.py::test_extension_btree_gist_instalada_tras_migrar` |
| 21 | base-de-datos-local | Restricción de exclusión utilizable | `I/test_migraciones.py::test_restriccion_de_exclusion_utilizable_y_sin_residuos` (+ `test_la_restriccion_acepta_periodos_consecutivos_y_otro_recurso`) |
| 22 | base-de-datos-local | El comando explícito deja la base al día | `I/test_migraciones.py::test_el_comando_explicito_deja_la_base_al_dia` (+ paso 4 de `test.ps1`) |
| 23 | base-de-datos-local | El arranque de la API no migra | `A/El arranque de la API no migra` |
| 24 | base-de-datos-local | Sin tablas de dominio | `I/test_migraciones.py::test_sin_tablas_de_dominio` |
| 25 | base-de-datos-local | Base inaccesible | `U/test_database.py::test_verificar_conexion_falla_con_error_de_conexion_si_la_base_es_inaccesible` |
| 26 | base-de-datos-local | URL de pruebas igual a la de desarrollo rechazada | `U/test_database.py::test_guardia_rechaza_la_misma_base_que_desarrollo[3 variantes]` (+ ejecución e2e en verificaciones manuales) |
| 27 | base-de-datos-local | URL de pruebas ausente rechazada | `U/test_database.py::test_guardia_rechaza_url_de_pruebas_ausente`, `..._vacia` (+ e2e) |
| 28 | base-de-datos-local | Nombre de base de pruebas no admitido | `U/test_database.py::test_guardia_rechaza_nombre_de_base_que_no_termina_en_test[3 variantes]` |
| 29 | base-de-datos-local | Base de pruebas separada y efímera | `A/Base de pruebas separada y efimera` |
| 30 | base-de-datos-local | La suite corre sobre la base de pruebas | `I/test_base_de_datos.py::test_la_suite_corre_sobre_la_base_de_pruebas` |
| 31 | frontend-base | Render del encabezado | `F/App > renderiza el encabezado principal con el texto exacto` |
| 32 | frontend-base | Un único encabezado principal | `F/App > tiene un unico encabezado principal` |
| 33 | frontend-base | Verificación de tipos estricta | `A/Verificacion de tipos estricta` + paso 6 de `test.ps1` (`tsc --noEmit`, código 0) |
| 34 | ejecucion-de-pruebas | Todas las suites pasan | Ejecución completa de `.\scripts\test.ps1`, código 0 (sección 2); además `A/test.ps1 sin .env...` ejercita el arranque del script |
| 35 | ejecucion-de-pruebas | Un paso falla | `A/Un paso falla` y fallo de extremo a extremo (sección 3) |
| 36 | ejecucion-de-pruebas | Todos los pasos de la secuencia pasan | `A/Todos los pasos de la secuencia pasan` |
| 37 | ejecucion-de-pruebas | Falta el archivo .env | `A/Falta el archivo .env` y `A/test.ps1 sin .env termina con error antes de cualquier suite` |
| 38 | ejecucion-de-pruebas | Pruebas existentes en verde | `U/test_superposicion_turnos.py` (19 PASSED en el paso 2) + `A/Pruebas existentes en verde (archivo sin cambios)` |
| 39 | base-de-datos-local | Migración de pruebas con URL insegura rechazada | `U/test_migraciones.py::test_destino_test_sin_url_de_pruebas_se_rechaza`, `..._con_url_de_pruebas_vacia_se_rechaza`, `test_destino_test_apuntando_a_desarrollo_se_rechaza[3 variantes]`, `test_destino_test_con_nombre_sin_sufijo_test_se_rechaza`, `test_los_errores_no_incluyen_contrasenas_ni_urls[5 variantes]`, `test_env_py_rechaza_target_test_cuando_la_url_de_pruebas_es_la_de_desarrollo`, `test_env_py_rechaza_target_test_sin_url_de_pruebas` |
| 40 | base-de-datos-local | URL explícita que apunta a desarrollo rechazada | `U/test_migraciones.py::test_url_explicita_que_apunta_a_desarrollo_se_rechaza`, `test_url_explicita_con_nombre_sin_sufijo_test_se_rechaza` |
| 41 | base-de-datos-local | URL explícita junto al destino de desarrollo rechazada | `U/test_migraciones.py::test_url_explicita_junto_a_destino_desarrollo_se_rechaza_por_ambigua` |
| 42 | base-de-datos-local | Migración de pruebas válida apunta a la base de pruebas | `U/test_migraciones.py::test_destino_test_valido_resuelve_la_base_de_pruebas`, `test_url_explicita_valida_de_pruebas_se_acepta`, `test_url_explicita_valida_junto_a_destino_test_se_acepta`, `test_env_py_con_target_test_valido_genera_el_sql_de_la_migracion` (+ migraciones de `I/test_migraciones.py` y paso 4 de `test.ps1`, que ahora pasan por la guardia) |
| 43 | base-de-datos-local | Migración de desarrollo explícita sigue apuntando a DATABASE_URL | `U/test_migraciones.py::test_sin_destino_ni_url_explicita_resuelve_la_base_de_desarrollo`, `test_destino_desarrollo_explicito_resuelve_la_base_de_desarrollo`, `test_desarrollo_no_exige_ni_valida_la_url_de_pruebas`, `test_env_py_sin_destino_sigue_usando_la_base_de_desarrollo` |
| 44 | base-de-datos-local | Destino de migración desconocido rechazado | `U/test_migraciones.py::test_destino_desconocido_se_rechaza_listando_los_valores_admitidos[4 variantes]`, `test_env_py_rechaza_un_destino_desconocido` |

Cobertura: **44 de 44** escenarios (38 originales + 6 de la corrección previa al Archive) con prueba automatizada o ejecución verificada del comando único; ninguno queda sin evidencia.

## Verificaciones manuales (con evidencia)

Detalle completo, con la salida de cada comando, en `tdd-evidencia.md` (secciones Bloque 2, 3 y 4):

| Verificación | Resultado |
|---|---|
| Ejecución integrada (`docker compose up -d --build`, sin `db-test`) | `http://localhost:5173/` 200; `http://localhost:8000/docs` 200; `http://localhost:8000/api/health` 200 `{"status":"ok"}` |
| CORS con preflight real (`OPTIONS`) | Origen `http://localhost:5173`: 200 con `access-control-allow-origin`; origen `http://otro-origen.invalid`: 400 sin esa cabecera |
| Recarga en caliente | `WatchFiles detected changes in 'app/api/salud.py'. Reloading...` y `[vite] hmr update /src/App.tsx`; ediciones revertidas byte a byte (sha256) |
| Health con la base detenida (F7) | `docker compose stop db` -> `GET /api/health` 200 `{"status":"ok"}`; luego `docker compose start db` |
| Logs sin datos sensibles (7.7) | `docker compose logs api`: 0 coincidencias de `DATABASE_URL`, `postgresql+psycopg`, `app:app` o `password` |
| Persistencia del volumen de desarrollo (8.10) | `alembic upgrade head` -> `0001`; `docker compose stop db` + `up -d --wait db` -> `alembic current` = `0001 (head)`; sin advertencias de PGDATA (solo el aviso estándar de `initdb` por autenticación `trust`) |
| Las pruebas no tocan la base de desarrollo (8.9) | `turnos` (desarrollo): 0 tablas y solo `plpgsql` antes y después de la suite de integración; `db-test`: `turnos_test` con `alembic_version` |
| Guardia de extremo a extremo | `TEST_DATABASE_URL` igual a la de desarrollo -> 9 errors `ValueError ... mismo host, puerto y base ...`; vacía -> 9 errors `TEST_DATABASE_URL no esta definida ...`; la base de desarrollo no se modificó |
| Finales de línea | `git check-attr`: `eol=lf` en archivos de configuración, `eol=crlf` en `.ps1`; barrido de bytes `0x0d` en archivos nuevos: ninguno (se normalizaron 7 escritos con CRLF por Python en Windows) |
| README | `git diff --numstat README.md`: `69 0` (69 líneas agregadas, 0 eliminadas); las 361 líneas originales se conservan en orden; el borrado del volumen se documenta como acción destructiva manual y no se ejecutó |

Comandos del README ejecutados tal como están escritos: `copy .env.example .env` (en un directorio temporal, para no sobrescribir el `.env` existente), `docker compose up -d --build`, `docker compose run --rm api alembic upgrade head` (idempotente: base ya en `0001`) y `.\scripts\test.ps1` (código 0). **No** se ejecutó `docker compose down -v` (destructivo, solo manual del usuario).

## Búsquedas de higiene (D1, X1, S2)

- `any` en `frontend/src` (`Select-String -Pattern '\bany\b'`): 0 coincidencias.
- `print(`, `logging` o `logger` en `backend/app`: 0 coincidencias (sin logs con datos sensibles).
- Datos de pacientes, DNI, correos o teléfonos en código de C-01 (frontend, `app/`, pruebas de integración): 0 coincidencias.
- `git diff --check`: sin errores de espacios; solo la advertencia informativa de CRLF del `README.md` preexistente.
- `.env` ignorado (`.gitignore:2`) y ausente de `git status`; `CHANGES.md`, `AGENTS.md`, `CLAUDE.md` y `knowledge-base/` sin cambios.

## Condiciones de O2 (AGENTS.md)

| Condición | Estado |
|---|---|
| `openspec validate foundation-setup --strict` sin errores | Cumplida (sección 1 y re-ejecución posterior a las correcciones, código 0) |
| pytest exitoso | Cumplida: 86 unitarias (19 de regresión; 57 + 29 de la corrección previa al Archive) + 9 de integración |
| Todos los escenarios cubiertos por pruebas automatizadas | Cumplida: 44 de 44 (tabla de trazabilidad) |
| Registro de comandos, resultados y evidencia | Cumplida: este archivo y `tdd-evidencia.md` |

## Revisión final de Verify (2026-11-04, orquestador)

Re-ejecución independiente, después de cerrar Apply:

| Comando | Resultado |
|---|---|
| `openspec validate foundation-setup --strict` | `Change 'foundation-setup' is valid`, código 0 |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1` | Código 0: autoprueba OK; 57 unitarias pasadas; migración `-> 0001` sobre `db-test`; 9 de integración pasadas; `tsc --noEmit` OK; Vitest 2 pasadas; `db-test` eliminada al final |
| `pytest backend/tests/unit/test_superposicion_turnos.py` (venv del host) | `19 passed` |
| Las mismas 19 dentro del contenedor `api` | `19 passed` |
| `git diff --quiet f13f0ba -- backend/tests/unit/test_superposicion_turnos.py backend/app/domain/superposicion_turnos.py` | Código 0 (sin cambios) |
| `docker compose ps` y `curl` a 5173, `/docs` y `/api/health` | `db` healthy, `api` y `frontend` Up; las tres URLs devuelven 200 |
| Base de desarrollo `turnos` (solo lectura con `psql`) | PostgreSQL 18.6; extensiones `btree_gist` y `plpgsql`; 0 tablas públicas además de `alembic_version` |
| Trazabilidad | Las 38 filas citan pruebas que existen en el código: 29 funciones pytest, casos de autoprueba y pruebas de Vitest |
| `git diff --numstat README.md` y `git diff --check` | `69 0`; sin errores |

### Decisiones del autor (2026-11-04)

- **Deuda técnica DT-01 (httpx):** se mantiene `httpx==0.28.1`. Las pruebas que usan `starlette.testclient` emiten `StarletteDeprecationWarning` ("Using httpx with starlette.testclient is deprecated; install httpx2 instead"). No rompe ninguna prueba. La migración a `httpx2` queda para un Change futuro.
- **`/docs` (Swagger):** se mantiene disponible en el entorno local de desarrollo, publicado solo en `127.0.0.1`.
- No se incorporan linters (DP-05 sigue abierta) ni funcionalidades fuera de C-01.

### Observaciones (no bloquean)

- Corregido antes del Archive: `alembic/env.py` tomaba `TEST_DATABASE_URL` (`-x target=test`) y la `sqlalchemy.url` explícita sin pasar por la guardia `validar_url_de_pruebas`. Ahora delega en `resolver_url_de_migracion` (ver "Correcciones previas al Archive" y `test_migraciones.py`).
- En el README, la nota "en implementación (Apply)" de la sección de C-01 debe actualizarse durante el Archive.

## Correcciones previas al Archive (2026-11-04)

Dos correcciones pedidas por el autor antes del Archive, hechas con TDD estricto (detalle RED/GREEN en `tdd-evidencia.md`, Bloque 6).

1. **Guardia de las migraciones de prueba.** Causa raíz: `env.py` resolvía `TEST_DATABASE_URL` y la URL explícita sin la guardia. Diseño: función pura `resolver_url_de_migracion(settings, destino, url_explicita)` en `backend/app/core/migraciones.py`; `env.py` solo lee entradas y delega (online y offline). Sin `-x`: `DATABASE_URL`; `target=test` o URL explícita: `validar_url_de_pruebas`; URL explícita con `target=desarrollo`: ambigua, se rechaza; otro destino: se rechaza listando los admitidos. Errores sin URLs ni credenciales. `alembic.ini` no define `sqlalchemy.url`. Cubierto por 6 escenarios nuevos en `specs/base-de-datos-local/spec.md` y las tareas 8.12 y 8.13.
2. **`verify.md`.** Se dejó una única sección `## Conclusión` (al final), se actualizaron los conteos (86 unitarias, 44 escenarios) y la observación resuelta de `env.py` pasó a nota de corrección. Se conservó toda la evidencia (tablas, comandos, salidas, decisiones DT-01 y `/docs`) y la observación pendiente del README.

Salida de las pruebas nuevas en RED (antes de implementar): `ModuleNotFoundError: No module named 'app.core.migraciones'`; con la función lista y `env.py` sin cambiar: `4 failed, 25 passed` (3 pruebas de `env.py` y 1 de hermeticidad del entorno, corregida).

| # | Comando | Resultado |
|---|---|---|
| 1 | `docker compose run --rm --no-deps api python -m pytest -p no:cacheprovider tests/unit -q` | `86 passed, 1 warning in 2.29s`, código 0 (57 previas + 29 nuevas, incluidas las 19) |
| 2 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1` | Código 0: autoprueba OK; `86 passed`; migración `-> 0001` sobre `db-test`; integración `9 passed`; `tsc --noEmit` OK; Vitest `2 passed`; `Todas las suites pasaron.`; `db-test` eliminada |
| 3 | `backend/.venv/Scripts/python -m pytest -p no:cacheprovider backend/tests/unit/test_superposicion_turnos.py -q` (host) | `19 passed in 0.03s` |
| 3b | `git diff --quiet f13f0ba -- backend/tests/unit/test_superposicion_turnos.py backend/app/domain/superposicion_turnos.py` | Código 0 (sin cambios) |
| 4 | `openspec validate foundation-setup --strict` | `Change 'foundation-setup' is valid`, código 0 |
| 5 | `docker compose run --rm --no-deps -e TEST_DATABASE_URL=<URL de desarrollo> api alembic -x target=test upgrade head --sql` | `ValueError: TEST_DATABASE_URL apunta al mismo host, puerto y base que DATABASE_URL ...`, código 1 |
| 6 | `docker compose run --rm --no-deps api alembic -x target=prod upgrade head --sql` | `ValueError: destino de migracion no admitido (-x target=...): los valores admitidos son desarrollo o test`, código 1 |
| 7 | `alembic -x target=test upgrade head --sql` (entorno real) y `alembic upgrade head --sql` (desarrollo) | Ambos generan `CREATE EXTENSION IF NOT EXISTS btree_gist;`, código 0 |
| 8 | `docker compose run --rm api alembic current` (desarrollo, solo lectura) | `0001 (head)`, código 0; no se ejecutó ningún `downgrade` ni `down -v` contra desarrollo |
| 9 | `docker compose ps`; `curl` a 5173, `/docs` y `/api/health` | `db` healthy, `api` y `frontend` Up; las tres URLs devuelven 200; `db-test` no queda en ejecución |

Finales de línea: los archivos nuevos o editados (`migraciones.py`, `test_migraciones.py`, `env.py`, `spec.md`, `tasks.md`, `design.md`, `tdd-evidencia.md`, `verify.md`) no contienen bytes `0x0d`.

## Conclusión

Tras las correcciones previas al Archive (guardia de migraciones de prueba y limpieza de este documento), la implementación cumple las cuatro condiciones de O2: el Change está **listo para Archive** a juicio de esta verificación. El Archive **no se ejecutó**: requiere indicación del autor, y al archivar debe marcarse C-01 `[x]` en `CHANGES.md` (C-15 sigue `[ ]`). Pendiente para el autor: el commit (G1) y las decisiones DP-05 a DP-08 de `design.md`. La advertencia de `httpx2` quedó registrada como deuda técnica DT-01.

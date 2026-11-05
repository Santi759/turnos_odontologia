# Evidencia TDD: foundation-setup

Registro por tarea (TDD estricto). Se completa bloque a bloque durante Apply. Datos ficticios únicamente.

## Línea base (tarea 1.2)

- Comando: `backend/.venv/Scripts/python.exe -m pytest -v -p no:cacheprovider` desde `backend/` (antes de crear código nuevo).
- Resultado: `19 passed in 0.08s`.

## Entorno del host (tarea 1.3)

| Herramienta | Versión observada | Coincide con design.md |
|---|---|---|
| Docker (servidor / cliente) | 29.9.2 / 29.9.2 | Sí |
| Docker Compose | v5.6.1 | Sí |
| Python (host) | 3.14.5 | Sí |
| Node | v22.23.1 | Sí |
| npm | 10.9.8 | (no figuraba en el cuadro) |
| openspec | 1.14.1 | Sí (AGENTS.md O2) |

## Compatibilidad verificada en el contenedor (DP-02, tarea 4.1/7.1, bloque 1)

- Imagen `python:3.14.10-slim-trixie` (Python 3.14.10), construida con `docker build -t turnos-api-dev:scratch backend` (el servicio de Compose llega en el bloque 4).
- `pip install -r requirements-dev.txt` instaló sin compilar ruedas (0 apariciones de "building wheel" en una reconstrucción `--no-cache`).
- `pip freeze` (extracto): alembic==1.20.1, fastapi==0.162.0, httpx==0.28.1, psycopg==3.3.6, psycopg-binary==3.3.6, pydantic==2.14.2, pydantic-settings==2.16.2, pydantic_core==2.50.2, pytest==9.1.1, SQLAlchemy==2.1.6, starlette==1.10.0, uvicorn==0.54.0.
- `python -c "import httpx, fastapi.testclient; print(httpx.__version__)"` imprime `0.28.1`; emite `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead` (advertencia, no error).

## Tabla de ciclos

Columnas: Safety Net = pruebas previas en verde antes de modificar archivos existentes; RED = prueba escrita y ejecutada viéndola fallar; GREEN = código mínimo y ejecución en verde; TRIANGULATE = casos adicionales con datos distintos; REFACTOR = suite en verde tras cada paso.

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.2 | `backend/tests/unit/test_superposicion_turnos.py` | Unit | 19/19 | n/a (línea base) | 19 passed | n/a | n/a |
| 2.1-2.2 | `scripts/tests/autoprueba.ps1` | Script (PS 5.1) | n/a (archivo nuevo) | Sí: sin `Pasos.ps1` falló por archivo inexistente; con `Pasos.ps1` vacío, 2 casos fallaron ("Invoke-Paso" no existe), código 1 | `Invoke-Paso` con revisión de `$LASTEXITCODE`; autoprueba código 0 | 2 casos ("Un paso falla" con `cmd /c exit 3` y tercer paso no ejecutado; "Todos los pasos pasan") | Pendiente (2.6, bloque 5) |
| 2.3-2.4 | `scripts/tests/autoprueba.ps1` | Script | 2/2 casos previos | Sí: "Falta el archivo .env" falló (función inexistente) | `Assert-RequisitosPrevios`; autoprueba código 0; el directorio temporal se elimina | Mismo caso comprueba error sin `.env` y no-error con `.env` | Pendiente (2.6) |
| 3.1 | `git ls-files --eol` / `git status --short` | Verificación | 91 i/lf sin cambios | n/a (configuración) | `.gitattributes` creado; el índice sigue en LF; ningún archivo existente modificado | n/a | n/a |
| 3.2-3.3 | `scripts/tests/autoprueba.ps1` | Script | 3/3 casos previos | Sí: "Plantilla completa" falló (`.env.example` no existe). El caso ".env ignorado" pasó desde el inicio (el `.gitignore` ya lo cubría; se conserva como regresión) | `.env.example` con 8 variables ficticias; autoprueba código 0 | Verifica 8 variables presentes, `POSTGRES_PASSWORD=app`, `TEST_DATABASE_URL` hacia `db-test`/`*_test`, y ausencia de `AUTH_*`/`EMAIL_*` | Pendiente |
| 3.4 | listado + `git status --short` | Verificación | n/a | n/a | Carpetas DF-01 creadas con `__init__.py`/`.gitkeep`; `backend/app/domain/` y `backend/tests/unit/test_superposicion_turnos.py` sin diferencias respecto de `f13f0ba` (`git diff --quiet` = 0) | n/a | n/a |
| 4.1 | `git diff backend/requirements-dev.txt` | Verificación | n/a | n/a | `pytest==9.1.1` conservado; `-r requirements.txt` y `httpx==0.28.1` agregados | n/a | n/a |
| 5.1-5.2 | `backend/tests/unit/test_config.py` | Unit | 19/19 | Sí: `ModuleNotFoundError: app.core.config` | `Settings`/`cargar_configuracion`; 1 passed | ver 5.3-5.5 | ver 5.7 |
| 5.3 | `test_config.py` | Unit | 1/1 | Sí: 3 fallos (el error mencionaba `database_url`/`app_env`, no la variable de entorno) | `validation_alias` con el nombre de la variable; 4 passed | Falta DATABASE_URL, falta APP_ENV, APP_ENV inválido | Sí |
| 5.4 | `test_config.py` | Unit | 4/4 | Sí: `test_el_error_no_muestra_el_valor_recibido` falló (el error mostraba `input_value`). La prueba de la contraseña con APP_ENV inválido ya pasaba antes (la contraseña no estaba en el error de esa variable) | `hide_input_in_errors=True`; 6 passed | 2 pruebas (contraseña ficticia y valor recibido) | Sí |
| 5.5 | `test_config.py` | Unit | 6/6 | Sí: 4 fallos paramétricos (`*`, `a,*`, vacío, ` , `). "Varios orígenes" y "espacios recortados" ya pasaban (caracterización) | validador que rechaza lista vacía y `*`; 12 passed | 2 orígenes, espacios, 4 valores inválidos | Sí |
| 5.6 | `test_config.py` | Unit | 12/12 | Sí: 2 fallos (`AttributeError`) | `test_database_url` opcional `SecretStr`; 14 passed | ausente (None) y presente (sin revelar contraseña en `repr`) | Sí |
| 5.7 | `test_config.py` | Unit | 14/14 | n/a | n/a | n/a | Nombres `snake_case`, anotaciones de tipo, línea larga ajustada; 14 passed |
| 6.1-6.3 | `backend/tests/unit/test_esquemas.py` | Unit | 17/17 | Sí: error de colección (`app.schemas.base` inexistente) | `EsquemaEntrada` con `extra="forbid"`; 3 passed | `consultorio_id` extra, solo campos declarados, otro campo extra (`rol`) | Sí |
| 7.1 | comando en contenedor | Verificación | n/a | n/a | httpx 0.28.1 importa y `fastapi.testclient` carga en Python 3.14.10 (con advertencia de deprecación, ver arriba) | n/a | n/a |
| 7.2-7.3 | `backend/tests/unit/test_salud.py` | Unit | 36/36 | Sí: error de colección (`app.main` inexistente) | `crear_app`, `api/salud.py`, `schemas/salud.py`; 1 passed | ver 7.4 | Sí |
| 7.4 | `test_salud.py` | Unit | 1/1 | No hubo RED: ya pasaban porque la implementación no depende de la base (caracterización de F7). Se sustituyó el evento `Pool.connect` del diseño por `Engine.do_connect` y se agregó una prueba de control (`test_el_instrumento_detecta_intentos_de_conexion`) para que la aserción "sin intentos de conexión" no sea vacua | 4 passed | base inaccesible con listener, control del listener, 404 en `/api/no-existe` y `/api/health/otra` | Sí |
| 7.5-7.6 | `backend/tests/unit/test_cors.py` | Unit | 40/40 | Sí: 3 fallos (origen permitido x3); "origen no permitido" ya pasaba | `CORSMiddleware` (DF-06); 45 passed | 2 orígenes configurados, no permitido, sin credenciales | Sí |

## Ejecuciones de referencia del bloque 1

- Contenedor (`docker run --rm -v C:/dev/turnos_odontologia/backend:/app turnos-api-dev:scratch python -m pytest -p no:cacheprovider tests/unit -q`): `45 passed` (19 de superposición + 14 config + 3 esquemas + 4 salud + 5 CORS).
- Regresión: `tests/unit/test_superposicion_turnos.py` en contenedor `19 passed in 0.17s`; en el venv del host `19 passed in 0.03s`; `git diff --quiet f13f0ba -- backend/tests/unit/test_superposicion_turnos.py backend/app/domain/superposicion_turnos.py` = 0.
- Autoprueba: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/tests/autoprueba.ps1` = código 0 (5 casos).

## Bloque 2: base de datos, SQLAlchemy y Alembic

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 8.1-8.2 | `backend/tests/unit/test_database.py` | Unit | 45/45 | Sí: error de colección (`app.core.database` inexistente) | `crear_engine`, `verificar_conexion`, `validar_url_de_pruebas`; 12 passed | Base inaccesible con error real `OperationalError` (no omitido); guardia: válida, ausente, vacía, misma base (3 variantes: contraseña distinta, puerto implícito), sufijo `_test` (3 variantes), mismo nombre en otro puerto; el error no contiene credenciales | Se extrajo `crear_engine_desde_url` (57 passed al cierre) |
| 8.3 | `backend/tests/integration/{conftest,test_base_de_datos}.py` | Integration (PostgreSQL 18.6 real, `db-test`) | n/a | Sí, con `db-test` detenida: `4 errors` (`failed to resolve host 'db-test'`), ninguna omitida | `docker compose up -d --wait db-test`; `4 passed` | `current_database() == 'turnos_test'` además de 4 escenarios | n/a |
| 8.4 | `test_base_de_datos.py` | Integration | 4/4 | Cambio temporal `== 18` por `== 17`: `1 failed, 3 passed` | Revertido: `4 passed`; `psql select version()` = PostgreSQL 18.6 (Debian 18.6-1.pgdg13+2) | Caracterizan el entorno real | n/a |
| 8.5-8.6 | `backend/tests/integration/test_migraciones.py` | Integration | 4/4 | Sí: `1 failed, 4 errors` (Alembic sin inicializar: `CommandError`) | `alembic.ini`, `env.py`, `script.py.mako`, `app/models/base.py`, migración `0001`; `alembic -x target=test upgrade head` ok; `9 passed` | Exclusión rechaza solapamiento (SQLSTATE 23P01) y no deja residuos en `pg_class`; acepta consecutivos `[10:00,10:30)`+`[10:30,11:00)` y otro recurso; downgrade a `base` y upgrade a `head` idempotente | Se agregó `path_separator = os` (quita DeprecationWarning de Alembic); 9 passed |
| 8.7 | `scripts/tests/autoprueba.ps1` | Script | 5/5 casos | La primera versión del caso `db-test` falló por mi aserción (en `docker compose config` el tmpfs va en `tmpfs`, no en `volumes`); se corrigió la aserción | 7 casos pasan, código 0 | Mutación temporal: agregar `ports` a `db-test` hace fallar el caso ("db-test publica puertos en el host"); revertido, vuelve a código 0 | n/a |
| 8.9-8.11, 4.2, 7.7 | verificaciones manuales | Manual | n/a | n/a | ver abajo | n/a | n/a |

### Ejecuciones de cierre del bloque 2
- Unit en contenedor: `docker compose run --rm --no-deps api python -m pytest -p no:cacheprovider tests/unit -q` → `57 passed, 1 warning` (incluye las 19).
- 19 en contenedor: `19 passed in 0.25s`; en venv del host: `19 passed in 0.06s`; `git diff --quiet f13f0ba -- test_superposicion_turnos.py superposicion_turnos.py` = 0.
- Integración: `docker compose run --rm --no-deps api python -m pytest -p no:cacheprovider tests/integration -v` → `9 passed in 1.14s`.
- Autoprueba: código 0 (7 casos).

### Notas para verify.md: aislamiento y no destrucción (tareas 8.9-8.11, 7.7)
El volumen `turnos_odontologia_pgdata` lo creó este Apply (no existía antes; `docker volume ls` vacío al empezar el bloque 2): no hay datos preexistentes.

Aislamiento (8.9), base de desarrollo `turnos` consultada con `psql` antes y después de correr `alembic -x target=test upgrade head` y la suite de integración (9 passed):
```
ANTES   tablas en public: 0 ; extensiones: plpgsql
DESPUES tablas en public: 0 ; extensiones: plpgsql ; to_regclass('public.alembic_version') = (vacío)
db-test: current_database() = turnos_test ; tablas: alembic_version
```
Guardia de extremo a extremo (sin tocar la base de desarrollo; `docker compose run --rm --no-deps -e TEST_DATABASE_URL=... api pytest tests/integration`):
```
TEST_DATABASE_URL = URL de desarrollo -> 9 errors: ValueError: TEST_DATABASE_URL apunta al mismo host, puerto y base que DATABASE_URL (base de desarrollo): se rechaza ejecutar las pruebas
TEST_DATABASE_URL vacía               -> 9 errors: ValueError: TEST_DATABASE_URL no esta definida: las pruebas de integracion requieren una base de pruebas separada
```
Tras ambas, la base de desarrollo seguía con 0 tablas.

Persistencia del volumen (8.10), solo sobre la base de desarrollo recién creada: `docker compose run --rm --no-deps api alembic upgrade head` → `Running upgrade -> 0001`; `alembic current` → `0001 (head)`; `docker compose stop db`; `docker compose up -d --wait db`; `alembic current` → `0001 (head)`; `psql`: extensiones `btree_gist, plpgsql`; tabla `alembic_version`. `docker compose logs db`: solo `initdb: warning: enabling "trust" authentication for local connections` (advertencia estándar de initdb; ninguna sobre el punto de montaje de PGDATA). No se ejecutó `down -v`, ni downgrade, ni DROP contra la base de desarrollo.

Health y logs (7.7) y F7 (8.11): `docker compose up -d --wait api`; `curl -s -i http://localhost:8000/api/health` → `HTTP/1.1 200 OK` `{"status":"ok"}`. `docker compose logs api | grep -ciE "DATABASE_URL|postgresql\+psycopg|app:app|password"` → `0`. Con `docker compose stop db`: `curl` → `HTTP/1.1 200 OK` `{"status":"ok"}`; luego `docker compose start db`. El arranque de `api` no ejecutó migraciones (logs solo de uvicorn).

## Bloque 3: frontend (React + TypeScript + Vitest)

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 9.1-9.2 | `docker compose config`, `npm ls` | Verificación | n/a | n/a | package.json con versiones exactas (sin `^`), tsconfig `strict: true`, vite.config.ts, Dockerfile, servicio `frontend` en Compose con volumen `frontend_node_modules`. `package-lock.json` generado en el contenedor `node:22.23.1-trixie-slim` con `npm install --package-lock-only` (la imagen aún no se podía construir sin lock, y así no se escribe `node_modules` en el bind mount); `docker compose build frontend` hizo `npm ci` | `npm ls --depth=0` (abajo) coincide exactamente, sin advertencias de peers | n/a |
| 9.3-9.4 | `frontend/src/App.test.tsx` | Unit (Vitest + jsdom + Testing Library + jest-dom) | n/a (archivo nuevo) | Sí: `FAIL src/App.test.tsx ... Failed to resolve import "./App"`, `no tests` | `App.tsx` y `main.tsx`; `1 passed` | ver 9.5 | n/a |
| 9.5 | `App.test.tsx` | Unit | 1/1 | Sí (real): el 2.º caso falló (`Tests 1 failed \| 1 passed`) porque sin `globals` Testing Library no limpia el DOM entre pruebas y se acumulaban dos `<h1>` | `afterEach(cleanup)` en `src/setupTests.ts`; `2 passed` | "texto exacto" + "un único encabezado" | n/a |
| 9.6 | `scripts/tests/autoprueba.ps1` | Script | 7/7 casos | Los casos nuevos pasaron de entrada (`tsconfig` ya era estricto): son verificaciones de regresión. Mutaciones: `strict: false` hace fallar "Verificación de tipos estricta"; `export const x: any = 1;` en `src/` hace fallar "Sin any en el código del frontend"; ambas revertidas | 9 casos pasan, código 0; `npm run typecheck` código 0 | n/a | Corregí un error propio de escapes (`	`, ``) en el script antes de dar por buena la verificación |

### DP-03 (TypeScript 6.0.3): veredicto compatible
- `npm run typecheck` (`tsc --noEmit -p tsconfig.json`, `strict: true`): código 0, sin errores.
- `npm run build` (`vite build`, Vite 8.3.5): `✓ 15 modules transformed ... ✓ built in 249ms`, código 0 (se borró `frontend/dist` después).
- `npm test` (`vitest run`, Vitest 5.1.0, jsdom 30.1.3): `Test Files 1 passed (1)`, `Tests 2 passed (2)`.
- `npm ls --depth=0` en el contenedor (sin `UNMET`/`invalid`):
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
- Servidor de desarrollo: `docker compose up -d frontend` → `VITE v8.3.5 ready`, `curl http://localhost:5173/` = HTTP 200 con `id="root"`; luego `docker compose stop frontend`.
- `node_modules` solo existe en el volumen `frontend_node_modules`; en el bind mount queda un directorio vacío (punto de montaje) que Git ignora; `git status --short -uall` no lista `node_modules` ni `dist`.

## Bloque 4: Docker Compose y ejecución integrada

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 4.3 | `docker compose build api` + `pip freeze` | Verificación | n/a | n/a | Imagen construida; reconstrucción `--no-cache`: 0 apariciones de "building wheel" (todo con ruedas). `psycopg==3.3.6`, `psycopg-binary==3.3.6` instalados en Python 3.14.10 (DP-02 confirmado) | n/a | n/a |
| 4.4 | `backend/tests/unit/test_superposicion_turnos.py` | Unit (contenedor) | n/a | n/a (regresión) | `docker compose run --rm --no-deps api python -m pytest -p no:cacheprovider tests/unit -v`: `57 passed`, de las cuales 19 son `test_superposicion_turnos` (19 PASSED); archivo solo: `19 passed in 0.29s` | n/a | n/a |
| 4.5 | `scripts/tests/autoprueba.ps1` | Script | 9/9 casos | Es verificación de no regresión (pasa de entrada). Mutación: agregar una línea a `test_superposicion_turnos.py` hizo fallar el caso; revertido con copia exacta (`git diff --quiet f13f0ba` = 0) | 10 casos pasan, código 0 | Comprueba también `superposicion_turnos.py` | n/a |
| 10.1-10.3 | verificaciones manuales | Manual | n/a | n/a | ver abajo | n/a | Se normalizaron a LF 7 archivos propios que Python había escrito con CRLF (ver 10.3) |

### Notas para verify.md: ejecución integrada (10.1)
`docker compose up -d --build` (db, api, frontend; sin db-test) y, desde el host:
```
http://localhost:5173/            -> 200  (<title>Turnos Odontología</title>, #root)
http://localhost:8000/docs        -> 200  (<title>turnos_odontologia - Swagger UI</title>)
http://localhost:8000/api/health  -> 200  {"status":"ok"}
```
CORS (preflight `OPTIONS /api/health` con `Access-Control-Request-Method: GET`):
```
Origin: http://localhost:5173         -> 200 OK, access-control-allow-origin: http://localhost:5173, access-control-allow-methods: GET
Origin: http://otro-origen.invalid    -> 400 Bad Request, sin access-control-allow-origin
GET con Origin permitido -> access-control-allow-origin: http://localhost:5173 ; GET con Origin ajeno -> 0 cabeceras allow-origin
```

### Recarga en caliente (10.2)
Edición temporal de `backend/app/api/salud.py` (comentario agregado) y de `frontend/src/App.tsx` (texto "(HMR temporal)"):
```
api-1      | WARNING:  WatchFiles detected changes in 'app/api/salud.py'. Reloading...
api-1      | INFO:     Started server process [11] / Application startup complete.
frontend-1 | 3:23:35 PM [vite] (client) hmr update /src/App.tsx
curl http://localhost:5173/src/App.tsx | grep "HMR temporal"  -> HMR temporal   (cambio servido)
GET /api/health tras el reload -> 200
```
Reversión por copia previa: `sha256sum` de ambos archivos idéntico antes y después (`REVERT_BYTE_IDENTICAL`, `cmp` OK); al revertir hubo una segunda recarga/HMR (`hmr update` 3:23:44) y el texto temporal dejó de servirse (0 coincidencias).

### Finales de línea (10.3)
- `git check-attr eol text`: `docker-compose.yml`, `Dockerfile`, `main.py`, `package.json`, `.env.example`, `alembic.ini` -> `eol: lf`, `text: auto`; los tres `.ps1` -> `eol: crlf`, `text: set`.
- Bytes 0x0d en la copia de trabajo (sin staging): hallazgo propio: 7 archivos nuevos tenían CRLF porque los reescribí con Python en modo texto en Windows (`docker-compose.yml`, `app/main.py`, `core/config.py`, `core/database.py`, `test_config.py`, `test_salud.py`, `App.test.tsx`). Se normalizaron a LF con `sed -i 's/$//'` (contenido sin cambios) y se re-ejecutaron todas las suites. Luego un barrido de todos los archivos sin seguimiento (excepto `openspec/`) no encontró ningún CR; los archivos de `openspec/changes/foundation-setup/` tampoco tienen CR.
- Los `.ps1` están en LF en la copia de trabajo (PowerShell 5.1 los ejecuta bien); Git los pasará a CRLF al extraerlos por el atributo `eol=crlf`.
- Los archivos preexistentes conservan CRLF en la copia de trabajo (`README.md` 360 CR, `pyproject.toml` 3 CR) con índice en LF (`git ls-files --eol`: `i/lf w/crlf attr/text=auto eol=lf`): `.gitattributes` no los modificó.

## Bloque 5: comando único, documentación y verificación

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.5 | `scripts/tests/autoprueba.ps1` (caso "test.ps1 sin .env ...") | Script | 10/10 casos | Sí: `No se encuentra la ruta ... scripts	est.ps1` (no existía) | `scripts/test.ps1` creado; sin `.env` (copia en directorio temporal) termina con código distinto de cero, mensaje "copiar .env.example a .env" y ninguna línea `==>`; con `.env` (ejecución real) código 0 | Caso sin `.env` + ejecución completa | Ver 2.6 |
| 2.6 | `autoprueba.ps1` (caso "Scripts en ASCII y sin redireccion ...") | Script | 11/11 | El caso pasó de entrada (verificación de regresión; los scripts ya eran ASCII y sin la redirección) | 12 casos pasan, código 0 | Revisa todos los `.ps1` | n/a |
| 4.6, 8.8, 9.7 | `scripts/test.ps1` completo | Integración del runner | n/a | n/a | Pasos 1 a 7 agregados; ejecución real, código 0, con las 19 de superposición dentro de las 57 unitarias | Fallo de extremo a extremo (12.2) | n/a |
| 11.1 | `git diff README.md` | Verificación | n/a | n/a | `69 0` (69 agregadas, 0 eliminadas); 361 de 361 líneas originales conservadas en orden; CRLF del árbol de trabajo conservado | n/a | n/a |
| 12.1-12.7 | `verify.md` | Verificación | n/a | n/a | Ver `verify.md` (comando único código 0, validate --strict, 38 de 38 escenarios trazados, higiene, O2) | n/a | n/a |

Notas: `scripts/test.ps1` usa `try/catch/finally`: ante un fallo imprime `ERROR: Paso fallido: <nombre> (codigo de salida N)`, sale con código 1 y siempre elimina `db-test` (`docker compose --profile test rm -sf db-test`) sin tocar `db` ni `pgdata`. Los `.ps1` están en LF en el árbol de trabajo; `.gitattributes` (`*.ps1 text eol=crlf`) los entrega en CRLF al extraer.

## Bloque 6: corrección previa al Archive (2026-11-04): guardia de migraciones de prueba

Causa raíz: `alembic/env.py` resolvía `TEST_DATABASE_URL` (`-x target=test`) y una `sqlalchemy.url` explícita sin pasar por `validar_url_de_pruebas`; una `TEST_DATABASE_URL` igual a la de desarrollo habría migrado la base de desarrollo.

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 8.12 | `backend/tests/unit/test_migraciones.py` (función pura) | Unit | 57/57 | Sí: `ModuleNotFoundError: No module named 'app.core.migraciones'` (error de colección) | `app/core/migraciones.py::resolver_url_de_migracion`; los 24 casos de la función pasan | Desarrollo por defecto y explícito; `target=test` válido; ausente, vacío, idéntico, otras credenciales, puerto implícito, sin `_test`; URL explícita a desarrollo, sin `_test`, válida, válida con `test`, junto a `desarrollo`; destinos `prod`, `Test`, vacío, `tests`; 5 casos de error sin contraseñas ni `postgresql` | Mensajes sin URLs; `assert` de tipado |
| 8.13 | `test_migraciones.py` (`env.py` de extremo a extremo, `command.upgrade(sql=True)`, sin base) | Unit (Alembic offline) | 57/57 + función pura | Sí: con la función ya implementada y `env.py` sin cambiar, 3 de 5 pruebas de `env.py` fallan: `RuntimeError: TEST_DATABASE_URL no esta definida` (esperado `ValueError`), `target=test` con URL igual a la de desarrollo sin rechazo y `target=prod` sin rechazo (`DID NOT RAISE`). Además una prueba unitaria falló porque el entorno del contenedor filtraba `TEST_DATABASE_URL`: se hizo hermética pasando siempre la variable | `env.py` solo lee entradas y delega; `86 passed` | Rechazos por URL igual a desarrollo, ausente y destino desconocido; caso válido genera `CREATE EXTENSION IF NOT EXISTS btree_gist`; sin `-x` usa desarrollo aun con `TEST_DATABASE_URL` insegura | `env.py` quedó con 4 líneas en `_obtener_url` |

Comprobación manual por CLI (contenedor `api`, `--no-deps`, modo `--sql`: no abre conexiones):

```
alembic -x target=test upgrade head --sql   (con -e TEST_DATABASE_URL = URL de desarrollo)
  -> ValueError: TEST_DATABASE_URL apunta al mismo host, puerto y base que DATABASE_URL ...   rc=1
alembic -x target=prod upgrade head --sql
  -> ValueError: destino de migracion no admitido (-x target=...): los valores admitidos son desarrollo o test   rc=1
alembic -x target=test upgrade head --sql   (entorno real)  -> CREATE EXTENSION IF NOT EXISTS btree_gist;   rc=0
alembic upgrade head --sql                  (desarrollo)    -> CREATE EXTENSION IF NOT EXISTS btree_gist;   rc=0
alembic current                             (desarrollo, solo lectura) -> 0001 (head)   rc=0
```

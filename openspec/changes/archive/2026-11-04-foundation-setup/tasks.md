# Tareas: foundation-setup

> Referencias: requisitos y escenarios en `specs/*/spec.md` (seis capacidades); decisiones en `design.md` (F1–F8, DF-01 a DF-20, DP-01 a DP-08).
> TDD estricto donde hay comportamiento: RED (prueba que falla, ejecutada) → GREEN (código mínimo, ejecutado) → TRIANGULATE (otro caso con datos distintos) → REFACTOR (en verde tras cada paso). La evidencia por tarea se registra en `openspec/changes/foundation-setup/tdd-evidencia.md`.
> Datos ficticios únicamente (D1). No se modifican `backend/app/domain/superposicion_turnos.py` ni `backend/tests/unit/test_superposicion_turnos.py`.
> DP-01 a DP-04 resueltas por el autor el 2026-11-03 (ver `design.md`): `btree_gist` por migración inicial, `psycopg[binary]==3.3.6`, TypeScript 6.0.3 y base de pruebas separada y efímera (`db-test`).

## 1. Autorización y red de seguridad

- [x] 1.1 Pedir y registrar la autorización explícita del autor para descargar imágenes de Docker e instalar dependencias de PyPI y npm dentro de los contenedores; verificar: autorización registrada en la conversación de Apply antes de 4.3. (Autorización concedida por el autor en el mensaje de Apply del 2026-11-03.)
- [x] 1.2 Red de seguridad: ejecutar `python -m pytest -v -p no:cacheprovider` desde `backend/` con el venv existente; verificar y anotar en `tdd-evidencia.md` la línea base "19 passed". Si alguna falla, detenerse y reportarlo como falla preexistente.
- [x] 1.3 Anotar versiones del host (`docker version`, `docker compose version`, `python --version`, `node --version`, `npm --version`, `openspec --version`) para la sección Entorno de `verify.md`; verificar que coinciden con las de `design.md` o registrar la diferencia.

## 2. Runner de pruebas (capacidad `ejecucion-de-pruebas`)

- [x] 2.1 RED: crear `scripts/tests/autoprueba.ps1` (ASCII, compatible con PowerShell 5.1) con los casos "Un paso falla" (segundo paso `cmd /c exit 3`, el tercero no debe ejecutarse, error que nombra el segundo paso) y "Todos los pasos de la secuencia pasan", que cargan `scripts/lib/Pasos.ps1`; verificar con `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/tests/autoprueba.ps1` que termina con código distinto de cero porque `Invoke-Paso` no existe.
- [x] 2.2 GREEN: implementar `Invoke-Paso -Nombre -Comando` en `scripts/lib/Pasos.ps1` revisando `$LASTEXITCODE` tras cada bloque (DF-15); verificar que la autoprueba termina con código 0.
- [x] 2.3 RED: agregar a la autoprueba el caso "Falta el archivo .env" sobre un directorio temporal sin `.env`, que espera un error con el texto que indica copiar `.env.example` a `.env`; verificar que falla.
- [x] 2.4 GREEN: implementar `Assert-RequisitosPrevios -Raiz`; verificar que la autoprueba pasa y que el directorio temporal se elimina al terminar.
- [x] 2.5 Crear `scripts/test.ps1` con `Set-StrictMode -Version Latest`, `$ErrorActionPreference = 'Stop'`, `Assert-RequisitosPrevios`, el paso 0 (autoprueba) y salida `exit 1` con el nombre del paso fallido; verificar que sin `.env` termina con código distinto de cero y el mensaje esperado, y que con `.env` termina con código 0.
- [x] 2.6 REFACTOR: revisar que ningún comando use `2>&1` y que los `.ps1` sean ASCII; verificar con la autoprueba en verde.

## 3. Higiene del repositorio (capacidad `configuracion-backend`, requisito de plantilla)

- [x] 3.1 Crear `.gitattributes` con `* text=auto eol=lf` y `*.ps1 text eol=crlf` (DF-13); verificar con `git ls-files --eol` que el índice sigue en LF y con `git status --short` que no aparecen archivos existentes modificados.
- [x] 3.2 RED: agregar a la autoprueba los escenarios ".env ignorado por Git" (`git check-ignore -q .env`) y "Plantilla completa con valores ficticios" (las ocho variables, `POSTGRES_PASSWORD=app`, sin `AUTH_*` ni `EMAIL_*`); verificar que falla porque `.env.example` no existe.
- [x] 3.3 GREEN: crear `.env.example` con los valores locales ficticios de DF-05; verificar que la autoprueba pasa.
- [x] 3.4 Crear las carpetas de DF-01 (`backend/app/{core,api,schemas,repositories,models}`, `backend/tests/{integration,isolation}`, `frontend/src/{features,shared,pages}`) con sus archivos mínimos; verificar con un listado que existen y que `backend/app/domain/` y `backend/tests/unit/` no cambiaron (`git status --short`).

## 4. Imagen del backend y regresión en contenedor

- [x] 4.1 Crear `backend/requirements.txt` con las versiones exactas del cuadro de `design.md` y extender `backend/requirements-dev.txt` a `-r requirements.txt`, `pytest==9.1.1`, `httpx==0.28.1` (sin quitar la línea de pytest); verificar con `git diff backend/requirements-dev.txt` que `pytest==9.1.1` se conserva.
- [x] 4.2 Crear `backend/Dockerfile` (DF-11) y `docker-compose.yml` con los servicios `db`, `db-test` y `api` (DF-10: `postgres:18.6-trixie`, volumen `pgdata` en `/var/lib/postgresql` para `db`; `db-test` con `tmpfs`, sin volumen con nombre ni puertos, perfil `test`; puertos en `127.0.0.1`, `healthcheck`, `env_file`, `WATCHFILES_FORCE_POLLING`, comando uvicorn con `--factory` y `--reload`, sin migraciones); verificar con `docker compose config` que la configuración resuelve sin errores.
- [x] 4.3 Construir la imagen con `docker compose build api`; verificar que la instalación termina sin compilar ruedas y registrar `docker compose run --rm --no-deps api pip freeze` para `verify.md`. Si `psycopg[binary]==3.3.6` falla, detenerse y consultar al autor (DP-02); no cambiar de versión en silencio.
- [x] 4.4 Regresión en contenedor: ejecutar `docker compose run --rm --no-deps api python -m pytest -p no:cacheprovider tests/unit -v`; verificar "19 passed", igual que la línea base de 1.2.
- [x] 4.5 RED: agregar a la autoprueba la comprobación de que `git diff --quiet f13f0ba -- backend/tests/unit/test_superposicion_turnos.py` termina con 0 (escenario "Pruebas existentes en verde"); ejecutarla y confirmar que pasa (es una verificación de no regresión, no requiere código nuevo).
- [x] 4.6 Agregar a `scripts/test.ps1` los pasos 1 (`docker compose build api`) y 2 (pytest unitario con `--no-deps`); verificar que `scripts/test.ps1` termina con código 0 y que la salida muestra las 19 pruebas.

## 5. Configuración del backend (capacidad `configuracion-backend`)

- [x] 5.1 RED: escribir `backend/tests/unit/test_config.py` con el escenario "Carga de valores válidos" usando `monkeypatch.setenv`, que importa `cargar_configuracion` desde `app.core.config`; verificar en el contenedor que falla por import inexistente.
- [x] 5.2 GREEN: implementar `Settings` y `cargar_configuracion()` (DF-05) con `database_url: SecretStr`, `app_env: Literal["local", "test"]` y `cors_allowed_origins` con `NoDecode`; verificar que la prueba pasa.
- [x] 5.3 RED/GREEN: agregar "Falta DATABASE_URL" y "APP_ENV con valor no admitido" (error que menciona la variable); verificar con pytest.
- [x] 5.4 RED/GREEN: agregar "El error no revela la contraseña" (`clave-ficticia` ausente del texto del error) y activar `hide_input_in_errors=True`; verificar que la prueba falla antes y pasa después.
- [x] 5.5 RED/GREEN: agregar "Varios orígenes separados por comas", "Comodín rechazado" y "Lista vacía rechazada"; implementar el validador de orígenes; verificar con pytest.
- [x] 5.6 RED/GREEN: agregar "TEST_DATABASE_URL opcional" (ausente: `test_database_url` es `None`; presente: se carga como `SecretStr` sin revelar la contraseña en `repr`); verificar con pytest.
- [x] 5.7 REFACTOR: revisar nombres en `snake_case` y anotaciones de tipo en funciones públicas (S1); verificar que las pruebas unitarias siguen en verde.

## 6. Base de esquemas de entrada (capacidad `validacion-entrada`)

- [x] 6.1 RED: escribir `backend/tests/unit/test_esquemas.py` con un esquema de prueba derivado de `EsquemaEntrada` (campo `nombre`) y el escenario "Campo no declarado rechazado" (`consultorio_id` extra); verificar que falla por import inexistente.
- [x] 6.2 GREEN: crear `app/schemas/base.py` con `EsquemaEntrada` y `extra="forbid"`; verificar que pasa.
- [x] 6.3 TRIANGULATE: agregar "Solo campos declarados" (`nombre` = `Consultorio Ficticio`); verificar con pytest.

## 7. Aplicación, health y CORS (capacidades `salud-api` y `configuracion-backend`)

- [x] 7.1 Verificar httpx en Python 3.14: ejecutar en el contenedor `python -c "import httpx, fastapi.testclient; print(httpx.__version__)"`; verificar que imprime `0.28.1` sin errores. Si falla, detenerse y consultar al autor.
- [x] 7.2 RED: escribir `backend/tests/unit/test_salud.py` con "Health responde ok" usando `TestClient(crear_app(settings))`; verificar que falla por import inexistente.
- [x] 7.3 GREEN: implementar `app/main.py` (`crear_app`), `app/api/salud.py` y `app/schemas/salud.py` (`RespuestaSalud`); verificar que pasa y que el cuerpo es exactamente `{"status": "ok"}`.
- [x] 7.4 TRIANGULATE: agregar "Health responde ok con la base inaccesible" (`DATABASE_URL` con `host-inexistente.invalid` y listener del evento `do_connect` de `Engine` que no debe dispararse, DF-07; con una prueba de control que demuestra que el listener detecta un intento real) y "Ruta no declarada" (404); verificar con pytest.
- [x] 7.5 RED: escribir `backend/tests/unit/test_cors.py` con "Origen permitido" y "Origen no permitido"; verificar que falla sin el middleware.
- [x] 7.6 GREEN: agregar `CORSMiddleware` con los parámetros de DF-06; verificar que ambas pruebas pasan.
- [x] 7.7 Comprobar a mano que `docker compose up -d api` arranca y que `curl -s -i http://localhost:8000/api/health` devuelve 200 con `{"status":"ok"}`, y que `docker compose logs api` no contiene `DATABASE_URL` ni la contraseña; registrar la salida para `verify.md`.

## 8. Base de datos, Alembic y `btree_gist` (capacidad `base-de-datos-local`)

- [x] 8.1 RED: escribir en `backend/tests/unit/test_database.py` el escenario "Base inaccesible" (`verificar_conexion` contra `host-inexistente.invalid` lanza error de conexión, sin `skip`) y los escenarios de la guardia ("URL de pruebas igual a la de desarrollo rechazada", "URL de pruebas ausente rechazada", "Nombre de base de pruebas no admitido", y un caso válido con `db-test`/`turnos_test`); verificar que fallan por import inexistente.
- [x] 8.2 GREEN: implementar `crear_engine`, `verificar_conexion` y `validar_url_de_pruebas` en `app/core/database.py` (DF-08, DF-04); verificar que pasan, que el error de la guardia no contiene la contraseña y que la prueba de conexión no queda omitida.
- [x] 8.3 Escribir `backend/tests/integration/conftest.py` (guardia `validar_url_de_pruebas` + motor desde `test_database_url` + `verificar_conexion` + comprobación de `current_database()`, sin `skip`) y `test_base_de_datos.py` con "Consulta trivial", "Versión mayor del servidor", "Extensión disponible en el servidor" y "La suite corre sobre la base de pruebas"; ejecutar `docker compose run --rm api python -m pytest -p no:cacheprovider tests/integration -v`. Primero con `db-test` detenida para ver el RED (fallan con error de conexión, no se omiten) y luego con `docker compose up -d --wait db-test` para el GREEN; verificar ambas salidas.
- [x] 8.4 TRIANGULATE: confirmar que "Versión mayor del servidor" falla si se compara contra 17 (cambio temporal, revertido) y pasa con 18; verificar con pytest y registrar en `tdd-evidencia.md` que estas pruebas caracterizan el entorno real.
- [x] 8.5 RED: agregar "Extensión instalada tras migrar", "Restricción de exclusión utilizable" (tabla temporal en transacción revertida, `recurso` entero y periodos `[10:00, 10:30)` y `[10:15, 10:45)` del 2026-11-02 en UTC-03:00), "El comando explícito deja la base al día" (bajar a `base` y subir a `head` con la API de Alembic sobre la base de pruebas, comparar con la última revisión) y "Sin tablas de dominio"; verificar que fallan porque Alembic no está inicializado.
- [x] 8.6 GREEN: crear `backend/alembic.ini` (sin `sqlalchemy.url`), `alembic/env.py` (URL desde `cargar_configuracion()`: `database_url`, o `test_database_url` con `-x target=test`; `target_metadata = Base.metadata`), `alembic/script.py.mako`, `app/models/base.py` (DF-09) y la migración `0001_habilitar_btree_gist` (DF-02, DP-01); ejecutar `docker compose run --rm api alembic -x target=test upgrade head` y verificar que las pruebas del paso 8.5 pasan.
- [x] 8.7 RED/GREEN: agregar a la autoprueba los escenarios "El arranque de la API no migra" (el comando del servicio `api` en `docker compose config --format json` no contiene `alembic`) y "Base de pruebas separada y efímera" (`db-test` con `tmpfs`, sin volúmenes con nombre, sin puertos publicados, perfil `test`); verificar que pasan.
- [x] 8.8 Agregar a `scripts/test.ps1` los pasos 3 (`docker compose up -d --wait db-test`), 4 (`alembic -x target=test upgrade head`) y 5 (pytest de integración); verificar que `scripts/test.ps1` termina con código 0.
- [x] 8.9 Comprobar a mano que las pruebas no tocan la base de desarrollo: con `db` levantada, ejecutar la suite de integración y verificar que la base `turnos` de desarrollo sigue sin tablas (`alembic_version` ausente); registrar la salida para `verify.md`.
- [x] 8.10 Comprobar a mano la persistencia del volumen de desarrollo: aplicar `docker compose run --rm api alembic upgrade head` sobre `db`, luego `docker compose down` (sin `-v`) y `docker compose up -d --wait db`, y `alembic current` muestra `0001`; y que `docker compose logs db` no advierte sobre el punto de montaje de PGDATA; registrar la salida para `verify.md`.
- [x] 8.11 Comprobar a mano F7 con la base detenida: `docker compose stop db`, `curl -s -i http://localhost:8000/api/health` devuelve 200; registrar la salida y volver a levantar `db`.
- [x] 8.12 RED/GREEN (corrección previa al Archive, 2026-11-04): escribir `backend/tests/unit/test_migraciones.py` con los 6 escenarios de "Migraciones de pruebas protegidas por la guardia" (función pura `resolver_url_de_migracion`; destino de desarrollo por defecto y explícito; `target=test` válido, ausente, vacío, igual a desarrollo con credenciales distintas o puerto implícito y sin sufijo `_test`; URL explícita a desarrollo, sin sufijo, válida y junto a `desarrollo`; destino desconocido; errores sin URLs ni contraseñas); verificar que fallan por import inexistente (RED) y que pasan con `app/core/migraciones.py` (GREEN).
- [x] 8.13 RED/GREEN: hacer que `alembic/env.py` solo lea sus entradas (`sqlalchemy.url`, `-x target`, `cargar_configuracion()`) y delegue en `resolver_url_de_migracion` (modos online y offline); probar `env.py` de extremo a extremo sin base con `command.upgrade(..., sql=True)`; verificar que esas pruebas fallan antes del cambio de `env.py` (RED: `RuntimeError`/sin error) y pasan después; comprobar a mano con `docker compose run --rm --no-deps api alembic ... --sql` y `alembic current` (solo lectura) que el destino de desarrollo se conserva.

## 9. Frontend (capacidad `frontend-base`)

- [x] 9.1 Crear `frontend/package.json` con versiones exactas sin `^` (cuadro de `design.md`, TypeScript según DP-03) y los scripts `dev`, `build`, `typecheck`, `test`; `frontend/Dockerfile` (DF-11); `tsconfig.json` con `strict: true` (DF-14); `vite.config.ts` con plugin React, `server.watch.usePolling`, entorno `jsdom` y `setupFiles`; `index.html`, `src/main.tsx`, `src/vite-env.d.ts` (tipo de `VITE_API_BASE_URL`) y `src/setupTests.ts`; agregar el servicio `frontend` a `docker-compose.yml` con el volumen `frontend_node_modules`; verificar con `docker compose config`.
- [x] 9.2 Generar `frontend/package-lock.json` dentro del contenedor (`docker compose run --rm --no-deps frontend npm install` con la autorización de 1.1) y construir con `docker compose build frontend` (`npm ci`); verificar con `npm ls --depth=0` en el contenedor que las versiones coinciden exactamente y que no hay advertencias de peers sin resolver; registrar la salida.
- [x] 9.3 RED: escribir `src/App.test.tsx` con "Render del encabezado" (`getByRole("heading", { level: 1 })` con texto exacto `Turnos Odontología`); verificar con `docker compose run --rm --no-deps frontend npm test` que falla porque `App` no existe.
- [x] 9.4 GREEN: crear `src/App.tsx` (componente en `PascalCase`, sin datos de pacientes ni turnos); verificar que la prueba pasa.
- [x] 9.5 TRIANGULATE: agregar "Un único encabezado principal" (`getAllByRole("heading", { level: 1 })` con longitud 1); verificar con `npm test`.
- [x] 9.6 RED/GREEN: agregar a la autoprueba el escenario "Verificación de tipos estricta" (lee `frontend/tsconfig.json` y exige `strict: true`) y ejecutar `docker compose run --rm --no-deps frontend npm run typecheck`; verificar código 0.
- [x] 9.7 Agregar a `scripts/test.ps1` los pasos de build de `frontend`, 6 (`npm run typecheck`) y 7 (`npm test`); verificar que `scripts/test.ps1` termina con código 0.

## 10. Entorno de desarrollo en Windows

- [x] 10.1 Levantar todo con `docker compose up -d --build`; verificar que `http://localhost:5173` muestra `Turnos Odontología` y que `http://localhost:8000/api/health` responde 200.
- [x] 10.2 Recarga en caliente: modificar temporalmente el texto de `App.tsx` y el de un comentario de `app/api/salud.py` y verificar en los logs (`docker compose logs frontend api`) que ambos servicios recargan; revertir los cambios y registrar la evidencia.
- [x] 10.3 Verificar con `git ls-files --eol` que los archivos nuevos quedaron en LF en el índice (y `.ps1` con `eol=crlf` en el atributo) y registrar el resultado.

## 11. Documentación

- [x] 11.1 Ampliar `README.md` según DF-18 (requisitos, `copy .env.example .env`, `docker compose up --build`, comando explícito de migraciones, `scripts/test.ps1`, estructura, reconstrucción de dependencias y borrado del volumen) conservando todo el contenido existente; verificar con `git diff README.md` que no se eliminaron líneas salvo filas de estado actualizadas a propósito, y ejecutar cada comando documentado tal como está escrito.

## 12. Verificación (integración; antes de cualquier Archive)

- [x] 12.1 Ejecutar `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1` desde la raíz; verificar código de salida 0 y que corrieron todos los pasos en orden (autoprueba, unitarias con las 19 de regresión, migraciones, integración, typecheck, Vitest).
- [x] 12.2 Comprobar el fallo de extremo a extremo: cambiar temporalmente, sin commitear, el texto esperado en `backend/tests/unit/test_salud.py`; verificar que `scripts/test.ps1` termina con código distinto de cero, nombra el paso de pruebas unitarias y no ejecuta los pasos siguientes; revertir y confirmar con `git status --short` y `git diff` que no quedó ningún cambio.
- [x] 12.3 Ejecutar `openspec validate foundation-setup --strict`; verificar código 0 y "is valid".
- [x] 12.4 Construir la tabla de trazabilidad escenario → prueba para los 38 escenarios de las seis specs (`archivo::prueba` o caso de la autoprueba); verificar que ningún escenario queda sin prueba automatizada.
- [x] 12.5 Buscar `any` en `frontend/src` (`Select-String -Path frontend/src -Pattern '\bany\b' -Recurse` o equivalente) y revisar que no haya datos reales ni logs con datos sensibles (D1, X1); registrar el resultado.
- [x] 12.6 Crear `openspec/changes/foundation-setup/verify.md` con la estructura de DF-17 (Entorno, Comandos y resultados con salida real de 12.1 y 12.3, Trazabilidad, verificaciones manuales de 7.7, 8.9, 8.10, 8.11 y 10.2, Conclusión); verificar que cumple las cuatro condiciones de O2.
- [x] 12.7 Ejecutar `git status --short` y `git diff --check`; verificar que solo aparecen los archivos del alcance de este Change, que `.env` no aparece y que `CHANGES.md` no fue modificado todavía.

## Workflow follow-up

- NO archivar si falla `openspec validate --strict`, si falla alguna suite, si algún escenario no tiene prueba automatizada o si falta la evidencia en `verify.md` (AGENTS.md O2).
- Archive (`/opsx:archive foundation-setup`) solo después de Verify exitoso y con indicación del autor; al archivar se marca C-01 `[x]` en `CHANGES.md`; C-15 sigue `[ ]`.
- Commit solo con autorización explícita del autor, sin `git add .` (G1).

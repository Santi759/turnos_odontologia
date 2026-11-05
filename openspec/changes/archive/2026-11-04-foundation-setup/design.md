# Diseño: foundation-setup

## Contexto

Motivación y alcance: ver `proposal.md`. Requisitos y escenarios: ver `specs/*/spec.md` (seis capacidades nuevas).

Estado actual observado en el repositorio (2026-11-03, rama `main`, árbol limpio):

- `backend/` contiene solo lo del recorte académico archivado `validacion-superposicion-turnos`: `app/__init__.py`, `app/domain/__init__.py`, `app/domain/superposicion_turnos.py`, `tests/unit/test_superposicion_turnos.py` (19 pruebas recolectadas con `python -m pytest --collect-only -q`), `pyproject.toml` (solo `[tool.pytest.ini_options]` con `testpaths = ["tests"]` y `pythonpath = ["."]`) y `requirements-dev.txt` (`pytest==9.1.1`). Hay un `backend/.venv` local ignorado por Git.
- No existen `frontend/`, `docker-compose.yml`, `.env.example`, `.gitattributes` ni `scripts/`.
- `.gitignore` ya ignora `.env`, `.env.*` (salvo `!.env.example`), `.venv/`, `node_modules/`, `dist/`, `.pytest_cache/`.
- Git en el host tiene `core.autocrlf=true`: el índice guarda LF (91 archivos `i/lf`) y la copia de trabajo tiene CRLF (`w/crlf`). Sin `.gitattributes`, los archivos nuevos que se monten en contenedores Linux podrían tener CRLF.
- En el host solo está Windows PowerShell 5.1 (`powershell.exe`); **no** hay PowerShell 7 (`pwsh`).
- `.atl/skill-registry.md`: no hay skills de dominio instaladas (decisión del autor en `find-skill`); este diseño no depende de ninguna.
- KB 08 propone la estructura de directorios, la estrategia de pruebas y las variables de entorno; KB 09 fija DD-10 (stack) y DD-11 (solo local, Docker Compose, sin servicios externos).

## Objetivos / No objetivos

**Objetivos de diseño:**

- Entorno local reproducible con un solo `docker compose up` y un solo comando de pruebas, en Windows 11 con Docker Desktop y WSL 2.
- Importar la aplicación sin efectos secundarios (sin leer variables ni conectar a la base al importar), para que las pruebas unitarias controlen la configuración.
- Dejar listos los puntos de extensión que usarán C-02 en adelante (`Base` declarativa de SQLAlchemy, Alembic, base de esquemas de entrada, carpeta `tests/isolation/`) sin adelantar ninguna decisión de dominio, autenticación ni aislamiento.

**No objetivos de diseño** (además de los de `proposal.md`):

- Imagen de producción, servidor estático del build del frontend o configuración de despliegue (PA-02).
- Endpoint de readiness que consulte la base (ver DF-07).
- Base de pruebas persistente o con datos de dominio (la base de pruebas de C-01 es efímera, ver DF-04).

## Decisiones adoptadas por el autor (Engram #21, aprobadas el 2026-11-03)

| Id | Decisión | Cómo se refleja en este diseño |
|---|---|---|
| F1 | Docker Desktop con backend WSL 2 | DF-10, DF-12: bind mounts desde `C:\dev`, recarga por sondeo |
| F2 | SQLAlchemy 2 + psycopg 3 síncrono; `DATABASE_URL=postgresql+psycopg://app:app@db:5432/turnos` | DF-05, DF-08; credenciales locales ficticias solo en `.env.example` |
| F3 | Python 3.14; versión de PostgreSQL fijada tras verificación | `python:3.14.10-slim-trixie`; `postgres:18.6-trixie` (cuadro de versiones) |
| F4 | pip con `requirements.txt` (ejecución) y `requirements-dev.txt` (desarrollo y pruebas, que extiende el existente y conserva `pytest==9.1.1`) | DF-16 |
| F5 | `scripts/test.ps1` como comando único (pytest unitario con las 19 de regresión + integración, y Vitest), con detención ante el primer fallo | DF-15 |
| F6 | Migraciones con comando explícito (`docker compose run --rm api alembic upgrade head`), nunca al arrancar la API; Alembic sin migraciones de dominio | DF-02, DF-09 |
| F7 | `GET /api/health` independiente de PostgreSQL; la conectividad y `btree_gist` se prueban aparte, contra PostgreSQL real (X2) | DF-07, DF-08, DF-04 |
| F8 | Repositorio en `C:\dev\turnos_odontologia`, fuera de OneDrive | Rutas de bind mount relativas a la raíz; sin dependencias de rutas absolutas |
| F9 | DP-04 (autor, 2026-11-03): las pruebas de integración NO destruyen datos de desarrollo; base de pruebas separada y efímera | DF-04, DF-10 |

## Decisiones derivadas

### DF-01. Estructura de archivos

```
turnos_odontologia/
├── .gitattributes                      # nuevo (DF-13)
├── .env.example                        # nuevo (DF-05)
├── docker-compose.yml                  # nuevo (DF-10)
├── README.md                           # se amplía conservando el contenido (DF-18)
├── scripts/
│   ├── test.ps1                        # comando único (DF-15)
│   ├── lib/Pasos.ps1                   # Invoke-Paso y requisitos previos
│   └── tests/autoprueba.ps1            # autoprueba del runner e higiene del repo
├── backend/
│   ├── Dockerfile                      # imagen de desarrollo (DF-11)
│   ├── requirements.txt                # nuevo: dependencias de ejecución
│   ├── requirements-dev.txt            # se extiende: -r requirements.txt + pytest==9.1.1 + httpx
│   ├── pyproject.toml                  # se conserva; solo se agregan opciones si hacen falta
│   ├── alembic.ini
│   ├── alembic/{env.py, script.py.mako, versions/0001_habilitar_btree_gist.py}
│   ├── app/
│   │   ├── main.py                     # crear_app(settings) (DF-07)
│   │   ├── core/{config.py, database.py}   # database.py: crear_engine, verificar_conexion, validar_url_de_pruebas
│   │   ├── api/salud.py                # router de /api/health
│   │   ├── schemas/{base.py, salud.py} # EsquemaEntrada (extra='forbid'), RespuestaSalud
│   │   ├── domain/                     # existente, sin cambios
│   │   ├── repositories/__init__.py    # vacío (punto de extensión)
│   │   └── models/{__init__.py, base.py}  # Base declarativa, sin modelos
│   └── tests/
│       ├── unit/                       # existente + test_salud.py, test_config.py, test_cors.py, test_esquemas.py, test_database.py
│       ├── integration/{conftest.py, test_base_de_datos.py, test_migraciones.py}
│       └── isolation/__init__.py       # vacío; lo usan C-03 en adelante
└── frontend/
    ├── Dockerfile
    ├── package.json, package-lock.json
    ├── tsconfig.json, vite.config.ts, index.html
    └── src/{main.tsx, App.tsx, App.test.tsx, vite-env.d.ts, setupTests.ts, features/, shared/, pages/}
```

`app/schemas/` no figura en la lista de `CHANGES.md` pero sí en KB 08 §Estructura de directorios; se incluye porque aloja la base de esquemas de entrada (capacidad `validacion-entrada`). Las carpetas vacías (`features/`, `shared/`, `pages/`, `repositories/`, `isolation/`) se versionan con un archivo mínimo (`.gitkeep` o `__init__.py`).

### DF-02. `btree_gist` en una migración de infraestructura de Alembic (DP-01 aprobado por el autor el 2026-11-03)

La primera y única migración de C-01 (`0001_habilitar_btree_gist`) ejecuta `CREATE EXTENSION IF NOT EXISTS btree_gist` en `upgrade` y `DROP EXTENSION IF EXISTS btree_gist` en `downgrade`. Habilitar una extensión no es una migración de dominio: no crea tablas ni reglas de negocio.

- Justificación: (1) la extensión queda versionada en la misma cadena de migraciones que la restricción de exclusión de C-15, que dependerá de ella (`down_revision`); (2) se aplica igual en cualquier base que reciba `alembic upgrade head` (local, una futura base de pruebas o una base futura fuera de Docker), mientras que un script de `docker-entrypoint-initdb.d` solo corre cuando el volumen está vacío y queda atado a Docker; (3) es verificable con una prueba de integración tras el comando explícito (escenario "Extensión instalada tras migrar").
- Alternativas: script de inicialización en `docker-entrypoint-initdb.d` (no corre en volúmenes existentes, no queda en el historial de Alembic); crear la extensión dentro de la propia prueba de integración (la prueba no verificaría el entorno real sino que lo modificaría).
- Consecuencia: el usuario de `DATABASE_URL` necesita privilegio para crear la extensión. En local, `POSTGRES_USER` es superusuario del contenedor; en un despliegue futuro puede no serlo (riesgo registrado).

### DF-03. Las pruebas corren dentro de contenedores

`scripts/test.ps1` ejecuta cada suite con `docker compose run --rm` sobre los servicios `api` y `frontend`, que usan las mismas imágenes y versiones que el desarrollo. Así la evidencia de Verify no depende de lo instalado en el host (Python 3.14.5 y Node 22.23.1 locales son solo una conveniencia).

- Las pruebas unitarias corren con `--no-deps`: no arrancan `db`, lo que además refuerza que el health no depende de la base.
- Las pruebas de integración reciben `TEST_DATABASE_URL` del entorno del servicio `api` (cargado desde `.env` por Docker Compose), que apunta al servicio `db-test` por la red interna de Compose (DF-04). No hay sustitutos de la base (X2).
- El venv del host (`backend/.venv`) sigue sirviendo para correr las pruebas unitarias puras con `python -m pytest tests/unit`, pero no forma parte del comando único.

### DF-04. Base de las pruebas de integración (DP-04 resuelta por el autor el 2026-11-03)

Las pruebas de integración NO usan la base de desarrollo: usan una base de pruebas separada, efímera y verificable.

- Servicio `db-test` de Docker Compose: misma imagen `postgres:18.6-trixie`, perfil `test`, datos en `tmpfs` (`/var/lib/postgresql`), sin volumen con nombre, sin puertos publicados en el host (solo accesible por la red interna de Compose), credenciales ficticias literales en el propio servicio (`app`/`app`) y base `turnos_test`. Se levanta con `docker compose up -d --wait db-test`.
- Variable `TEST_DATABASE_URL` (`postgresql+psycopg://app:app@db-test:5432/turnos_test`), declarada en `.env.example`. `Settings` la expone como `test_database_url: SecretStr | None` (opcional: la API no la usa).
- Guardia `validar_url_de_pruebas(url_pruebas, url_desarrollo)` en `app/core/database.py`: lanza error si falta la URL de pruebas, si host, puerto y nombre de base coinciden con los de `DATABASE_URL`, o si el nombre de la base de pruebas no termina en `_test`. `tests/integration/conftest.py` la invoca antes de abrir el motor; si la guardia rechaza, la suite falla (nunca `skip`). Es lógica pura y se prueba en `tests/unit/test_database.py`.
- El conftest verifica además, ya conectado, que `current_database()` es el nombre de la base de pruebas.
- Alembic: `env.py` acepta `-x target=test` y entonces usa `test_database_url`, siempre validada con la guardia (ver DF-09); sin ese argumento usa `database_url`. `scripts/test.ps1` ejecuta `alembic -x target=test upgrade head` (el comando explícito de F6, apuntado a la base de pruebas). Para desarrollo el comando documentado sigue siendo `alembic upgrade head`.
- Las pruebas de integración corren con `docker compose run --rm api python -m pytest ...`; el servicio `api` recibe `DATABASE_URL` y `TEST_DATABASE_URL` por `env_file`, pero las pruebas solo abren conexiones con la segunda.
- `db` (desarrollo, volumen `pgdata`) no participa en `scripts/test.ps1`; nada del comando único la modifica. Verificación manual: con `db` levantada, tras ejecutar la suite, la base `turnos` de desarrollo sigue sin `alembic_version` ni cambios.

La preparación de la suite obtiene el motor desde `test_database_url` y llama a `verificar_conexion(engine)` (en `app/core/database.py`), que ejecuta `SELECT 1` y deja propagar el error. Nunca usa `pytest.skip` ni `importorskip`: si la base de pruebas no está, la suite falla (capacidad `base-de-datos-local`, requisito "Las pruebas de integración fallan sin base real"). Ese comportamiento se prueba en `tests/unit/test_database.py` con `host-inexistente.invalid` y `connect_timeout` corto: es una prueba de fallo de conexión real, no una simulación de la base.

### DF-05. Configuración con pydantic-settings

`app/core/config.py` define `Settings(BaseSettings)`:

- `database_url: SecretStr` (obligatoria; además `test_database_url: SecretStr | None = None`, solo para pruebas y Alembic, DF-04; `SecretStr` evita que aparezca en `repr` o en logs, X1), `cors_allowed_origins: Annotated[list[str], NoDecode]` con un validador que separa por comas, recorta espacios y rechaza `*` y la lista vacía, y `app_env: Literal["local", "test"]`.
- `model_config = SettingsConfigDict(case_sensitive=False, hide_input_in_errors=True)`: los errores de validación nombran la variable pero no muestran el valor recibido (escenario "El error no revela la contraseña").
- `Settings` no lee archivos `.env` por sí mismo: Docker Compose inyecta las variables. Así `extra` puede quedar en el valor por defecto (`ignore`) sin efecto, porque no hay archivo que pueda traer claves extra. `Settings` no es un esquema de entrada de la API; S1 se aplica a los esquemas de entrada (DF-06).
- `cargar_configuracion() -> Settings` es la única función pública de carga. No hay instancia global al importar.
- `.env.example` contiene solo valores locales ficticios: `POSTGRES_USER=app`, `POSTGRES_PASSWORD=app`, `POSTGRES_DB=turnos`, `DATABASE_URL=postgresql+psycopg://app:app@db:5432/turnos`, `TEST_DATABASE_URL=postgresql+psycopg://app:app@db-test:5432/turnos_test`, `CORS_ALLOWED_ORIGINS=http://localhost:5173`, `APP_ENV=local`, `VITE_API_BASE_URL=http://localhost:8000`. No incluye `AUTH_*` (PA-03) ni `EMAIL_*` (D5 no aprobado) ni `DEFAULT_TIMEZONE` (lo usa C-02).
- Alternativas: `os.environ` a mano (sin validación tipada); `cors_allowed_origins` como JSON (formato incómodo en `.env` y distinto del ejemplo de KB 08).

### DF-06. Base de esquemas de entrada y CORS

- `app/schemas/base.py` define `EsquemaEntrada(BaseModel)` con `model_config = ConfigDict(extra="forbid")`. Todo esquema de entrada futuro deriva de él (S1, D5). Se prueba con un esquema de prueba definido en `tests/unit/test_esquemas.py`, con datos ficticios (`Consultorio Ficticio`). `RespuestaSalud` es un esquema de salida (`status: Literal["ok"]`).
- `crear_app` agrega `CORSMiddleware` con `allow_origins=settings.cors_allowed_origins`, `allow_methods=["GET"]`, `allow_headers=["Content-Type"]` y `allow_credentials=False`. Es el mínimo para C-01; los métodos, cabeceras y credenciales se amplían en los Changes que los necesiten (credenciales y `Authorization` dependen de PA-03, que no se resuelve aquí).

### DF-07. Fábrica de aplicación y health de liveness

`app/main.py` expone `crear_app(settings: Settings | None = None) -> FastAPI`; si no recibe configuración llama a `cargar_configuracion()`. uvicorn arranca con `--factory app.main:crear_app`, de modo que importar `app.main` no lee variables ni crea el motor. Las pruebas construyen la app con un `Settings` explícito y `TestClient` (requiere `httpx`).

El router `app/api/salud.py` declara `GET /api/health` → `RespuestaSalud(status="ok")` sin dependencias. `CHANGES.md` dice "opcionalmente chequea la DB"; por F7 no lo hace. Un endpoint de readiness con chequeo de base, si hace falta, se propone en otro Change.

La prueba "no se intentó ninguna conexión" registra un listener de SQLAlchemy sobre el evento `do_connect` de `Engine` (se dispara en cada intento de conexión, antes de contactar al servidor; el evento `connect` de `Pool` solo se dispara tras una conexión exitosa y no detectaría intentos contra un host inexistente) durante la petición y verifica que no se disparó, con una prueba de control que demuestra que el listener sí detecta un intento real; no se reemplaza ningún componente por un doble.

### DF-08. Motor de SQLAlchemy perezoso

`app/core/database.py` ofrece `crear_engine(settings) -> Engine` (`create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})`) y `verificar_conexion(engine) -> None`. `create_engine` no conecta hasta el primer uso. En C-01 ningún endpoint usa sesiones; la fábrica de sesiones por petición se agrega cuando exista el primer repositorio (C-02).

### DF-09. Alembic

- `backend/alembic.ini` sin `sqlalchemy.url` (no hay credenciales en archivos versionados); `alembic/env.py` obtiene la URL con `cargar_configuracion().database_url.get_secret_value()` y usa `target_metadata = Base.metadata`.
- `app/models/base.py` define `Base(DeclarativeBase)` con una `MetaData(naming_convention=...)` para nombres de restricciones estables en futuras autogeneraciones. Sin modelos.
- Selección de la URL (corregida el 2026-11-04, antes del Archive): `env.py` solo lee sus entradas (`sqlalchemy.url`, `-x target`, `cargar_configuracion()`) y delega en la función pura `resolver_url_de_migracion(settings, destino, url_explicita)` de `app/core/migraciones.py`, en modo online y offline. Sin `-x target` (o `target=desarrollo`) y sin URL explícita → `database_url` (comando de desarrollo documentado, sin validar `TEST_DATABASE_URL`). `target=test` → `test_database_url` tras pasar `validar_url_de_pruebas`. Una `sqlalchemy.url` explícita (la fijan las pruebas de migraciones con la API de Alembic) se trata siempre como destino de pruebas y también pasa por la guardia; junto a `target=desarrollo` es ambigua y se rechaza; cualquier otro valor de `target` se rechaza listando los admitidos. Causa de la corrección: la versión inicial tomaba `TEST_DATABASE_URL` y la URL explícita sin la guardia. Los errores nunca incluyen URLs ni credenciales (X1). Las ejecuciones de pruebas y migraciones de prueba con `docker compose run` usan `--no-deps` para no arrancar `db` (desarrollo).
- Revisiones con identificadores legibles (`0001`) y nombre de archivo descriptivo.
- Comando explícito documentado en README: `docker compose run --rm api alembic upgrade head` (o `docker compose exec api alembic upgrade head` con la API levantada).

### DF-10. Docker Compose

| Servicio | Imagen | Puertos (host) | Volúmenes | Comando |
|---|---|---|---|---|
| `db` | `postgres:18.6-trixie` | `127.0.0.1:5432:5432` | volumen con nombre `pgdata` en `/var/lib/postgresql` | por defecto de la imagen |
| `api` | build de `backend/Dockerfile` | `127.0.0.1:8000:8000` | bind `./backend:/app` | `uvicorn --factory app.main:crear_app --host 0.0.0.0 --port 8000 --reload` |
| `db-test` | `postgres:18.6-trixie` | ninguno | `tmpfs` en `/var/lib/postgresql` (sin volumen con nombre); perfil `test` | por defecto de la imagen |
| `frontend` | build de `frontend/Dockerfile` | `127.0.0.1:5173:5173` | bind `./frontend:/app` + volumen `frontend_node_modules:/app/node_modules` | `npm run dev -- --host 0.0.0.0 --port 5173` |

- `api` usa `env_file: .env` (de ahí toma `DATABASE_URL`, `CORS_ALLOWED_ORIGINS` y `APP_ENV`) más `WATCHFILES_FORCE_POLLING=true` en `environment`; `frontend` recibe solo `VITE_API_BASE_URL` (por `environment` con interpolación desde `.env`, para no pasarle las credenciales de la base).
- `db` usa `env_file: .env` (solo lee `POSTGRES_*`) y un `healthcheck` con `pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"`. `api` depende de `db` con `condition: service_healthy` (la dependencia se omite en el paso unitario con `--no-deps`).
- `db-test` define `POSTGRES_USER=app`, `POSTGRES_PASSWORD=app` y `POSTGRES_DB=turnos_test` en su propio `environment` (valores ficticios), un `healthcheck` equivalente y `profiles: ["test"]`, de modo que `docker compose up` no la arranca.
- Puertos publicados solo en `127.0.0.1`: nada queda expuesto a la red local.
- **Volumen de PostgreSQL 18**: la documentación oficial de la imagen (`https://hub.docker.com/_/postgres`, consultada el 2026-11-03) indica que "the `PGDATA` environment variable of the image was changed to be version specific in PostgreSQL 18 and above" (para 18: `/var/lib/postgresql/18/docker`) y que "the defined `VOLUME` was changed in 18 and above to `/var/lib/postgresql`. Mounts and volumes should be targeted at the updated location". Por eso el volumen se monta en `/var/lib/postgresql` y **no** en `/var/lib/postgresql/data` como en 17 o anteriores. Es un volumen local con datos ficticios únicamente; `docker compose down -v` lo borra.
- La imagen oficial incluye los módulos contrib, entre ellos `btree_gist` (se verifica con el escenario "Extensión disponible en el servidor").

### DF-11. Imágenes de desarrollo

- `backend/Dockerfile`: `FROM python:3.14.10-slim-trixie`, `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`, `WORKDIR /app`, copia `requirements*.txt` y ejecuta `pip install --no-cache-dir -r requirements-dev.txt`. Una sola imagen de desarrollo (no hay imagen de producción, PA-02). `PYTHONDONTWRITEBYTECODE` evita que el contenedor escriba `__pycache__` en el bind mount; pytest corre con `-p no:cacheprovider` por el mismo motivo.
- `frontend/Dockerfile`: `FROM node:22.23.1-trixie-slim`, `WORKDIR /app`, copia `package.json` y `package-lock.json` y ejecuta `npm ci`. El volumen `frontend_node_modules` se inicializa con el `node_modules` de la imagen la primera vez. Si cambian las dependencias: `docker compose build frontend` y `docker compose run --rm frontend npm ci` (documentado en README).

### DF-12. Recarga en caliente desde Windows

Los eventos de `inotify` no se propagan de forma fiable desde un bind mount de Windows (`C:\dev`) a un contenedor en WSL 2. Por eso:

- `api`: `WATCHFILES_FORCE_POLLING=true` en el entorno del servicio, porque `uvicorn --reload` usa `watchfiles` (incluido en `uvicorn[standard]`).
- `frontend`: `server.watch.usePolling: true` en `vite.config.ts` (no depende de `process.env`, así no hace falta `@types/node`).
- `node_modules` vive en un volumen de contenedor, no en el bind mount: evita mezclar binarios de Windows y Linux y mejora el rendimiento.
- Verificación manual en Apply (no es un escenario de spec): editar `App.tsx` y `app/api/salud.py` y comprobar que el cambio se recarga.

### DF-13. `.gitattributes`

```
* text=auto eol=lf
*.ps1 text eol=crlf
```

- `eol=lf` para todo: los archivos montados en contenedores Linux (Python, Dockerfile, `.env`, scripts, configuración) deben tener LF aunque el host use `core.autocrlf=true`.
- `*.ps1 eol=crlf`: los scripts de PowerShell se ejecutan solo en el host Windows con PowerShell 5.1; CRLF es su final de línea nativo y evita diferencias en editores de Windows. Ningún `.ps1` se ejecuta en un contenedor.
- Como el índice ya guarda LF, agregar `.gitattributes` no genera cambios de contenido en archivos versionados. La copia de trabajo de los archivos existentes puede seguir con CRLF hasta que se vuelvan a extraer; Python tolera CRLF. No se reescribe historial ni se usan comandos destructivos (G1); en Apply se verifica con `git ls-files --eol` y `git status --short`.

### DF-14. Frontend

- Vite + React + TypeScript. `tsconfig.json` único con `strict: true`, `noEmit: true`, `jsx: "react-jsx"`, `module: "ESNext"`, `moduleResolution: "bundler"`, `target: "ES2022"`, `types: ["vite/client"]`, que incluye `src` y `vite.config.ts`.
- Scripts de `package.json`: `dev` (`vite`), `build` (`vite build`), `typecheck` (`tsc --noEmit -p tsconfig.json`), `test` (`vitest run`).
- `vite.config.ts` con `defineConfig` de `vitest/config`: plugin React, `server.watch.usePolling`, `test.environment: "jsdom"`, `test.setupFiles: ["./src/setupTests.ts"]` (que importa `@testing-library/jest-dom/vitest`).
- `App.tsx` renderiza un `<h1>Turnos Odontología</h1>` y un texto estático; `App.test.tsx` usa `render` y `screen.getByRole("heading", { level: 1 })`.
- `VITE_API_BASE_URL` se declara en `.env.example` y se tipa en `vite-env.d.ts`, pero C-01 no incluye cliente HTTP (lo agrega el primer Change con pantallas que consuman la API). Se elige URL directa más CORS en lugar de un proxy de Vite porque coincide con KB 08 §Variables de entorno y ejercita la política CORS real.
- Sin `any` (S2). Sin linter en C-01 (decisión pendiente): en Verify se busca `any` en `frontend/src` con `Select-String` y se registra el resultado.

### DF-15. `scripts/test.ps1`

Compatible con Windows PowerShell 5.1 (el host no tiene `pwsh`):

- `Set-StrictMode -Version Latest` y `$ErrorActionPreference = 'Stop'`. En 5.1, `Stop` **no** detiene ante un código de salida distinto de cero de un comando nativo, así que cada paso pasa por `Invoke-Paso -Nombre <texto> -Comando <scriptblock>`, que ejecuta el bloque, revisa `$LASTEXITCODE` y lanza un error con el nombre del paso si es distinto de cero. Un `trap`/`try` final imprime el paso fallido y termina con `exit 1`.
- No se redirige `2>&1` en los comandos de Docker: en 5.1, con `Stop`, la salida de error redirigida de un comando nativo (Docker escribe el progreso por stderr) se convierte en una excepción aunque el comando termine bien.
- Contenido ASCII únicamente (sin tildes) para evitar problemas de codificación de 5.1 con archivos UTF-8 sin BOM.
- `Assert-RequisitosPrevios -Raiz <ruta>` verifica que exista `.env` y, si no, lanza un error que indica copiar `.env.example` a `.env`, antes de cualquier suite.
- Pasos, en orden:
  0. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/tests/autoprueba.ps1` (runner e higiene).
  1. `docker compose build api frontend`.
  2. `docker compose run --rm --no-deps api python -m pytest -p no:cacheprovider tests/unit -v`.
  3. `docker compose up -d --wait db-test`.
  4. `docker compose run --rm api alembic -x target=test upgrade head` (el comando explícito de F6, apuntado a la base de pruebas).
  5. `docker compose run --rm api python -m pytest -p no:cacheprovider tests/integration -v`.
  6. `docker compose run --rm --no-deps frontend npm run typecheck`.
  7. `docker compose run --rm --no-deps frontend npm test`.
- `tests/isolation/` no se ejecuta como paso propio en C-01 porque está vacía (pytest terminaría con código 5); el primer Change que agregue pruebas de aislamiento agrega su paso.
- `scripts/tests/autoprueba.ps1` (sin frameworks, solo PowerShell) cubre: los escenarios de `Invoke-Paso` (secuencia con un paso que termina con `cmd /c exit 3` y otra que pasa), `Assert-RequisitosPrevios` sobre un directorio temporal sin `.env`, `git check-ignore -q .env`, el contenido de `.env.example`, que el comando del servicio `api` en `docker compose config --format json` no contenga `alembic`, que `db-test` use `tmpfs`, no tenga volúmenes con nombre ni puertos publicados, que `frontend/tsconfig.json` tenga `strict: true` y que `git diff --quiet f13f0ba -- backend/tests/unit/test_superposicion_turnos.py` termine con 0. Termina con código distinto de cero si alguna verificación falla.
- Alternativas: Pester (la versión incluida en Windows es la 3.4, antigua, y agregar otra es instalar una dependencia); un `Makefile` (no hay `make` en el host); ejecutar desde el host con venv y npm locales (menos reproducible).

### DF-16. Política de versiones

- Python: versiones exactas con `==` en `requirements.txt` (dependencias directas, más `starlette` fijado explícitamente porque FastAPI 0.162.0 declara `starlette>=0.46.0` sin cota superior). `requirements-dev.txt` queda como `-r requirements.txt`, `pytest==9.1.1`, `httpx==0.28.1`.
- npm: versiones exactas sin `^` ni `~` en `package.json` y `package-lock.json` versionado; se instala con `npm ci` en la imagen.
- Imágenes con etiqueta completa (`python:3.14.10-slim-trixie`, `postgres:18.6-trixie`, `node:22.23.1-trixie-slim`), todas sobre Debian trixie.

### DF-17. Evidencia para Verify (O2)

Siguiendo el Change archivado, en Apply se mantiene `tdd-evidencia.md` (tabla RED/GREEN/TRIANGULATE/REFACTOR por tarea) y en Verify se crea `verify.md` dentro de `openspec/changes/foundation-setup/` con: entorno (versiones de Docker, imágenes y paquetes instalados realmente, salida de `pip freeze` y `npm ls --depth=0` dentro de los contenedores), comandos ejecutados con salida y código de salida (`openspec validate foundation-setup --strict`, `scripts/test.ps1`), trazabilidad escenario → prueba para todos los escenarios de las seis specs, verificaciones manuales (recarga en caliente, health con `db` detenida vía `curl`, persistencia del volumen) y conclusión. Si alguna condición falla, no se archiva.

### DF-18. README

Se agregan secciones nuevas (requisitos de Docker Desktop, `copy .env.example .env`, `docker compose up --build`, comando explícito de migraciones, `scripts/test.ps1`, estructura de `backend/` y `frontend/`, cómo reconstruir dependencias, cómo borrar el volumen local) y se actualizan solo las filas de estado que cambien tras el archivo. Todo el contenido existente se conserva, incluida la sección de ejecución en PowerShell del Change académico.

### DF-19. `uvicorn[standard]`

Se usa `uvicorn[standard]==0.54.0` porque aporta `watchfiles` para `--reload` con sondeo (DF-12). Se verificó que todas sus dependencias opcionales tienen ruedas cp314 para Linux x86_64 (evidencia abajo).

### DF-20. TypeScript 6.0.3 en lugar de 7.0.2 (DP-03 aprobado por el autor el 2026-11-03)

TypeScript 7.0.2 (`latest` en npm) es la reescritura nativa: su paquete exporta solo `./lib/version.cjs` y APIs `./unstable/*`, sin la API clásica de compilador en JavaScript. Vite 8, `@vitejs/plugin-react` 6 y Vitest 5 no la necesitan para transpilar, pero el ecosistema de herramientas que sí la usa todavía no la admite: `typescript-eslint@8.72.1` declara `typescript: ">=4.8.4 <6.1.0"`. Se elige **TypeScript 6.0.3** (última 6.x, publicada el 2026-04-16), que conserva la API clásica y deja abierta la incorporación de un linter sin cambiar de versión. El autor aprobó 6.0.3 el 2026-11-03, a condición de confirmar la compatibilidad ejecutando `typecheck`, `build` y Vitest en Apply. Las peerDependencies de vite 8.3.5, vitest 5.1.0, plugin-react 6.2.1, Testing Library y jsdom 30.1.3 se reverificaron el 2026-11-03: ninguna declara peer de `typescript`.

## Cuadro de versiones exactas

| Componente | Versión | Fuente de verificación |
|---|---|---|
| Docker / Docker Compose (host) | 29.9.2 / v5.6.1 | verificado por el orquestador |
| Imagen API | `python:3.14.10-slim-trixie` | `docker manifest inspect` (orquestador) |
| Imagen base de datos | `postgres:18.6-trixie` | `docker manifest inspect` (orquestador) |
| Imagen frontend | `node:22.23.1-trixie-slim` | `docker manifest inspect` (orquestador) |
| fastapi | 0.162.0 | PyPI |
| starlette | 1.10.0 | PyPI |
| uvicorn[standard] | 0.54.0 | PyPI |
| sqlalchemy | 2.1.6 | PyPI |
| alembic | 1.20.1 | PyPI |
| pydantic | 2.14.2 (fija `pydantic-core==2.50.2`) | PyPI |
| pydantic-settings | 2.16.2 | PyPI |
| psycopg[binary] | 3.3.6 (DP-02, aprobado 2026-11-03) | PyPI (publicada el 2026-09-18; `requires_python >=3.10`; `psycopg-binary` con rueda `cp314` manylinux x86_64 y win_amd64) |
| pytest | 9.1.1 (se conserva) | `requirements-dev.txt` existente |
| httpx | 0.28.1 | PyPI (verificar en 3.14 en Apply) |
| react / react-dom | 19.3.1 / 19.3.1 | npm |
| vite | 8.3.5 | npm |
| @vitejs/plugin-react | 6.2.1 | npm |
| typescript | **6.0.3** (desvío, DF-20) | npm |
| vitest | 5.1.0 | npm |
| jsdom | 30.1.3 | npm |
| @testing-library/react | 16.3.3 | npm |
| @testing-library/dom | 10.4.2 | npm (peer obligatorio de Testing Library) |
| @testing-library/jest-dom | 7.0.1 | npm |
| @types/react / @types/react-dom | 19.3.0 / 19.3.0 | npm |

## Evidencia de compatibilidad (2026-11-03, solo metadatos; sin instalar nada)

Comandos de solo lectura ejecutados desde el directorio temporal de la sesión:

1. `npm view <paquete>@<versión> peerDependencies peerDependenciesMeta engines --json`:
   - `vitest@5.1.0`: peer `vite: "^6.4.0 || ^7.0.0 || ^8.0.0"` (obligatorio), `jsdom: "*"` (opcional); engines `node: "^22.12.0 || ^24.0.0 || >=26.0.0"` → compatible con vite 8.3.5, jsdom 30.1.3 y Node 22.23.1.
   - `@vitejs/plugin-react@6.2.1`: peer `vite: "^8.0.0"`; engines `node: "^20.19.0 || >=22.12.0"` → compatible.
   - `vite@8.3.5`: engines `node: "^20.19.0 || >=22.12.0"`; no tiene peer de TypeScript → compatible con Node 22.23.1 y con TypeScript 6.
   - `@testing-library/react@16.3.3`: peers `react` y `react-dom` `"^18.0.0 || ^19.0.0"`, `@types/react` y `@types/react-dom` `"^18.0.0 || ^19.0.0"`, `@testing-library/dom: "^10.0.0"` (obligatorio) → se agrega `@testing-library/dom@10.4.2` (última, `engines.node >=18`).
   - `@testing-library/jest-dom@7.0.1`: peers `vitest: ">= 0.32"` (opcional) y `@testing-library/dom: ">=10 <11"`; engines `node >=22` → compatible con vitest 5.1.0 y dom 10.4.2.
   - `jsdom@30.1.3`: engines `node: "^22.22.2 || ^24.15.0 || >=26.0.0"` → Node 22.23.1 cumple; por eso la imagen del frontend fija `node:22.23.1` y no una 22 anterior a 22.22.2.
   - `react-dom@19.3.1`: peer `react: "^19.3.1"`; `@types/react-dom@19.3.0`: peer `@types/react: "^19.3.0"` → compatibles.
   - `typescript@7.0.2`: `exports` solo con `./lib/version.cjs` y `./unstable/*`; `typescript-eslint@8.72.1` peer `typescript: ">=4.8.4 <6.1.0"` → motivo de DF-20. `typescript@6.0.3`: engines `node >=14.17`.
2. Script `python -I pypi_check.py` (urllib sobre `https://pypi.org/pypi/<paquete>/<versión>/json`):
   - `fastapi 0.162.0`: `requires_python >=3.10`, clasificador 3.14, requiere `starlette>=0.46.0`, `pydantic>=2.9.0`, `typing-inspection`, `annotated-doc`, `opentelemetry-api>=1.44.0` → compatible con starlette 1.10.0 y pydantic 2.14.2.
   - `starlette 1.10.0` (`>=3.11`), `sqlalchemy 2.1.6` (`>=3.11`, rueda `cp314` manylinux x86_64), `alembic 1.20.1` (`SQLAlchemy>=2.0`), `pydantic 2.14.2` (fija `pydantic-core==2.50.2`, con rueda `cp314` manylinux x86_64), `pydantic-settings 2.16.2` (`pydantic>=2.7.0`), `psycopg 3.3.6` y `psycopg-binary 3.3.6` (rueda `cp314` manylinux x86_64 y win_amd64; reverificado el 2026-11-03 con `python -I`: `requires_python >=3.10`, clasificador 3.14), `uvicorn 0.54.0`, `pytest 9.1.1`: todos declaran el clasificador de Python 3.14.
   - Extras de `uvicorn[standard]`: `uvloop 0.23.0`, `httptools 0.9.0`, `watchfiles 1.3.0`, `websockets 17.4`, `pyyaml 6.0.3` con ruedas `cp314` manylinux x86_64; `python-dotenv 1.2.4` puro → instalables en `python:3.14.10-slim-trixie` sin compilar.
   - `httpx 0.28.1`: puro Python, `requires_python >=3.8`, **sin** clasificador 3.14 → tarea de verificación en tiempo de ejecución en Apply.
   - `psycopg 3.3.x` publicadas: 3.3.6 (2026-09-18) y 3.3.7 (2026-11-03, el mismo día de esta propuesta).
3. Documentación de la imagen `postgres` en Docker Hub (consulta web de solo lectura, 2026-11-03): cambio de `PGDATA` y de `VOLUME` en 18+, citado en DF-10.

La compatibilidad real (instalación y ejecución) se confirma en Apply y se registra en `verify.md`.

## Riesgos / Trade-offs

- [psycopg 3.3.6 podría no instalarse o fallar en Python 3.14] → el autor aprobó 3.3.6 (DP-02) siempre que se compruebe la compatibilidad; si falla la instalación en el contenedor, detenerse y consultar; no cambiar de versión en silencio.
- [httpx 0.28.1 no declara Python 3.14] → tarea explícita en Apply que ejecuta `TestClient` en el contenedor; si falla, detenerse y consultar al autor.
- [FastAPI 0.162 con Starlette 1.x podría tener incompatibilidades no declaradas] → `starlette` fijado; las pruebas unitarias de health y CORS lo ejercitan.
- [El usuario de la base debe poder crear extensiones; en un despliegue futuro puede no ser superusuario] → documentado; se revisa cuando se decida PA-02.
- [Las pruebas de integración destruyan datos de desarrollo] → base `db-test` separada y efímera (tmpfs, sin volumen con nombre), nombre `turnos_test`, y guardia que rechaza ejecutar si la URL de pruebas coincide con la de desarrollo (DF-04).
- [Sondeo de archivos consume CPU] → aceptado en desarrollo local; intervalos por defecto.
- [Volumen `frontend_node_modules` desactualizado tras cambiar dependencias] → procedimiento de reconstrucción en README.
- [Archivos existentes con CRLF en la copia de trabajo montados en contenedores] → Python y Node toleran CRLF; los archivos nuevos se crean con LF por `.gitattributes`; no hay scripts de shell montados.
- [Diferencias de PowerShell 5.1 con comandos nativos] → `Invoke-Paso` con `$LASTEXITCODE`, sin `2>&1`, contenido ASCII; cubierto por la autoprueba.
- [El volumen de PostgreSQL 18 montado en la ruta de 17] → montado en `/var/lib/postgresql` según la documentación oficial; verificación manual de persistencia en Verify.
- [Confundir C-01 con el Change académico o con C-15] → `proposal.md` lo aclara; al archivar solo se marca C-01.

## Plan de migración

No hay datos ni despliegue. Revertir C-01 equivale a: `docker compose down -v` (borra contenedores y volúmenes locales con datos ficticios) y eliminar los archivos nuevos; los archivos extendidos (`requirements-dev.txt`, `pyproject.toml`, `README.md`) se restauran desde Git sin reescribir historial. La migración `0001` tiene `downgrade` que elimina la extensión.

## Decisiones pendientes para el autor

Ninguna resuelve una pregunta abierta de la KB (PA-xx, P-xx, NE-xx), que siguen abiertas (D6).

| Id | Decisión | Propuesta del diseño | Estado |
|---|---|---|---|
| DP-01 | Dónde se habilita `btree_gist` | Migración de infraestructura `0001` de Alembic (DF-02), sin modelos ni tablas de dominio | **Resuelta**: aprobada por el autor el 2026-11-03 |
| DP-02 | Versión de psycopg | `psycopg[binary]==3.3.6`, con compatibilidad verificada (metadatos de PyPI el 2026-11-03; instalación real en el contenedor en Apply) | **Resuelta**: el autor eligió 3.3.6 (no 3.3.7) el 2026-11-03; si no es compatible, detenerse |
| DP-03 | Versión de TypeScript | 6.0.3 (DF-20) | **Resuelta**: aprobada por el autor el 2026-11-03, sujeta a confirmar compatibilidad ejecutando typecheck, build y Vitest |
| DP-04 | Base de datos dedicada a pruebas de integración | `db-test` efímera + `TEST_DATABASE_URL` + guardia (DF-04) | **Resuelta**: el autor decidió el 2026-11-03 que las pruebas no destruyan datos de desarrollo |
| DP-05 | Linter y formateador (ESLint + typescript-eslint, ruff) | Fuera de C-01; control manual de `any` en Verify | Pendiente |
| DP-06 | Fijar dependencias transitivas de Python (archivo de restricciones o lock) | Solo dependencias directas + `starlette`; se registra `pip freeze` en `verify.md` | Pendiente |
| DP-07 | Credenciales y cabeceras de CORS (`allow_credentials`, `Authorization`) | Desactivadas en C-01 | Pendiente: depende de PA-03 |
| DP-08 | Endpoint de readiness con chequeo de base | No se implementa (F7) | Pendiente para un Change futuro |

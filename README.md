# turnos_odontologia

SaaS multi-consultorio de gestión de turnos odontológicos para Argentina. Es un MVP académico (v0.1) del trabajo práctico de **Metodología I**.

- **Autor:** Santiago Chepilla (único integrante)
- **Estado para el TPI (2026-11-17):**
  - fundación metodológica completa;
  - **cinco Changes implementados, verificados y archivados**: el Change académico `validacion-superposicion-turnos` y C-01 a C-04 (infraestructura, modelo base, autenticación y aislamiento entre consultorios);
  - hay un backend FastAPI con PostgreSQL y Docker Compose, inicio de sesión y aislamiento por consultorio con RLS y roles;
  - **todavía no hay gestión de turnos por API ni frontend funcional**: el resto del roadmap está planificado, no implementado.

> ⚠️ **Datos ficticios únicamente.** Todo el desarrollo, las pruebas, los ejemplos y la documentación de este repositorio usan datos inventados (por ejemplo, `PROF-A`, "Consultorio Demo A", emails `@example.test`). Nunca se cargan datos reales de pacientes, profesionales ni consultorios (DD-13, RN-PA-08). Tampoco se incluyen datos clínicos.

---

## Índice

1. [Problema que busca resolver](#problema-que-busca-resolver)
2. [Contexto académico y metodología](#contexto-académico-y-metodología)
3. [Estado real del proyecto](#estado-real-del-proyecto)
4. [Stack tecnológico](#stack-tecnológico)
5. [Estructura del repositorio](#estructura-del-repositorio)
6. [Documentos y evidencias](#documentos-y-evidencias)
7. [Puesta en marcha con Docker Compose](#puesta-en-marcha-con-docker-compose)
8. [API disponible y Swagger](#api-disponible-y-swagger)
9. [Pruebas](#pruebas)
10. [Seguridad: autenticación y aislamiento (C-03 y C-04)](#seguridad-autenticación-y-aislamiento-c-03-y-c-04)
11. [Skill propia: `verificar-aislamiento-consultorios`](#skill-propia-verificar-aislamiento-consultorios)
12. [MCP utilizado: Context7](#mcp-utilizado-context7)
13. [Demostración para el TPI](#demostración-para-el-tpi)
14. [Change académico: `validacion-superposicion-turnos` (Parcial 2)](#change-académico-validacion-superposicion-turnos-parcial-2)
15. [Roadmap: completo y pendiente](#roadmap-completo-y-pendiente)
16. [Datos ficticios](#datos-ficticios)

---

## Problema que busca resolver

El objetivo es **evitar errores y superposiciones de turnos en consultorios odontológicos**, con una agenda que respete:

- la duración de cada prestación;
- la disponibilidad de cada profesional;
- los períodos bloqueados.

Un problema secundario es el tiempo que se pierde coordinando citas.

El problema es un **planteo del autor**:

- No está cuantificado para Argentina.
- No se validó con entrevistas a consultorios. Figura como pregunta abierta en el Discovery.
- En el estudio de mercado de 18 sistemas, muy pocos documentan públicamente el control de la duración por prestación o la imposibilidad de superponer turnos. Esto es una interpretación de la evidencia pública, no una prueba de que el problema no esté resuelto.

Detalle: [`knowledge-base/01_vision_y_objetivos.md`](knowledge-base/01_vision_y_objetivos.md).

---

## Contexto académico y metodología

El proyecto es el trabajo práctico de Metodología I y lo desarrolla una sola persona. Tuvo dos entregas:

- **Parcial 2 (octubre de 2026):** la consigna pedía **un Change funcional pequeño**, con una regla de negocio verificable, al menos tres escenarios (exitoso, error de negocio y caso límite) e implementación como módulo de dominio o API, sin interfaz gráfica. Se entregó el Change académico `validacion-superposicion-turnos` (ver [su sección](#change-académico-validacion-superposicion-turnos-parcial-2)).
- **TPI (entrega del 18 de noviembre de 2026):** pide **al menos dos Changes relevantes, completos, verificados y archivados**. Además se documentan una skill propia creada con `skill-creator` y el uso real de un servidor MCP. Para el TPI se presentan C-03 y C-04 como Changes funcionales principales, junto con el Change académico; C-01 y C-02 son la base técnica.

La metodología combina cuatro enfoques:

| Enfoque | Qué aportó | Resultado en el repositorio |
|---|---|---|
| **Discovery** | Investigación del problema, los usuarios, las reglas de negocio y el mercado (18 sistemas evaluados con una rúbrica de 7 criterios), antes de escribir requisitos | `discovery/`, `docs/discovery/` |
| **Active Stack** | Flujo de fundación guiado por etapas, con un punto de control del autor en cada una: Discovery → Knowledge Base → roadmap → skills → instrucciones para agentes | `.active-orchestrator-state.json` (estado `done`) |
| **Spec-Driven Development** | Cada funcionalidad se especifica antes de implementarse, con requisitos y escenarios DADO / CUANDO / ENTONCES. La implementación sigue TDD estricto: primero una prueba que falla, después el código mínimo para que pase, más casos y refactorización | `openspec/specs/`, `backend/tests/` |
| **OpenSpec** (CLI 1.14.1) | Gestiona el ciclo de cada Change: Explore → Propose → Apply → Verify → Archive | `openspec/` |

Las decisiones del autor quedaron registradas con fecha en cada etapa. Las preguntas que siguen abiertas no se resuelven sin el autor.

---

## Estado real del proyecto

### Changes archivados

| Change | Qué aporta | Archivado | Tareas | Verificación |
|---|---|---|---|---|
| `validacion-superposicion-turnos` (Change académico, Parcial 2) | Regla de dominio: un profesional no puede tener dos turnos superpuestos | 2026-10-14 | 31/31 | [`verify.md`](openspec/changes/archive/2026-10-14-validacion-superposicion-turnos/verify.md) |
| C-01 `foundation-setup` | Docker Compose, PostgreSQL con `btree_gist`, FastAPI, Alembic, frontend base y runner de pruebas | 2026-11-04 | 67/67 | [`verify.md`](openspec/changes/archive/2026-11-04-foundation-setup/verify.md) |
| C-02 `modelo-base-consultorios-seed` | Tablas `consultorio` y `usuario`, repositorios acotados por consultorio y seed ficticio | 2026-11-04 | 34/34 | [`verify.md`](openspec/changes/archive/2026-11-04-modelo-base-consultorios-seed/verify.md) |
| C-03 `autenticacion-sesion` | Inicio y cierre de sesión con cookie, CSRF, límite de intentos y credenciales locales | 2026-11-09 | 57/57 | [`verify.md`](openspec/changes/archive/2026-11-09-autenticacion-sesion/verify.md) |
| C-04 `aislamiento-roles-rbac` | Roles de PostgreSQL con privilegios mínimos, RLS forzada, contexto por transacción y autorización por rol; revisión de seguridad RT3 con GO final | 2026-11-16 | 114/114 | [`verify.md`](openspec/changes/archive/2026-11-16-aislamiento-roles-rbac/verify.md) |

Hay 19 especificaciones vigentes en [`openspec/specs/`](openspec/specs/) y no queda ningún Change activo.

### Qué existe hoy

- **Backend FastAPI** con `GET /api/health` y la API de sesión (`POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`). Swagger está disponible solo en desarrollo local.
- **PostgreSQL 18 y Docker Compose**: servicios `db`, `api`, `frontend`, `admin` (comandos administrativos) y `db-test` (base de pruebas efímera).
- **Modelo base**: consultorios y usuarios con tres roles (`administrador`, `secretaria`, `odontologo`), sesiones e intentos de login. Hay un seed con dos consultorios de demostración.
- **Autenticación (C-03)**: contraseñas con Argon2id, cookie de sesión `HttpOnly`, token CSRF, verificación de `Origin`, límite de intentos y un comando local para asignar credenciales.
- **Aislamiento entre consultorios (C-04)**:
  - cuatro roles de PostgreSQL con privilegios mínimos;
  - RLS habilitada y forzada en las tablas con datos de consultorio;
  - contexto de consultorio por transacción;
  - el consultorio nunca se toma de lo que envía el cliente;
  - autorización por rol (`require_rol`);
  - separación de credenciales entre la API y la administración.
- **Regla de superposición de turnos**: función pura de dominio (Change académico).
- **Frontend React + Vite + TypeScript**: solo la pantalla inicial de C-01.

### Qué todavía NO existe

- Gestión de turnos por API: no hay endpoints para crear, reprogramar ni cancelar turnos, ni para consultar la agenda o la disponibilidad. La regla de superposición existe solo como función de dominio.
- Tabla de turnos, restricción de exclusión en PostgreSQL ni control de concurrencia (C-15).
- Profesionales, prestaciones, horarios, bloqueos y pacientes (C-07 a C-13).
- Gestión de usuarios por API (C-05).
- **Frontend funcional**: no hay pantalla de inicio de sesión (C-06) ni de gestión de turnos (C-21).
- Reserva online, notificaciones y cualquier endpoint público (candidatas, sin decisión del autor).

---

## Stack tecnológico

El stack lo decidió el autor (DD-10 en la Knowledge Base).

| Capa | Tecnología | Estado |
|---|---|---|
| API REST | FastAPI, Python 3.14 | ✅ Implementado (C-01, C-03, C-04) |
| Acceso a datos y migraciones | SQLAlchemy 2.1, Alembic (migraciones `0001` a `0004`) | ✅ Implementado |
| Validación de entradas | Pydantic (esquemas de entrada con `extra="forbid"`) | ✅ Implementado |
| Base de datos | PostgreSQL 18 con `btree_gist` | ✅ Implementado |
| Autenticación | Sesión con cookie opaca, Argon2id, CSRF y límite de intentos (PA-03 resuelta en C-03) | ✅ Implementado |
| Aislamiento | RLS de PostgreSQL y roles con privilegios mínimos (PA-04 resuelta en C-04) | ✅ Implementado |
| Pruebas del backend | pytest | ✅ Implementado |
| Frontend | React con Vite, en TypeScript | 🟡 Solo la base (C-01); sin pantallas funcionales |
| Pruebas del frontend | Vitest | 🟡 Configurado, con pruebas mínimas |
| Entorno local | Docker Compose | ✅ Implementado |
| Especificaciones | OpenSpec CLI 1.14.1 | ✅ En uso |

Detalle: [`knowledge-base/02_descripcion_general.md`](knowledge-base/02_descripcion_general.md) y [`knowledge-base/08_arquitectura_propuesta.md`](knowledge-base/08_arquitectura_propuesta.md).

---

## Estructura del repositorio

```
turnos_odontologia/
├── README.md                          este archivo
├── AGENTS.md / CLAUDE.md              instrucciones para agentes (copias idénticas)
├── CHANGES.md                         roadmap: 30 Changes con dependencias y fases
├── docker-compose.yml                 servicios db, api, admin, frontend y db-test
├── .env.example                       plantilla de configuración local (valores ficticios)
├── .active-orchestrator-state.json    estado de la fundación Active Stack
├── .atl/skill-registry.md             registro de skills (incluye la skill propia)
├── .claude/
│   ├── commands/opsx/                 comandos del flujo OpenSpec
│   └── skills/verificar-aislamiento-consultorios/   skill propia del proyecto
├── backend/
│   ├── app/                           api/, auth/, core/, models/, repositories/, schemas/,
│   │                                  domain/ (regla de superposición), seed/,
│   │                                  credenciales/, roles_postgres/, mantenimiento/
│   ├── alembic/versions/              migraciones 0001 a 0004
│   └── tests/                         unit/, integration/, isolation/
├── frontend/                          React + Vite + TypeScript (base de C-01)
├── db/test-init/                      inicialización de la base de pruebas
├── scripts/                           test.ps1 (comando único de pruebas), lib/, tests/
├── discovery/ y docs/discovery/       Discovery e informe de mercado
├── docs/evidencia-tpi/                evidencias del TPI (skill propia y MCP)
├── knowledge-base/                    Knowledge Base (README + 10 archivos)
└── openspec/
    ├── specs/                         19 especificaciones vigentes
    └── changes/archive/               5 Changes archivados
```

---

## Documentos y evidencias

| Documento | Ubicación |
|---|---|
| Discovery aprobado | [`discovery/discovery.md`](discovery/discovery.md) |
| Informe de Discovery (18 sistemas) | [`docs/discovery/informe-discovery.md`](docs/discovery/informe-discovery.md) (también en [PDF](docs/discovery/informe-discovery.pdf)) |
| Checklist y fuentes del Discovery | [`docs/discovery/checklist-discovery.md`](docs/discovery/checklist-discovery.md), [`docs/discovery/fuentes.md`](docs/discovery/fuentes.md) |
| Metodología de evaluación (rúbrica y matriz) | [`docs/discovery/metodologia/`](docs/discovery/metodologia/) |
| Knowledge Base | [`knowledge-base/README.md`](knowledge-base/README.md) (índice de los 10 archivos) |
| Reglas de negocio | [`knowledge-base/05_reglas_de_negocio.md`](knowledge-base/05_reglas_de_negocio.md) |
| Preguntas abiertas | [`knowledge-base/10_preguntas_abiertas.md`](knowledge-base/10_preguntas_abiertas.md) |
| Roadmap de Changes | [`CHANGES.md`](CHANGES.md) |
| Instrucciones para agentes | [`AGENTS.md`](AGENTS.md) y [`CLAUDE.md`](CLAUDE.md) (contenido idéntico) |
| Registro de skills | [`.atl/skill-registry.md`](.atl/skill-registry.md) |
| Changes archivados (propuesta, diseño, specs, tareas, verificación y evidencia TDD) | [`openspec/changes/archive/`](openspec/changes/archive/) |
| Evidencia: creación de la skill propia | [`docs/evidencia-tpi/skill-creator/registro-creacion.md`](docs/evidencia-tpi/skill-creator/registro-creacion.md) |
| Evidencia: aplicación de la skill a C-04 | [`docs/evidencia-tpi/revision-c04-skill.md`](docs/evidencia-tpi/revision-c04-skill.md) |
| Evidencia: uso del MCP Context7 | [`docs/evidencia-tpi/mcp-context7.md`](docs/evidencia-tpi/mcp-context7.md) |

---

## Puesta en marcha con Docker Compose

### Requisitos

| Herramienta | Para qué | Versión verificada |
|---|---|---|
| Windows 11 con Docker Desktop (backend WSL 2) | Ejecutar `db`, `api`, `admin` y `frontend` | Docker 29.9.2, Docker Compose v5.6.1 |
| Windows PowerShell 5.1 | Ejecutar `scripts/test.ps1` y los ejemplos de esta guía | 5.1 |
| Git | Clonar el repositorio | — |
| Node.js y la CLI de OpenSpec (opcional) | Validar especificaciones | Node 22.23.1, OpenSpec 1.14.1 |

No hace falta instalar Python, Node ni PostgreSQL en el equipo para el sistema: todo corre en contenedores. Conviene clonar el repositorio en una ruta corta y fuera de OneDrive (por ejemplo, una carpeta `dev` en la raíz del disco). Si aparece `Filename too long`, usá una ruta más corta o `git config --global core.longpaths true`.

### Configuración local (`.env`)

```powershell
copy .env.example .env
```

`.env` está ignorado por Git y **nunca se versiona**. `.env.example` solo trae valores locales ficticios y marcadores. Antes del primer arranque, completá en `.env`:

| Variable | Para qué | Quién la usa |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Superusuario local de PostgreSQL (administración) | `db` |
| `DATABASE_MIGRATION_URL` | Conexión de administración (superusuario) para Alembic, seed y comandos locales | solo `admin` |
| `DATABASE_URL` | Conexión de la API con el rol `turnos_app` | `api` |
| `DATABASE_LOGIN_URL` | Conexión del login con el rol `turnos_login` | `api` |
| `AUTH_SECRET_KEY` | Clave para firmar tokens de sesión y CSRF | `api` |
| `CORS_ALLOWED_ORIGINS` | Orígenes permitidos (el frontend local, `http://localhost:5173`) | `api` |
| `APP_ENV` | `local` en desarrollo: habilita Swagger y los comandos locales | `api`, `admin` |
| `AUTH_COOKIE_SECURE` | `true` por defecto. La plantilla explica cuándo se admite `false` (solo con `APP_ENV=local` y HTTP) | `api` |

- Las contraseñas de `turnos_app` y `turnos_login` dentro de `DATABASE_URL` y `DATABASE_LOGIN_URL` las elegís vos y **deben coincidir** con las que ingreses al crear los roles (paso 2 de la preparación inicial).
- Usá valores locales inventados; no reutilices contraseñas reales.
- `TEST_DATABASE_URL` de la plantilla ya no se usa (deuda técnica DT-14): el runner arma la URL de pruebas en cada ejecución.

### Preparación inicial (instalación nueva)

Todos los comandos se ejecutan desde la raíz del repositorio. La API **nunca** migra ni carga datos al arrancar: cada paso es explícito.

```powershell
# 1. Levantar solo la base de desarrollo
docker compose up -d db

# 2. Crear los cuatro roles de PostgreSQL de C-04 (pide las contraseñas de turnos_app y turnos_login dos veces, con lectura oculta)
docker compose run --rm -it --no-deps admin python -m app.roles_postgres crear

# 3. Aplicar las migraciones 0001 a 0004 (la 0004 exige que los roles ya existan)
docker compose run --rm --no-deps admin alembic upgrade head

# 4. Cargar el seed ficticio (idempotente: no duplica ni modifica filas existentes)
docker compose run --rm --no-deps admin python -m app.seed

# 5. Asignar una contraseña a un usuario de demostración (pide código de consultorio, email y contraseña)
docker compose run --rm -it --no-deps admin python -m app.credenciales

# 6. Levantar la API y el frontend
docker compose up -d --build api frontend
```

Detalles:

- **Servicio `admin` (DD-34):** es el único que recibe la credencial de administración. No se levanta con `docker compose up`; se usa solo con `docker compose run --rm --no-deps admin <comando>`, y con `-it` cuando el comando pide datos. Los mismos comandos con `api` fallan sin conectarse.
- **Seed:** crea "Consultorio Demo A" (código `c-c7d08d776d19`) y "Consultorio Demo B" (código `c-c7d1647cab52`), cada uno con un usuario `administrador`, uno `secretaria` y uno `odontologo` (por ejemplo `administracion.a@example.test`). Los usuarios quedan **sin credencial** hasta el paso 5.
- **Credenciales:** la contraseña debe tener entre 15 y 128 caracteres, no puede ser común y no puede contener términos del contexto. Nunca se pasa por argumentos ni por variables de entorno.
- **Código de solo lectura:** `api` y `admin` montan `./backend` en `/app` de solo lectura. La recarga automática de la API funciona igual, porque detecta los cambios hechos en el host.

### Mantenimiento de una instalación existente

Una base de desarrollo ya preparada **no se vuelve a inicializar**:

| Situación | Comando |
|---|---|
| Arrancar o detener sin perder datos | `docker compose up -d` y `docker compose stop` |
| Aplicar migraciones nuevas | Antes, hacé un respaldo de la base. Después: `docker compose run --rm --no-deps admin alembic upgrade head` |
| Instalación creada antes de C-04 | Crear los roles (paso 2) **antes** de aplicar `0004` y completar `DATABASE_URL` y `DATABASE_LOGIN_URL` con los nuevos roles. La transición real está documentada en el [`verify.md` de C-04](openspec/changes/archive/2026-11-16-aislamiento-roles-rbac/verify.md) (grupo 13) |
| Verificar roles existentes o rotar una contraseña | `docker compose run --rm -it --no-deps admin python -m app.roles_postgres crear [--rotar-contrasena turnos_app]` (nunca corrige roles en silencio) |
| Reemplazar la contraseña de un usuario | `docker compose run --rm -it --no-deps admin python -m app.credenciales --reemplazar` (pide confirmación y revoca las sesiones del usuario) |
| Revisar los parámetros de hash de las credenciales | `docker compose run --rm --no-deps admin python -m app.credenciales --revisar-hashes` (solo lectura) |
| Limpiar sesiones vencidas e intentos viejos | `docker compose run --rm --no-deps admin python -m app.mantenimiento limpiar` |
| Consultar consultorios (solo lectura) | `docker compose exec db psql -U app -d turnos -c "SELECT nombre, codigo, activo FROM consultorio ORDER BY nombre;"` |

> ⚠️ **Acción destructiva:** `docker compose down -v` elimina los contenedores **y los volúmenes** (`pgdata` y `frontend_node_modules`), es decir, toda la base de desarrollo local. No forma parte de ningún script ni de las pruebas. Ejecutalo solo si querés empezar de cero, y después repetí la preparación inicial completa.
>
> Si al usar `docker compose run admin` aparece una advertencia de recreación de `db`, revisá que el comando tenga `--no-deps`: todos los comandos de esta guía lo llevan.

---

## API disponible y Swagger

### Endpoints reales

| Método y ruta | Acceso | Qué hace |
|---|---|---|
| `GET /api/health` | Público | Responde `{"status":"ok"}` sin consultar la base |
| `POST /api/auth/login` | Público, con `Origin` permitido | Recibe `codigo_consultorio`, `email` y `contrasena` (JSON). Si son correctos, emite la cookie `turnos_session` y el token CSRF en la cabecera `X-CSRF-Token`, y devuelve el usuario, su rol y su consultorio. Si no, responde 401; ante demasiados intentos, 429 |
| `GET /api/auth/me` | Requiere sesión | Devuelve la identidad, el rol y el consultorio **tomados de la sesión**. También renueva `X-CSRF-Token` |
| `POST /api/auth/logout` | Requiere sesión, `Origin` permitido y `X-CSRF-Token` | Revoca la sesión actual y borra la cookie (204) |

Con `APP_ENV=local` también se publican `/docs` (Swagger), `/redoc` y `/openapi.json`; en cualquier otro entorno no existen. No hay otros endpoints: en particular, **no hay endpoints de turnos ni de reserva**.

### Swagger

| Qué | URL |
|---|---|
| Documentación de la API (Swagger) | http://localhost:8000/docs |
| Salud de la API | http://localhost:8000/api/health |
| Frontend (pantalla inicial de C-01) | http://localhost:5173 |

Los puertos se publican solo en `127.0.0.1`.

**Limitación conocida:** Swagger sirve para recorrer los esquemas y probar `GET /api/health`. Las rutas que cambian estado (`login` y `logout`) exigen que la cabecera `Origin` coincida con un origen de `CORS_ALLOWED_ORIGINS`. Swagger envía el origen de su propia página (`http://localhost:8000`), que no está en esa lista con la configuración habitual (solo el frontend). Es la defensa CSRF funcionando, no un error.

Comprobaciones HTTP sobre la API local (2026-11-17), hechas con `curl.exe` y un cuerpo inválido (`{}`), sin credenciales:

| Solicitud a `POST /api/auth/login` | Código | Interpretación |
|---|---|---|
| Sin cabecera `Origin` | 403 | Rechazada antes de leer el cuerpo |
| `Origin: http://localhost:5173` (frontend) | 422 | Origen permitido; rechazada por el cuerpo inválido |
| `Origin: http://localhost:8000` (el de Swagger) | 403 | Origen no permitido |

En la misma fecha, `GET /api/health` respondió 200, `GET /docs` 200 y `GET /api/auth/me` sin sesión 401.

- Son solicitudes HTTP que reproducen la cabecera `Origin`, **no una ejecución de "Try it out" en el navegador**. Por ellas se espera que "Try it out" en `POST /api/auth/login` responda 403, pero eso no se probó en el navegador.
- El inicio de sesión completo se verificó el mismo día fuera de Swagger, con un ensayo manual del autor: login 200, `/me` 200, logout 204 y `/me` con la cookie revocada 401 (ver [`demo-autenticacion.md`](docs/evidencia-tpi/demo-autenticacion.md)).

Para repetirlo, usá PowerShell y `curl.exe` ([Demostración](#demostración-para-el-tpi)), sin agregar el origen de Swagger a la configuración.

---

## Pruebas

### Comando único

```powershell
.\scripts\test.ps1
```

Si PowerShell no permite ejecutar scripts: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1`.

Requiere Docker Desktop en ejecución y el archivo `.env`. Ejecuta, en orden, y se detiene en el primer fallo:

1. autoprueba del runner;
2. construcción de imágenes;
3. pruebas unitarias del backend;
4. base de pruebas efímera `db-test`;
5. migraciones sobre `db-test`;
6. pruebas de integración contra PostgreSQL real;
7. pruebas de aislamiento con los roles `turnos_app` y `turnos_login`;
8. verificación de tipos del frontend (`tsc`);
9. Vitest.

Termina con código 0 solo si todo pasa.

- **Nunca toca la base de desarrollo:** `db-test` corre en memoria, sin puertos publicados, y se elimina al terminar, incluso si algo falla.
- El runner genera en cada ejecución la contraseña de `db-test` y la URL de pruebas, y solo la pasa a los contenedores efímeros de prueba.
- Se niega a ejecutar si encuentra credenciales de administración en la sesión de PowerShell.
- **Reconstruye las imágenes** (`docker compose build`), pero no recrea los contenedores de desarrollo en ejecución.

### Últimos resultados registrados

Corrida completa del 2026-11-15: regresión 16.19 de C-04, registrada en su [`verify.md`](openspec/changes/archive/2026-11-16-aislamiento-roles-rbac/verify.md) y en su [`tdd-evidencia.md`](openspec/changes/archive/2026-11-16-aislamiento-roles-rbac/tdd-evidencia.md).

| Suite | Pruebas aprobadas |
|---|---|
| Autoprueba del runner (PowerShell) | 35 |
| Unitarias del backend (incluye las 19 del Change académico) | 785 |
| Integración contra PostgreSQL real | 509 |
| Aislamiento con roles reales | 234 |
| Frontend: `tsc --noEmit` | sin errores |
| Frontend: Vitest | 2 |

Son resultados **históricos y fechados**. Para obtener los actuales hay que volver a ejecutar `scripts/test.ps1`.

### Pruebas del Change académico sin Docker

El módulo de superposición no tiene I/O y se puede probar con Python 3.14 local, desde `backend/`:

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest tests/unit/test_superposicion_turnos.py
```

Resultado esperado: `19 passed`.

- `requirements-dev.txt` instala también las dependencias del backend.
- Ejecutar `python -m pytest` **sin indicar el archivo** corre toda la suite, y las pruebas de integración necesitan PostgreSQL. Para la suite completa usá el runner.
- Si PowerShell bloquea `Activate.ps1`: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`.

### Validar las especificaciones

```powershell
npm install -g @fission-ai/openspec@1.14.1   # una sola vez
openspec validate --specs --strict
openspec list
```

Resultado esperado: 19 especificaciones válidas y `No active changes found.`

---

## Seguridad: autenticación y aislamiento (C-03 y C-04)

**C-03 `autenticacion-sesion`:**
- sesión en una cookie opaca `HttpOnly` y `SameSite=Lax`, con vencimiento por inactividad y absoluto;
- token CSRF por sesión y verificación de `Origin` en toda ruta que cambia estado;
- límite de intentos por cuenta y por dirección IP;
- contraseñas con Argon2id y una política de contraseñas nuevas;
- errores sin datos del usuario (mismo 401 para cuenta inexistente y contraseña incorrecta).

**C-04 `aislamiento-roles-rbac`:**
- **Roles de PostgreSQL:** la API se conecta como `turnos_app`, y el login como `turnos_login`, que solo ejecuta funciones de acceso. Ninguno es superusuario ni omite RLS, y los privilegios son por columna (por ejemplo, `turnos_app` no puede leer la columna de credenciales).
- **RLS:** habilitada y **forzada** en `consultorio`, `usuario`, `sesion` e `intento_login`. Sin contexto de consultorio, las consultas no devuelven filas.
- **Contexto por transacción:** el consultorio de la sesión autenticada se fija al comenzar cada transacción, con alcance local (`set_config(..., true)`), y se limpia al devolver la conexión al pool.
- **El cliente nunca elige el consultorio:** se rechaza con 422 un `consultorio_id` en la query o la cabecera `X-Consultorio-Id`, y los esquemas de entrada no aceptan campos no declarados.
- **Autorización por rol:** la dependencia `require_rol` limita rutas a roles concretos. Hoy se ejerce con rutas de prueba, porque todavía no hay endpoints de negocio.
- **Separación de credenciales (DD-34):** la API no recibe credenciales de administración y se niega a arrancar si las detecta. Además verifica el rol real de cada conexión y monta el código en solo lectura.
- **Pruebas de acceso cruzado:** un registro obliga a que cada ruta protegida tenga su prueba de acceso cruzado.

**Límite reconocido:** RLS protege ante errores de la aplicación, no ante una API totalmente comprometida (DD-06, PD-01). La deuda técnica DT-10 a DT-14 está documentada en el diseño de C-04.

---

## Skill propia: `verificar-aislamiento-consultorios`

| Aspecto | Detalle |
|---|---|
| Propósito | Verificar en solo lectura, con evidencia citada (`ruta:línea` o comando reproducible), que el proyecto mantiene el aislamiento entre consultorios. Produce un informe con veredicto GO o NO-GO |
| Ubicación | [`.claude/skills/verificar-aislamiento-consultorios/`](.claude/skills/verificar-aislamiento-consultorios/SKILL.md): `SKILL.md`, `references/` (controles, plantilla del informe, consultas de catálogo) y `evals/` |
| Controles | V-01 a V-10, basados en C-04: cobertura de escenarios, referencias de la matriz, RLS forzada, contexto transaccional, funciones `SECURITY DEFINER`, roles, privilegios mínimos, consultorio que nunca viene del cliente, separación de credenciales y acceso cruzado por endpoint |
| Modos | `estatico` (por defecto). `pruebas` (ejecuta el runner) y `catalogo` (consultas SELECT) requieren autorización expresa del autor |
| Creación | Se creó el 2026-11-17 con la skill `skill-creator`: borrador, tres casos de prueba, corridas con y sin la skill, calificación, benchmark, tres iteraciones y validación con `quick_validate.py`. Detalle en [`registro-creacion.md`](docs/evidencia-tpi/skill-creator/registro-creacion.md) |
| Integración | Registrada en [`.atl/skill-registry.md`](.atl/skill-registry.md) y en [`AGENTS.md`](AGENTS.md) / [`CLAUDE.md`](CLAUDE.md), con su uso en el paso de Verify |
| Aplicación real | Revisión estática nueva, posterior al Archive de C-04: **GO**, con V-01 a V-10 en Cumple. Detalle en [`revision-c04-skill.md`](docs/evidencia-tpi/revision-c04-skill.md) |

Cómo se aplica: en Claude Code, con el repositorio abierto, alcanza con pedir por ejemplo "verificá el aislamiento entre consultorios del repositorio en modo estático". La skill identifica el commit, aplica los diez controles y escribe el informe solo en una ruta que autorice el autor.

---

## MCP utilizado: Context7

| Aspecto | Detalle |
|---|---|
| Servidor | `context7`, paquete `@upstash/context7-mcp@2.2.5`, transporte `stdio`, configurado en el ámbito de usuario de Claude Code. No usa clave de API |
| Herramientas usadas | `resolve-library-id` (identificó `/sqlalchemy/sqlalchemy` con la versión `rel_2_1_6`) y `query-docs` (tres consultas) |
| Propósito | Contrastar el contexto transaccional de C-04 (`backend/app/core/contexto_bd.py`, DD-04 y DD-05) con la documentación oficial de SQLAlchemy 2.1.6, la versión del proyecto |
| Aporte | La documentación respalda los mecanismos usados: el evento `after_begin` por transacción y por conexión, el *autobegin* que lo vuelve a disparar después de `commit` y `rollback`, `Session.info` y el evento `reset` del pool. Dos comportamientos (excepción dentro de `reset` y savepoints) no quedaron confirmados por la documentación devuelta y siguen respaldados por las pruebas de C-04 |
| Alcance | Revisión posterior al Archive de C-04, hecha para el TPI. Context7 no intervino en la implementación original y **no valida C-04 completo** |
| Evidencia | [`docs/evidencia-tpi/mcp-context7.md`](docs/evidencia-tpi/mcp-context7.md) |

Configuración reproducible, sin credenciales:

```powershell
claude mcp add --scope user context7 -- npx -y --package=@upstash/context7-mcp@2.2.5 -- context7-mcp
claude mcp list    # esperado: "context7: ... - ✔ Connected"
```

Si en algún momento se usa una clave de API de Context7, va en la configuración local del usuario y nunca en el repositorio.

---

## Demostración para el TPI

Recorrido sugerido. El 2026-11-17 se ensayaron en vivo contra la API local los pasos 1 a 3: health 200, `/docs` 200, login sin `Origin` 403, y el flujo de autenticación con login 200, `/me` 200, logout 204 y `/me` con la cookie revocada 401 (evidencia en [`docs/evidencia-tpi/demo-autenticacion.md`](docs/evidencia-tpi/demo-autenticacion.md)). Antes de grabar, conviene repetir el ensayo en el equipo de la grabación.

1. **Salud y Swagger.** Abrí http://localhost:8000/docs y ejecutá `GET /api/health` (esperado: `{"status":"ok"}`).
2. **Defensa por `Origin`, sin contraseña.** Un login sin `Origin` debería responder 403 antes de mirar el cuerpo:

   ```powershell
   curl.exe -i -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d "{}"
   ```

3. **Inicio de sesión, identidad y cierre.** Requiere haber asignado una contraseña con el paso 5 de la preparación inicial.
   - El login se hace con `Invoke-WebRequest`, que pide la contraseña con lectura oculta para que no quede en el historial.
   - La consulta de identidad y el cierre se hacen con `curl.exe`, que envía la cookie de sesión explícitamente.
   - Se hace **un solo** intento de login, y el script solo muestra códigos HTTP y la identidad del usuario ficticio.

   ```powershell
   $base   = 'http://localhost:8000'
   $origen = 'http://localhost:5173'   # debe ser uno de los orígenes de CORS_ALLOWED_ORIGINS
   $segura = Read-Host 'Contraseña' -AsSecureString
   $bstr   = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura)
   try {
     $cuerpo = @{
       codigo_consultorio = 'c-c7d08d776d19'
       email              = 'administracion.a@example.test'
       contrasena         = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
     } | ConvertTo-Json
     $login = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$base/api/auth/login" `
              -ContentType 'application/json; charset=utf-8' -Headers @{ Origin = $origen } `
              -Body ([Text.Encoding]::UTF8.GetBytes($cuerpo))
   } finally {
     [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
     $cuerpo = $null
   }
   "login: $($login.StatusCode)"; $login.Content                 # 200: usuario, rol y consultorio

   $cookie = ($login.Headers['Set-Cookie'] -split ';')[0]        # turnos_session=... (no lo imprimas)
   $csrf   = $login.Headers['X-CSRF-Token']

   curl.exe -s -w "`nme: %{http_code}`n" -H "Cookie: $cookie" "$base/api/auth/me"                       # 200 y la identidad
   curl.exe -s -o NUL -w "logout: %{http_code}`n" -X POST -H "Origin: $origen" -H "Cookie: $cookie" `
            -H "X-CSRF-Token: $csrf" "$base/api/auth/logout"                                            # 204
   curl.exe -s -o NUL -w "me tras logout: %{http_code}`n" -H "Cookie: $cookie" "$base/api/auth/me"     # 401
   Remove-Variable cookie, csrf
   ```

   - En el ensayo del 2026-11-17, `/me` con la cookie enviada por `Invoke-WebRequest` respondió 401, mientras que `curl.exe` con la misma cookie respondió 200. Por eso `/me` y el logout usan `curl.exe`. La causa no se investigó; una explicación posible es que Windows PowerShell 5.1 maneje la cabecera `Cookie` de forma distinta. Usá siempre `curl.exe`, no el alias `curl` de PowerShell 5.1.
   - El cuerpo del login se envía como bytes UTF-8 con `application/json; charset=utf-8`, para que una contraseña con tildes o `ñ` llegue intacta también en Windows PowerShell 5.1.
   - `ZeroFreeBSTR` borra y libera la copia de la contraseña que crea `SecureStringToBSTR`. En cambio, convertirla en un string de .NET (`PtrToStringBSTR`) y en el JSON deja **copias temporales en memoria** que no se pueden borrar de forma garantizada: el script reduce la exposición, no la elimina.
   - La cookie y el token CSRF viajan como argumentos de `curl.exe`. No se imprimen, pero mientras el comando corre son visibles para otros procesos del mismo equipo. Para una demo local con datos ficticios es aceptable; no repitas este patrón con credenciales reales.
   - La cookie se envía explícitamente porque, con `AUTH_COOKIE_SECURE=true`, lleva el atributo `Secure` y un cliente no la reenviaría solo por `http://`.
   - Si el login responde 401, la contraseña no coincide. No reintentes muchas veces: el límite de intentos bloquea con 429.
   - No copies la contraseña, el valor de la cookie ni el token en capturas.

4. **Aislamiento.** No hay endpoints de negocio para mostrarlo con solicitudes HTTP. Se demuestra con:
   - las pruebas de aislamiento (`backend/tests/isolation/`, parte del runner);
   - el informe de la skill propia ([`revision-c04-skill.md`](docs/evidencia-tpi/revision-c04-skill.md)).
5. **Regla de superposición.** `python -m pytest tests/unit/test_superposicion_turnos.py -v` (19 pruebas).

---

## Change académico: `validacion-superposicion-turnos` (Parcial 2)

> Esta sección describe la entrega del Parcial 2 (2026-10-14). Sigue vigente como regla de dominio, pero en ese momento el repositorio no tenía API, base de datos ni Docker. Todo eso llegó después, con C-01 a C-04.

### Qué implementa

Una función pura de dominio, sin I/O, que impide que un turno se superponga con otro turno **del mismo profesional**. Aplica dos reglas:

- **RN-AG-02**: un profesional no puede tener dos turnos superpuestos.
- **RN-AG-04**: los intervalos son semiabiertos `[inicio, fin)`.

Archivo: [`backend/app/domain/superposicion_turnos.py`](backend/app/domain/superposicion_turnos.py).

| Elemento | Descripción |
|---|---|
| `IntervaloDeTurno` | Dato inmutable: `profesional_id`, `inicio`, `fin`. No contiene datos del paciente |
| `validar_sin_superposicion(candidato, turnos_que_ocupan_agenda)` | No devuelve nada si el turno es aceptable. Si no lo es, lanza uno de los dos errores siguientes |
| `SuperposicionError` | Rechazo de negocio, con un mensaje fijo: *"El horario se superpone con otro turno del mismo profesional."* El mensaje no incluye datos del turno en conflicto |
| `IntervaloInvalidoError` | Error de validación: el inicio no es anterior al fin, o los instantes no tienen zona horaria |

### Comportamiento

- **Validación previa:** primero se validan el candidato y **todos** los turnos recibidos, incluso los de otros profesionales. Un intervalo inválido produce `IntervaloInvalidoError`.
- **Rechazo:** se rechaza cualquier intersección con un turno del mismo profesional: parcial, contenida, contenedora o idéntica.
- **Turnos consecutivos:** se aceptan. Por ejemplo, 10:00–10:30 y 10:30–11:00 no se superponen.
- **Otros profesionales:** sus turnos se ignoran al evaluar la superposición.

### Límites

Este Change **demuestra la regla en el dominio, pero no garantiza por sí solo la ausencia de superposiciones en el sistema.**

- No hay persistencia de turnos ni restricción de exclusión en PostgreSQL. Todo eso es alcance de C-15, que sigue pendiente.
- No cubre las creaciones simultáneas (RN-AG-03, PA-20). La garantía final será la restricción de la base de datos.
- No conoce los estados del turno: recibe los turnos ya seleccionados por quien la llama. Qué estados ocupan agenda es la pregunta abierta PA-07.
- No controla sillones ni boxes (PA-01): dos profesionales distintos en el mismo horario se aceptan.
- **Archivar este Change no completa C-15.**

### Evidencia y resultados del Parcial 2

| Artefacto | Ubicación |
|---|---|
| Especificación vigente | [`openspec/specs/superposicion-turnos/spec.md`](openspec/specs/superposicion-turnos/spec.md) |
| Change archivado | [`openspec/changes/archive/2026-10-14-validacion-superposicion-turnos/`](openspec/changes/archive/2026-10-14-validacion-superposicion-turnos/) |
| Verificación y trazabilidad | [`verify.md`](openspec/changes/archive/2026-10-14-validacion-superposicion-turnos/verify.md) |
| Evidencia TDD | [`tdd-evidencia.md`](openspec/changes/archive/2026-10-14-validacion-superposicion-turnos/tdd-evidencia.md) |

Resultados obtenidos el 2026-10-14 y repetidos en un clon limpio:
- **19 pruebas aprobadas**;
- **17 de 17 escenarios** cubiertos;
- 31 de 31 tareas;
- 13 pruebas que fallaron antes de implementar y pasaron después; las demás son triangulaciones o se verificaron con una mutación temporal del código.

Las 19 pruebas siguen formando parte de la suite unitaria actual.

---

## Roadmap: completo y pendiente

El plan completo está en [`CHANGES.md`](CHANGES.md): 30 Changes en fases, con dependencias, lecturas previas y decisiones abiertas para cada uno.

| Estado | Changes |
|---|---|
| ✅ Completos y archivados | Change académico `validacion-superposicion-turnos`; C-01 `foundation-setup`; C-02 `modelo-base-consultorios-seed`; C-03 `autenticacion-sesion`; C-04 `aislamiento-roles-rbac` |
| ⏭️ Siguiente en el camino crítico | C-07 `profesionales` |
| ⏳ Pendientes de la línea de corte | C-05 `gestion-usuarios`, C-06 `frontend-base-sesion`, C-08 a C-21 (prestaciones, horarios, bloqueos, pacientes, aviso de privacidad, creación de turnos sin superposición, disponibilidad, reprogramación, cancelación y estados, agenda y pantallas del frontend) |
| 💡 Candidatas, sin decisión | C-24 a C-30 (reserva online, comunicación y trazabilidad) |

Camino crítico: `C-01 → C-02 → C-03 → C-04 → C-07 → C-09 → C-15 → C-16 → C-20 → C-21`. Los cuatro primeros están completos.

**Ciclo de cada Change:**

```
/opsx:explore <nombre>   (opcional)
/opsx:propose <nombre>
/opsx:apply <nombre>     (TDD estricto)
Verify                   (openspec validate --strict + pruebas + evidencia en el Change)
/opsx:archive <nombre>   (solo si Verify pasó)
```

Antes de proponer un Change: leé su ficha en `CHANGES.md` y los archivos de la Knowledge Base que indica, verificá que sus dependencias estén archivadas y resolvé con el autor las preguntas abiertas que lo bloquean. Si el Change toca endpoints privados, `consultorio_id`, migraciones o permisos, en Verify aplicá la skill `verificar-aislamiento-consultorios`.

Las reglas obligatorias del proyecto están en [`AGENTS.md`](AGENTS.md). Incluyen:
- datos ficticios;
- ningún dato clínico;
- aislamiento real entre consultorios;
- ninguna decisión abierta resuelta sin el autor;
- commits solo con autorización.

---

## Datos ficticios

> ⚠️ Este repositorio es académico. **Todos los datos de desarrollo, pruebas, ejemplos y capturas son ficticios.**
>
> - Las pruebas de dominio usan los profesionales `PROF-A` y `PROF-B`.
> - El seed usa "Consultorio Demo A" y "Consultorio Demo B", con usuarios `@example.test` (un dominio reservado).
>
> Nunca se deben cargar datos reales de pacientes, profesionales ni consultorios, ni agregar datos clínicos (historia clínica u odontograma) al MVP. Una futura versión productiva deberá definir sus propios controles para datos reales.

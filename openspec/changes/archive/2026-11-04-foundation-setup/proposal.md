# Propuesta: foundation-setup

## Why

El proyecto todavía no tiene la base técnica sobre la que se construyen los Changes del roadmap: hoy solo existe el módulo de dominio puro del Change académico (`backend/app/domain/superposicion_turnos.py`) con sus 19 pruebas pytest, ejecutadas en un entorno mínimo de Python. C-01 `foundation-setup` (`CHANGES.md`, FASE 0) es el primer Change de desarrollo y el prerrequisito técnico de C-02 en adelante: sin FastAPI, PostgreSQL con `btree_gist`, Docker Compose, frontend y suites de pruebas cableadas no se puede persistir, exponer endpoints ni probar restricciones contra una base real (X2).

**C-01 es infraestructura, no el Change académico.** No contiene historias de usuario ni reglas de negocio (`CHANGES.md`, "Niveles de alcance", Nivel 2). La preparación mínima de Python y pytest hecha dentro del recorte académico `validacion-superposicion-turnos` (archivado el 2026-10-14) **no completó C-01**: C-01 sigue pendiente hasta cumplir todo el alcance de esta propuesta (AGENTS.md O1).

## What Changes

- **Estructura de directorios** según KB 08: `backend/app/{core,api,repositories,models}` (se conserva `app/domain/`), `backend/alembic/`, `backend/tests/{integration,isolation}` (se conserva `tests/unit/`), y `frontend/` (Vite + React + TypeScript con `src/{features,shared,pages}`).
- **Backend mínimo FastAPI** con `GET /api/health` de liveness, independiente de PostgreSQL, y configuración por variables de entorno (`DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, `APP_ENV`) validada con pydantic-settings. CORS restringido a los orígenes configurados, sin comodín.
- **Acceso a datos y migraciones**: SQLAlchemy 2 con psycopg 3 síncrono; Alembic inicializado, sin migraciones de dominio, con una única migración de infraestructura que habilita `btree_gist`. Las migraciones se aplican con un **comando explícito**, nunca al arrancar la API.
- **Docker Compose local** con los servicios `db` (PostgreSQL 18 con `btree_gist`, volumen con nombre, puerto solo en `127.0.0.1`), `api` (uvicorn con recarga) y `frontend` (servidor de desarrollo de Vite). `.env.example` con valores ficticios y sin secretos reales; `.env` ya está ignorado por Git.
- **Pruebas cableadas**: pytest unitario (health, configuración, CORS y las 19 pruebas existentes de superposición como regresión), pytest de integración contra PostgreSQL real en una base de pruebas efímera y separada de la de desarrollo (conexión y `btree_gist`) y Vitest con jsdom y Testing Library (render mínimo), más la verificación de tipos estricta de TypeScript.
- **Comando único de pruebas** `scripts/test.ps1`, que corre todas las suites dentro de contenedores y termina con código distinto de cero si cualquiera falla.
- **Desarrollo en Windows**: `.gitattributes` para fijar finales de línea LF en lo que se ejecuta en contenedores Linux, y recarga en caliente por sondeo (polling) para los bind mounts desde Windows a WSL 2.
- **Documentación**: se amplía `README.md` (arranque con Docker Compose, migraciones, pruebas, estructura) **conservando su contenido actual**.
- Versiones exactas fijadas y verificadas en `design.md` (`==` en pip; versiones exactas sin `^` en `package.json` más `package-lock.json`).

## Capabilities

### New Capabilities

- `salud-api`: endpoint de liveness `GET /api/health` que responde sin depender de la base de datos.
- `configuracion-backend`: carga y validación de la configuración del backend desde variables de entorno y política CORS restringida a orígenes declarados.
- `validacion-entrada`: base común de los esquemas de entrada de la API que rechaza campos no declarados (S1), verificada con un esquema de prueba porque C-01 no tiene endpoints con cuerpo.
- `base-de-datos-local`: conexión a PostgreSQL real, disponibilidad e instalación de `btree_gist` y aplicación de migraciones de Alembic por comando explícito.
- `frontend-base`: aplicación React + Vite + TypeScript estricta que renderiza una pantalla mínima verificada con Vitest.
- `ejecucion-de-pruebas`: comando único que ejecuta todas las suites, conserva la regresión de las pruebas existentes, falla ante cualquier suite fallida y verifica la higiene de `.env`.

### Modified Capabilities

Ninguna. La capacidad existente `superposicion-turnos` no cambia sus requisitos: sus 19 pruebas solo se ejecutan como regresión.

## Impact

- **Código nuevo (en Apply)**: `backend/app/main.py`, `backend/app/core/`, `backend/app/api/`, `backend/app/models/`, `backend/app/repositories/`, `backend/alembic/` y `backend/alembic.ini`, `backend/Dockerfile`, `backend/requirements.txt`, `backend/tests/integration/`, `backend/tests/isolation/`, `frontend/` completo, `docker-compose.yml`, `.env.example`, `.gitattributes`, `scripts/test.ps1` y su autoprueba.
- **Archivos existentes que se extienden sin perder contenido**: `backend/requirements-dev.txt` (conserva `pytest==9.1.1`), `backend/pyproject.toml` (conserva la configuración de pytest), `README.md`. No se tocan `backend/app/domain/superposicion_turnos.py` ni `backend/tests/unit/test_superposicion_turnos.py`.
- **Dependencias**: imágenes `python:3.14.10-slim-trixie`, `postgres:18.6-trixie`, `node:22.23.1-trixie-slim`; paquetes de PyPI y npm del cuadro de versiones de `design.md`. La instalación y la descarga de imágenes ocurren en Apply, con autorización del autor.
- **APIs**: solo `GET /api/health`.
- **Base de datos**: ninguna tabla de dominio; solo la extensión `btree_gist` y la tabla de control `alembic_version`.
- **Roadmap**: no cambia los 30 Changes ni sus dependencias. Al archivar este Change se marca C-01 en `CHANGES.md`; C-15 sigue `[ ]`.
- **Gobernanza**: BAJO (infraestructura local, sin datos reales ni seguridad), según `CHANGES.md`.

## Fuera de alcance (no objetivos)

- Autenticación (PA-03), roles y RBAC, contexto de consultorio y aislamiento multi-consultorio (RN-MT, PA-04). La carpeta `tests/isolation/` se crea vacía para los Changes que la usen.
- Entidades y funcionalidades de dominio: consultorios, pacientes, profesionales, prestaciones, agenda y turnos; modelos SQLAlchemy de dominio y migraciones de dominio o de negocio.
- Datos semilla (seed): corresponden a C-02.
- CI en la nube, despliegue y cualquier servicio externo (DD-11, PA-02, X3).
- Cliente HTTP del frontend, ruteo, componente de calendario y pantallas funcionales.
- Linter de TypeScript o Python (queda como decisión pendiente en `design.md`).
- Chequeo de base de datos dentro de `GET /api/health` (el health es solo liveness).

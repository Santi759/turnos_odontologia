# Propuesta: modelo-base-consultorios-seed

## Why

C-01 `foundation-setup` (archivado el 2026-11-04) dejó la infraestructura lista (PostgreSQL 18 con `btree_gist`, Alembic con la migración `0001`, `Base` declarativa sin modelos, `EsquemaEntrada` con `extra='forbid'`), pero el sistema todavía no tiene ninguna noción de **consultorio** ni de **usuario**. C-02 (`CHANGES.md`, FASE 1, camino crítico) es el cimiento de identidad y de aislamiento multi-consultorio (D2, R6, RN-MT-01/02): sin estas dos tablas, sin repositorios acotados al consultorio y sin datos ficticios de dos consultorios no se puede construir la autenticación (C-03) ni las barreras de aislamiento y roles (C-04), ni probar el aislamiento entre consultorios (RG3).

Governance **CRÍTICO**. Las decisiones DC-01 a DC-12 fueron aprobadas por el autor el 2026-11-04 (Engram #30) antes de este Propose; este Change no resuelve ninguna otra pregunta abierta (D6): lo nuevo queda en "Decisiones pendientes para el autor" de `design.md`.

## What Changes

- **Modelo base** con SQLAlchemy 2 tipado (`Mapped[...]`), registrado en `Base.metadata`:
  - `consultorio`: `id` UUIDv7 generado por PostgreSQL 18 (`uuidv7()`, DC-01), `nombre`, `zona_horaria` (por defecto `America/Argentina/Buenos_Aires`), `anticipacion_cancelacion_horas` (por defecto 24, `CHECK >= 0`), `activo`, `creado_en` (`timestamptz`).
  - `usuario`: `id` UUIDv7, `consultorio_id` obligatorio con clave foránea `ON DELETE RESTRICT`, `email` normalizado y único **dentro de cada consultorio** (DC-05), `nombre`, `credencial` que puede quedar **sin credencial** (NULL, DC-08), `rol` como texto con `CHECK` (`administrador`, `secretaria`, `odontologo`, DC-09), `activo`, `creado_en`, y el ancla `UNIQUE (consultorio_id, id)` para futuras claves foráneas compuestas (DC-02).
- **Migración `0002_modelo_base_consultorios`** escrita a mano, reversible, con `down_revision = "0001"` (DC-11); no inserta datos. El `downgrade` solo se ejecuta contra la base de pruebas `db-test`.
- **Repositorios acotados al consultorio** (DC-03, DC-10): base reutilizable que aplica el consultorio en toda consulta, tomado de un `ContextoConsultorio` tipado construido solo en el servidor (nunca de un parámetro libre del cliente); `UsuarioRepositorio` (listar, obtener por id, buscar por email, crear, desactivar) y `ConsultorioRepositorio` (solo el consultorio actual). El acceso a un usuario de otro consultorio responde igual que uno inexistente (`None`, RN-MT-05).
- **Seed ficticio** por comando explícito e independiente de las migraciones (`docker compose run --rm api python -m app.seed`, DC-07): 2 consultorios ("Consultorio Demo A" y "Consultorio Demo B") y 1 administrador + 1 secretaría + 1 odontólogo por consultorio, con emails `@example.test` y **sin credenciales utilizables** (DC-08). Idempotente (identificadores fijos e `INSERT ... ON CONFLICT DO NOTHING`), nunca actualiza ni borra, se niega a correr fuera de `APP_ENV=local` y no escribe datos personales en su salida (X1).
- **Evolución del contrato de C-01**: el escenario "Sin tablas de dominio" de `base-de-datos-local` pasa a exigir exactamente las tablas del modelo base, vacías tras migrar; la prueba `test_sin_tablas_de_dominio` se actualiza en Apply con esa justificación.
- **Sesiones**: fábrica de sesiones de SQLAlchemy en `app/core/database.py` (anunciada en C-01 DF-08 para el primer repositorio). Sin dependencias de FastAPI por petición: no hay endpoints.
- README: sección del comando de seed (en Apply).

## Capabilities

### New Capabilities

- `modelo-consultorios-usuarios`: tablas `consultorio` y `usuario`, sus valores por defecto, restricciones (`CHECK`, unicidad del email por consultorio, integridad referencial, ancla compuesta), identificadores UUIDv7 generados por la base, representación "sin credencial" y la migración `0002` reversible y sin datos.
- `repositorios-acotados`: contexto de consultorio confiable y repositorios que aplican el consultorio en toda lectura y escritura, sin aceptar `consultorio_id` del cliente.
- `seed-ficticio`: comando explícito de datos ficticios idempotente, no destructivo, protegido por entorno y sin datos personales en su salida.

### Modified Capabilities

- `base-de-datos-local`: el requisito "Migraciones aplicadas solo por comando explícito" deja de exigir que no haya tablas de dominio (contrato de C-01) y pasa a exigir que, tras migrar, existan exactamente `alembic_version`, `consultorio` y `usuario`, sin filas en las tablas del modelo, y que las migraciones no ejecuten el seed.

`ejecucion-de-pruebas` no cambia: `scripts/test.ps1` conserva sus pasos (las pruebas nuevas entran en los pasos unitario e integración existentes) y la regresión de las 19 pruebas de superposición.

## Impact

- **Código nuevo (en Apply)**: `backend/app/models/{consultorio.py, usuario.py}` (+ registro en `models/__init__.py`), `backend/alembic/versions/0002_modelo_base_consultorios.py`, `backend/app/repositories/{base.py, contexto.py, usuarios.py, consultorios.py}`, `backend/app/seed/{__init__.py, __main__.py, datos.py}`, pruebas en `backend/tests/unit/` y `backend/tests/integration/`.
- **Archivos existentes que se modifican**: `backend/app/core/database.py` (fábrica de sesiones), `backend/tests/integration/test_migraciones.py` (`test_sin_tablas_de_dominio`, justificado por la delta de `base-de-datos-local`), `scripts/tests/autoprueba.ps1` (comprobación de que el arranque de la API no ejecuta el seed), `README.md` (sección del seed). No cambian `docker-compose.yml`, `.env.example`, `Settings`, `scripts/test.ps1`, `alembic/env.py`, `app/models/base.py`, `superposicion_turnos.py` ni su prueba.
- **Dependencias**: ninguna nueva (SQLAlchemy 2.1.6, psycopg 3.3.6, Alembic 1.20.1 y Python 3.14 ya están; `uuidv7()` requiere PostgreSQL 18, ya fijado por C-01).
- **APIs**: ninguna. Sin endpoints de dominio, de alta de consultorio ni de administración de plataforma.
- **Base de datos**: tablas `consultorio` y `usuario`. En Apply, el seed y `alembic upgrade head` sobre la base de **desarrollo** solo se ejecutan con autorización del autor y únicamente con datos ficticios.
- **Roadmap**: no cambia los Changes ni sus dependencias. Al archivar se marca C-02 y se corrige la numeración histórica de migraciones de `CHANGES.md` ("Migración 001" → `0002` en C-02; "migración 002" → `0003` en C-04), según DC-11.
- **Seguridad**: UUIDv7 y los filtros por consultorio **no reemplazan** la autorización por rol ni RLS (C-04, RN-MT-06).

## Fuera de alcance (no objetivos)

- Autenticación, contraseñas, hash, sesiones o tokens (PA-03, C-03); recuperación de contraseña (PA-11, C-05).
- RLS, rol de base de datos de la aplicación sin privilegios (DC-04, C-04), claves foráneas compuestas hacia `usuario` (no hay tablas que referencien a usuario todavía) y autorización por rol (RBAC, C-04).
- Endpoints de dominio (Profesional, Paciente, Turno, etc.), endpoints de usuarios (C-05), alta de consultorios y administrador de plataforma (PA-05 = solo seed, DC-12).
- Membresías de un usuario en varios consultorios (DC-06, SU-02).
- Cambios de infraestructura (`docker-compose.yml`, `.env.example`, `Settings`).
- Datos reales de cualquier tipo (D1) y ampliación del seed con profesionales, prestaciones, pacientes o turnos (C-23).

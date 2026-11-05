# turnos_odontologia

SaaS multi-consultorio de gestión de turnos odontológicos para Argentina. Es un MVP académico (v0.1) del trabajo práctico de **Metodología I**.

- **Autor:** Santiago Chepilla
- **Estado:** fundación metodológica completa y **dos Changes implementados y archivados**: el Change académico funcional (`validacion-superposicion-turnos`) y la infraestructura C-01 (`foundation-setup`). El resto del sistema está planificado, no implementado.

> ⚠️ **Datos ficticios únicamente.** Todo el desarrollo, las pruebas, los ejemplos y la documentación de este repositorio usan datos inventados (por ejemplo, `PROF-A`, `PROF-B`). Nunca se cargan datos reales de pacientes, profesionales ni consultorios (DD-13, RN-PA-08). Tampoco se incluyen datos clínicos.

---

## Índice

1. [Problema que busca resolver](#problema-que-busca-resolver)
2. [Contexto académico y metodología](#contexto-académico-y-metodología)
3. [Estado real del proyecto](#estado-real-del-proyecto)
4. [Stack tecnológico](#stack-tecnológico)
5. [Estructura del repositorio](#estructura-del-repositorio)
6. [Documentos del proyecto](#documentos-del-proyecto)
7. [Change académico: `validacion-superposicion-turnos`](#change-académico-validacion-superposicion-turnos)
8. [Requisitos previos](#requisitos-previos)
9. [Ejecución en Windows PowerShell](#ejecución-en-windows-powershell)
10. [Evidencia del Change](#evidencia-del-change)
11. [Resultados verificados](#resultados-verificados)
12. [Cómo continuar el desarrollo](#cómo-continuar-el-desarrollo)
13. [Datos ficticios](#datos-ficticios)
14. [Entorno de desarrollo con Docker Compose (C-01)](#entorno-de-desarrollo-con-docker-compose-c-01-foundation-setup)

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

El proyecto es el trabajo práctico de Metodología I, desarrollado por una sola persona. La consigna pide documentar el proceso completo y entregar **un Change funcional pequeño**, con:

- una regla de negocio verificable;
- al menos tres escenarios (exitoso, error de negocio y caso límite);
- implementación como módulo de dominio o API, sin interfaz gráfica.

La metodología combina cuatro enfoques:

| Enfoque | Qué aportó | Resultado en el repositorio |
|---|---|---|
| **Discovery** | Investigación del problema, los usuarios, las reglas de negocio y el mercado (18 sistemas evaluados con una rúbrica de 7 criterios), antes de escribir requisitos | `discovery/`, `docs/discovery/` |
| **Active Stack** | Flujo de fundación guiado por etapas, con un punto de control del autor en cada etapa: Discovery → Knowledge Base → roadmap → skills → instrucciones para agentes | `.active-orchestrator-state.json` (estado `done`) |
| **Spec-Driven Development** | Cada funcionalidad se especifica antes de implementarse (requisitos y escenarios DADO / CUANDO / ENTONCES). La implementación sigue TDD estricto: una prueba que falla primero, el código mínimo para que pase, más casos y refactorización | `openspec/specs/`, `backend/tests/` |
| **OpenSpec** (CLI 1.14.1) | Herramienta que gestiona el ciclo de cada Change: Explore → Propose → Apply → Verify → Archive | `openspec/` |

Las decisiones del autor quedaron registradas con fecha en cada etapa. Las preguntas que siguen abiertas no se resuelven sin el autor.

---

## Estado real del proyecto

| Elemento | Estado |
|---|---|
| Discovery | ✅ Aprobado (2026-10-10; informe ampliado el 2026-10-12) |
| Knowledge Base | ✅ Aprobada (2026-10-13) |
| Roadmap (`CHANGES.md`) | ✅ Aprobado (2026-10-13): 30 Changes planificados (C-01 a C-30) |
| Skills y registro de skills | ✅ Evaluadas; el autor decidió no instalar skills de dominio por ahora |
| Instrucciones para agentes (`AGENTS.md` y `CLAUDE.md`) | ✅ Generadas (2026-10-13) |
| Change académico `validacion-superposicion-turnos` | ✅ Implementado, verificado y archivado (2026-10-14) |
| C-01 `foundation-setup` (infraestructura) | ✅ **Implementado, verificado y archivado** (2026-11-04) |
| C-15 `turnos-crear-sin-superposicion` (creación completa de turnos) | ⏳ **Pendiente**. El Change académico implementa solo su núcleo de dominio. |
| Resto de los Changes (C-02 a C-30) | ⏳ Planificados, no implementados |

**Lo que existe hoy como código:** una función pura de dominio en Python y sus pruebas automatizadas.

**Lo que todavía no existe:**
- API ni endpoints;
- base de datos;
- autenticación;
- frontend;
- Docker;
- persistencia de turnos.

---

## Stack tecnológico

El stack fue decidido por el autor (DD-10 en la Knowledge Base). **Casi todo está planificado y todavía no está implementado.**

| Capa | Tecnología | Estado en el repositorio |
|---|---|---|
| Lógica de dominio | Python | ✅ **Implementado** (módulo puro del Change académico; probado con Python 3.14.5) |
| Pruebas del backend | pytest | ✅ **Implementado** (pytest 9.1.1) |
| Especificaciones | OpenSpec | ✅ **En uso** (CLI 1.14.1) |
| API REST | FastAPI | ✅ Implementado (C-01) |
| Acceso a datos y migraciones | SQLAlchemy 2, Alembic | ✅ Implementado (C-01; sin tablas de dominio) |
| Validación de entradas | Pydantic | ✅ Implementado (C-01; base de esquemas) |
| Base de datos | PostgreSQL (con `btree_gist` para la restricción de exclusión) | ✅ Implementado (C-01) |
| Frontend | React con Vite, en TypeScript (decisión del autor en la Etapa 4) | ✅ Implementado (C-01; pantalla inicial) |
| Pruebas del frontend | Vitest | ✅ Implementado (C-01) |
| Entorno local | Docker Compose | ✅ Implementado (C-01) |
| Autenticación | Sin definir (pregunta abierta PA-03) | ❓ Abierta |

Detalle: [`knowledge-base/02_descripcion_general.md`](knowledge-base/02_descripcion_general.md) y [`knowledge-base/08_arquitectura_propuesta.md`](knowledge-base/08_arquitectura_propuesta.md).

---

## Estructura del repositorio

```
turnos_odontologia/
├── README.md                          este archivo
├── AGENTS.md / CLAUDE.md              instrucciones para agentes (copias idénticas)
├── CHANGES.md                         roadmap: 30 Changes con dependencias y fases
├── .active-orchestrator-state.json    estado de la fundación Active Stack
├── .atl/skill-registry.md             registro de skills
├── .claude/commands/opsx/             comandos del flujo OpenSpec
├── discovery/
│   ├── discovery.md                   Discovery aprobado (checklist de 11 puntos)
│   └── sources/                       notas y fichas de los sistemas investigados
├── docs/discovery/                    informe de Discovery (.md y .pdf), checklist,
│                                      fuentes y metodología de evaluación
├── knowledge-base/                    Knowledge Base (README + 10 archivos)
├── openspec/
│   ├── config.yaml
│   ├── specs/superposicion-turnos/    especificación vigente (sincronizada)
│   └── changes/archive/               Changes archivados
└── backend/                           mínimo para ejecutar el Change académico
    ├── pyproject.toml                 configuración de pytest
    ├── requirements-dev.txt           pytest==9.1.1
    ├── app/domain/superposicion_turnos.py
    └── tests/unit/test_superposicion_turnos.py
```

`backend/` contiene solo lo necesario para ejecutar el Change académico. **No es la estructura de C-01**: falta, entre otras cosas, `main.py`, la API, los modelos, Alembic y Docker.

---

## Documentos del proyecto

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

---

## Change académico: `validacion-superposicion-turnos`

### Qué implementa

Implementa una función pura de dominio, sin I/O, que impide que un turno se superponga con otro turno **del mismo profesional**. Aplica dos reglas:

- **RN-AG-02**: un profesional no puede tener dos turnos superpuestos.
- **RN-AG-04**: los intervalos son semiabiertos `[inicio, fin)`.

Archivo: [`backend/app/domain/superposicion_turnos.py`](backend/app/domain/superposicion_turnos.py).

| Elemento | Descripción |
|---|---|
| `IntervaloDeTurno` | Dato inmutable: `profesional_id`, `inicio`, `fin`. No contiene datos del paciente. |
| `validar_sin_superposicion(candidato, turnos_que_ocupan_agenda)` | No devuelve nada si el turno es aceptable. Si no lo es, lanza uno de los dos errores siguientes. |
| `SuperposicionError` | Rechazo de negocio, con un mensaje fijo: *"El horario se superpone con otro turno del mismo profesional."* El mensaje no incluye datos del turno en conflicto. |
| `IntervaloInvalidoError` | Error de validación: el inicio no es anterior al fin, o los instantes no tienen zona horaria. |

### Comportamiento

- **Validación previa:** primero se validan el candidato y **todos** los turnos recibidos, incluso los de otros profesionales. Un intervalo inválido produce `IntervaloInvalidoError`.
- **Rechazo:** se rechaza cualquier intersección con un turno del mismo profesional: parcial, contenida, contenedora o idéntica.
- **Turnos consecutivos:** se aceptan. Por ejemplo, 10:00–10:30 y 10:30–11:00 no se superponen.
- **Otros profesionales:** sus turnos se ignoran al evaluar la superposición.

### Límites

Este Change **demuestra la regla en el dominio, pero no garantiza por sí solo la ausencia de superposiciones en el sistema.**

- No hay persistencia, modelo `Turno` ni restricción de exclusión en PostgreSQL. Todo eso es alcance de C-15.
- No cubre las creaciones simultáneas (RN-AG-03, PA-20). La garantía final será la restricción de la base de datos.
- No conoce los estados del turno: recibe los turnos ya seleccionados por quien la llama. Qué estados ocupan agenda es la pregunta abierta PA-07.
- No controla sillones ni boxes (PA-01): dos profesionales distintos en el mismo horario se aceptan.
- No incluye endpoints, autenticación, aislamiento entre consultorios ni datos de pacientes.
- **Archivar este Change no completa C-15.** C-15 sigue pendiente en `CHANGES.md`. (C-01 se completó y archivó después, el 2026-11-04.)

---

## Requisitos previos

| Herramienta | Para qué | Versión verificada |
|---|---|---|
| Windows con PowerShell | Ejecutar los comandos de esta guía | Windows 11, PowerShell 5.1 |
| Python 3.14 (con el lanzador `py`) | Ejecutar el módulo y las pruebas | 3.14.5 |
| Node.js y npm | Instalar la CLI de OpenSpec (solo para validar especificaciones) | Node 22.23.1, npm 10.9.8 |
| OpenSpec CLI | Validar especificaciones | 1.14.1 |

No se necesitan Docker ni PostgreSQL: el módulo no tiene I/O.

**Si al clonar aparece `Filename too long`:** algunas rutas del Change archivado son largas. Ese error aparece cuando el repositorio se clona en una carpeta de ruta muy profunda. Hay dos soluciones:
- clonarlo en una ruta corta;
- habilitar las rutas largas en Git con `git config --global core.longpaths true`.

---

## Ejecución en Windows PowerShell

Todos los comandos se ejecutan **desde la raíz del repositorio**.

### 1. Crear y activar el entorno virtual

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

- Debe mostrar `Python 3.14.x`.
- `backend/.venv` está excluido de Git.

Si PowerShell bloquea `Activate.ps1` por la política de ejecución, habilitala solo para la sesión actual y volvé a activar:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar las dependencias de desarrollo

```powershell
python -m pip install -r requirements-dev.txt
```

Instala solo `pytest==9.1.1` y sus dependencias propias.

### 3. Ejecutar las pruebas

```powershell
python -m pytest
```

Resultado esperado: `19 passed`. Para ver cada prueba por nombre:

```powershell
python -m pytest -v
```

### 4. Validar las especificaciones con OpenSpec

Instalar la CLI una sola vez (si no está instalada):

```powershell
npm install -g @fission-ai/openspec@1.14.1
```

Luego, desde la raíz del repositorio:

```powershell
deactivate
cd ..
openspec validate --all --strict
openspec list --specs
```

Resultado esperado:

```
✓ spec/superposicion-turnos
Totals: 1 passed, 0 failed (1 items)

Specs:
  superposicion-turnos     requirements 5
```

`openspec list` debe responder `No active changes found.`, porque el Change académico ya está archivado.

---

## Evidencia del Change

| Artefacto | Ubicación |
|---|---|
| Especificación vigente (sincronizada) | [`openspec/specs/superposicion-turnos/spec.md`](openspec/specs/superposicion-turnos/spec.md) |
| Change archivado | [`openspec/changes/archive/2026-10-14-validacion-superposicion-turnos/`](openspec/changes/archive/2026-10-14-validacion-superposicion-turnos/) |
| Propuesta y diseño | `proposal.md` y `design.md` (dentro del Change archivado) |
| Tareas (31 de 31 completadas) | `tasks.md` (dentro del Change archivado) |
| Verificación y trazabilidad | [`verify.md`](openspec/changes/archive/2026-10-14-validacion-superposicion-turnos/verify.md) |
| Evidencia TDD: pruebas que fallaron antes de implementar y pasaron después | [`tdd-evidencia.md`](openspec/changes/archive/2026-10-14-validacion-superposicion-turnos/tdd-evidencia.md) |

---

## Resultados verificados

Resultados obtenidos el 2026-10-14 y repetidos en un clon limpio del repositorio con los comandos de esta guía:

| Verificación | Resultado |
|---|---|
| `python -m pytest` | **19 pruebas aprobadas**, 0 fallidas |
| Escenarios de la especificación | **17 de 17 cubiertos** por pruebas automatizadas (tabla en `verify.md`) |
| `openspec validate --all --strict` | 1 especificación válida, 0 errores |
| Tareas del Change | 31 de 31 completadas |
| Evidencia TDD | 13 pruebas fallaron antes de implementar y pasaron después; las demás son triangulaciones o se verificaron con una mutación temporal del código (detalle en `tdd-evidencia.md`) |

Los 17 escenarios cubren cinco requisitos:
- aceptación sin superposición;
- rechazo por superposición con el mismo profesional;
- turnos consecutivos (caso límite);
- independencia entre profesionales distintos;
- validación de los intervalos de entrada.

---

## Cómo continuar el desarrollo

El plan completo está en [`CHANGES.md`](CHANGES.md): 30 Changes en fases, con dependencias, lecturas previas y decisiones abiertas para cada uno.

1. **Siguiente Change:** C-02 `modelo-base-consultorios-seed`. C-01 `foundation-setup` ya está implementado y archivado en [`openspec/changes/archive/2026-11-04-foundation-setup/`](openspec/changes/archive/2026-11-04-foundation-setup/). Todavía no está propuesto.
2. **Antes de proponer un Change:**
   - leer su ficha en `CHANGES.md` y los archivos de la Knowledge Base que indica;
   - verificar que sus dependencias estén en `openspec/changes/archive/`;
   - resolver con el autor las preguntas abiertas que lo bloquean.
3. **Ciclo de cada Change:**
   ```
   /opsx:explore <nombre>   (opcional)
   /opsx:propose <nombre>
   /opsx:apply <nombre>     (TDD estricto)
   Verify                   (openspec validate --strict + pytest + evidencia en el Change)
   /opsx:archive <nombre>   (solo si Verify pasó)
   ```
4. **Al archivar un Change completo:** marcarlo `[x]` en `CHANGES.md`. El Change académico **no** marca C-15.

Las reglas obligatorias del proyecto están en [`AGENTS.md`](AGENTS.md). Incluyen:
- datos ficticios;
- ningún dato clínico;
- aislamiento real entre consultorios;
- ninguna decisión abierta resuelta sin el autor;
- commits solo con autorización.

---

## Datos ficticios

> ⚠️ Este repositorio es académico. **Todos los datos de desarrollo, pruebas, ejemplos y capturas son ficticios.** Las pruebas usan los profesionales `PROF-A` y `PROF-B`, la fecha 2026-11-02 y la zona horaria UTC-03:00. Nunca se deben cargar datos reales de pacientes, profesionales ni consultorios, ni agregar datos clínicos (historia clínica u odontograma) al MVP. Una futura versión productiva deberá definir sus propios controles para datos reales.

---

## Entorno de desarrollo con Docker Compose (C-01 `foundation-setup`)

> **Estado:** C-01 `foundation-setup` está **implementado y archivado** el 2026-11-04 en [`openspec/changes/archive/2026-11-04-foundation-setup/`](openspec/changes/archive/2026-11-04-foundation-setup/), con su verificación en `verify.md`. Esta sección documenta cómo usar el entorno. Todo usa **datos ficticios** y solo servicios locales. Archivar C-01 no completa C-15.

### Requisitos

| Herramienta | Para qué | Versión verificada |
|---|---|---|
| Windows 11 con Docker Desktop (backend WSL 2) | Ejecutar `db`, `api` y `frontend` | Docker 29.9.2, Docker Compose v5.6.1 |
| Windows PowerShell 5.1 | Ejecutar `scripts/test.ps1` (no hace falta PowerShell 7) | 5.1 |

No hace falta instalar Python, Node ni PostgreSQL en el equipo: todo corre en contenedores. El repositorio debe estar fuera de OneDrive (por ejemplo, `C:\dev\turnos_odontologia`).

### Puesta en marcha

```powershell
copy .env.example .env
docker compose up -d --build
```

`.env.example` contiene solo valores locales ficticios (por ejemplo, usuario y contraseña `app`); `.env` está ignorado por Git. `docker compose up` levanta `db`, `api` y `frontend`, no la base de pruebas.

| Qué | URL |
|---|---|
| Frontend (React) | http://localhost:5173 |
| Documentación de la API (Swagger) | http://localhost:8000/docs |
| Salud de la API | http://localhost:8000/api/health (responde `{"status":"ok"}` sin consultar la base) |

Los puertos se publican solo en `127.0.0.1`. La API y el frontend se recargan solos al editar archivos (con sondeo, por el bind mount de Windows).

### Migraciones (comando explícito)

La API **nunca** migra al arrancar. Para aplicar las migraciones a la base de desarrollo:

```powershell
docker compose run --rm api alembic upgrade head
```

La única migración de C-01 habilita la extensión `btree_gist` (infraestructura); no crea tablas de dominio.

### Pruebas (comando único)

```powershell
.\scripts\test.ps1
```

Si PowerShell no permite ejecutar scripts: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1`. Requiere Docker Desktop en ejecución y el archivo `.env`. Ejecuta, en orden y deteniéndose en el primer fallo: autoprueba del runner, construcción de imágenes, pruebas unitarias del backend (incluye las 19 de superposición), migraciones sobre la base de pruebas, pruebas de integración contra PostgreSQL real, verificación de tipos y pruebas del frontend (Vitest). Termina con código 0 solo si todo pasa.

- **Base de pruebas separada:** las pruebas de integración y las migraciones del comando único usan el servicio `db-test` (misma imagen de PostgreSQL, datos en memoria, sin volumen ni puertos publicados, perfil `test`) con `TEST_DATABASE_URL`. Nunca tocan la base de desarrollo; una guardia se niega a ejecutar si la URL de pruebas coincide con la de desarrollo. `scripts/test.ps1` elimina `db-test` al terminar, incluso si hay un fallo.
- **`--no-deps`:** los comandos de prueba usan `docker compose run --rm --no-deps ...` para no arrancar la base de desarrollo. Sin `--no-deps`, `docker compose run api ...` arranca `db` porque `api` depende de ella.

### Estructura de C-01

```
backend/    app/{main.py, core/, api/, schemas/, models/, repositories/, domain/}, alembic/, tests/{unit,integration,isolation}
frontend/   src/{App.tsx, main.tsx, features/, shared/, pages/}, vite.config.ts, tsconfig.json (strict)
scripts/    test.ps1 (comando único), lib/Pasos.ps1, tests/autoprueba.ps1
docker-compose.yml, .env.example, .gitattributes
```

### Dependencias, detener y borrar datos

- **Reconstruir dependencias:** backend, `docker compose build api`; frontend, `docker compose build frontend` y luego `docker compose run --rm frontend npm ci` (los `node_modules` viven en el volumen `frontend_node_modules`, no en la carpeta del repositorio).
- **Detener** sin perder datos: `docker compose stop` (o `docker compose stop db`, etc.). Volver a levantar: `docker compose up -d`.
- **Borrar la base de desarrollo local (acción destructiva, solo manual del usuario):** `docker compose down -v` elimina los contenedores **y los volúmenes** `pgdata` y `frontend_node_modules`, y con ellos todos los datos locales (ficticios). Ejecutarlo únicamente si se quiere empezar de cero; no forma parte de ningún script ni de las pruebas.

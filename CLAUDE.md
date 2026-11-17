# turnos_odontologia — Instrucciones para Agentes

> Este archivo (y su copia idéntica `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado con `agent-instruction` a partir de `knowledge-base/`, `CHANGES.md` y `.atl/skill-registry.md`; reglas duras confirmadas por el autor (Santiago Chepilla) el 2026-10-13. No editar a mano sin re-sincronizar ambos archivos.

SaaS multi-consultorio de turnos odontológicos (Argentina). MVP académico v0.1 para Metodología I, una sola persona desarrolladora. Problema central: evitar errores y superposiciones de turnos (D1).

---

## Stack Tecnológico

Copia de `knowledge-base/02_descripcion_general.md` §Stack tecnológico (DD-10):

| Capa | Tecnologías | Versión mínima | Estado |
|---|---|---|---|
| Frontend | React con Vite | A definir al iniciar | [DEC] |
| Componente de agenda (vistas diaria y semanal) | Librería de calendario para React (por ejemplo, FullCalendar) | A definir | [PROP] candidata, no elegida |
| Backend (API REST) | FastAPI | A definir al iniciar | [DEC] |
| Acceso a datos | SQLAlchemy 2 | 2.x | [DEC] |
| Migraciones | Alembic | A definir | [DEC] |
| Validación y esquemas | Pydantic | A definir | [DEC] |
| Base de datos | PostgreSQL | A definir | [DEC] |
| Pruebas del backend | pytest | A definir | [DEC] |
| Pruebas del frontend | Vitest | A definir | [DEC] |
| Entorno local | Docker Compose | A definir | [DEC] preferido por el autor |
| Autenticación | **Sin definir** (requisitos en `08_arquitectura_propuesta.md`) | — | [ABIERTA] PA-03 |

> **Decisión posterior (Etapa 4, autor, 2026-10-13):** el frontend React + Vite se escribe en **TypeScript**. Es posterior a Discovery y a la aprobación de la KB, no la modifica retrospectivamente (DD-10 sigue sin fijar el lenguaje) y está registrada en `CHANGES.md` §Cómo usar este documento. Backend: FastAPI con Python; base de datos: PostgreSQL.

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/` (aprobada por el autor el 2026-10-13). **Leé el archivo relevante ANTES de implementar.** Convenciones de etiquetas ([DEC], [REQ], [PROP], [SUP], [ABIERTA]): ver [knowledge-base/README.md](knowledge-base/README.md).

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito, alcance v0.1 y fuera de alcance |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack, arquitectura general, integraciones |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Roles, matriz RBAC, rutas públicas |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, relaciones, restricciones, seed |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-AG, RN-TU, RN-MT, RN-AU, RN-PA, RN-GL) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario US-001 a US-026 por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos de punta a punta |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura, aislamiento, seguridad, pruebas, variables de entorno |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones DD-01 a DD-14 y supuestos SU-01 a SU-10 |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Preguntas abiertas (PA, P, M, T, NE) a resolver ANTES del Change que bloquean |

> ⚠️ Las preguntas de prioridad **Alta** de `10_preguntas_abiertas.md` se resuelven antes del propose del Change que bloquean (ver "Decisiones previas al propose" de cada Change en `CHANGES.md`). Según `CHANGES.md`, C-01 no tiene PA bloqueantes y el recorte académico de C-15 no depende de PA-07.

---

## Skills Disponibles

Fuente de verdad: [.atl/skill-registry.md](.atl/skill-registry.md). En `find-skill` (2026-10-13) el autor decidió **no instalar skills de dominio** por ahora (5 pospuestas, 1 descartada; detalle en `.active-orchestrator-state.json` → `skills`). Skill propia del proyecto: `verificar-aislamiento-consultorios`, creada con `skill-creator` el 2026-11-17 y versionada en `.claude/skills/verificar-aislamiento-consultorios/`.

| Agente (perfil técnico) | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | Dominio, FastAPI, SQLAlchemy, migraciones | Ninguna instalada (decisión de `find-skill`) |
| **Backend Aux** | Datos de pacientes, privacidad, servicios auxiliares | Ninguna instalada (decisión de `find-skill`) |
| **Frontend** | React + Vite + TypeScript, Vitest | Ninguna instalada (decisión de `find-skill`) |
| **Orquestación** | Fundación Active Stack, KB, roadmap, reglas | `active-orchestrator`, `kb-creator`, `roadmap-generator`, `agent-instruction` (declarada como `agents-md-generator`) |
| **Investigación** | Discovery y fuentes de mercado | `discovery-research`, `web-scraper` |
| **Mantenimiento de skills** | Buscar o crear skills | `find-skill` (declarada como `find-skills`), `skill-creator` |
| **Verificación de aislamiento** | Revisión de solo lectura del aislamiento entre consultorios: RLS, roles y privilegios de PostgreSQL, credenciales de la API y evidencia de pruebas (controles V-01 a V-10) | `verificar-aislamiento-consultorios` (skill propia, `.claude/skills/verificar-aislamiento-consultorios/`) |

Los perfiles "Backend Core / Backend Aux / Frontend" son responsabilidades técnicas, no personas: hay un solo desarrollador y la ejecución es secuencial. Comandos de flujo OpenSpec disponibles: `/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive`, `/opsx:sync`, `/opsx:update` (no hay `/opsx:verify`; ver Flujo de Trabajo).

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; **versionado en Git** como entregable de Metodología I desde el commit 107dd3c). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md) (aprobado por el autor el 2026-10-13). Resumen:

- **Total**: 30 changes (C-01 a C-30) en 9 fases con changes, más una FASE 9 informativa sin changes.
- **Camino crítico** (10): `C-01 → C-02 → C-03 → C-04 → C-07 → C-09 → C-15 → C-16 → C-20 → C-21`.
- **Línea de corte** (20): C-01 a C-04 y C-06 a C-21. Es una propuesta para demostrar el MVP, no obligatoria para la próxima entrega.
- **Primer change de desarrollo**: C-01 `foundation-setup` (infraestructura; no es el Change académico).
- **Change académico**: alcance académico inicial de C-15. Es una función o servicio puro de dominio en Python que impide solapamientos de turnos por profesional, con pruebas pytest. Nombre propuesto en OpenSpec: `validacion-superposicion-turnos`, que se confirma en Propose. Según `CHANGES.md`, su dependencia real es C-01 (proyecto Python con pytest).
- **Preparación mínima ≠ C-01**: una preparación mínima de Python y pytest para ejecutar las pruebas del recorte **no equivale a completar C-01** `foundation-setup` (Docker Compose, PostgreSQL con `btree_gist`, FastAPI, frontend, Vitest y README). C-01 sigue pendiente hasta cumplir todo su alcance; si esa preparación se hace dentro del recorte, se documenta en Propose.
- **Candidatas** (C-24 a C-30: reserva online, comunicación y trazabilidad) y **posteriores** (FASE 9): solo planificadas, fuera del camino crítico.

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change, los archivos de "Leer antes" y sus "Decisiones previas al propose".

---

## Reglas Duras (específicas del proyecto)

> Reglas **globales** ya definidas en `~/.claude/CLAUDE.md` (orquestador, delegación, OpenSpec como fuente de estado, governance, TDD estricto, engram, modelos por fase): el proyecto las **hereda**, no se repiten acá. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubre (Git). Son contrato; romperlas es un defecto.

### Dominio y datos

- **D1 — Datos ficticios.** NUNCA usar datos reales de pacientes, profesionales o consultorios en desarrollo, pruebas, seed, ejemplos, capturas ni en el repositorio académico → usar solo datos ficticios (DD-13, RN-PA-08). Esta regla no limita a una futura versión productiva, que gestionará datos reales con los controles que se definan en su momento.
- **D2 — Sin datos clínicos.** NUNCA agregar historia clínica, odontograma ni campos clínicos al MVP → solo la ficha básica del paciente (D3, RN-PA-09).
- **D3 — Sin solapamientos por profesional.** NUNCA aceptar un turno que se superponga con otro turno que ocupa agenda del **mismo profesional** (RN-AG-02, R2) → validarlo en el dominio y, cuando exista persistencia, también con la restricción de exclusión de PostgreSQL. La convención de intervalos semiabiertos `[inicio, fin)`, según la cual los consecutivos se aceptan (RN-AG-04), es **propuesta** y se confirma en Propose. Qué estados ocupan agenda lo define PA-07, no el agente.
- **D4 — Sillones y boxes.** NUNCA modelar sillones o boxes como recurso de agenda ni asumir que el control por profesional evita conflictos de sillón → es la pregunta abierta PA-01; documentarlo como limitación.
- **D5 — Aislamiento real entre consultorios.** En operaciones privadas, NUNCA tomar `consultorio_id` del body, query, header ni de ningún dato enviado por el cliente → derivarlo de la identidad autenticada (RN-MT-02). NUNCA considerar suficiente un filtro por consultorio → sumar la barrera en base que decida PA-04 y una prueba de acceso cruzado por cada endpoint (RN-MT-06). Los futuros endpoints públicos (por ejemplo, la reserva online, candidata D4) requieren un diseño explícito de seguridad y autorización, **pendiente**: NUNCA implementarlos ni inventar su mecanismo sin decisión del autor.
- **D6 — Decisiones abiertas.** NUNCA resolver por cuenta propia una pregunta abierta (PA-xx, P-xx, NE-xx) ni completar un dato sin evidencia → detenerse, consultar al autor y marcar "Pendiente" o "No evidenciado".
- **X1 — Datos sensibles fuera de logs.** NUNCA escribir en logs ni en mensajes técnicos datos personales del paciente ni la prestación del turno → tratarlos como posiblemente sensibles (D9, RN-PA-03).

### OpenSpec y verificación

- **O1 — Especificación y dependencias.** NUNCA implementar sin un Change propuesto ni fuera de su especificación aprobada → si cambia el alcance, actualizar primero la especificación, con aprobación del autor. Antes de proponer: leer `CHANGES.md` y los "Leer antes", y comprobar que las dependencias estén archivadas. Usar como nombre el que figura entre comillas invertidas en `CHANGES.md`, nunca `C-NN`. Las candidatas (C-24 a C-30) solo se proponen con decisión del autor.
  - **Recorte académico de C-15**: está autorizado como un Change independiente de lógica de dominio pura. NUNCA afirmar que C-15 completo o sus dependencias funcionales (C-08, C-09, C-10, C-12 y, a través de ellas, C-02 a C-04) están implementados. NUNCA marcar C-15 como completado al archivar el recorte. NUNCA presentar la preparación mínima de Python y pytest del recorte como C-01 implementado: C-01 se completa solo con su alcance propio. Su alcance exacto (reglas, escenarios, exclusiones y decisiones abiertas que afecten el comportamiento) se resuelve y documenta en Propose, antes de Apply.
- **O2 — Verify y Archive.** El flujo OpenSpec puede ser flexible (global), pero **Archive es obligatoriamente condicional**. Para archivar hace falta:
  - `openspec validate <change> --strict` sin errores (comando de la versión instalada, 1.14.1);
  - pytest exitoso;
  - todos los escenarios de la especificación cubiertos por pruebas automatizadas;
  - registro en el Change de los comandos ejecutados, los resultados y la evidencia de las pruebas.

  NUNCA archivar con pruebas o validaciones fallidas. No hace falta un comando `/opsx:verify`.

### Stack

- **S1 — Python.** Nombres en `snake_case` y anotaciones de tipo en las funciones públicas. NUNCA esquemas Pydantic de entrada sin `extra='forbid'` → rechazar campos no declarados (además impide colar `consultorio_id`, D5).
- **S2 — TypeScript.** `tsconfig` con `strict: true`; componentes en `PascalCase`. NUNCA usar `any` → tipar de forma estricta; cualquier excepción se justifica y la aprueba el autor antes de incorporarse.
- **X2 — Pruebas y base de datos.** Las pruebas del módulo puro del Change académico no requieren Docker ni PostgreSQL (dominio sin I/O). NUNCA simular la base en las pruebas de restricciones de base, concurrencia o aislamiento → usar PostgreSQL real (Docker Compose) cuando se implementen.
- **X3 — Servicios externos.** En el MVP académico, usar herramientas y servicios locales. NUNCA contratar, conectar ni configurar servicios externos o de nube sin autorización explícita del autor (DD-11, PA-02). No es una prohibición definitiva para el producto futuro.
- **X4 — Idioma.** Documentación, artefactos de OpenSpec y mensajes al autor en español. Los identificadores de dominio siguen la KB (`Turno`, `Profesional`, `Consultorio`, `Prestacion`, `Paciente`).

### Git (no cubierto por el global)

- **G1 — Commits solo con autorización explícita del autor.** NUNCA commitear automáticamente → presentar antes los archivos y el mensaje, y esperar el "sí".
  - NUNCA `git add .` → agregar solo los archivos del avance aprobado.
  - Antes del commit: `git status --short` y `git diff --check` (o `git diff --cached --check` si ya están en stage).
  - NUNCA incluir `.env`, secretos, credenciales, datos reales de pacientes ni archivos temporales.
  - Mensajes descriptivos con prefijo convencional (por ejemplo, `docs:`, `chore:`, `feat:`).
  - NUNCA agregar la línea `Co-Authored-By` → solo si el autor la autoriza expresamente.
  - NUNCA `git push`, `git reset --hard`, `git rebase` ni `git commit --amend` sin autorización específica.
  - NUNCA reescribir el historial ni modificar fechas de commits. Esto incluye no modificar commits ya existentes como 107dd3c.
  - Después de cada commit: mostrar hash, mensaje y `git status --short`.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)          → entender el dominio
2. Identificar el change en CHANGES.md             → dependencias, "Leer antes", decisiones previas
3. /opsx:explore <nombre>   (opcional)             → pensar antes de comprometer
4. /opsx:propose <nombre>                          → proposal + design + specs + tasks; resolver decisiones abiertas
5. /opsx:apply <nombre>                            → implementar las tasks con TDD estricto y las reglas duras
6. Verify (sin comando propio)                     → openspec validate <nombre> --strict + pytest + evidencia en el Change (O2)
   Si el Change toca endpoints privados, consultorio_id, migraciones o permisos → skill verificar-aislamiento-consultorios (solo lectura)
7. /opsx:archive <nombre> + marcar [x] en CHANGES  → solo si Verify pasó; el recorte académico NO marca C-15
8. Commit                                          → solo con autorización del autor (G1)
```

`<nombre>` es el nombre del Change entre comillas invertidas en `CHANGES.md` (por ejemplo, `foundation-setup`), sin el prefijo `C-NN`.

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen. Ante una decisión abierta, frenar y consultar al autor (D6).

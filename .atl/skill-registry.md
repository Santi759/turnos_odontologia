# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

Nota: la plantilla de `skill-registry` remite a `_shared/skill-resolver.md` para el protocolo completo de resolución, pero **ese archivo no existe** en esta instalación (no hay carpeta `_shared` en `~/.claude/skills` ni en `~/.config/opencode/skills`). El protocolo vigente es el descrito en este archivo: el delegador copia los bloques de *Compact Rules* que correspondan en el prompt del subagente.

Proyecto: turnos_odontologia (SaaS multi-consultorio de turnos odontológicos, MVP académico). Generado el 2026-10-13. No hay skills instaladas de dominio (React/FastAPI/pytest/etc.): el autor decidió no instalar ninguna en `find-skill` (`skills.installed` = []). Todas las skills registradas son de fundación/orquestación. Las rutas usan `~` (carpeta del usuario) en lugar de la ruta absoluta local.

**Inconsistencias conocidas en skills globales (documentadas, no modificadas):** la carpeta `find-skill` declara `name: find-skills`; la carpeta `agent-instruction` declara `name: agents-md-generator`; `discovery-research` todavía menciona `jr-orchestrator` y `.jr-orchestrator-state.json` (nombres anteriores de `active-orchestrator` y `.active-orchestrator-state.json`).

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| /active-orchestrator:init, :kb, :rules, :discovery, :openspec, :devops, :find-skill; o cuando el usuario quiere arrancar un proyecto desde cero con el flujo de fundación SDD/OpenSpec | active-orchestrator | ~/.claude/skills/active-orchestrator/SKILL.md |
| Crear/generar/actualizar AGENTS.md o CLAUDE.md, "armar las reglas del proyecto", "instrucciones para los agentes", "generar claude.md", o tras correr kb-creator + roadmap-generator (name en frontmatter: `agents-md-generator`) | agent-instruction | ~/.claude/skills/agent-instruction/SKILL.md |
| Cuando se despacha la fase discovery del flujo de fundación, o el usuario quiere investigar el mercado / pensar qué construir antes de tener claridad (derivado de la descripción) | discovery-research | ~/.claude/skills/discovery-research/SKILL.md |
| "how do I do X", "find a skill for X", "is there a skill that can...", interés en extender capacidades (derivado de la descripción; name en frontmatter: `find-skills`) | find-skill | ~/.claude/skills/find-skill/SKILL.md |
| Crear/construir/generar una knowledge base, documentar un proyecto desde fuentes (.txt, .docx, .pdf), "armar base de conocimiento" / "crear KB" / "documentar proyecto" | kb-creator | ~/.claude/skills/kb-creator/SKILL.md |
| Crear/regenerar/actualizar CHANGES.md, roadmap, mapa de changes, plan de implementación; "armar CHANGES", "armar roadmap", "qué changes necesito", "índice de changes" | roadmap-generator | ~/.claude/skills/roadmap-generator/SKILL.md |
| Crear una skill nueva, modificar/mejorar una existente, correr evals/benchmarks, optimizar la descripción de una skill (derivado de la descripción) | skill-creator | ~/.claude/skills/skill-creator/SKILL.md |
| Pedido de investigar/scrapear un competidor a partir de una URL, o invocada por discovery-research durante Discovery (derivado de la descripción) | web-scraper | ~/.claude/skills/web-scraper/SKILL.md |

## Project Skills

Skills propias de este proyecto, versionadas en el repositorio (no en `~/.claude/skills`).

| Trigger | Skill | Path |
|---------|-------|------|
| Verificar, auditar o revisar el aislamiento entre consultorios, RLS, roles, privilegios de PostgreSQL, acceso cruzado o la matriz escenario-prueba; Verify o Archive de un Change que toque endpoints privados, `consultorio_id`, migraciones o permisos; pedidos de credenciales "para verificar" | verificar-aislamiento-consultorios | .claude/skills/verificar-aislamiento-consultorios/SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### active-orchestrator
- Orquestador fino del flujo de fundación: `openspec init` -> [discovery-research] -> kb-creator -> roadmap-generator -> find-skill -> skill-registry -> agent-instruction.
- NUNCA reimplementar la lógica de una fase: enrutar siempre a su sub-skill (Skill para fases interactivas, Agent para mecánicas).
- NUNCA preguntar contenido estratégico (tipo de sistema, escala, stack, problema, checklist de Discovery): pertenece a kb-creator y discovery-research.
- Es dueño SOLO del archivo de estado `.active-orchestrator-state.json` y del campo `step`; cada sub-skill escribe únicamente su propia sección.
- Checkpoint obligatorio entre fases: nunca avanzar `step` sin confirmación explícita del usuario; tras cada AskUserQuestion, parar y esperar.
- NUNCA instalar nada de forma autónoma: find-skill recomienda, el usuario elige (efecto HIGH en skills globales).
- Retomar con la lógica de resume del estado compartido; no volver a correr lo que ya existe (idempotente a nivel de flujo).

### agent-instruction
- Pre-checks: requiere `knowledge-base/` y `02_descripcion_general.md`; si falta `CHANGES.md`, generar igual pero omitir la sección Roadmap y avisar.
- Salida: `AGENTS.md` y `CLAUDE.md` en la RAÍZ con el mismo contenido (copia, no referencia); nunca dentro de `.claude/` ni `openspec/`. Validar con `diff AGENTS.md CLAUDE.md`.
- Fuente de verdad de skills: `.atl/skill-registry.md` (no re-escanear). Mapear skill->rol de agente; no inventar skills inexistentes.
- DRY: NO copiar los compact rules en AGENTS.md; solo mapeo skill->rol y referencia al registry.
- NO repetir el CLAUDE.md global (`~/.claude/CLAUDE.md`): verificar qué reglas universales trae realmente; las ausentes (commits/build/co-autoría) se escriben en el proyecto.
- Única parte interactiva: reglas duras derivadas del stack real; confirmarlas con AskUserQuestion, esperar, y escribir SOLO las confirmadas ("NUNCA X -> hacer Y").
- Secciones obligatorias: Stack, Base de Conocimiento, Skills Disponibles, Roadmap de Changes, Reglas Duras, Flujo de Trabajo.

### discovery-research
- Fase de Discovery previa a la KB (gobernanza MEDIA): Fuentes -> Checklist Q&A (11 puntos, `references/checklist.md`) -> Gate final -> Escribir.
- Si hay URLs de competidores, invocar `web-scraper` una vez por URL; no reimplementar scraping. Sin URLs, seguir con Q&A pura.
- Con scraping previo, correr `scripts/collect_sources.py` y no repreguntar lo ya resuelto.
- Riesgos y preguntas abiertas: distinguir hecho verificado vs supuesto sin probar.
- NUNCA escribir `discovery/discovery.md` ni tocar el estado sin confirmación explícita del resumen por el usuario.
- Escribir en prosa legible; actualizar SOLO la sección `discovery` del archivo de estado (no version/step/owner ni otras secciones).
- No decide si corresponde hacer Discovery; su salida es insumo de kb-creator, no lo reemplaza.

### find-skill
- Frontmatter name real: `find-skills` (carpeta `find-skill`). Descubre/instala skills con `npx skills find|add|update` (catálogo https://skills.sh/).
- Antes de buscar, mirar el leaderboard de skills.sh; luego `npx skills find <query>`.
- Verificar calidad antes de recomendar: instalaciones (preferir 1K+; cuidado con <100), reputación de la fuente, estrellas del repo (<100 = escepticismo).
- Presentar: nombre y qué hace, installs y fuente, comando de instalación, enlace a skills.sh.
- Instalar solo si el usuario acepta (`npx skills add <owner/repo@skill> -g -y`). En este proyecto el autor decidió NO instalar ninguna skill adicional.
- Si no hay resultados: decirlo y ofrecer ayudar directamente.

### kb-creator
- Modo auto-detectado: A (silencioso, desde fuentes en `docs/`) o B (interactivo, desde cero). Si existe `knowledge-base/` completa, no regenerar: sugerir ediciones puntuales.
- Salida SIEMPRE en `knowledge-base/` en la raíz; NUNCA mezclar con `docs/`.
- 10 archivos canónicos con nombres exactos: 01_vision_y_objetivos, 02_descripcion_general, 03_actores_y_roles, 04_modelo_de_datos, 05_reglas_de_negocio, 06_funcionalidades, 07_flujos_principales, 08_arquitectura_propuesta, 09_decisiones_y_supuestos, 10_preguntas_abiertas (.md) + `README.md` índice.
- Extras permitidos con prefijo 1X_/2X_ en kebab-case; nunca reemplazan a los canónicos. Plantillas en `assets/canonical-templates.md`.
- Modo A: sin preguntas; las dudas van a `10_preguntas_abiertas.md`. Modo B: 3-5 preguntas estratégicas, esperar respuesta, iterar archivo por archivo; marcar supuestos con `**Suposición:**`.
- Si existe sección `discovery` de nivel superior en el estado, leerla como insumo; ejecutar el hook de estado de `assets/state-contract.md` al terminar.

### roadmap-generator
- Genera UN archivo `CHANGES.md` en la raíz (no dentro de `openspec/`); fire-and-forget, sin preguntas.
- Pre-checks: `knowledge-base/` con los 10 canónicos y `openspec/` existente; si fallan, NO generar y avisar.
- Leer siempre KB 04, 06, 07, 08; opcional 03, 05, 10. Si orquestado, usar `state.kb.files` como lista autoritativa.
- La estructura de primer nivel de CHANGES.md es contrato: no agregar ni quitar secciones (árbol de dependencias, paralelismo por GATES, camino crítico, plan con 3 agentes, FASEs con `[C-NN]` en kebab-case).
- Cada change es atómico (~4-6 h), con estado `[ ]`, scope, governance, dependencias y "Leer antes" hacia la KB.
- Si CHANGES.md ya existe y se quiere tocar un solo change, sugerir edición puntual.

### skill-creator
- Flujo: capturar intención -> entrevista/investigación -> escribir SKILL.md -> casos de prueba -> evaluar -> iterar.
- SKILL.md: frontmatter con `name` y `description` (la descripción es el mecanismo de triggering: incluir cuándo usarla).
- Evaluación: lanzar en el mismo turno corridas con skill y baseline; redactar assertions mientras corren; usar el viewer de evals para revisión humana.
- Iterar generalizando desde el feedback (no sobreajustar a los casos); mantener el prompt conciso.
- Optimización de descripción: generar queries de trigger (deben/no deben activar), revisar con el usuario, correr el loop de optimización.
- Solo usar cuando se crea/mejora una skill; no aplica al desarrollo del producto de turnos.

### web-scraper
- Entrada: URL(s) http(s) de competidores; usa WebFetch/WebSearch sin API keys. Salida: `discovery/sources/<slug>.md` (slug con `scripts/slugify.py`).
- Esquema de salida FIJO de 8 campos, siempre en el mismo orden (`references/output-schema.md`; plantilla `assets/example-source-note.md`).
- NUNCA inventar datos: campo sin información pública = `(no publicado)`.
- Ante contenido vacío, SPA sin datos o bloqueo (403, paywall, CAPTCHA): NO evadir; reportar la limitación y seguir con la siguiente URL.
- Procesar URLs una por una e informar cuántas se resolvieron y cuántas fallaron; no abortar el lote.
- Sin crawling ni scraping masivo; sitios con JS pesado o anti-bot no están soportados en v1.

### verificar-aislamiento-consultorios
- Skill propia del proyecto (creada con `skill-creator` el 2026-11-17). Solo lectura por defecto: el único archivo que puede escribir es el informe, en una ruta autorizada.
- Nunca modificar `openspec/changes/archive/`; nunca abrir `.env` ni `.env.example`; nunca mostrar contraseñas, URLs con credenciales, hashes, tokens ni rutas personales.
- Modos: `estatico` (por defecto), `pruebas` (`scripts/test.ps1`) y `catalogo` (SELECT de `references/consultas-catalogo.sql`); los dos últimos solo con autorización expresa e independiente del autor.
- Aplicar los controles V-01 a V-10 de `references/controles.md`; cada control lleva estado Cumple / No cumple / No evidenciado, origen (Verificado ahora / Citado del historial) y evidencia reproducible (comando o `ruta:linea`).
- Identificar el commit HEAD revisado; en modo estático no afirmar que las pruebas pasan hoy.
- Informe con `references/plantilla-informe.md` y veredicto GO / NO-GO; sanear el texto antes de entregarlo.

## Project Conventions

**No existen `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `GEMINI.md` ni `copilot-instructions.md` en la raíz del proyecto todavía** (los generará `agent-instruction` más adelante). Lo que existe hoy:

| File | Path | Notes |
|------|------|-------|
| openspec/config.yaml | openspec/config.yaml | Configuración del flujo OpenSpec del proyecto |
| CHANGES.md | CHANGES.md | Roadmap operativo: 30 changes (C-01..C-30); alcance académico inicial en C-15. Leer antes de cualquier `/opsx:propose` |
| knowledge-base/README.md | knowledge-base/README.md | Índice de la KB (10 archivos canónicos `01_..10_*.md` en `knowledge-base/`) |
| discovery/ | discovery/ | Resultado de Discovery (`discovery.md`, `sources/`) |
| docs/ | docs/ | Documentos fuente / documentación de discovery |
| .active-orchestrator-state.json | .active-orchestrator-state.json | Estado compartido del flujo de fundación |

### Comandos de workflow OPSX (comandos, no skills)

| Comando | Path | Notes |
|---------|------|-------|
| /opsx:explore | .claude/commands/opsx/explore.md | Explorar ideas y requisitos |
| /opsx:propose | .claude/commands/opsx/propose.md | Crear un change con todos sus artefactos |
| /opsx:apply | .claude/commands/opsx/apply.md | Implementar tareas de un change |
| /opsx:archive | .claude/commands/opsx/archive.md | Archivar un change completado |
| /opsx:sync | .claude/commands/opsx/sync.md | Sincronizar delta specs a main specs |
| /opsx:update | .claude/commands/opsx/update.md | Revisar artefactos de planificación de un change |

Stack del proyecto: React + Vite + TypeScript, FastAPI + SQLAlchemy 2 + Alembic + Pydantic, PostgreSQL, pytest + Vitest, Docker Compose.

Read the convention files listed above for project-specific patterns and rules. All referenced paths have been extracted — no need to read index files to discover more.

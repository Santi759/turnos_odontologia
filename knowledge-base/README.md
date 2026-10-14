# turnos_odontologia — Base de Conocimiento

Base de conocimiento de la **Etapa 3** del trabajo práctico de Metodología I. Se generó con `kb-creator` en modo mixto (una ronda de preguntas al autor y generación a partir de documentos) el 2026-10-13.

- **Autor del proyecto**: Santiago Chepilla
- **Versión del alcance**: v0.1 — MVP académico
- **Estado**: aprobada por el autor el 2026-10-13 (versión corregida tras la auditoría final de 16 observaciones)

## Fuentes

| Fuente | Uso |
|---|---|
| `discovery/discovery.md` (aprobado el 2026-10-10) | Problema, roles, CU1–CU5, alcance, R1–R6, integraciones, restricciones, RG1–RG7, 19 preguntas abiertas, D1–D9 |
| `docs/discovery/informe-discovery.md` (versión final, 2026-10-13) | Estudio de 18 sistemas: funciones estándar, diferenciadores, vacíos, MVP sugerido, tensiones, preguntas del mercado |
| `docs/discovery/checklist-discovery.md` | Checklist estructurado de 11 puntos (réplica de Discovery con evidencia) |
| `docs/discovery/fuentes.md` | Trazabilidad de URLs |
| `docs/discovery/metodologia/` | Rúbrica (C1–C7) y matriz de puntuación |
| Sección `discovery` de `.active-orchestrator-state.json` | Datos estructurados de Discovery |
| Respuestas del autor (2026-10-13) | Stack (DD-10), infraestructura (DD-11), sillones (DD-12), datos ficticios (DD-13), clasificación técnica (DD-14) |

## Convenciones

Cada afirmación lleva su origen (`D#`, `R#`, `CU#`, `RG#`, `P-##`, sección del informe) y una de estas etiquetas:

| Etiqueta | Significado |
|---|---|
| **[DEC]** | Decisión del autor, con el **estado original** que tiene en `09_decisiones_y_supuestos.md`. No todas las D# están "decididas": varias son propuestas. |
| **[REQ]** | Requisito de la v0.1: forma parte del núcleo del MVP propuesto por el autor en Discovery §5, de una regla R1–R6 o de una decisión confirmada en la Etapa 3, **o es una consecuencia necesaria de alguno de ellos**, en cuyo caso se marca "[REQ] (derivada)" e indica de qué se deriva. R1–R6 siguen siendo propuestas del autor **pendientes de validar con consultorios** (RG2). [REQ] no significa "incluido en el primer Change": la priorización y la división en Changes se hacen en el roadmap. Las buenas prácticas técnicas que agregó esta KB no son [REQ], sino [PROP] "requisito técnico propuesto". |
| **[PROP]** | Propuesta o candidata: D4–D7 y D9, sugerencias del informe §6.3 o propuestas técnicas de esta KB. Requiere decisión antes de implementarse como definitiva. |
| **[SUP]** | Supuesto inferido (SU-01 a SU-10), con su forma de validación. |
| **[ABIERTA]** | Incertidumbre o pregunta sin resolver; está en `10_preguntas_abiertas.md`. |
| **[MERCADO]** | Evidencia del estudio de 18 sistemas. Describe lo que publica el mercado; **no es una decisión del producto**. "No evidenciado" significa sin respaldo público, no que la función no exista. |
| **[PEND]** | Dato pendiente de verificación heredado de Discovery. |

## Índice de Archivos

| Archivo | Contenido |
|---------|-----------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, contexto de mercado (18 sistemas), objetivos por actor, alcance v0.1 (núcleo, candidatos, segunda etapa), fuera de alcance, métricas del MVP |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack elegido (DD-10), arquitectura general, integraciones (ninguna en el núcleo), recursos de la API |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, matriz de permisos por rol dentro del consultorio, rutas públicas |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Entidades, relaciones y restricciones (exclusión de solapamientos por profesional), extensión no aprobada para sillones, seed data ficticio |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | Reglas RN por dominio: multi-consultorio, autenticación, agenda, turnos, pacientes y privacidad, comunicación, reserva online |
| [06_funcionalidades.md](06_funcionalidades.md) | 9 épicas y 26 historias de usuario con estado (núcleo, candidata, segunda etapa) y dependencias de las historias del núcleo |
| [07_flujos_principales.md](07_flujos_principales.md) | 11 flujos de punta a punta, con el flujo central de creación de turnos sin superposiciones |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Capas, estructura de directorios, pruebas, requisitos y alternativas de autenticación, aislamiento en profundidad, Docker Compose, variables de entorno |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | D1–D9 con su estado original, DD-10 a DD-14 de la Etapa 3, supuestos SU-01 a SU-10 |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Inconsistencias, 19 preguntas originales, 7 del mercado, 4 tensiones, 20 nuevas y 12 vacíos "No evidenciado" |

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md)
6. Antes de codificar → [10](10_preguntas_abiertas.md), en especial las de prioridad Alta (P-01, P-05, PA-03, PA-04, PA-05, PA-07, T-02)

## Resumen Ejecutivo

turnos_odontologia es un SaaS multi-consultorio para Argentina que busca evitar errores y superposiciones de turnos en consultorios odontológicos. Su agenda respeta la duración de cada prestación, los horarios de atención de cada profesional y los períodos bloqueados, y garantiza en la base de datos que un mismo profesional no tenga dos turnos superpuestos. Es un MVP académico de una sola persona, con React, FastAPI y PostgreSQL ejecutado localmente con datos ficticios.

Quedan fuera la historia clínica, el odontograma y la gestión de obras sociales. La reserva online del paciente, los avisos por email o wa.me y la asignación de sillones o boxes siguen como candidatas o preguntas abiertas.

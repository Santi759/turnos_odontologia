# Propuesta: validacion-superposicion-turnos

## Why

El problema central del producto es evitar errores y superposiciones de turnos (Discovery D1). La regla firme R2 / RN-AG-02 ("un profesional no puede tener dos turnos superpuestos") todavía no está demostrada en ningún código. Este Change es el **alcance académico inicial de C-15** aprobado por el autor el 2026-10-13 (`CHANGES.md`, §Niveles de alcance, Nivel 2, y entrada C-15, bloque "Alcance académico inicial"): una sola funcionalidad pequeña del MVP, con una regla verificable y escenarios exitoso, de error de negocio y de caso límite, que puede completar el ciclo Explore → Propose → Apply → Verify → Archive sin depender de persistencia, endpoints ni autenticación.

## What Changes

- Se agrega un módulo de dominio puro en Python (sin base de datos, sin endpoints, sin interfaz) que decide si un turno candidato se superpone con los turnos que ocupan agenda **del mismo profesional**.
- Regla única: RN-AG-02 (R2) con la convención de intervalos semiabiertos `[inicio, fin)` (RN-AG-04), **confirmada por el autor para este Change** el 2026-10-13: turnos consecutivos no se superponen.
- Si hay superposición, el rechazo es un error de dominio de superposición con un **mensaje fijo** que no revela datos de pacientes ni del turno en conflicto (RN-GL-03).
- Entradas inválidas producen un **error de validación distinto** del de superposición: instantes sin zona horaria (naive), mezcla de instantes con y sin zona horaria, o `inicio >= fin` (invariante `inicio < fin` de KB 04 §Turno). Aplica tanto al candidato como a los turnos existentes recibidos.
- La función recibe los turnos que ocupan agenda **ya seleccionados por quien la llama**; no conoce estados (PA-07 sigue abierta). Ignora por sí misma los turnos de otros profesionales.
- Preparación mínima de Python y pytest en `backend/` (solo lo necesario para ejecutar las pruebas del recorte), que **no** constituye C-01 `foundation-setup`.

## Capabilities

### New Capabilities

- `superposicion-turnos`: regla de dominio que impide que un turno candidato se superponga con los turnos que ocupan agenda del mismo profesional, con intervalos semiabiertos `[inicio, fin)`, validación de instantes con zona horaria y rechazo con mensaje fijo sin datos sensibles.

### Modified Capabilities

Ninguna (no existen specs previas en `openspec/specs/`).

## Impact

- **Código nuevo (en Apply):** `backend/app/domain/` (módulo de la regla y sus tipos de error) y `backend/tests/unit/` (pruebas pytest). Archivos mínimos de entorno en `backend/` según `design.md`.
- **Dependencias:** Python 3.14.5 (instalado localmente) y pytest (a instalar en un entorno virtual durante Apply, con autorización del autor en ese momento).
- **APIs, base de datos, frontend:** sin impacto.
- **Roadmap:** no cambia los 30 Changes ni sus dependencias. C-15 completo reutilizará esta función dentro de `crear_turno`.
- **Gobernanza:** MEDIO (lógica de negocio pura, sin datos reales ni seguridad): implementación por pasos con checkpoints y decisiones no obvias informadas al autor.

## Fuera de alcance / Limitaciones

Este recorte **demuestra la regla en el dominio, pero NO garantiza por sí solo la ausencia de superposiciones en el sistema** (RT9). Quedan fuera, y siguen pendientes en C-15 u otros Changes:

- Persistencia: modelo `Turno`, tablas y migraciones.
- Restricción de exclusión de PostgreSQL (`btree_gist`) por profesional y rango.
- Garantía ante operaciones concurrentes (RN-AG-03) y concurrencia turno vs bloqueo u horario (PA-20).
- Endpoints (`POST /api/turnos`) y cualquier API.
- Autenticación (PA-03) y aislamiento multi-consultorio (RN-MT, PA-04).
- Gestión de estados del turno y definición de qué estados ocupan agenda (RN-AG-02b, RN-TU-05, PA-07): no se inventan estados.
- Sillones o boxes (PA-01): el control es solo por profesional; el conflicto de sillón entre profesionales distintos no se controla.
- Cálculo del fin por duración de la prestación (R1, C-08): el fin llega ya calculado.
- Franjas de atención (R3), bloqueos (R4) y rechazo de turnos en el pasado (RN-TU-06).
- Reprogramación y exclusión del propio turno (C-17): no hay identificador de turno existente.

**Estado del roadmap:** C-01 `foundation-setup` **sigue pendiente**; la preparación mínima de Python y pytest de este Change no lo completa (AGENTS.md O1). Archivar este Change **no** completa C-15: su casilla en `CHANGES.md` sigue `[ ]` hasta implementar todo su alcance.

## Trazabilidad

Discovery R2 y D1 → KB RN-AG-02 y RN-AG-04 (`knowledge-base/05_reglas_de_negocio.md`) → US-011 (`knowledge-base/06_funcionalidades.md`; criterios: "se rechaza si se superpone con otro turno que ocupa agenda del mismo profesional, indicando el motivo" y "turnos consecutivos se aceptan") → `CHANGES.md` C-15, alcance académico inicial → este Change `validacion-superposicion-turnos`, capacidad `superposicion-turnos`.

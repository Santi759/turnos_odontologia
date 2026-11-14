# Verify tecnico (grupo 12): aislamiento-roles-rbac (C-04)

> Todo contra `db-test` efimera (o sin base, en las unitarias). Nada toco `db`, `api` ni `frontend` de desarrollo, ningun `.env*`, ninguna credencial real. Datos ficticios. Ningun comando con `getpass` se ejecuto de verdad. Fecha: 2026-11-10. `openspec` 1.14.1.

## 12.1 Migracion 0004 en db-test

Ciclo manual sobre `db-test` nueva (`alembic -x target=test`):

| Comando | Resultado |
|---|---|
| `upgrade head` | `0001 -> 0002 -> 0003 -> 0004` |
| `current` | `0004 (head)` |
| `downgrade 0003` | `Running downgrade 0004 -> 0003` |
| `current` | `0003` |
| `upgrade head` | `Running upgrade 0003 -> 0004` |
| `current` | `0004 (head)` |

Pruebas (`test_migracion_aislamiento.py`, `test_migraciones.py`, `test_migracion_autenticacion.py`, `test_convenciones_esquema.py`): **50 passed** (verificacion previa de roles, subida con huella de filas igual, bajada con catalogo igual al de 0003 y roles conservados, resubida identica, `uq_sesion_consultorio_id_id`). Registrado: OK.

## 12.2 Roles y privilegios con conexiones reales

`tests/isolation/test_arnes.py`, `test_catalogo_roles.py`, `test_privilegios.py`, `test_funciones_acceso.py`, `test_login_sin_escritura.py`, `test_guardia_rol_api.py`: **163 passed** (catalogo de roles, matriz de privilegios, 42501 reales, funciones de acceso, login sin escritura de credenciales, guardias de rol). OK.

## 12.3 RLS y aislamiento entre consultorios

`test_rls.py`, `test_contexto_transaccional.py`, `test_acceso_cruzado.py`, `test_registro.py`: **42 passed**. OK.

## 12.4 Autorizacion

`tests/unit/test_autorizacion.py`, `test_consultorio_cliente.py`, `test_lecturas_de_peticion.py`, `test_comparaciones_de_rol.py`, `tests/integration/test_autorizacion_roles.py`, `test_consultorio_cliente.py`, `test_dependencias_auth.py`: **97 passed** (`require_rol`, matriz de roles, 401/403/404, 422 de `consultorio_id` y de `X-Consultorio-Id`, lista blanca de lecturas). OK.

## 12.5 Regresion de C-03 y PD-04

- `tests/isolation/test_regresion_auth.py`, `test_pool_login.py`, `test_conexiones_login.py` y `tests/unit/test_presupuesto_conexiones.py`, `test_pools_y_guardias.py`: **42 passed en cada una de 3 corridas consecutivas** (estables).
- `tests/integration` completo: **509 passed**.
- Las nueve condiciones de 5.7 en verde con la configuracion real de los pools (login 4/11, app 5/10, espera 30 s, `connect_timeout` 5; **valores sin cambios**, ver `app/core/database.py`). Ninguna prueba de concurrencia, permisos, RLS, sesiones, aislamiento ni pools fallo en esta sesion.
- Adaptaciones de pruebas de C-03 (todas justificadas en `tdd-evidencia.md`): 3 casos de `test_dependencias_auth.py` por el 422 de `consultorio_id`/`X-Consultorio-Id` (delta `validacion-entrada`); las de sesiones anteriores (firmas de `acceso_*`, rehash, apps de prueba).

OK.

## 12.6 Validacion de OpenSpec

- `openspec validate aislamiento-roles-rbac --strict`: `Change 'aislamiento-roles-rbac' is valid` (codigo 0).
- `openspec validate --specs --strict`: `Totals: 15 passed, 0 failed (15 items)` (codigo 0).

## 12.7 `scripts/test.ps1` completo (sesion 2026-11-14, tras 1.6 y 10.2)

`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1`: **codigo 0** ("Todas las suites pasaron."). Solo db-test efimera y contenedores efimeros; db-test eliminada al terminar.

| Paso | Resultado |
|---|---|
| 0. autoprueba | 22 casos `[OK]`, 0 `[FALLA]` (incluye 'Plantilla completa con valores ficticios') |
| 2. unitarias | **765 passed** (incluidas las 19 de superposicion; +3 de la plantilla de 1.6 respecto de 762) |
| 5. integracion | **509 passed** |
| 6. aislamiento (`turnos_app` y `turnos_login`) | **234 passed** |
| 7. `tsc --noEmit` | OK |
| 8. Vitest | **2 passed** (1 archivo) |

Antes del runner: pruebas de la plantilla (1.6) **23 passed**. `test_superposicion_turnos.py` no cambio. La matriz de `tdd-evidencia.md` cubre **194 de 194** escenarios (referencias verificadas contra el codigo).

Validaciones de OpenSpec de esta sesion: `openspec validate aislamiento-roles-rbac --strict` -> `Change 'aislamiento-roles-rbac' is valid` (codigo 0); `openspec validate --specs --strict` -> `Totals: 15 passed, 0 failed` (codigo 0).

## 12.8 Decision go/no-go hacia la transicion (grupo 13), reevaluada el 2026-11-14

**GO.** 12.1 a 12.7 completas y en verde con resultados reales:
1. La tarea 1.6 se completo (plantilla editada a mano por el autor; GREEN 23 passed; escenario cubierto): ya no hay escenarios sin prueba (194 de 194).
2. El grupo 11 (documentacion) esta completo (11.1 a 11.8 marcadas).
3. El punto 3 del NO-GO anterior (comandos interactivos con `getpass`) **no bloquea el Verify**: esos comandos se ejecutan de verdad en el grupo 13 (autorizacion A2) y en Apply se probaron con lecturas inyectadas.
4. Runner con codigo 0, validaciones estrictas en verde, regresion de C-03 y PD-04 en verde (12.5).

Pendiente documental D2 (fuera de C-04): PA-03 y PA-11 en `knowledge-base/10_preguntas_abiertas.md` y US-001 en `knowledge-base/06_funcionalidades.md` siguen abiertas/"Condicionada" aunque C-03 las resolvio; se corrigen en un cambio documental aparte (ver seccion siguiente).

El GO no autoriza nada por si mismo: **el grupo 13 NO se inicio**; requiere las autorizaciones A1 a A5 del autor.

## Pendiente documental separado de C-04 (decisión D2 del autor, 2026-11-14)

`knowledge-base/10_preguntas_abiertas.md:110` (PA-03) y `:118` (PA-11) siguen como abiertas y `knowledge-base/06_funcionalidades.md:15` (US-001) sigue "Condicionada" por ellas, aunque C-03 las resolvió. Por decisión del autor no se modifican en C-04; quedan registradas como posible desactualización a corregir en un cambio documental aparte.

## Checkpoint de Git previo al grupo 13 (autorizado por el autor, 2026-11-14)

El autor revisó personalmente `git diff -- .env.example` y autorizó un commit local de checkpoint de C-04 antes de la transición del grupo 13, con los 124 archivos auditados (se excluye `backend/tests/unit/test_superposicion_turnos.py`, que conserva una diferencia preexistente de finales de línea). El checkpoint no archiva el Change, no inicia el grupo 13, no aplica 0004 en desarrollo ni modifica PostgreSQL de desarrollo; C-04 sigue activo y la tarea 15.1 queda abierta para el commit de cierre.

# Verificacion de aislamiento entre consultorios: C-04 `aislamiento-roles-rbac` y estado actual de `main`

> Revision generada con la skill `verificar-aislamiento-consultorios`. Es una revision nueva, posterior al Archive de C-04 (2026-11-16); no forma parte del Change archivado ni modifica su evidencia. `openspec/changes/archive/2026-11-16-aislamiento-roles-rbac/` se leyo y no se modifico (`git status --porcelain -- openspec/changes/archive` vacio al terminar).

## Identificacion

| Campo | Valor |
|---|---|
| Fecha | 2026-11-17 |
| Commit revisado | `e0e1f4f0500a1b4a3e411f8a68110765a72123f1` |
| Rama | `main` |
| Cambios sin confirmar | `.atl/skill-registry.md`, `.gitignore`, `AGENTS.md`, `CLAUDE.md` (integracion de la skill), `.claude/skills/` y `docs/evidencia-tpi/` (nuevos), `backend/tests/unit/test_superposicion_turnos.py` (solo finales de linea, previo y ajeno al aislamiento). Ninguno toca codigo, migraciones, pruebas de aislamiento ni Compose |
| Alcance | Estado actual del repositorio y Change archivado `openspec/changes/archive/2026-11-16-aislamiento-roles-rbac/` |
| Modo | `estatico` |
| Autorizaciones | Autorizacion expresa del autor (2026-11-17) para la primera aplicacion real de la skill a C-04 en modo estatico. Sin Docker, `scripts/test.ps1`, consultas a PostgreSQL, `.env` ni `.env.example` |

## Resultado por control

| ID | Control | Estado | Origen | Evidencia |
|---|---|---|---|---|
| V-01 | Cobertura de escenarios | Cumple | Verificado ahora | Comando 4: los 14 deltas archivados (`.../specs/<capacidad>/spec.md`) tienen 226 `#### Scenario` y la matriz 10.2 de `tdd-evidencia.md` tiene fila para los 226, sin huecos (por capacidad: 37, 44, 19, 14, 30, 19, 11, 11, 6, 3, 15, 4, 5, 8). Las 4 capacidades nuevas coinciden tambien con la spec vigente (37, 44, 14, 15). Las specs modificadas tienen mas escenarios vigentes que el delta (por ejemplo `configuracion-backend` 38 frente a 19) porque el resto proviene de Changes anteriores, fuera de esta matriz |
| V-02 | Referencias de la matriz existen | Cumple | Verificado ahora | Comandos 5 y 6. Criterio RT3 reproducido: 175 apariciones `modulo::funcion` (159 unicas), 0 inexistentes. Criterio ampliado de esta revision: 229 referencias unicas a funciones (228 existen; la restante, `test_crear_app::ningun_motor_de_la_app_apunta_a_database_migration_url`, es una mencion historica que la propia matriz declara reemplazada por DD-34 en `tdd-evidencia.md:440`), 10 referencias a modulo completo (10 existen) y 8 casos AUTO (8 en `scripts/tests/autoprueba.ps1`). Detalle de criterios en el Anexo A |
| V-03 | RLS habilitada y forzada | Cumple | Verificado ahora | `backend/alembic/versions/0004_aislamiento_roles_rbac.py:84` (`_TABLAS_CON_RLS` = consultorio, usuario, sesion, intento_login) y `:386-388` (`ENABLE` y `FORCE ROW LEVEL SECURITY` por tabla). Las tablas de `backend/app/models/` son exactamente esas cuatro (`consultorio.py:22`, `usuario.py:38`, `sesion.py:22`, `intento_login.py:21`); `codigo.py` no define tabla |
| V-04 | Politicas cerradas y contexto transaccional | Cumple | Verificado ahora | `0004...py:76` (`NULLIF(current_setting('app.consultorio_id', true), '')::uuid`), `:394-396` (politica `pol_<tabla>_aislamiento` con `USING` y `WITH CHECK`). `backend/app/core/contexto_bd.py:19` fija el contexto con `set_config(..., true)` y `:20`/`:74` hace `RESET` al devolver la conexion. Comando 7: `app.consultorio_id` solo aparece en `contexto_bd.py` dentro de `backend/app`; no hay `SET app.` ni `is_local` falso |
| V-05 | Funciones SECURITY DEFINER | Cumple | Verificado ahora | `0004...py:126` (`SECURITY DEFINER SET search_path = pg_catalog, pg_temp` en la cabecera comun), `:155` (`_FUNCIONES`, 10 funciones `acceso.*`), `:380-381` (`CREATE SCHEMA acceso` y `REVOKE ALL ... FROM PUBLIC`), `:407-408` (`REVOKE ALL ON FUNCTION ... FROM PUBLIC` y `GRANT EXECUTE` a un rol por funcion) |
| V-06 | Atributos y pertenencia de roles | Cumple (como exigencia de la migracion y del codigo) | Verificado ahora | `backend/app/core/roles_bd.py:9-15` (cuatro roles; dos con LOGIN y dos duenios) y `:19` (`_ATRIBUTOS_PROHIBIDOS`). `0004...py:38` y `:49-66` (la migracion se niega a aplicarse si un rol tiene SUPERUSER, BYPASSRLS, CREATEROLE, CREATEDB o REPLICATION, si LOGIN no corresponde, si hay membresias o si posee objetos) y `:373` (se ejecuta primero). El estado real de una base no se verifica en modo estatico (ver Limitaciones) |
| V-07 | Privilegios minimos | Cumple | Verificado ahora | `0004...py:97-117` (`_PRIVILEGIOS`): `turnos_app` recibe `SELECT` por columnas de `usuario` sin `credencial` (`:101`), nada sobre `intento_login` (comando 8: 0 concesiones) y solo `UPDATE (revocada_en)` en `sesion`; `credencial` solo para `turnos_acceso_login` (`:114`). `turnos_login` no recibe privilegios sobre tablas. Comando 8: ningun `GRANT CREATE` ni `GRANT ALL` |
| V-08 | El consultorio no viene del cliente | Cumple | Verificado ahora | Comando 9: `consultorio_id` no aparece en `backend/app/api` ni en `backend/app/schemas`. `backend/app/schemas/base.py:7` (`extra="forbid"`; `EntradaLogin` hereda de `EsquemaEntrada`, `schemas/auth.py:12`). `backend/app/auth/dependencias.py:73` (`rechazar_consultorio_del_cliente`: 422 ante `consultorio_id` en query o cabecera `X-Consultorio-Id`), aplicada a toda la app en `backend/app/main.py:56`. Pruebas: `backend/tests/unit/test_consultorio_cliente.py`, `backend/tests/integration/test_consultorio_cliente.py` |
| V-09 | Credenciales e identidad de la conexion | Cumple | Verificado ahora + Citado del historial | `docker-compose.yml:44-84` (servicio `api`): sin `env_file` (los unicos `env_file` estan en `db`, `:4`, y `admin`, `:89`), `environment` con 9 claves (`:52-62`; solo nombres, sin valores) que no incluyen `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD`, `PGPASSWORD` ni `TEST_DATABASE_URL`, y `./backend:/app:ro` (`:68`; `admin` igual en `:92`). `backend/app/main.py:28`, `:31`, `:46` (rechazo de credenciales de administracion en `crear_app`). `backend/app/core/database.py:75` y `:101` (`verificar_rol_de_conexion` en cada conexion nueva). Pruebas: `test_crear_app.py`, `test_montaje_codigo.py`, `test_pools_y_guardias.py` (unit), `test_guardia_rol_api.py`, `test_pool_login.py` (isolation). Historial: 16.21 (`verify.md:545`, 2026-11-16) registro en el servicio en ejecucion `/app rw=false` y la ausencia de esas variables |
| V-10 | Acceso cruzado por endpoint privado | Cumple | Verificado ahora (existencia) + Citado del historial (ejecucion) | Rutas reales (comando 10): `POST /api/auth/login` y `GET /api/health` publicas; `GET /api/auth/me` y `POST /api/auth/logout` dependen de `identidad_actual` (`backend/app/api/auth.py:158`, `:168`). Ambas estan en `backend/tests/isolation/registro.py:31` y `:34`; `verificar_registro` (`registro.py:40-48`) falla si una ruta protegida no tiene entrada, y `test_acceso_cruzado.py:159-165` exige un ejecutor por entrada. Recurso de A pedido por B: `test_acceso_cruzado.py:62` y `:80`. Ejecucion: regresion 16.19 (2026-11-15) con 234 pruebas de aislamiento |

## Hallazgos

Sin hallazgos `No cumple`.

Observaciones (no son defectos de C-04):
1. La matriz 10.2 cita `test_crear_app::ningun_motor_de_la_app_apunta_a_database_migration_url`, que ya no existe; la misma celda (`tdd-evidencia.md:440`) indica que fue reemplazada por DD-34 y sus reemplazos existen. Es historia documentada, no cobertura rota.
2. Las dos rutas privadas actuales operan sobre la sesion propia; el escenario "recurso del consultorio A pedido desde B" se ejercita con rutas de prueba (`test_acceso_cruzado.py:62`, `:80`). Cada endpoint de negocio futuro (C-07 en adelante) necesitara su entrada en el registro, su RLS y su prueba (RN-MT-06).

## Comandos ejecutados

Todos de solo lectura, desde la raiz del repositorio.

1. `git rev-parse HEAD`, `git branch --show-current`, `git status --short`
2. `git status --porcelain -- openspec/changes/archive` (vacio) y `git log -1 --format='%h %ad %s' --date=short -- openspec/changes/archive/2026-11-16-aislamiento-roles-rbac` (`e0e1f4f 2026-11-16`)
3. `npx --no-install openspec validate --specs --strict` (19 passed, 0 failed) y conteo de casillas en el `tasks.md` archivado (114 `[x]`, 0 `[ ]`)
4. Script Python de solo lectura (`python -I`): por cada seccion `### <capacidad>` de la matriz 10.2, numeros de escenario con fila frente a `#### Scenario` del delta archivado y de la spec vigente
5. Criterio RT3, reproducido literalmente: extrae con la expresion regular `` `(test_\w+)::([\w*]+)` `` cada aparicion en la seccion 10.2 y busca `def test_<funcion>` (con `*` como comodin) en cualquier archivo de `backend/tests/` con ese nombre de modulo
6. Script Python de solo lectura con el criterio ampliado del Anexo A (conservado fuera del repositorio, segun la skill)
7. `git grep -n "app\.consultorio_id" -- backend/app` y `git grep -n -E "set_config|SET app\.|is_local" -- backend/app`
8. `grep -n` sobre `_PRIVILEGIOS` en `0004_aislamiento_roles_rbac.py` (concesiones de `turnos_app` y de `intento_login`) y `grep -n "CREATE ON\|GRANT CREATE\|GRANT ALL"` (sin coincidencias)
9. `git grep -n "consultorio_id" -- backend/app/api backend/app/schemas` (sin coincidencias) y `git grep -n "rechazar_consultorio_del_cliente" -- backend/app`
10. `git grep -n -E "@router\.(get|post|put|patch|delete)\(" -- backend/app/api` y lectura de `backend/tests/isolation/registro.py`
11. `grep -n` de `env_file`, `environment:` y `/app:ro` en `docker-compose.yml`, mostrando solo nombres de variables (valores interpolados reemplazados por un marcador)

## Limitaciones

- **Modo estatico.** No se ejecuto ninguna prueba en esta revision y no se afirma que pasen hoy. La ultima regresion completa registrada es la 16.19 (`tdd-evidencia.md:654`, 2026-11-15; resumida en `verify.md:604`: autoprueba 35, unitarias 785, integracion 509, aislamiento 234, `tsc`, Vitest 2). La verificacion del servicio en ejecucion es la 16.21 (`verify.md:545`, 2026-11-16). Ambas son **evidencia anterior**, citada del historial.
- **V-03, V-06 y V-07** prueban lo que la migracion `0004` crea y exige, no el catalogo actual de una base concreta. Comprobarlo requiere el modo `catalogo`, con autorizacion expresa e independiente del autor. No se consulto PostgreSQL.
- **V-09** verifica la configuracion declarada en `docker-compose.yml`; el entorno efectivo del contenedor solo consta en el historial (16.21).
- **V-01** cubre los escenarios de los 14 deltas de C-04. Los escenarios de esas specs que provienen de Changes anteriores pertenecen a las matrices de esos Changes y no se revisaron aqui.
- **V-02** comprueba existencia por nombre, no contenido ni resultado de cada prueba. Los scripts auxiliares de conteo se conservaron fuera del repositorio; sus criterios estan descritos en el Anexo A para que se puedan reproducir.
- Decisiones y deuda abiertas que no se resuelven aca (regla D6): DT-10 a DT-14 de C-04 y el diseno de futuros endpoints publicos.

## Veredicto

**GO (estatico).** Los diez controles dan `Cumple` con evidencia citada y verificada en esta revision; ningun control queda `No cumple` ni `No evidenciado`. Las garantias que dependen de ejecucion (pruebas en verde, catalogo real, entorno efectivo) se apoyan en evidencia historica fechada (16.19 y 16.21) y se declaran como tal; confirmarlas hoy requiere los modos `pruebas` o `catalogo`, que no estaban autorizados.

---

## Anexo A. Diferencia entre las 175 referencias de RT3 y las 234 de la evaluacion de la skill

*(Anexo pedido por el autor; no altera la matriz historica.)*

Los tres numeros miden cosas distintas sobre la misma seccion 10.2 y ninguno contradice a los otros: con todos los criterios, **ninguna referencia vigente falta**.

| Conteo | Origen | Criterio | Resultado |
|---|---|---|---|
| **175** | Revision RT3 final (16.13, `verify.md:624`, 2026-11-16) | Cuenta **cada aparicion** (con repeticion) de tokens escritos exactamente como `` `test_modulo::funcion` `` con la funcion formada solo por letras, numeros, `_` o `*`. No cuenta nombres abreviados con `...`, parametrizados `[...]`, funciones que heredan el modulo de la referencia anterior ni referencias a modulo completo. El comando se reconstruyo de la sesion de RT3 y se reprodujo hoy (comando 5) | 175 apariciones, 159 unicas, 0 inexistentes |
| **234** | Verdad de referencia del caso 2 de la evaluacion de la skill (2026-11-17, registrada en `docs/evidencia-tpi/skill-creator/registro-creacion.md`) | Cuenta **tuplas unicas** (directorio, modulo, nombre), incluyendo las funciones que heredan el modulo y los nombres abreviados con `...` o `*`; excluye 13 tokens que no son pruebas. Ese primer criterio contaba como "funcion" dos referencias a modulo completo y la mencion reemplazada | 234 tuplas; 3 marcadas, ninguna faltante real (2 modulos que existen y la mencion historica) |
| **229 + 10 + 8** | Esta revision (comando 6) | Afina el criterio anterior: separa las referencias a modulo completo (con o sin `.py`), reconoce comodines al inicio (`..._tras_rollback`) y prefijos de una palabra (`guardia_*`), y cuenta los casos AUTO por separado excluyendo texto que no es un caso | 229 funciones unicas (228 existen + 1 mencion historica), 10 modulos (10 existen), 8 casos AUTO (8 existen) |

Por que difieren: RT3 cuenta **apariciones** de una sola forma de escritura; la evaluacion cuenta **referencias unicas** de todas las formas de escritura que usa la matriz. La diferencia entre 175 y 234 no indica pruebas nuevas ni perdidas.

## Anexo B. Seccion academica

*(Anexo pedido por el autor para el TPI de Metodologia I.)*

- **Solicitud realizada a la skill.** "Modo estatico. Alcance: estado actual del repositorio (`main`) y Change archivado `openspec/changes/archive/2026-11-16-aislamiento-roles-rbac/`. Revision nueva posterior al Archive de C-04. Informe autorizado en `docs/evidencia-tpi/revision-c04-skill.md`. Explicar diferencia entre 175 referencias (RT3) y 234 (evaluacion nueva)."
- **Skill efectivamente utilizada.** `verificar-aislamiento-consultorios`, skill propia versionada en `.claude/skills/verificar-aislamiento-consultorios/`, invocada con la herramienta Skill del agente (no solo leida). Es la version validada con `skill-creator` el 2026-11-17 (`SKILL.md` con SHA-256 `2186769940cf1ccd2daf93d9578244305d48efc9cb8643efdec79b889dca6002`).
- **Controles ejecutados.** V-01 a V-10 del catalogo `references/controles.md`, en el orden del procedimiento de la skill: identificacion del commit, evidencia por control, estado, origen, veredicto, saneamiento y plantilla `references/plantilla-informe.md`.
- **Resultado obtenido.** GO estatico: 10 de 10 controles `Cumple`, sin `No cumple` ni `No evidenciado`, con limitaciones explicitas del modo estatico.
- **Aporte concreto de la skill a la verificacion de C-04.**
  - Convirtio la revision en una lista cerrada de diez controles derivados de las reglas de C-04 (D5, RN-MT-02, RN-MT-06, DD-03, DD-29, DD-34), en lugar de una lectura libre.
  - Exigio evidencia reproducible por control (`ruta:linea` o comando) y separo lo verificado ahora de lo citado del historial, de modo que la revision no "hereda" resultados de ejecucion sin decirlo.
  - Sus reglas sobre la matriz (prefijo `test_` omitido, comodines, referencias a modulo, menciones "reemplaza a") evitaron declarar como faltante una prueba que existe y llevaron a reconstruir y explicar el criterio de las 175 referencias de RT3.
  - Mantuvo los limites de seguridad: sin `.env`, sin base, sin Docker y sin modificar el Change archivado.
- **Como se reviso la respuesta.**
  - Cada cita `ruta:linea` se obtuvo con `grep -n` o `git grep -n` durante la revision; las afirmaciones de V-01 y V-02 provienen de scripts de solo lectura cuyos criterios estan en el Anexo A.
  - El conteo de RT3 se reconstruyo a partir del comando original y se volvio a ejecutar sobre la ruta archivada, obteniendo el mismo 175.
  - Se busco en el informe final la presencia de URLs con credenciales, hashes Argon2 o SCRAM, claves privadas, SID, rutas personales y emails reales (sin coincidencias), y se comprobo que el Change archivado no cambio.

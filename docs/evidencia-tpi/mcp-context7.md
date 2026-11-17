# Evidencia de uso del MCP Context7: contexto transaccional de C-04

> Evidencia para el TPI de Metodología I. Es una **revisión posterior al Archive de C-04** (`openspec/changes/archive/2026-11-16-aislamiento-roles-rbac/`), hecha para preparar la entrega. Context7 **no intervino** en la implementación original de C-04 y esta revisión no modifica el Change archivado, el código ni las pruebas. El documento resume la información obtenida; no reproduce salidas crudas de las herramientas.

## 1. Identificación

| Campo | Valor |
|---|---|
| Fecha de ejecución | 2026-11-17 |
| Commit del repositorio | `e0e1f4f0500a1b4a3e411f8a68110765a72123f1` (`main`) |
| Cliente | Claude Code (agente del autor) |
| Servidor MCP | `context7`, paquete `@upstash/context7-mcp@2.2.5`, transporte `stdio` |
| Herramientas del servidor | `resolve-library-id` y `query-docs` (en Claude Code: `mcp__context7__resolve-library-id` y `mcp__context7__query-docs`) |
| Autorización | Autorización expresa del autor para verificar, usar y documentar Context7 |

## 2. Propósito

C-04 aísla los consultorios con RLS de PostgreSQL. El consultorio de cada petición se fija con un **contexto local a la transacción** (`set_config('app.consultorio_id', ..., true)`) desde eventos de SQLAlchemy. La corrección de esa decisión (DD-04 y DD-05 de `design.md`) depende de cómo se comportan, según la documentación de SQLAlchemy, los siguientes elementos:

- el evento de sesión `after_begin`;
- el *autobegin* de la `Session`, `Session.in_transaction()` y `Session.info`;
- el evento `reset` del pool de conexiones, que C-04 usa como defensa adicional.

Se usó Context7 para consultar la documentación oficial de la **misma versión** de SQLAlchemy que usa el proyecto (2.1.6) y contrastarla con la implementación.

## 3. Conexión verificada

| Comprobación | Resultado |
|---|---|
| Configuración | Servidor `context7` en el ámbito de usuario de Claude Code: tipo `stdio`, comando `npx`, paquete `@upstash/context7-mcp@2.2.5`. Sin variables de entorno ni clave de API configuradas |
| Estado | `claude mcp list` → `context7: ... - ✔ Connected` |
| Herramientas | Se cargaron en la sesión con sus esquemas: `resolve-library-id` (parámetros `libraryName`, `query`) y `query-docs` (parámetros `libraryId`, `query`) |
| Uso efectivo | 4 llamadas reales en la sesión del 2026-11-17 (sección 4) |

## 4. Llamadas realizadas

Las consultas solo contenían preguntas generales sobre SQLAlchemy. No incluyeron código, nombres de tablas, datos ni credenciales del proyecto, porque Context7 envía las consultas a un servicio externo.

| # | Herramienta | Consulta (resumen fiel) | Resultado |
|---|---|---|---|
| 1 | `resolve-library-id` | `libraryName="SQLAlchemy"`; eventos de sesión y de pool en 2.x para fijar un valor local por transacción | ID `/sqlalchemy/sqlalchemy` (reputación de la fuente: High), con la versión `rel_2_1_6` disponible, que es la que usa el proyecto |
| 2 | `query-docs` | `/sqlalchemy/sqlalchemy/rel_2_1_6`: cuándo se llama `SessionEvents.after_begin`, sus argumentos y si se puede ejecutar SQL en esa conexión | Fragmentos de `doc/build/orm/events.rst` y `doc/build/orm/session_events.rst` (y de `session_transaction.rst`, sobre la configuración por transacción) |
| 3 | `query-docs` | Misma versión: `PoolEvents.reset`, `reset_state.terminate_only`, relación con el *reset on return* y efecto de una excepción | Fragmentos de `doc/build/core/events.rst`, `doc/build/core/pooling.rst` y `doc/build/changelog/changelog_20.rst` |
| 4 | `query-docs` | Misma versión: *autobegin* tras commit o rollback, `Session.in_transaction()` y `Session.info` | Fragmentos de `doc/build/orm/session_basics.rst`, `session_transaction.rst` y `session_api.rst` |

Las fuentes son archivos de la documentación oficial dentro del repositorio de SQLAlchemy, en la etiqueta `rel_2_1_6` (`github.com/sqlalchemy/sqlalchemy`, carpeta `doc/build/`).

## 5. Resumen de lo que dice la documentación

1. **`after_begin`** (`orm/events.rst`, `orm/session_events.rst`):
   - se ejecuta *después* de que empieza una transacción en una conexión;
   - recibe la `Session`, la `SessionTransaction` y la `Connection` en la que empezó la transacción;
   - es un evento **por conexión**: una `Session` con varias conexiones lo emite para cada una cuando se usa dentro de la transacción actual.
2. **Autobegin** (`orm/session_basics.rst`, `orm/session_transaction.rst`):
   - la `Session` empieza una transacción automáticamente con el primer trabajo (`execute`, `add`, una consulta);
   - después de `commit()` o `rollback()`, **vuelve a empezar automáticamente** con la siguiente operación;
   - `Session.in_transaction()` devuelve `True` si ese paso ya ocurrió.
3. **`Session.info`** (`orm/session_api.rst`): es un diccionario modificable por el usuario.
4. **`PoolEvents.reset`** (`core/events.rst`, `core/pooling.rst`, `changelog_20.rst`):
   - se llama *antes* de la acción de reset de una conexión del pool y permite un reset personalizado;
   - recibe `dbapi_connection`, `connection_record` y `reset_state`;
   - `reset_state.terminate_only` indica que la conexión se va a cerrar y no vuelve al pool;
   - desde 2.0 el evento se emite en todos los casos, aunque la `Connection` ya haya hecho su propio reset, para permitir esquemas de reset personalizados.
5. **Invalidación** (`core/pooling.rst`): si al devolver la conexión el `rollback()` o `commit()` del *reset on return* lanza una excepción, se intenta cerrarla y se descarta. El ejemplo oficial de reset personalizado **desactiva** el reset por defecto (`pool_reset_on_return=None`) y sigue llamando a `rollback()` dentro del evento, para mantener coherente el estado transaccional del driver.

## 6. Contraste con C-04

Archivos y decisiones contrastados:
- `backend/app/core/contexto_bd.py`;
- `backend/app/main.py:62` y `:67`;
- DD-04 y DD-05 en `openspec/changes/archive/2026-11-16-aislamiento-roles-rbac/design.md:167-182`;
- requisito "Contexto de consultorio por transacción" de `openspec/specs/aislamiento-base-de-datos/spec.md:114-115`.

| Aspecto de C-04 | Implementación | Qué aporta la documentación | Conclusión |
|---|---|---|---|
| Fijar el contexto al empezar cada transacción (DD-04) | `contexto_bd.py:23-30`: `after_begin` registrado con `event.listen(fabrica, "after_begin", ...)`; ejecuta `set_config(..., true)` en la `Connection` recibida | `after_begin` se emite después de que empieza la transacción y entrega la `Connection` de esa transacción | **Consistente**: el valor se fija en la conexión y la transacción que van a ejecutar las consultas |
| Recuperar el contexto tras `COMMIT` y `ROLLBACK` (DD-05) | El consultorio se guarda en `Session.info` (`:37`) y el evento lo vuelve a leer en cada transacción (`:25`) | La `Session` vuelve a empezar sola después de commit o rollback, y cada inicio emite `after_begin`; `Session.info` es un diccionario del usuario | **Consistente**: cada transacción nueva de la misma `Session` recibe el contexto vigente |
| Aplicar el contexto con una transacción ya abierta | `aplicar_contexto` (`:33-39`) usa `in_transaction()` y fija de inmediato | `in_transaction()` indica si ya ocurrió el *autobegin* | **Consistente**: sin esa rama, una transacción ya iniciada no recibiría el contexto hasta la siguiente |
| Varias conexiones por `Session` | La fábrica de la API se crea sobre un solo motor (`main.py:67`) | `after_begin` es por conexión | **Consistente**; si en el futuro una `Session` usara varios motores, cada conexión recibiría su propio `set_config` |
| Defensa adicional en el pool (DD-04) | `contexto_bd.py:63-81`: evento `reset` que ignora `terminate_only`, hace `rollback()`, `RESET app.consultorio_id` y `commit()`; registrado en `main.py:62`. No se configura `pool_reset_on_return` (comando 4 de la sección 8) | El evento se llama antes del reset por defecto y se emite en todos los casos; `terminate_only` marca conexiones que no vuelven al pool | **Consistente**: como el reset por defecto (rollback) no está desactivado, sigue ejecutándose después del evento sobre una conexión ya confirmada, sin efecto adicional. Omitir el trabajo con `terminate_only` evita tareas inútiles en conexiones que se descartan |

**Aporte concreto:** la documentación oficial de SQLAlchemy 2.1.6 respalda los **mecanismos** de SQLAlchemy en los que se apoya DD-04/DD-05: el evento `after_begin` por transacción y por conexión, el *autobegin* que vuelve a disparar ese evento tras commit y rollback, `Session.info` como lugar del dato y el evento `reset` del pool, con su orden respecto del reset por defecto. Context7 no aportó información sobre PostgreSQL ni sobre RLS.

## 7. Limitaciones

- **Alcance acotado.** El aporte se limita al comportamiento de SQLAlchemy en el contexto transaccional. Context7 **no validó C-04 completo**: no revisó RLS, políticas, roles, privilegios, funciones `SECURITY DEFINER` ni la separación de credenciales. Esos aspectos están en `docs/evidencia-tpi/revision-c04-skill.md`.
- **Comportamientos no confirmados por la documentación devuelta:**
  - **Excepción dentro del evento `reset`.** DD-04 afirma que, si el evento falla, la conexión se invalida. La documentación obtenida solo describe la invalidación cuando falla el `rollback()` o `commit()` del *reset on return*, no una excepción arbitraria dentro de un evento `reset` personalizado. No se confirma con Context7.
  - **Savepoints.** DD-05 afirma que `begin_nested()` no dispara `after_begin` y describe su efecto con la fixture `create_savepoint`. Los fragmentos devueltos no cubren ese caso.

  Ambos comportamientos están cubiertos por pruebas del propio C-04 contra PostgreSQL real, cuya última ejecución registrada es la regresión 16.19 del 2026-11-15, **evidencia anterior** no repetida en esta revisión:
  - `backend/tests/isolation/test_contexto_transaccional.py:59`, `:72`, `:144` y `:160`;
  - `backend/tests/unit/test_contexto_bd.py:160` y `:201`.
- **Semántica de PostgreSQL.** Que `set_config(..., true)` dure solo hasta el fin de la transacción es comportamiento de PostgreSQL, no de SQLAlchemy, y no se consultó en Context7.
- **Fragmentos.** Context7 devuelve extractos de la documentación, no páginas completas. Las conclusiones se limitan a lo que dicen esos extractos.
- **Servicio externo.** Las consultas salen del equipo hacia el servicio de Context7. Por eso solo contenían preguntas generales y la versión de la biblioteca.

## 8. Cómo se revisó la información

1. Antes de usar el servidor se confirmó su estado con `claude mcp list` (`✔ Connected`). La configuración se inspeccionó con un script que solo imprimía tipo, comando, paquete y nombres de variables, y ocultaba cualquier clave.
2. Las 4 llamadas de la sección 4 se hicieron en esta sesión. Este documento no menciona ninguna llamada que no se haya hecho. Se respetó el límite de 3 consultas de documentación que indica la propia herramienta.
3. Cada afirmación de la sección 5 se tomó de un fragmento devuelto, con su archivo de origen. Las que la documentación no cubría figuran como limitaciones.
4. El contraste se hizo leyendo el código y las decisiones, sin ejecutar pruebas ni conectarse a la base. Comandos de solo lectura, desde la raíz del repositorio:
   - lectura de `backend/app/core/contexto_bd.py`;
   - `git grep -n -E "pool_reset_on_return|registrar_reset_del_pool|registrar_contexto_transaccional|crear_fabrica_de_sesiones\(|create_engine\(" -- backend/app` (sin `pool_reset_on_return`);
   - `grep -n` en `openspec/specs/aislamiento-base-de-datos/spec.md` y lectura de DD-04 y DD-05 en el `design.md` archivado;
   - `grep -n "^def test_"` en `test_contexto_transaccional.py` y `test_contexto_bd.py`, para ubicar las pruebas citadas.
5. Antes de entregarlo, se buscaron en este documento contraseñas, tokens, URLs con credenciales, hashes y rutas personales (sección 10).

## 9. Configuración reproducible del MCP (sin credenciales)

Requisitos: Claude Code y Node.js con `npx`. Context7 funciona sin clave de API, con límites de uso del servicio. Si se agrega una clave, va en la configuración local del usuario y nunca en el repositorio.

```powershell
# Registrar el servidor en el ámbito del usuario (fijando la versión usada en esta evidencia).
# Comando de referencia: no se ejecutó en esta sesión, porque el servidor ya estaba configurado.
claude mcp add --scope user context7 -- npx -y --package=@upstash/context7-mcp@2.2.5 -- context7-mcp

# Comprobar la conexión
claude mcp list
# Resultado esperado: "context7: ... - ✔ Connected"
```

Prueba de uso dentro de Claude Code:
1. Pedir "resolvé el ID de Context7 para SQLAlchemy". Debe invocar `resolve-library-id` y devolver `/sqlalchemy/sqlalchemy`, con versiones como `rel_2_1_6`.
2. Pedir una consulta de documentación con ese ID y la versión. Debe invocar `query-docs` y devolver fragmentos con la ruta del archivo de documentación de origen.

Esta configuración la hizo el autor fuera de esta revisión. En esta sesión **no** se modificó ninguna configuración del MCP: solo se leyó y se comprobó.

## 10. Comprobación de privacidad

Se revisó este documento buscando contraseñas, tokens, claves, URLs de conexión con usuario y contraseña, hashes de contraseñas, rutas personales y emails. No hay coincidencias. Los únicos identificadores largos son el commit del repositorio y nombres públicos de paquetes y bibliotecas.

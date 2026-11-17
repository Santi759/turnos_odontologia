# Catalogo de controles V-01 a V-10

Basado en las reglas de C-04 `aislamiento-roles-rbac` (archivado en `openspec/changes/archive/2026-11-16-aislamiento-roles-rbac/`) y en las specs vigentes `aislamiento-base-de-datos`, `acceso-previo-al-contexto`, `autorizacion-roles`, `pruebas-aislamiento` y `configuracion-backend`. Las rutas son relativas a la raiz del repositorio. Si una ruta ya no existe, no supongas: marca el control `No evidenciado` y explica que cambio.

Cada control indica **que** se verifica, **por que** importa, **donde** buscar y **que cuenta como evidencia** en modo `estatico`. Los modos `pruebas` y `catalogo` agregan evidencia de ejecucion; no la reemplazan.

---

## V-01 Cobertura de escenarios

- **Que:** cada escenario (`#### Scenario`) de las specs de aislamiento tiene al menos una prueba automatizada en la matriz escenario-prueba.
- **Por que:** la regla O2 exige que todos los escenarios esten cubiertos; un escenario sin prueba es una garantia sin respaldo.
- **Donde:** `openspec/specs/<capacidad>/spec.md` y la matriz 10.2 de `openspec/changes/archive/2026-11-16-aislamiento-roles-rbac/tdd-evidencia.md`.
- **Evidencia:** conteo de `#### Scenario` por spec frente a filas de la matriz por spec. Las specs pueden haber cambiado despues del Archive: si el conteo actual difiere del historico, informa la diferencia y que escenarios no estan en la matriz.

## V-02 Referencias de la matriz existen

- **Que:** cada referencia `archivo::funcion` de la matriz apunta a una prueba que existe hoy.
- **Por que:** una matriz con referencias rotas aparenta cobertura que ya no existe (pruebas renombradas o borradas).
- **Donde:** matriz 10.2 y `backend/tests/{unit,integration,isolation}/`, `scripts/tests/autoprueba.ps1`.
- **Evidencia:** total de referencias, cuantas existen y lista exacta de las faltantes. Reglas de lectura en la seccion "Por que la matriz necesita cuidado" de `SKILL.md` (prefijo `test_` omitido, prefijos UNI/INT/AIS/AUTO/RUN, modulo heredado).

## V-03 RLS habilitada y forzada

- **Que:** toda tabla con datos de un consultorio tiene `ENABLE ROW LEVEL SECURITY` y `FORCE ROW LEVEL SECURITY`.
- **Por que:** sin `FORCE`, el duenio de la tabla ignora las politicas; sin RLS, el filtro depende solo del codigo (RN-MT-06 pide una barrera en la base).
- **Donde:** `_TABLAS_CON_RLS` y el bucle de `upgrade()` en `backend/alembic/versions/0004_aislamiento_roles_rbac.py`; modelos en `backend/app/models/`.
- **Evidencia:** lista de tablas con RLS frente a lista de modelos con `consultorio_id` (o que son el consultorio). Una tabla nueva con `consultorio_id` que no este en la lista es `No cumple` (Alta). Prueba relacionada: `backend/tests/isolation/test_rls.py`.

## V-04 Politicas cerradas por defecto y contexto transaccional

- **Que:** las politicas de aislamiento comparan la columna del consultorio con `NULLIF(current_setting('app.consultorio_id', true), '')::uuid` en `USING` y `WITH CHECK`; el contexto se fija solo con `set_config(..., true)` (local a la transaccion) y se limpia al devolver la conexion.
- **Por que:** sin contexto debe haber cero filas (falla cerrada, DD-03); un `SET` de sesion podria filtrar el consultorio de una peticion a la siguiente en el pool.
- **Donde:** `_EXPRESION_CONSULTORIO`, `_TABLAS_POR_CONSULTORIO` y `_POLITICAS` en la migracion `0004`; `backend/app/core/contexto_bd.py` (unico modulo de `app/` que menciona `app.consultorio_id`).
- **Evidencia:** citas `ruta:linea`; `git grep -n "app.consultorio_id" -- backend/app` debe devolver solo `contexto_bd.py`; ausencia de `is_local` falso o `SET app.` fuera de ese modulo. Las politicas de los roles duenios (`TO turnos_acceso_previo` / `turnos_acceso_login`, `USING (true)`) son intencionales: verifica que esos roles no tengan LOGIN (V-06) en lugar de marcarlas como violacion.

## V-05 Funciones SECURITY DEFINER del esquema `acceso`

- **Que:** cada funcion `SECURITY DEFINER` fija `SET search_path = pg_catalog, pg_temp`, usa nombres calificados, tiene `REVOKE ALL ... FROM PUBLIC` y un `GRANT EXECUTE` a un solo rol; el esquema `acceso` tiene `REVOKE ALL ... FROM PUBLIC`.
- **Por que:** una funcion definer sin `search_path` fijo puede ejecutar objetos plantados por quien la llama; un `EXECUTE` publico la convierte en una puerta trasera al acceso previo al contexto.
- **Donde:** `_CABECERA`, `_FUNCIONES` y el bucle final de `upgrade()` en la migracion `0004`.
- **Evidencia:** citas `ruta:linea` y el numero de funciones. Pruebas relacionadas: `backend/tests/isolation/test_funciones_acceso.py`.

## V-06 Atributos y pertenencia de los roles

- **Que:** los cuatro roles (`turnos_app`, `turnos_login`, `turnos_acceso_previo`, `turnos_acceso_login`) no tienen SUPERUSER, BYPASSRLS, CREATEROLE, CREATEDB ni REPLICATION; solo los dos de conexion tienen LOGIN; no son miembros de otros roles y los de conexion no son duenios de objetos.
- **Por que:** cualquiera de esos atributos o una membresia anula RLS o permite escalar privilegios.
- **Donde:** `backend/app/core/roles_bd.py` (constantes y `violaciones_de_rol`), `_VERIFICACION_PREVIA` en la migracion `0004`.
- **Evidencia:** citas `ruta:linea`. En modo `estatico` esto prueba que la migracion **se niega** a aplicarse con roles incorrectos, no el estado actual de una base concreta: decilo asi. Pruebas relacionadas: `test_catalogo_roles.py`. El estado real solo se verifica en modo `catalogo`.

## V-07 Privilegios minimos por tabla y columna

- **Que:** los `GRANT` son por columna cuando corresponde; `turnos_app` no puede leer la columna `credencial` de `usuario` ni la tabla `intento_login`; ningun rol de conexion tiene `CREATE` en esquemas.
- **Por que:** el principio de minimo privilegio limita el dano de una inyeccion SQL o de un error de codigo en la API.
- **Donde:** `_PRIVILEGIOS` en la migracion `0004`.
- **Evidencia:** citas de los `GRANT` relevantes y ausencia de `credencial` en los de `turnos_app`. Pruebas relacionadas: `test_privilegios.py` (matriz exacta con `has_*_privilege`).

## V-08 El consultorio nunca viene del cliente

- **Que:** ningun esquema de entrada ni parametro de endpoint acepta `consultorio_id`; los esquemas de entrada heredan `extra="forbid"`; el consultorio se deriva de la sesion autenticada.
- **Por que:** es la regla D5 / RN-MT-02: aceptar el consultorio del body, query o header permite pedir datos de otro consultorio.
- **Donde:** `backend/app/schemas/` (base con `ConfigDict(extra="forbid")`), `backend/app/api/`.
- **Evidencia:** `git grep -n "consultorio_id" -- backend/app/api backend/app/schemas` (resultado esperado: ninguno o solo respuestas, nunca entradas) y la cita de la base de esquemas. Cada endpoint nuevo debe revisarse uno por uno.

## V-09 Separacion de credenciales e identidad de la conexion

- **Que:** el servicio `api` no tiene `env_file`, recibe solo la lista explicita de variables de `environment` y monta `./backend:/app:ro`; `crear_app` rechaza credenciales de administracion; cada conexion de la API verifica su rol real.
- **Por que:** DD-34 (hallazgos RT3 ALTO-1 y ALTO-2): si la API recibe la credencial de administracion o puede escribir su propio codigo, un compromiso de la API se convierte en control total de la base.
- **Donde:** servicios `api` y `admin` en `docker-compose.yml`; `VARIABLES_DE_ADMINISTRACION` y `rechazar_credenciales_de_administracion` en `backend/app/main.py`; `verificar_rol_de_conexion` en `backend/app/core/database.py`.
- **Evidencia:** lista de claves de `environment` de `api` (solo nombres, nunca valores) y ausencia de `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD`, `PGPASSWORD` y `TEST_DATABASE_URL`; citas de la guardia. Pruebas relacionadas: `test_crear_app.py`, `test_montaje_codigo.py`, `backend/tests/isolation/test_guardia_rol_api.py`.

## V-10 Prueba de acceso cruzado por endpoint privado

- **Que:** cada endpoint privado tiene una prueba que intenta acceder a datos del otro consultorio y espera la misma respuesta que para un recurso inexistente.
- **Por que:** RN-MT-06: un filtro por consultorio no alcanza; cada endpoint necesita su prueba de acceso cruzado, y la respuesta identica evita revelar que el recurso existe.
- **Donde:** `backend/tests/isolation/registro.py` (registro de rutas privadas), `backend/tests/isolation/test_acceso_cruzado.py` (incluye una prueba que exige un ejecutor por cada entrada del registro), rutas en `backend/app/api/`.
- **Evidencia:** lista de rutas privadas reales frente a entradas del registro. Una ruta privada fuera del registro es `No cumple` (Alta).

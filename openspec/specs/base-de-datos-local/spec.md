# base-de-datos-local Specification

## Purpose
Garantizar que el entorno local dispone de una base PostgreSQL real, accesible con la configuración del backend, con la extensión `btree_gist` instalada mediante migraciones que se aplican solo por comando explícito, como base de las futuras restricciones de exclusión (RN-AG-03).

Convenciones de los escenarios: base local de Docker Compose con datos ficticios únicamente (D1); las pruebas de esta capacidad se ejecutan contra PostgreSQL real, nunca contra un sustituto (X2). Las pruebas de integración y las migraciones del comando único usan la base de pruebas efímera (`db-test`, `TEST_DATABASE_URL`), nunca la base de desarrollo (decisión DP-04 del autor, 2026-11-03).

## Requirements

### Requirement: Conexión a PostgreSQL real
El sistema DEBE (MUST) poder abrir una conexión a PostgreSQL usando exclusivamente `DATABASE_URL` y ejecutar una consulta. El servidor DEBE (MUST) ser PostgreSQL de versión mayor 18.

#### Scenario: Consulta trivial
- **DADO** que el servicio `db-test` está en ejecución y `TEST_DATABASE_URL` apunta a él
- **CUANDO** se ejecuta `SELECT 1` con una conexión abierta desde la configuración del backend
- **ENTONCES** el resultado es `1`

#### Scenario: Versión mayor del servidor
- **DADO** que el servicio `db-test` está en ejecución
- **CUANDO** se consulta `server_version_num`
- **ENTONCES** la versión mayor es 18

### Requirement: Extensión btree_gist instalada y utilizable
Tras aplicar las migraciones, la base DEBE (MUST) tener instalada la extensión `btree_gist` y DEBE (MUST) admitir una restricción de exclusión que combine igualdad sobre un entero y superposición de rangos de tiempo. La verificación NO DEBE (MUST NOT) dejar tablas en la base.

#### Scenario: Extensión disponible en el servidor
- **CUANDO** se consulta `pg_available_extensions`
- **ENTONCES** figura `btree_gist`

#### Scenario: Extensión instalada tras migrar
- **DADO** que se aplicaron las migraciones con el comando explícito
- **CUANDO** se consulta `pg_extension`
- **ENTONCES** figura `btree_gist`

#### Scenario: Restricción de exclusión utilizable
- **DADO** que `btree_gist` está instalada
- **CUANDO** dentro de una transacción se crea una tabla temporal con `EXCLUDE USING gist (recurso WITH =, periodo WITH &&)` y se insertan dos filas con el mismo `recurso` y periodos `[10:00, 10:30)` y `[10:15, 10:45)`
- **ENTONCES** la segunda inserción falla por violación de exclusión
- **Y** al revertir la transacción no queda ninguna tabla creada por la prueba

### Requirement: Migraciones aplicadas solo por comando explícito
Las migraciones DEBEN (MUST) aplicarse únicamente mediante un comando explícito documentado; el arranque de la API NO DEBE (MUST NOT) ejecutarlas. Desde C-02 las migraciones son la de infraestructura (`0001`, habilitar `btree_gist`) y la del modelo base (`0002`, tablas `consultorio` y `usuario`); NO DEBEN (MUST NOT) crear otras tablas, NO DEBEN (MUST NOT) insertar filas en las tablas del modelo y NO DEBEN (MUST NOT) ejecutar el seed, que tiene su propio comando explícito.

#### Scenario: El comando explícito deja la base al día
- **DADO** una base sin migraciones aplicadas o con migraciones parciales
- **CUANDO** se ejecuta el comando explícito de migración
- **ENTONCES** la revisión actual registrada en la base coincide con la última revisión del repositorio

#### Scenario: El arranque de la API no migra
- **CUANDO** se inspecciona el comando de arranque efectivo del servicio `api` en la configuración resuelta de Docker Compose
- **ENTONCES** no invoca migraciones

#### Scenario: Sin tablas de dominio
Se conserva el nombre del escenario de C-01 (OpenSpec no admite renombrar escenarios en una delta) con contenido actualizado: "dominio" se refiere a las tablas de agenda, pacientes y turnos de Changes posteriores; `consultorio` y `usuario` son el modelo base aprobado en C-02.
- **DADO** que se aplicaron las migraciones
- **CUANDO** se listan las tablas del esquema `public`
- **ENTONCES** las tablas son exactamente `alembic_version`, `consultorio` y `usuario`

#### Scenario: Tablas del modelo base vacías tras migrar
- **DADO** que se aplicaron las migraciones
- **CUANDO** se cuentan las filas de `consultorio` y `usuario`
- **ENTONCES** ambas tienen cero filas

### Requirement: Las pruebas de integración fallan sin base real
Si la base configurada no es accesible, la preparación de las pruebas de integración DEBE (MUST) fallar con error; NO DEBE (MUST NOT) omitir las pruebas ni sustituir la base.

#### Scenario: Base inaccesible
- **DADO** que la URL de la base apunta a `host-inexistente.invalid`
- **CUANDO** se ejecuta la verificación de conexión que usa la preparación de las pruebas de integración
- **ENTONCES** termina con un error de conexión
- **Y** no se marca como omitida

### Requirement: Las pruebas de integración no tocan la base de desarrollo
Las pruebas de integración y las migraciones del comando único DEBEN (MUST) ejecutarse contra una base de pruebas efímera y separada (`db-test`, `TEST_DATABASE_URL`). La preparación de las pruebas DEBE (MUST) negarse a ejecutar si la URL de pruebas falta, coincide en host, puerto y nombre de base con `DATABASE_URL`, o no tiene un nombre de base terminado en `_test`. El servicio `db-test` NO DEBE (MUST NOT) usar volúmenes con nombre ni publicar puertos en el host.

#### Scenario: URL de pruebas igual a la de desarrollo rechazada
- **DADO** una URL de pruebas con el mismo host, puerto y nombre de base que `DATABASE_URL`
- **CUANDO** se ejecuta la guardia de la base de pruebas
- **ENTONCES** la guardia falla con un error que lo indica
- **Y** el error no contiene la contraseña

#### Scenario: URL de pruebas ausente rechazada
- **DADO** que `TEST_DATABASE_URL` no está definida
- **CUANDO** se ejecuta la guardia de la base de pruebas
- **ENTONCES** la guardia falla con un error que menciona `TEST_DATABASE_URL`

#### Scenario: Nombre de base de pruebas no admitido
- **DADO** una URL de pruebas cuyo nombre de base no termina en `_test`
- **CUANDO** se ejecuta la guardia de la base de pruebas
- **ENTONCES** la guardia falla

#### Scenario: Base de pruebas separada y efímera
- **DADO** la configuración resuelta de Docker Compose
- **CUANDO** se inspecciona el servicio `db-test`
- **ENTONCES** usa `tmpfs` para sus datos, no declara volúmenes con nombre ni puertos publicados y pertenece al perfil `test`

#### Scenario: La suite corre sobre la base de pruebas
- **DADO** que `db-test` está en ejecución
- **CUANDO** la preparación de las pruebas de integración abre la conexión
- **ENTONCES** `current_database()` es el nombre de la base de pruebas y no el de la base de desarrollo

### Requirement: Migraciones de pruebas protegidas por la guardia
Toda conexión de migración destinada a la base de pruebas (`-x target=test` o una URL explícita fijada por código) DEBE (MUST) pasar por la guardia de la base de pruebas antes de abrirse, de modo que nunca pueda apuntar por accidente a la base de desarrollo. La migración de desarrollo (`alembic upgrade head`, sin `-x`) DEBE (MUST) seguir apuntando a `DATABASE_URL`, y los dos destinos NO DEBEN (MUST NOT) poder confundirse. Los errores NO DEBEN (MUST NOT) incluir URLs ni credenciales.

#### Scenario: Migración de pruebas con URL insegura rechazada
- **DADO** `-x target=test` y una `TEST_DATABASE_URL` ausente, vacía, igual a la de desarrollo (aunque cambien las credenciales o el puerto sea implícito) o con un nombre de base que no termina en `_test`
- **CUANDO** Alembic resuelve la URL de la migración
- **ENTONCES** la resolución falla con un error que lo indica, sin abrir ninguna conexión
- **Y** el error no contiene URLs ni contraseñas

#### Scenario: URL explícita que apunta a desarrollo rechazada
- **DADO** una URL explícita de migración (`sqlalchemy.url`) con el mismo host, puerto y base que `DATABASE_URL`, o con un nombre de base que no termina en `_test`
- **CUANDO** Alembic resuelve la URL de la migración
- **ENTONCES** la resolución falla

#### Scenario: URL explícita junto al destino de desarrollo rechazada
- **DADO** una URL explícita de migración y el destino `desarrollo`
- **CUANDO** Alembic resuelve la URL de la migración
- **ENTONCES** la resolución falla por destino ambiguo

#### Scenario: Migración de pruebas válida apunta a la base de pruebas
- **DADO** `-x target=test` (o una URL explícita) con una URL de pruebas que supera la guardia
- **CUANDO** Alembic resuelve la URL de la migración
- **ENTONCES** usa la URL de pruebas y la migración se genera con `CREATE EXTENSION IF NOT EXISTS btree_gist`

#### Scenario: Migración de desarrollo explícita sigue apuntando a DATABASE_URL
- **DADO** una ejecución sin `-x target` (o con `target=desarrollo`) y sin URL explícita
- **CUANDO** Alembic resuelve la URL de la migración
- **ENTONCES** usa `DATABASE_URL`, sin exigir ni validar `TEST_DATABASE_URL`

#### Scenario: Destino de migración desconocido rechazado
- **DADO** un valor de `-x target` distinto de `desarrollo` y `test`
- **CUANDO** Alembic resuelve la URL de la migración
- **ENTONCES** la resolución falla y el error lista los valores admitidos

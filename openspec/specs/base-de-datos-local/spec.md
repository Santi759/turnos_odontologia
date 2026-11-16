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
Las migraciones DEBEN (MUST) aplicarse solo mediante un comando explícito documentado; el arranque de la API NO DEBE (MUST NOT) ejecutarlas. Desde C-04 son `0001` (`btree_gist`), `0002` (`consultorio` y `usuario`), `0003` (`consultorio.codigo`, `sesion` e `intento_login`) y `0004` (esquema `acceso`, sus funciones, RLS, políticas y privilegios, sin roles). NO DEBEN (MUST NOT) crear otras tablas, insertar filas en ninguna tabla ni ejecutar el seed, que tiene su propio comando explícito.

#### Scenario: El comando explícito deja la base al día
- **DADO** una base sin migraciones aplicadas o con migraciones parciales
- **CUANDO** se ejecuta el comando explícito de migración
- **ENTONCES** la revisión actual registrada en la base coincide con la última revisión del repositorio

#### Scenario: El arranque de la API no migra
- **CUANDO** se inspecciona el comando de arranque efectivo del servicio `api` en la configuración resuelta de Docker Compose
- **ENTONCES** no invoca migraciones

#### Scenario: Sin tablas de dominio
Se conserva el nombre del escenario de C-01 (OpenSpec no admite renombrar escenarios en una delta) con contenido actualizado: "dominio" se refiere a las tablas de agenda, pacientes y turnos de Changes posteriores; `consultorio` y `usuario` son el modelo base de C-02, y `sesion` e `intento_login` son las tablas de autenticación de C-03. La migración `0004` de C-04 no crea tablas.
- **DADO** que se aplicaron las migraciones
- **CUANDO** se listan las tablas del esquema `public`
- **ENTONCES** las tablas son exactamente `alembic_version`, `consultorio`, `intento_login`, `sesion` y `usuario`

#### Scenario: Tablas del modelo base vacías tras migrar
- **DADO** que se aplicaron las migraciones desde `base`
- **CUANDO** se cuentan las filas de `consultorio`, `usuario`, `sesion` e `intento_login`
- **ENTONCES** las cuatro tienen cero filas

### Requirement: Las pruebas de integración fallan sin base real
Si la base configurada no es accesible, la preparación de las pruebas de integración DEBE (MUST) fallar con error; NO DEBE (MUST NOT) omitir las pruebas ni sustituir la base.

#### Scenario: Base inaccesible
- **DADO** que la URL de la base apunta a `host-inexistente.invalid`
- **CUANDO** se ejecuta la verificación de conexión que usa la preparación de las pruebas de integración
- **ENTONCES** termina con un error de conexión
- **Y** no se marca como omitida

### Requirement: Las pruebas de integración no tocan la base de desarrollo
Las pruebas de integración y de aislamiento y las migraciones del comando único DEBEN (MUST) usar una base efímera y separada (`db-test`, `TEST_DATABASE_URL`). La preparación DEBE (MUST) negarse si la URL de pruebas falta, coincide en host, puerto y base con `DATABASE_URL`, `DATABASE_LOGIN_URL` o `DATABASE_MIGRATION_URL`, o su base no termina en `_test`. `db-test` NO DEBE (MUST NOT) usar volúmenes con nombre ni publicar puertos; solo monta, de solo lectura, su script de roles.

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
- **Y** su único montaje es el script de roles de prueba, de solo lectura, dentro de `/docker-entrypoint-initdb.d`

#### Scenario: La suite corre sobre la base de pruebas
- **DADO** que `db-test` está en ejecución
- **CUANDO** la preparación de las pruebas de integración abre la conexión
- **ENTONCES** `current_database()` es el nombre de la base de pruebas y no el de la base de desarrollo

#### Scenario: URL de pruebas igual a la de administración rechazada
- **DADO** una URL de pruebas con el mismo host, puerto y nombre de base que `DATABASE_MIGRATION_URL` o que `DATABASE_LOGIN_URL`, aunque cambien las credenciales
- **CUANDO** se ejecuta la guardia de la base de pruebas
- **ENTONCES** la guardia falla y el error no contiene URLs ni contraseñas

### Requirement: Migraciones de pruebas protegidas por la guardia
Toda conexión de migración destinada a la base de pruebas (`-x target=test` o una URL explícita fijada por código) DEBE (MUST) pasar por la guardia de la base de pruebas antes de abrirse. Desde C-04, la migración de desarrollo (sin `-x` o con `target=desarrollo`) DEBE (MUST) usar `DATABASE_MIGRATION_URL` y fallar si falta, nunca `DATABASE_URL`; los dos destinos NO DEBEN (MUST NOT) confundirse. Los errores NO DEBEN (MUST NOT) incluir URLs ni credenciales.

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
Se conserva el nombre del escenario de C-01 (OpenSpec no admite renombrar escenarios en una delta) con contenido actualizado por la decisión DA-02 de C-04: la migración de desarrollo usa la credencial de administración, distinta de la de la API.
- **DADO** una ejecución sin `-x target` (o con `target=desarrollo`), sin URL explícita y con `DATABASE_MIGRATION_URL` definida
- **CUANDO** Alembic resuelve la URL de la migración
- **ENTONCES** usa `DATABASE_MIGRATION_URL` y no `DATABASE_URL`, sin exigir ni validar `TEST_DATABASE_URL`

#### Scenario: Destino de migración desconocido rechazado
- **DADO** un valor de `-x target` distinto de `desarrollo` y `test`
- **CUANDO** Alembic resuelve la URL de la migración
- **ENTONCES** la resolución falla y el error lista los valores admitidos

#### Scenario: Migración de desarrollo sin credencial de administración
- **DADO** una ejecución sin `-x target` y sin `DATABASE_MIGRATION_URL`
- **CUANDO** Alembic resuelve la URL de la migración
- **ENTONCES** la resolución falla con un error que menciona `DATABASE_MIGRATION_URL`, sin abrir ninguna conexión

### Requirement: Backfill de la migración 0003 limitado a la columna nueva
La única modificación de datos existentes que admiten las migraciones DEBE (MUST) ser el backfill de `consultorio.codigo` de `0003`, que solo escribe esa columna nueva (justificación: DA-03, aprobada por el autor el 2026-11-05). Aplicar `0003` sobre la base de desarrollo requiere autorización explícita del autor.

#### Scenario: El backfill solo escribe la columna nueva
- **DADO** la base de pruebas en `0002` con consultorios y usuarios ficticios
- **CUANDO** se sube a `0003`
- **ENTONCES** cada columna de `consultorio` existente en `0002` y cada columna de `usuario` conserva su valor
- **Y** la cantidad de filas de `consultorio` y de `usuario` no cambia

### Requirement: Plantilla de variables montada de solo lectura en api
El servicio `api` de Docker Compose DEBE (MUST) montar únicamente `.env.example` de solo lectura en `/repo/.env.example`, fuera de `/app`, para las pruebas de la plantilla. NO DEBE (MUST NOT) montar `.env` ni otro archivo de secretos.

#### Scenario: Montaje de solo lectura
- **CUANDO** se inspecciona la configuración resuelta de Compose
- **ENTONCES** `api` monta `.env.example` en `/repo/.env.example` con `read_only` verdadero
- **Y** ningún servicio monta `.env`

#### Scenario: Escritura rechazada
- **CUANDO** un proceso del contenedor `api` intenta escribir en `/repo/.env.example`
- **ENTONCES** la escritura falla por sistema de archivos de solo lectura

### Requirement: Entorno de la API limitado a variables permitidas
El servicio `api` de Docker Compose NO DEBE (MUST NOT) usar `env_file` y DEBE (MUST) recibir solo las variables permitidas, cada una con su valor interpolado de forma explícita en un mapa `environment`. NO DEBE (MUST NOT) recibir `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB`, `PGPASSWORD` ni `TEST_DATABASE_URL`.

#### Scenario: Definición del servicio api
- **CUANDO** se inspecciona `docker-compose.yml`
- **ENTONCES** `api` no tiene `env_file` y las claves de su `environment` son exactamente `DATABASE_URL`, `DATABASE_LOGIN_URL`, `AUTH_SECRET_KEY`, `CORS_ALLOWED_ORIGINS`, `APP_ENV`, `AUTH_SESSION_MINUTES`, `AUTH_SESSION_MAX_HOURS`, `AUTH_COOKIE_SECURE` y `WATCHFILES_FORCE_POLLING`
- **Y** cada valor es un literal o una interpolación explícita, con `${VARIABLE:?mensaje}` para las cinco primeras, nunca una entrada de lista sin valor
- **Y** ninguna clave es de administración

#### Scenario: Entorno efectivo del contenedor api
- **DADO** el servicio `api` en ejecución
- **CUANDO** se listan solo los nombres de las variables de entorno del contenedor
- **ENTONCES** no aparecen `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB`, `PGPASSWORD` ni `TEST_DATABASE_URL`

#### Scenario: Variables del shell no se propagan
- **DADO** un proceso de PowerShell que define `DATABASE_MIGRATION_URL` y `POSTGRES_PASSWORD` con valores ficticios
- **CUANDO** se crea un contenedor del servicio `api` desde ese proceso sin opciones `-e`
- **ENTONCES** esas variables no aparecen entre los nombres del entorno del contenedor

### Requirement: Servicio administrativo efímero separado de la API
Docker Compose DEBE (MUST) definir un servicio `admin` con la imagen del backend, `env_file: .env`, perfil `admin`, `restart: "no"` y sin puertos publicados, del que ningún otro servicio dependa. Su comando por defecto DEBE (MUST) terminar de inmediato con código distinto de cero y un mensaje fijo que indique usar `docker compose run --rm --no-deps admin <comando>`, para que seleccionarlo con `up` no lo deje en ejecución.

#### Scenario: Definición del servicio admin
- **CUANDO** se inspecciona `docker-compose.yml`
- **ENTONCES** `admin` tiene perfil `admin`, `restart: "no"`, `env_file`, ningún `ports` y un comando por defecto que termina con error
- **Y** ningún servicio lo declara en `depends_on`

#### Scenario: Arranque normal sin admin
- **CUANDO** se ejecuta `docker compose up -d` sin perfiles
- **ENTONCES** no se crea ningún contenedor del servicio `admin`

#### Scenario: Selección explícita no lo deja en ejecución
- **CUANDO** se selecciona `admin` explícitamente con `up` o se ejecuta `docker compose run --rm --no-deps admin` sin comando
- **ENTONCES** el contenedor termina con código distinto de cero y el mensaje fijo, sin publicar puertos
- **Y** `docker compose ps` no muestra ningún contenedor `admin` en ejecución

### Requirement: Administración solo desde el servicio admin
Las migraciones de desarrollo, el seed y los comandos de credenciales, roles y mantenimiento DEBEN (MUST) documentarse y ejecutarse con `docker compose run --rm --no-deps admin`. Ejecutados con `api` DEBEN (MUST) fallar sin conectar, con el mensaje que menciona `DATABASE_MIGRATION_URL`.

#### Scenario: Migraciones de desarrollo con admin
- **DADO** la base de desarrollo en una revisión conocida
- **CUANDO** se ejecuta `docker compose run --rm --no-deps admin alembic current`
- **ENTONCES** informa esa revisión usando `DATABASE_MIGRATION_URL`

#### Scenario: Administración desde api falla cerrado
- **CUANDO** se ejecuta `docker compose run --rm --no-deps api alembic current`
- **ENTONCES** termina con código distinto de cero y un mensaje que menciona `DATABASE_MIGRATION_URL`, sin abrir conexiones

#### Scenario: Comandos documentados con admin
- **CUANDO** se inspeccionan `README.md` y la ayuda de los módulos `app.credenciales`, `app.roles_postgres` y `app.mantenimiento`
- **ENTONCES** las migraciones de desarrollo, el seed y esos comandos se indican con el servicio `admin` y no con `api`

### Requirement: Código montado de solo lectura en api y admin
Los servicios `api` y `admin` DEBEN (MUST) montar el código del backend de solo lectura (`./backend:/app:ro`) y NO DEBEN (MUST NOT) tener otro montaje escribible sobre el código ni privilegios adicionales (`privileged`, `cap_add`, `security_opt`). La recarga de la API, las pruebas y los comandos administrativos DEBEN (MUST) funcionar sin escribir en `/app`.

#### Scenario: Definición de los montajes
- **CUANDO** se inspecciona `docker-compose.yml`
- **ENTONCES** `api` y `admin` montan `./backend` en `/app` con `read_only` y ningún otro montaje de esos servicios es escribible sobre el código
- **Y** ninguno declara `privileged`, `cap_add` ni `security_opt`

#### Scenario: Escritura en el código rechazada
- **DADO** un contenedor del servicio `api`
- **CUANDO** se intenta crear un archivo en `/app`
- **ENTONCES** la operación falla con un error de sistema de archivos de solo lectura y no queda ningún archivo

#### Scenario: Montaje efectivo del servicio en ejecución
- **DADO** el servicio `api` en ejecución
- **CUANDO** se inspeccionan los montajes del contenedor
- **ENTONCES** el destino `/app` figura como no escribible

#### Scenario: La recarga funciona con el código de solo lectura
- **DADO** el servicio `api` en ejecución con el código de solo lectura
- **CUANDO** cambia la fecha de modificación de un archivo del backend en el host, sin cambiar su contenido
- **ENTONCES** el proceso de recarga detecta el cambio, reinicia el servidor y `GET /api/health` responde 200

# aislamiento-base-de-datos Specification

## Purpose
Agregar en PostgreSQL una barrera de aislamiento entre consultorios que no dependa de que cada consulta de la aplicación incluya su filtro: rol de aplicación sin privilegios, seguridad a nivel de fila cerrada por defecto, contexto por transacción, privilegios mínimos y referencias del mismo consultorio garantizadas por claves compuestas (RN-MT-03, RN-MT-06, PA-04).

Convenciones de los escenarios: las pruebas se ejecutan contra PostgreSQL 18 real en `db-test` (X2), nunca contra la base de desarrollo, con datos ficticios (D1). "Rol de aplicación" es `turnos_app` (`DATABASE_URL`); "rol de login" es `turnos_login` (`DATABASE_LOGIN_URL`); "dueños de las funciones" son `turnos_acceso_previo` y `turnos_acceso_login`; "rol de administración" es el de `DATABASE_MIGRATION_URL` (`app`). "Contexto" es el valor de `app.consultorio_id` en la transacción. Salvo indicación expresa, las pruebas usan conexiones reales autenticadas como el rol indicado, no `SET ROLE` desde un superusuario. Esta barrera protege ante errores de programación (filtros omitidos) y separa el código de negocio de las credenciales; no protege ante una aplicación comprometida, que puede fijar el contexto y usar todas sus conexiones.

## Requirements

### Requirement: Roles de conexión sin privilegios
La API DEBE (MUST) conectarse con dos roles distintos, el de aplicación y el de login, ambos con `LOGIN` y sin `SUPERUSER`, `BYPASSRLS`, `CREATEROLE`, `CREATEDB` ni `REPLICATION`, sin objetos propios y sin membresías. Los dueños de las funciones de acceso DEBEN (MUST) ser `NOLOGIN`, sin esos atributos, sin membresías y dueños solo de sus funciones.

#### Scenario: Atributos del rol de aplicación
- **CUANDO** se consulta el catálogo de `db-test` para el rol de aplicación
- **ENTONCES** tiene `LOGIN` y no tiene `SUPERUSER`, `BYPASSRLS`, `CREATEROLE` ni `CREATEDB`
- **Y** no es dueño de tablas, funciones, esquemas ni secuencias y no pertenece a ningún rol

#### Scenario: Atributos del rol de login
- **CUANDO** se consulta el catálogo de `db-test` para el rol de login
- **ENTONCES** tiene `LOGIN` y no tiene `SUPERUSER`, `BYPASSRLS`, `CREATEROLE`, `CREATEDB` ni `REPLICATION`
- **Y** no es dueño de objetos, no pertenece a ningún rol y ningún rol pertenece a él

#### Scenario: Atributos del dueño de las funciones
- **CUANDO** se consulta el catálogo de `db-test` para cada dueño de las funciones
- **ENTONCES** no tiene `LOGIN`, `SUPERUSER` ni `BYPASSRLS` y no pertenece a ningún rol

### Requirement: La API rechaza un rol de base privilegiado
Cada conexión nueva de los motores de aplicación y de login DEBE (MUST) verificar que su `current_user` es exactamente el rol esperado de ese motor, que no es superusuario, no tiene `BYPASSRLS`, no es dueño de objetos ni miembro de roles, y sus capacidades: el de aplicación sin acceso a credenciales ni a funciones de login; el de login sin privilegios de tabla. Si no, la conexión DEBE (MUST) descartarse sin ejecutar consultas de la petición y la respuesta NO DEBE (MUST NOT) contener datos.

#### Scenario: Conexión como rol de administración rechazada
- **DADO** una aplicación configurada con `DATABASE_URL` del rol de administración de `db-test`
- **CUANDO** se hace `GET /api/auth/me` con una cookie bien formada
- **ENTONCES** la petición falla sin consultar `sesion` y la respuesta no contiene datos de usuarios ni de consultorios

#### Scenario: Conexión como rol de aplicación admitida
- **DADO** una aplicación configurada con el rol de aplicación de `db-test`
- **CUANDO** se hace `GET /api/auth/me` con una sesión válida
- **ENTONCES** la respuesta es 200

#### Scenario: URL de login con el rol de aplicación rechazada
- **DADO** una aplicación con `DATABASE_LOGIN_URL` del rol de aplicación de `db-test`
- **CUANDO** se hace un login con credenciales correctas
- **ENTONCES** la petición falla sin buscar la cuenta, sin crear sesión y sin datos en la respuesta

#### Scenario: URL de la API con el rol de login rechazada
- **DADO** una aplicación con `DATABASE_URL` del rol de login de `db-test`
- **CUANDO** se hace `GET /api/auth/me` con una cookie bien formada
- **ENTONCES** la petición falla sin datos en la respuesta

#### Scenario: Rol con otro nombre rechazado
- **DADO** un rol de prueba con los mismos atributos y privilegios que el rol de aplicación pero otro nombre, creado y eliminado por la prueba, configurado en `DATABASE_URL`
- **CUANDO** se hace `GET /api/auth/me` con una cookie bien formada
- **ENTONCES** la petición falla porque `current_user` no es el rol esperado y la respuesta no contiene datos

#### Scenario: Conexión de login como rol de administración rechazada
- **DADO** una aplicación con `DATABASE_LOGIN_URL` del rol de administración de `db-test`
- **CUANDO** se hace un login con credenciales correctas
- **ENTONCES** la petición falla sin crear sesión y sin datos en la respuesta

### Requirement: Conexión de login restringida al login
Las sesiones de base del rol de login DEBEN (MUST) abrirse solo mediante una dependencia exclusiva de `POST /api/auth/login`; ninguna otra ruta, servicio, repositorio ni comando local DEBE (MUST) usar esa dependencia, su fábrica, su motor ni `DATABASE_LOGIN_URL`.

#### Scenario: Única ruta con la sesión de login
- **CUANDO** se recorren las rutas de la aplicación real y sus dependencias
- **ENTONCES** la única que depende de la sesión de login es `POST /api/auth/login`

#### Scenario: Ruta nueva con la sesión de login detectada
- **DADO** una aplicación de prueba con otra ruta que depende de la sesión de login
- **CUANDO** se ejecuta la verificación del recorrido
- **ENTONCES** falla nombrando el método y la ruta

#### Scenario: Usos acotados en el código
- **CUANDO** se buscan en el código de la aplicación los usos de la dependencia, la fábrica y el motor de login, del módulo de funciones de login y de `DATABASE_LOGIN_URL`
- **ENTONCES** solo aparecen en la fábrica de la app, la configuración, la dependencia, la ruta de login y el servicio de autenticación

### Requirement: Seguridad a nivel de fila forzada y cerrada por defecto
`consultorio`, `usuario` y `sesion` DEBEN (MUST) tener RLS habilitada y forzada con una política que exige, en lectura y escritura, que el consultorio de la fila sea `NULLIF(current_setting('app.consultorio_id', true), '')::uuid`. Sin contexto, el rol de aplicación DEBE (MUST) ver cero filas; un contexto que no es UUID DEBE (MUST) producir un error.

#### Scenario: Sin contexto no hay filas
- **DADO** consultorios A y B con usuarios y sesiones
- **CUANDO** el rol de aplicación consulta `consultorio`, `usuario` y `sesion` sin contexto
- **ENTONCES** las tres consultas devuelven cero filas

#### Scenario: Contexto vacío equivale a sin contexto
- **CUANDO** el rol de aplicación fija el contexto en `''` dentro de una transacción y consulta `usuario`
- **ENTONCES** devuelve cero filas

#### Scenario: Contexto no UUID
- **CUANDO** el rol de aplicación fija el contexto en `abc` dentro de una transacción y consulta `usuario`
- **ENTONCES** la consulta falla con un error de conversión

#### Scenario: RLS forzada en el catálogo
- **CUANDO** se consultan `relrowsecurity` y `relforcerowsecurity` de `consultorio`, `usuario`, `sesion` e `intento_login`
- **ENTONCES** ambos valen verdadero en las cuatro tablas

### Requirement: Filas acotadas por la base aunque falte el filtro
Con el contexto de A, una consulta del rol de aplicación sin condición sobre el consultorio DEBE (MUST) ver y modificar solo filas de A, y NO DEBE (MUST NOT) poder insertar ni mover filas a otro consultorio.

#### Scenario: Lectura sin filtro
- **DADO** el contexto de A y tres usuarios en A y tres en B
- **CUANDO** el rol de aplicación ejecuta `SELECT id FROM usuario` sin condición
- **ENTONCES** obtiene exactamente los tres usuarios de A

#### Scenario: Modificación de una fila de otro consultorio
- **DADO** el contexto de A y una sesión activa de B
- **CUANDO** el rol de aplicación revoca esa sesión por su `id`
- **ENTONCES** se afectan cero filas y la sesión de B sigue activa

#### Scenario: Inserción en otro consultorio
- **DADO** el contexto de A
- **CUANDO** el rol de aplicación inserta una sesión con el `consultorio_id` de B
- **ENTONCES** la inserción falla por la política de seguridad a nivel de fila

### Requirement: Contexto de consultorio por transacción
El contexto DEBE (MUST) fijarse con alcance de transacción al comenzar cada transacción de la sesión de la petición, con el consultorio de la identidad o vacío si no la hay. NO DEBE (MUST NOT) fijarse a nivel de sesión de PostgreSQL ni persistir en una conexión devuelta al pool; tras `COMMIT`, `ROLLBACK` o `ROLLBACK TO SAVEPOINT` DEBE (MUST) restablecerse.

#### Scenario: Recuperación tras COMMIT
- **DADO** una sesión de base con el contexto de A
- **CUANDO** se confirma una transacción y se ejecuta una consulta en la siguiente
- **ENTONCES** la nueva transacción tiene el contexto de A

#### Scenario: Reversión
- **DADO** una transacción que fija el contexto de A después de comenzar
- **CUANDO** se revierte con `ROLLBACK` o se revierte un savepoint creado antes de fijarlo
- **ENTONCES** el contexto vuelve al valor previo

#### Scenario: Conexión del pool sin contexto
- **DADO** un motor con una sola conexión en el pool usada por una petición de A
- **CUANDO** otra sesión toma esa conexión sin identidad y consulta `current_setting('app.consultorio_id', true)`
- **ENTONCES** el valor es vacío o nulo

#### Scenario: Sin SET de sesión
- **CUANDO** se buscan en el código de la aplicación sentencias que fijen `app.consultorio_id`
- **ENTONCES** solo existe la llamada a `set_config` con alcance de transacción

### Requirement: Privilegios mínimos del rol de aplicación
El rol de aplicación DEBE (MUST) tener solo: lectura de `consultorio`; lectura de `usuario` sin `credencial`; lectura de `sesion` sin `token_hmac`, inserción de sesiones y modificación de `revocada_en`; uso de los esquemas `public` y `acceso` y ejecución de las funciones de sesión. NO DEBE (MUST NOT) leer ni modificar `usuario.credencial`, ejecutar funciones de login ni tener privilegios sobre `intento_login`, `alembic_version` ni de borrado.

#### Scenario: Privilegios del catálogo
- **CUANDO** se comparan los privilegios de tabla, de columna y de función del rol de aplicación con la lista del requisito
- **ENTONCES** coinciden exactamente

#### Scenario: Columnas secretas no legibles
- **DADO** el contexto de A
- **CUANDO** el rol de aplicación selecciona `usuario.credencial` o `sesion.token_hmac`
- **ENTONCES** la consulta falla por falta de privilegios

#### Scenario: Credencial no modificable
- **DADO** el contexto de A
- **CUANDO** el rol de aplicación actualiza `usuario.credencial` de un usuario de A
- **ENTONCES** la sentencia falla por falta de privilegios y la credencial no cambia

#### Scenario: Tablas sin privilegios
- **CUANDO** el rol de aplicación consulta `intento_login` o `alembic_version`, o borra una fila de `sesion`
- **ENTONCES** cada sentencia falla por falta de privilegios

### Requirement: Privilegios mínimos del rol de login
El rol de login DEBE (MUST) tener solo uso del esquema `acceso` y ejecución de las funciones de login. NO DEBE (MUST NOT) tener privilegios sobre ninguna tabla, ejecutar funciones de sesión, crear objetos ni adoptar otro rol; por eso solo DEBE (MUST) leer credenciales e intentos a través de las funciones de login y NO DEBE (MUST NOT) poder modificar credenciales por ningún camino.

#### Scenario: Privilegios del catálogo del rol de login
- **CUANDO** se comparan los privilegios de esquema, tabla, columna y función del rol de login con la lista del requisito
- **ENTONCES** coinciden exactamente

#### Scenario: Sin acceso a tablas
- **CUANDO** el rol de login consulta `consultorio`, `usuario`, `sesion` o `intento_login`, o actualiza `usuario.credencial`
- **ENTONCES** cada sentencia falla por falta de privilegios

#### Scenario: Sin escalada de privilegios
- **CUANDO** el rol de login ejecuta `SET ROLE turnos_app`, `SET ROLE app`, `CREATE ROLE` o crea una tabla en `public`
- **ENTONCES** cada sentencia falla por falta de privilegios

### Requirement: Referencias del mismo consultorio con claves compuestas
Toda tabla con `consultorio_id`, salvo `consultorio`, DEBE (MUST) tener `UNIQUE (consultorio_id, id)`, y toda clave foránea hacia una tabla con `consultorio_id` DEBE (MUST) incluir `consultorio_id`, porque la integridad referencial no aplica RLS. Una prueba de esquema DEBE (MUST) verificarlo sobre el catálogo.

#### Scenario: Esquema actual conforme
- **DADO** la base de pruebas en `head`
- **CUANDO** se ejecuta la verificación de claves compuestas sobre el catálogo
- **ENTONCES** no informa incumplimientos

#### Scenario: Tabla no conforme detectada
- **DADO** una tabla temporal de prueba con `consultorio_id` y una clave foránea simple hacia `usuario (id)`
- **CUANDO** se ejecuta la verificación de claves compuestas incluyéndola
- **ENTONCES** informa esa clave foránea como incumplimiento

#### Scenario: Referencia cruzada rechazada
- **CUANDO** se inserta como administración una sesión con el `consultorio_id` de A y el `usuario_id` de un usuario de B
- **ENTONCES** la inserción falla por la clave foránea compuesta

### Requirement: Toda tabla nueva con RLS
Toda tabla del esquema `public`, salvo `alembic_version`, DEBE (MUST) tener RLS habilitada y forzada; las que tienen `consultorio_id` (o `consultorio`) DEBEN (MUST) tener la política de consultorio del requisito de RLS. Una prueba de esquema DEBE (MUST) fallar ante una tabla que no cumpla.

#### Scenario: Tablas actuales conformes
- **CUANDO** se ejecuta la verificación de RLS sobre las tablas de `public`
- **ENTONCES** no informa incumplimientos

#### Scenario: Tabla sin RLS detectada
- **DADO** una tabla temporal de prueba con `consultorio_id` sin RLS
- **CUANDO** se ejecuta la verificación de RLS incluyéndola
- **ENTONCES** la informa como incumplimiento

### Requirement: Migración 0004 con verificación previa de roles
La migración `0004` DEBE (MUST) depender de `0003`, crear el esquema `acceso`, sus funciones, las políticas y los privilegios, sin crear roles, tablas ni filas. Antes de cualquier cambio DEBE (MUST) fallar si falta alguno de los roles de conexión o de los dueños de las funciones, o si alguno tiene atributos indebidos, membresías u objetos propios. Solo con autorización del autor se aplica en desarrollo.

#### Scenario: Roles ausentes
- **DADO** una base de prueba en `0003` en un servidor sin el rol de aplicación
- **CUANDO** se sube a `0004`
- **ENTONCES** la migración falla con un mensaje que nombra el rol faltante
- **Y** la revisión sigue en `0003` sin políticas ni esquema `acceso`

#### Scenario: Rol de aplicación con atributos indebidos
- **DADO** el rol de aplicación con `BYPASSRLS`
- **CUANDO** se sube a `0004`
- **ENTONCES** la migración falla sin cambios

#### Scenario: Rol de login con atributos o membresías indebidos
- **DADO** el rol de login con `SUPERUSER`, o miembro del rol de aplicación
- **CUANDO** se sube a `0004`
- **ENTONCES** la migración falla sin cambios con un mensaje que nombra el rol

#### Scenario: Subida desde 0003 con datos previos
- **DADO** la base de pruebas en `0003` con consultorios, usuarios y sesiones ficticios
- **CUANDO** se sube a `0004`
- **ENTONCES** las filas y sus valores no cambian y la revisión `head` es `0004`

### Requirement: Migración 0004 reversible
La reversión de `0004` a `0003` DEBE (MUST) eliminar las políticas, la RLS, los privilegios concedidos y el esquema `acceso` con sus funciones, sin eliminar roles ni datos, y solo DEBE (MUST) ejecutarse contra la base de pruebas.

#### Scenario: Bajada a 0003
- **DADO** la base de pruebas en `0004` con datos ficticios
- **CUANDO** se baja a `0003`
- **ENTONCES** no existen políticas, el esquema `acceso` ni privilegios de los roles de conexión y de los dueños de las funciones sobre las tablas
- **Y** `relrowsecurity` es falso en las cuatro tablas, los datos no cambian y los roles siguen existiendo

### Requirement: Creación local de roles explícita
Los roles DEBEN (MUST) crearse fuera de las migraciones: en `db-test`, con el script de inicialización; en desarrollo, con un comando local idempotente, solo con `APP_ENV=local`, con la credencial de administración y la contraseña de cada rol de conexión por entrada interactiva oculta, distinta entre ambos, sin enviarla en texto plano en SQL ni mostrarla.

#### Scenario: Entorno de pruebas rechazado
- **DADO** `APP_ENV=test`
- **CUANDO** se ejecuta el comando de creación de roles
- **ENTONCES** termina con código distinto de cero sin abrir conexiones

#### Scenario: Ejecución idempotente
- **DADO** una base de pruebas donde los roles ya existen con los atributos esperados
- **CUANDO** se ejecuta la creación de roles con entradas inyectadas y sin la opción de rotar
- **ENTONCES** no cambia atributos ni contraseñas y termina con código 0

#### Scenario: Contraseña nunca en texto plano
- **CUANDO** se crean el rol de aplicación y el rol de login con contraseñas ficticias inyectadas
- **ENTONCES** cada sentencia enviada contiene solo un verificador `SCRAM-SHA-256` y ni las sentencias ni la salida contienen las contraseñas

#### Scenario: Contraseñas iguales rechazadas
- **CUANDO** se ingresa la misma contraseña ficticia para el rol de aplicación y para el rol de login
- **ENTONCES** el comando falla sin crear el segundo rol y la salida no contiene la contraseña

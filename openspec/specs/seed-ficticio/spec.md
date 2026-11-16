# seed-ficticio Specification

## Purpose
Ofrecer datos iniciales ficticios de dos consultorios con un usuario por rol, cargados con un comando explícito, idempotente y no destructivo, para probar el aislamiento entre consultorios y los permisos por rol sin datos reales (DD-13, SU-09, RN-PA-08).

Convenciones de los escenarios: las pruebas del contenido y de la idempotencia aplican el seed dentro de una transacción en la base de pruebas `db-test` y la deshacen al terminar (X2); la guardia de entorno se prueba sin abrir conexiones. El seed solo contiene datos ficticios (D1).

## Requirements

### Requirement: Seed separado de las migraciones
El seed DEBE (MUST) ejecutarse solo mediante un comando explícito propio, documentado e independiente de las migraciones. Aplicar las migraciones NO DEBE (MUST NOT) insertar datos ni invocar el seed, y el arranque de la API tampoco.

#### Scenario: Migrar no carga datos
- **DADO** la base de pruebas migrada a `head` desde `base`
- **CUANDO** se cuentan las filas de `consultorio` y `usuario`
- **ENTONCES** ambas tienen cero filas

#### Scenario: El arranque de la API no ejecuta el seed
- **CUANDO** se inspecciona el comando de arranque efectivo del servicio `api` en la configuración resuelta de Docker Compose
- **ENTONCES** no invoca el seed

### Requirement: Contenido ficticio del seed
El seed DEBE (MUST) crear exactamente los consultorios "Consultorio Demo A" y "Consultorio Demo B" y, en cada uno, un usuario con rol `administrador`, uno con `secretaria` y uno con `odontologo`. Todos los emails DEBEN (MUST) pertenecer al dominio reservado `example.test` y los nombres DEBEN (MUST) ser evidentemente ficticios.

#### Scenario: Dos consultorios y seis usuarios
- **DADO** la base de pruebas migrada y vacía
- **CUANDO** se aplica el seed
- **ENTONCES** hay exactamente 2 consultorios, "Consultorio Demo A" y "Consultorio Demo B"
- **Y** hay exactamente 6 usuarios, 3 por consultorio, con un usuario de cada rol en cada uno

#### Scenario: Datos evidentemente ficticios
- **CUANDO** se aplica el seed
- **ENTONCES** todos los emails terminan en `@example.test`
- **Y** todos los nombres de usuario contienen `Demo`

#### Scenario: Valores de consultorio del seed
- **CUANDO** se aplica el seed
- **ENTONCES** ambos consultorios quedan activos, con `zona_horaria = 'America/Argentina/Buenos_Aires'` y `anticipacion_cancelacion_horas = 24`
- **Y** "Consultorio Demo A" tiene el código `c-c7d08d776d19` y "Consultorio Demo B" el código `c-c7d1647cab52`

### Requirement: Usuarios del seed sin credenciales utilizables
Los usuarios del seed DEBEN (MUST) quedar **sin credencial** (credencial nula). El seed NO DEBE (MUST NOT) contener contraseñas, hashes ni ningún valor que permita autenticarse.

#### Scenario: Seis usuarios sin credencial
- **CUANDO** se aplica el seed
- **ENTONCES** los 6 usuarios tienen `credencial` nula

### Requirement: Seed idempotente
Ejecutar el seed más de una vez DEBE (MUST) dejar el mismo resultado que ejecutarlo una vez, sin duplicar filas ni fallar. Los registros del seed DEBEN (MUST) tener identificadores fijos, iguales en cada ejecución.

#### Scenario: Dos ejecuciones no duplican
- **DADO** la base de pruebas migrada y vacía
- **CUANDO** se aplica el seed dos veces seguidas
- **ENTONCES** hay exactamente 2 consultorios y 6 usuarios
- **Y** la segunda ejecución informa 0 filas insertadas

#### Scenario: Identificadores fijos
- **CUANDO** se aplica el seed, se deshace y se vuelve a aplicar
- **ENTONCES** los identificadores de los consultorios y usuarios son los mismos en ambas aplicaciones

### Requirement: Seed no destructivo
El seed NO DEBE (MUST NOT) actualizar ni borrar filas existentes. Si ya existe una fila con el mismo identificador o con el mismo email en el mismo consultorio, DEBE (MUST) omitirla sin modificarla y DEBE (MUST) informar cuántas filas omitió.

#### Scenario: Una fila del seed modificada no se sobrescribe
- **DADO** el seed aplicado y luego el nombre de "Consultorio Demo A" cambiado a `Consultorio Ficticio Renombrado`
- **CUANDO** se aplica el seed de nuevo
- **ENTONCES** el consultorio conserva el nombre `Consultorio Ficticio Renombrado`
- **Y** hay exactamente 2 consultorios

#### Scenario: Una fila ajena con el mismo email se respeta
- **DADO** el seed aplicado, el usuario administrador del seed del consultorio A eliminado, y otro usuario creado fuera del seed en A con el mismo email y nombre `Persona Ficticia Previa`
- **CUANDO** se aplica el seed de nuevo
- **ENTONCES** el usuario creado fuera del seed conserva su `id` y su nombre
- **Y** el seed informa al menos 1 fila omitida y ningún error

### Requirement: Guardia de entorno del seed
El comando de seed DEBE (MUST) negarse a ejecutar, sin abrir ninguna conexión, si `APP_ENV` no es `local`, y DEBE (MUST) terminar con código distinto de cero indicando el motivo. Con `APP_ENV=local` DEBE (MUST) usar únicamente la credencial de administración `DATABASE_MIGRATION_URL`, nunca `DATABASE_URL` ni `DATABASE_LOGIN_URL` (roles de la API), y fallar sin conectar si falta.

#### Scenario: Entorno de pruebas rechazado
- **DADO** `APP_ENV=test` y `DATABASE_URL` apuntando a `host-inexistente.invalid`
- **CUANDO** se ejecuta el comando de seed
- **ENTONCES** termina con código distinto de cero y un mensaje que menciona `APP_ENV`
- **Y** no se intentó ninguna conexión a la base

#### Scenario: Entorno local admitido
- **DADO** `APP_ENV=local`
- **CUANDO** se evalúa la guardia de entorno del seed
- **ENTONCES** la guardia no rechaza la ejecución

#### Scenario: Usa la credencial de administración
- **DADO** `APP_ENV=local`, `DATABASE_URL` apuntando a `host-api.invalid` y `DATABASE_MIGRATION_URL` apuntando a `host-admin.invalid`
- **CUANDO** se abre la sesión de base por defecto del seed
- **ENTONCES** el motor apunta a `host-admin.invalid`
- **Y** sin `DATABASE_MIGRATION_URL` el seed falla sin conectar con un mensaje que la menciona

### Requirement: Salida del seed sin datos personales
La salida y los mensajes de error del seed DEBEN (MUST) informar solo cantidades (insertadas y omitidas por tabla) y NO DEBEN (MUST NOT) incluir emails, nombres, credenciales, URLs de conexión ni contraseñas (X1).

#### Scenario: Resumen solo con cantidades
- **CUANDO** se aplica el seed y se obtiene su resumen
- **ENTONCES** el resumen informa las cantidades insertadas y omitidas de consultorios y de usuarios
- **Y** no contiene `@`, ningún nombre de usuario del seed ni el texto `postgresql`

### Requirement: Código de consultorio del seed
Desde C-03, el seed DEBE (MUST) indicar el `codigo` de cada consultorio como literal explícito igual al código corto derivado de su `id` fijo con la función compartida de la aplicación (capacidad `modelo-consultorios-usuarios`), el mismo que produce el backfill de `0003` sobre una base que ya tenía el seed.

#### Scenario: Literales del seed iguales a la regla de derivación
- **CUANDO** se comparan los códigos declarados en los datos del seed con el código corto derivado del `id` de cada consultorio del seed
- **ENTONCES** son iguales para cada consultorio

#### Scenario: Mismo código en una base nueva y en una base con backfill
- **DADO** la base de pruebas en `0002` con el seed aplicado y subida luego a `0003` (camino 1), y la misma base de pruebas bajada a `base`, migrada a `0003` y con el seed aplicado después (camino 2)
- **CUANDO** se comparan los códigos de los consultorios del seed obtenidos por ambos caminos
- **ENTONCES** son idénticos

### Requirement: Seed sin sobrescritura del código ni de credenciales
El seed DEBE (MUST) seguir usando solo `INSERT ... ON CONFLICT DO NOTHING`: NO DEBE (MUST NOT) usar `UPDATE` ni `DELETE`, sobrescribir filas existentes ni escribir `credencial` (condición literal de DA-10: "No modificar el comando seed de C-02 para que sobrescriba contraseñas").

#### Scenario: El seed indica el código sin sobrescribir
- **CUANDO** se inspeccionan las sentencias que genera el seed
- **ENTONCES** las de consultorios incluyen la columna `codigo` con los literales del seed
- **Y** ninguna sentencia es un `UPDATE` ni un `DELETE`, todas son `INSERT ... ON CONFLICT DO NOTHING` y ninguna incluye la columna `credencial`

#### Scenario: Código del seed ocupado por un consultorio ajeno
- **DADO** la base de pruebas en `head` con un consultorio ajeno al seed cuyo código es `c-c7d08d776d19`
- **CUANDO** se aplica el seed y el llamador revierte la transacción ante el error
- **ENTONCES** el seed falla
- **Y** el consultorio ajeno conserva todas sus columnas y no queda ninguna fila del seed

### Requirement: Seed mediante el servicio administrativo
El comando DEBE (MUST) documentarse y ejecutarse con `docker compose run --rm --no-deps admin python -m app.seed`, el único servicio que recibe `DATABASE_MIGRATION_URL`. Ejecutado con el servicio `api`, que no la recibe, DEBE (MUST) terminar con código distinto de cero y el mensaje que la menciona, sin abrir conexiones.

#### Scenario: Comando documentado con admin
- **CUANDO** se inspeccionan `README.md` y la ayuda del módulo `app.seed`
- **ENTONCES** el comando se indica con el servicio `admin` y no con `api`

#### Scenario: Ejecutado con el entorno de la API
- **DADO** `APP_ENV=local` y el entorno de la API, sin `DATABASE_MIGRATION_URL`
- **CUANDO** se ejecuta el comando
- **ENTONCES** termina con código distinto de cero y un mensaje que menciona `DATABASE_MIGRATION_URL`, sin abrir conexiones

# Spec Delta: seed-ficticio

## Purpose

Ofrecer datos iniciales ficticios de dos consultorios con un usuario por rol, cargados con un comando explícito, idempotente y no destructivo, para probar el aislamiento entre consultorios y los permisos por rol sin datos reales (DD-13, SU-09, RN-PA-08).

Convenciones de los escenarios: las pruebas del contenido y de la idempotencia aplican el seed dentro de una transacción en la base de pruebas `db-test` y la deshacen al terminar (X2); la guardia de entorno se prueba sin abrir conexiones. El seed solo contiene datos ficticios (D1).

## ADDED Requirements

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
El comando de seed DEBE (MUST) negarse a ejecutar, sin abrir ninguna conexión, si `APP_ENV` no es `local`, y DEBE (MUST) terminar con código distinto de cero indicando el motivo. Con `APP_ENV=local` DEBE (MUST) usar únicamente `DATABASE_URL`.

#### Scenario: Entorno de pruebas rechazado
- **DADO** `APP_ENV=test` y `DATABASE_URL` apuntando a `host-inexistente.invalid`
- **CUANDO** se ejecuta el comando de seed
- **ENTONCES** termina con código distinto de cero y un mensaje que menciona `APP_ENV`
- **Y** no se intentó ninguna conexión a la base

#### Scenario: Entorno local admitido
- **DADO** `APP_ENV=local`
- **CUANDO** se evalúa la guardia de entorno del seed
- **ENTONCES** la guardia no rechaza la ejecución

### Requirement: Salida del seed sin datos personales
La salida y los mensajes de error del seed DEBEN (MUST) informar solo cantidades (insertadas y omitidas por tabla) y NO DEBEN (MUST NOT) incluir emails, nombres, credenciales, URLs de conexión ni contraseñas (X1).

#### Scenario: Resumen solo con cantidades
- **CUANDO** se aplica el seed y se obtiene su resumen
- **ENTONCES** el resumen informa las cantidades insertadas y omitidas de consultorios y de usuarios
- **Y** no contiene `@`, ningún nombre de usuario del seed ni el texto `postgresql`

# ejecucion-de-pruebas Specification

## Purpose
Ofrecer un único comando local que ejecuta todas las suites de pruebas del proyecto de forma reproducible, conserva la regresión de las pruebas existentes y falla de inmediato ante cualquier suite fallida, como evidencia para Verify y Archive (O2).

## Requirements

### Requirement: Comando único de pruebas
El repositorio DEBE (MUST) ofrecer `scripts/test.ps1` que, desde la raíz en Windows, ejecute en orden: autoprueba del propio runner, pruebas unitarias del backend, migraciones sobre la base de pruebas, pruebas de integración del backend contra PostgreSQL real (base de pruebas efímera `db-test`, nunca la de desarrollo), pruebas de aislamiento con los roles de aplicación y de login sobre `db-test`, verificación de tipos y pruebas del frontend. Si todas pasan, DEBE (MUST) terminar con código 0.

#### Scenario: Todas las suites pasan
- **DADO** que existe `.env` copiado de `.env.example` y Docker Desktop está en ejecución
- **CUANDO** se ejecuta `powershell -ExecutionPolicy Bypass -File scripts/test.ps1`
- **ENTONCES** se ejecutan los pasos en el orden del requisito
- **Y** el comando termina con código 0

#### Scenario: Paso de aislamiento después de integración
- **CUANDO** se inspecciona el texto de `scripts/test.ps1`
- **ENTONCES** el paso que ejecuta `tests/isolation` está inmediatamente después del que ejecuta `tests/integration` y antes de la verificación de tipos del frontend
- **Y** pasa `-e AUTH_SECRET_KEY`, `-e TURNOS_APP_TEST_PASSWORD` y `-e TURNOS_LOGIN_TEST_PASSWORD` solo por nombre

### Requirement: Detención ante el primer fallo
`scripts/test.ps1` DEBE (MUST) detenerse en el primer paso que termine con código distinto de cero, no ejecutar los pasos siguientes y terminar con código distinto de cero, indicando qué paso falló.

#### Scenario: Un paso falla
- **DADO** una secuencia de pasos del runner en la que el segundo termina con código 3
- **CUANDO** se ejecuta la secuencia
- **ENTONCES** el tercer paso no se ejecuta
- **Y** el runner termina con código distinto de cero
- **Y** el mensaje de error nombra el segundo paso

#### Scenario: Todos los pasos de la secuencia pasan
- **DADO** una secuencia de dos pasos que terminan con código 0
- **CUANDO** se ejecuta la secuencia
- **ENTONCES** ambos pasos se ejecutan y el runner no informa error

#### Scenario: Falta el archivo .env
- **DADO** que no existe `.env` en la raíz del repositorio
- **CUANDO** se ejecuta `scripts/test.ps1`
- **ENTONCES** termina con código distinto de cero antes de ejecutar cualquier suite
- **Y** el mensaje indica copiar `.env.example` a `.env`

### Requirement: Regresión de la validación de superposición
El comando único DEBE (MUST) ejecutar, sin modificarlas, las 19 pruebas existentes de `superposicion-turnos`, y todas DEBEN (MUST) pasar.

#### Scenario: Pruebas existentes en verde
- **CUANDO** se ejecuta el paso de pruebas unitarias del backend
- **ENTONCES** las 19 pruebas de `tests/unit/test_superposicion_turnos.py` se recolectan y pasan
- **Y** el archivo de pruebas no tiene cambios respecto del commit `f13f0ba`

### Requirement: Clave de autenticación efímera en el runner
`scripts/test.ps1` DEBE (MUST) generar en cada ejecución una `AUTH_SECRET_KEY` aleatoria (CSPRNG, 48 bytes, base64url sin relleno) que la configuración acepte, dejarla solo en el entorno del proceso y pasarla a los contenedores por nombre (`-e AUTH_SECRET_KEY`), sin literal, sin mostrarla ni escribirla, y quitarla del entorno al terminar.

#### Scenario: Funciona sin clave en .env
- **DADO** un `.env` sin `AUTH_SECRET_KEY`
- **CUANDO** se ejecuta `scripts/test.ps1`
- **ENTONCES** las migraciones sobre `db-test` y las pruebas de integración reciben la clave efímera y no fallan por su ausencia

#### Scenario: Clave generada válida y distinta
- **CUANDO** se generan dos claves efímeras
- **ENTONCES** cada una tiene 64 caracteres base64url sin relleno y al menos 20 distintos, y difieren entre sí

#### Scenario: Sin literal ni valor en argumentos
- **CUANDO** se inspecciona el texto de `scripts/test.ps1`
- **ENTONCES** pasa `-e AUTH_SECRET_KEY` solo por nombre y no contiene `AUTH_SECRET_KEY=`

### Requirement: Pruebas de la plantilla de variables
Las pruebas unitarias de la plantilla DEBEN (MUST) fallar, nunca omitirse, si `/repo/.env.example` no existe en el contenedor, y verificar que la plantilla se rechaza por `AUTH_SECRET_KEY` y es válida al reemplazar solo esa variable.

#### Scenario: Plantilla ausente
- **DADO** que `/repo/.env.example` no existe
- **CUANDO** se ejecutan las pruebas unitarias de la plantilla
- **ENTONCES** fallan

### Requirement: Contraseñas efímeras de los roles de conexión en el runner
`scripts/test.ps1` DEBE (MUST) generar en cada ejecución dos contraseñas aleatorias (CSPRNG) y distintas para los roles de aplicación y de login de `db-test`, dejarlas solo en `TURNOS_APP_TEST_PASSWORD` y `TURNOS_LOGIN_TEST_PASSWORD` del entorno del proceso, pasarlas por nombre a `db-test` y a las pruebas de aislamiento, sin literal, sin mostrarlas ni escribirlas, y quitarlas al terminar. Sin ellas, `db-test` NO DEBE (MUST NOT) quedar disponible.

#### Scenario: Contraseña generada válida y distinta
- **CUANDO** se generan dos contraseñas efímeras
- **ENTONCES** cada una tiene al menos 43 caracteres base64url sin relleno y difieren entre sí

#### Scenario: Sin literal y retirada del entorno
- **CUANDO** se inspecciona el texto de `scripts/test.ps1`
- **ENTONCES** no contiene `TURNOS_APP_TEST_PASSWORD=` ni `TURNOS_LOGIN_TEST_PASSWORD=` y retira ambas variables en el bloque final

#### Scenario: db-test sin contraseña no arranca
- **DADO** un proyecto de Compose aislado con `db-test` y su script de roles, sin `TURNOS_APP_TEST_PASSWORD` o sin `TURNOS_LOGIN_TEST_PASSWORD`
- **CUANDO** se levanta `db-test` esperando su estado saludable
- **ENTONCES** el arranque falla y no existen los roles de aplicación ni de login

### Requirement: El runner no recibe ni propaga credenciales de administración
`scripts/test.ps1` DEBE (MUST) ejecutar las pruebas y las migraciones de pruebas en el servicio `api`, que no recibe credenciales de administración de desarrollo, y NO DEBE (MUST NOT) pasar `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB` ni `PGPASSWORD` con `-e`.

#### Scenario: Sin variables de administración en las opciones del runner
- **CUANDO** se inspecciona el texto de `scripts/test.ps1`
- **ENTONCES** ninguna invocación pasa `-e` con `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB` ni `PGPASSWORD`

#### Scenario: Suite completa sin credenciales de administración
- **DADO** el servicio `api` con su lista de variables permitidas
- **CUANDO** se ejecuta `scripts/test.ps1`
- **ENTONCES** todas las suites pasan y el comando termina con código 0

### Requirement: Verificación previa del entorno de PowerShell
Antes del primer paso, `scripts/test.ps1` DEBE (MUST) negarse a empezar, con código distinto de cero y un mensaje que nombre solo las variables, si el proceso de PowerShell define `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD` o `PGPASSWORD`.

#### Scenario: Variable de administración en el proceso de PowerShell
- **DADO** el proceso de PowerShell con `DATABASE_MIGRATION_URL` definida con un valor ficticio
- **CUANDO** se ejecuta la verificación previa del runner
- **ENTONCES** falla con un mensaje que nombra `DATABASE_MIGRATION_URL`, no contiene el valor y no se ejecuta ningún paso

### Requirement: URL de la base de pruebas solo en contenedores efímeros
`scripts/test.ps1` DEBE (MUST) generar en cada ejecución una contraseña aleatoria del superusuario de `db-test`, armar `TEST_DATABASE_URL` en su proceso con host `db-test` y una base terminada en `_test`, y pasarla por nombre solo a los contenedores efímeros de las migraciones de pruebas, integración y aislamiento, sin literal ni salida, retirándola al terminar.

#### Scenario: Sin literal y solo por nombre
- **CUANDO** se inspecciona el texto de `scripts/test.ps1` y de `docker-compose.yml`
- **ENTONCES** ninguno contiene una contraseña de `db-test`, `TEST_DATABASE_URL` se pasa solo con `-e TEST_DATABASE_URL` en esos tres pasos y se retira en el bloque final

#### Scenario: La URL apunta solo a db-test
- **CUANDO** el runner arma `TEST_DATABASE_URL`
- **ENTONCES** su host es `db-test`, su base termina en `_test` y la guardia de base de pruebas la acepta solo si no coincide con la de desarrollo

#### Scenario: db-test sin su contraseña efímera no arranca
- **DADO** un proyecto de Compose aislado con `db-test` sin la contraseña efímera de su superusuario
- **CUANDO** se levanta `db-test` esperando su estado saludable
- **ENTONCES** el arranque falla

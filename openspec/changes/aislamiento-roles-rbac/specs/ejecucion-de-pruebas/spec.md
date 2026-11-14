# Spec Delta: ejecucion-de-pruebas

## MODIFIED Requirements

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

## ADDED Requirements

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

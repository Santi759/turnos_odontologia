# ejecucion-de-pruebas Specification

## Purpose
Ofrecer un único comando local que ejecuta todas las suites de pruebas del proyecto de forma reproducible, conserva la regresión de las pruebas existentes y falla de inmediato ante cualquier suite fallida, como evidencia para Verify y Archive (O2).

## Requirements

### Requirement: Comando único de pruebas
El repositorio DEBE (MUST) ofrecer `scripts/test.ps1` que, desde la raíz en Windows, ejecute en orden: autoprueba del propio runner, pruebas unitarias del backend, migraciones sobre la base de pruebas, pruebas de integración del backend contra PostgreSQL real (base de pruebas efímera `db-test`, nunca la de desarrollo), verificación de tipos y pruebas del frontend. Si todas pasan, DEBE (MUST) terminar con código 0.

#### Scenario: Todas las suites pasan
- **DADO** que existe `.env` copiado de `.env.example` y Docker Desktop está en ejecución
- **CUANDO** se ejecuta `powershell -ExecutionPolicy Bypass -File scripts/test.ps1`
- **ENTONCES** se ejecutan los pasos en el orden del requisito
- **Y** el comando termina con código 0

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

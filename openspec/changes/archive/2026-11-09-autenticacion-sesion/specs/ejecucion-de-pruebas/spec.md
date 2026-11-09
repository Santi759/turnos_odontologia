# Spec Delta: ejecucion-de-pruebas

## ADDED Requirements

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

# Spec Delta: ejecucion-de-pruebas

## Purpose

Ofrecer un único comando local que ejecuta todas las suites de pruebas del proyecto de forma reproducible, conserva la regresión de las pruebas existentes y falla de inmediato ante cualquier suite fallida, como evidencia para Verify y Archive (O2).

## ADDED Requirements

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

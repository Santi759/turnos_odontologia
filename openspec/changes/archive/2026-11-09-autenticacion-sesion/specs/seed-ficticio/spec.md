# Spec Delta: seed-ficticio

## MODIFIED Requirements

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

## ADDED Requirements

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

# repositorios-acotados Specification

## Purpose
Garantizar que todo acceso a datos de un consultorio pase por repositorios que aplican el consultorio de un contexto confiable del servidor en cada lectura y escritura, para que un consultorio nunca lea ni modifique datos de otro (RN-MT-01, RN-MT-02, RN-MT-05).

Convenciones de los escenarios: las pruebas de comportamiento de los repositorios se ejecutan contra PostgreSQL 18 real en `db-test` (X2), con dos consultorios ficticios A y B y datos ficticios (D1); cada prueba deshace sus cambios. Los repositorios son una capa obligatoria de defensa en profundidad, pero **no reemplazan** la autorización por rol ni la barrera en la base de datos (RLS), que corresponden a C-04 (RN-MT-06).

## Requirements

### Requirement: Contexto de consultorio confiable
Los repositorios acotados DEBEN (MUST) recibir el consultorio exclusivamente mediante un contexto de consultorio tipado, construido en el servidor, que contiene un identificador UUID. Un contexto con un identificador que no sea UUID DEBE (MUST) rechazarse, y un repositorio NO DEBE (MUST NOT) aceptar un identificador suelto en lugar del contexto.

#### Scenario: Contexto con identificador válido
- **CUANDO** se construye un contexto de consultorio con un UUID
- **ENTONCES** el contexto expone ese identificador y no puede modificarse después de creado

#### Scenario: Contexto con identificador no UUID rechazado
- **CUANDO** se intenta construir un contexto de consultorio con el texto `"1"` o con un entero
- **ENTONCES** la construcción falla con un error de tipo

#### Scenario: Repositorio sin contexto rechazado
- **CUANDO** se intenta crear un repositorio acotado pasando un UUID suelto en lugar de un contexto de consultorio
- **ENTONCES** la creación falla con un error de tipo

### Requirement: Los esquemas de entrada nunca transportan el consultorio
Ningún esquema de entrada de la aplicación DEBE (MUST) declarar un campo `consultorio_id`; el consultorio se deriva siempre de la identidad (RN-MT-02, D5). Los datos para crear un usuario NO DEBEN (MUST NOT) admitir `consultorio_id`.

#### Scenario: Ningún esquema de entrada declara consultorio_id
- **CUANDO** se recorren todos los esquemas de entrada de la aplicación derivados de la base común
- **ENTONCES** ninguno declara un campo llamado `consultorio_id`

#### Scenario: Datos de alta de usuario sin consultorio_id
- **CUANDO** se intenta construir los datos de alta de un usuario indicando `consultorio_id`
- **ENTONCES** la construcción falla con un error de tipo

### Requirement: Lecturas acotadas al consultorio del contexto
Toda lectura de usuarios DEBE (MUST) devolver solo filas del consultorio del contexto. Buscar por identificador o por email un usuario de otro consultorio DEBE (MUST) responder igual que un usuario inexistente (sin resultado), sin revelar que existe (RN-MT-05).

#### Scenario: Listado solo del consultorio propio
- **DADO** tres usuarios en el consultorio A y tres en el B
- **CUANDO** el repositorio con contexto A lista los usuarios
- **ENTONCES** devuelve exactamente los tres usuarios de A

#### Scenario: Obtener por id un usuario de otro consultorio
- **DADO** un usuario del consultorio B
- **CUANDO** el repositorio con contexto A lo obtiene por su `id`
- **ENTONCES** no devuelve resultado
- **Y** la respuesta es idéntica a la de obtener un `id` inexistente

#### Scenario: Obtener por id un usuario propio
- **DADO** un usuario del consultorio A
- **CUANDO** el repositorio con contexto A lo obtiene por su `id`
- **ENTONCES** devuelve ese usuario

#### Scenario: Buscar por email dentro del consultorio
- **DADO** el email `persona.ficticia@example.test` registrado en A y en B como cuentas separadas
- **CUANDO** el repositorio con contexto A busca `Persona.Ficticia@Example.TEST`
- **ENTONCES** devuelve solo el usuario de A

#### Scenario: Buscar por email de otro consultorio
- **DADO** el email `solo.b@example.test` registrado solo en B
- **CUANDO** el repositorio con contexto A lo busca
- **ENTONCES** no devuelve resultado

#### Scenario: Toda consulta generada incluye el filtro por consultorio
- **CUANDO** se genera el SQL de las consultas de lectura del repositorio con un contexto
- **ENTONCES** cada consulta contiene la condición sobre `consultorio_id` con el identificador del contexto

### Requirement: Escrituras acotadas al consultorio del contexto
Crear un usuario DEBE (MUST) asignarle el consultorio del contexto y normalizar su email. Una modificación dirigida a un usuario de otro consultorio NO DEBE (MUST NOT) afectarlo y DEBE (MUST) informarse igual que si no existiera. Los repositorios NO DEBEN (MUST NOT) asignar credenciales.

#### Scenario: Alta con el consultorio del contexto
- **CUANDO** el repositorio con contexto A crea un usuario con email ` Nueva.Persona@Example.test `, nombre y rol `secretaria`
- **ENTONCES** el usuario queda con `consultorio_id` de A, email `nueva.persona@example.test`, `credencial` nula, `activo = true` e `id` UUID versión 7

#### Scenario: Alta con email repetido en el consultorio, sin distinguir mayúsculas
- **DADO** un usuario con `persona.ficticia@example.test` en A
- **CUANDO** el repositorio con contexto A crea otro usuario con `PERSONA.FICTICIA@example.test`
- **ENTONCES** el alta falla por violación de unicidad y no se crea el usuario

#### Scenario: Desactivar un usuario de otro consultorio
- **DADO** un usuario activo del consultorio B
- **CUANDO** el repositorio con contexto A intenta desactivarlo por su `id`
- **ENTONCES** informa que no encontró el usuario
- **Y** el usuario de B sigue activo

#### Scenario: Desactivar un usuario propio
- **DADO** un usuario activo del consultorio A
- **CUANDO** el repositorio con contexto A lo desactiva por su `id`
- **ENTONCES** informa que lo desactivó y el usuario queda con `activo = false`

### Requirement: Consultorio actual únicamente
El repositorio de consultorios DEBE (MUST) permitir obtener solo el consultorio del contexto y NO DEBE (MUST NOT) ofrecer operaciones para listar, crear ni consultar otros consultorios (PA-05 = solo seed).

#### Scenario: Obtener el consultorio actual
- **DADO** los consultorios A y B
- **CUANDO** el repositorio de consultorios con contexto A obtiene el consultorio actual
- **ENTONCES** devuelve A con su nombre, zona horaria y anticipación de cancelación

#### Scenario: Contexto de un consultorio inexistente
- **CUANDO** el repositorio de consultorios con un contexto cuyo UUID no existe obtiene el consultorio actual
- **ENTONCES** no devuelve resultado

#### Scenario: Sin operaciones sobre otros consultorios
- **CUANDO** se inspeccionan las operaciones públicas del repositorio de consultorios
- **ENTONCES** la única operación de lectura es la del consultorio actual y no hay operaciones de alta ni de listado

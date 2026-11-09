# Spec Delta: repositorios-acotados

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Contexto construido solo a partir de la sesión
Desde C-03, en tiempo de ejecución de la API el contexto de consultorio DEBE (MUST) construirse únicamente en la dependencia de identidad, a partir de una sesión validada (capacidad `autenticacion-sesion`); ningún código de rutas, servicios ni esquemas DEBE (MUST) construirlo con datos de la petición. Fuera de la API solo lo construyen las pruebas.

#### Scenario: Un único punto de construcción en la aplicación
- **CUANDO** se buscan en el código de la aplicación (excluidas las pruebas) las construcciones de `ContextoConsultorio`
- **ENTONCES** la única está en el módulo de la dependencia de identidad y usa el `consultorio_id` de la sesión validada

#### Scenario: Contexto de la sesión en una ruta protegida
- **DADO** una sesión válida de un usuario del consultorio A
- **CUANDO** una ruta protegida de prueba crea un repositorio de usuarios con el contexto inyectado y lista los usuarios
- **ENTONCES** devuelve solo usuarios de A

# Spec Delta: repositorios-acotados

## MODIFIED Requirements

### Requirement: Contexto construido solo a partir de la sesión
Desde C-03, en tiempo de ejecución de la API el contexto de consultorio DEBE (MUST) construirse únicamente en la dependencia de identidad, a partir de una sesión validada (capacidad `autenticacion-sesion`); ningún código de rutas, servicios ni esquemas DEBE (MUST) construirlo con datos de la petición. Fuera de la API solo lo construyen las pruebas. Desde C-04, el contexto de la base solo DEBE (MUST) fijarse desde esa dependencia o, en el login, desde la cuenta verificada.

#### Scenario: Un único punto de construcción en la aplicación
- **CUANDO** se buscan en el código de la aplicación (excluidas las pruebas) las construcciones de `ContextoConsultorio`
- **ENTONCES** la única está en el módulo de la dependencia de identidad y usa el `consultorio_id` de la sesión validada

#### Scenario: Contexto de la sesión en una ruta protegida
- **DADO** una sesión válida de un usuario del consultorio A
- **CUANDO** una ruta protegida de prueba crea un repositorio de usuarios con el contexto inyectado y lista los usuarios
- **ENTONCES** devuelve solo usuarios de A

#### Scenario: Puntos de fijación del contexto de la base
- **CUANDO** se buscan en el código de la aplicación (excluidas las pruebas) las llamadas que fijan el contexto de la base
- **ENTONCES** solo están en la dependencia de identidad y en el login tras verificar la contraseña

#### Scenario: Repositorio con el rol de aplicación y un filtro omitido
- **DADO** una sesión de A con el rol de aplicación y una consulta de prueba de usuarios sin condición sobre el consultorio
- **CUANDO** se ejecuta en una petición de A
- **ENTONCES** devuelve solo usuarios de A

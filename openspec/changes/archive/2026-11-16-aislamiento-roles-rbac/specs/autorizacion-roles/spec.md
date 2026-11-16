# Spec Delta: autorizacion-roles

## Purpose

Verificar en el servidor el rol del usuario autenticado en cada operación protegida, con un mecanismo único y reutilizable, y responder de forma que un consultorio no pueda descubrir recursos de otro (US-002, RN-AU-03, RN-MT-05).

Convenciones de los escenarios: datos ficticios únicamente (D1). Consultorios ficticios A y B; un usuario ficticio por rol (`administrador`, `secretaria`, `odontologo`) en A. Las rutas `/prueba/...` existen solo en la aplicación de pruebas. "Cuerpo de acceso denegado" es exactamente `{"detail": "Acceso denegado."}` y "cuerpo de no encontrado" es exactamente `{"detail": "No encontrado."}`. C-04 no aprueba la matriz de permisos de `03_actores_y_roles.md`: cada Change posterior confirma las celdas que usa.

## ADDED Requirements

### Requirement: Rol tipado en la identidad autenticada
La identidad autenticada DEBE (MUST) exponer el rol como uno de los valores admitidos `administrador`, `secretaria` u `odontologo`, con un tipo cerrado. Si la sesión resuelve un rol fuera de esos valores, la identidad NO DEBE (MUST NOT) resolverse y la petición DEBE (MUST) responder 401 con el cuerpo de no autenticado. Las respuestas de identidad DEBEN (MUST) seguir mostrando el rol como texto.

#### Scenario: Rol tipado desde la sesión
- **DADO** una sesión válida del usuario `secretaria` de A
- **CUANDO** una ruta protegida de prueba devuelve la identidad resuelta
- **ENTONCES** el rol es el valor tipado `secretaria`

#### Scenario: Respuesta de identidad sin cambios
- **DADO** una sesión válida del usuario `odontologo` de A
- **CUANDO** se hace `GET /api/auth/me`
- **ENTONCES** la respuesta es 200 y el rol del cuerpo es el texto `odontologo`

#### Scenario: Rol desconocido no autentica
- **DADO** una sesión cuya resolución devuelve el rol `auditor`
- **CUANDO** se hace `GET /api/auth/me`
- **ENTONCES** la respuesta es 401 con el cuerpo de no autenticado

### Requirement: Autorización por rol reutilizable
Toda operación protegida que restrinja roles DEBE (MUST) declararlos con un único mecanismo reutilizable del servidor que recibe uno o más roles tipados. Un rol no admitido DEBE (MUST) recibir 403 con el cuerpo de acceso denegado y `Cache-Control: no-store`. Declarar el mecanismo sin roles o con valores no tipados DEBE (MUST) fallar al construir la aplicación.

#### Scenario: Ruta solo para administrador
- **DADO** una ruta de prueba restringida a `administrador`
- **CUANDO** la invocan con sesión válida el administrador, la secretaria y el odontólogo de A
- **ENTONCES** el administrador recibe 200 y los otros dos reciben 403 con el cuerpo de acceso denegado

#### Scenario: Ruta para varios roles
- **DADO** una ruta de prueba restringida a `administrador` y `secretaria`
- **CUANDO** la invocan con sesión válida los tres usuarios de A
- **ENTONCES** el administrador y la secretaria reciben 200 y el odontólogo recibe 403

#### Scenario: Declaración inválida rechazada
- **CUANDO** se declara el mecanismo sin roles o con el texto `"administrador"` en lugar del rol tipado
- **ENTONCES** la declaración falla con un error antes de atender peticiones

### Requirement: Rechazo por rol sin consultar el recurso
El rechazo por rol DEBE (MUST) decidirse solo con la identidad autenticada, antes de cualquier consulta sobre el recurso pedido. La respuesta 403 DEBE (MUST) ser idéntica si el recurso existe, si es de otro consultorio o si no existe.

#### Scenario: 403 idéntico sin consultar la base
- **DADO** una ruta de prueba restringida a `administrador` que obtiene un usuario por su `id`
- **CUANDO** la secretaria de A la invoca con el `id` de un usuario de A, con el de un usuario de B y con un UUID inexistente
- **ENTONCES** las tres respuestas son 403 con el mismo cuerpo y las mismas cabeceras
- **Y** no se ejecutó ninguna consulta sobre `usuario` durante esas peticiones

### Requirement: Orden de las respuestas de autorización
En una operación protegida, la falta de identidad válida DEBE (MUST) responder 401 antes de evaluar el rol, y el rechazo por rol DEBE (MUST) producirse antes de buscar el recurso. En operaciones que cambian estado, el orden DEBE (MUST) ser `Origin` (403), identidad (401), token CSRF (403) y rol (403).

#### Scenario: Sin sesión en una ruta restringida
- **CUANDO** se invoca sin cookie una ruta de prueba restringida a `administrador`
- **ENTONCES** la respuesta es 401 con el cuerpo de no autenticado

#### Scenario: Token CSRF antes que el rol
- **DADO** una ruta de prueba que cambia estado restringida a `administrador`
- **CUANDO** la secretaria de A la invoca con `Origin` permitido y sin token CSRF
- **ENTONCES** la respuesta es 403 con el cuerpo `{"detail": "Solicitud rechazada."}`

### Requirement: Recurso ajeno indistinguible de inexistente
Pedir un recurso de otro consultorio DEBE (MUST) responder 404 con el cuerpo de no encontrado, con el mismo estado, cuerpo y cabeceras que pedir un identificador inexistente (RN-MT-05).

#### Scenario: Usuario de otro consultorio
- **DADO** una ruta de prueba que obtiene un usuario por su `id`, sin restricción de rol
- **CUANDO** la secretaria de A la invoca con el `id` de un usuario de B y con un UUID inexistente
- **ENTONCES** ambas respuestas son 404 con el cuerpo de no encontrado
- **Y** sus cabeceras son idénticas

#### Scenario: Usuario propio
- **CUANDO** la secretaria de A invoca la misma ruta con el `id` de un usuario de A
- **ENTONCES** la respuesta es 200 con los datos de ese usuario

### Requirement: Sesión propia accesible para todos los roles
`GET /api/auth/me` y `POST /api/auth/logout` DEBEN (MUST) estar disponibles para los tres roles, sin restricción de rol, porque solo operan sobre la sesión propia.

#### Scenario: Identidad para cada rol
- **CUANDO** el administrador, la secretaria y el odontólogo de A hacen `GET /api/auth/me` con sesión válida
- **ENTONCES** cada uno recibe 200 con su propio rol

#### Scenario: Cierre de sesión para cada rol
- **CUANDO** cada uno de los tres hace `POST /api/auth/logout` con `Origin` permitido y su token CSRF
- **ENTONCES** cada uno recibe 204 y solo su sesión queda revocada

### Requirement: Decisiones de rol centralizadas
Las comparaciones de rol del código de la aplicación DEBEN (MUST) estar solo en el módulo del mecanismo de autorización; ninguna ruta, servicio ni repositorio DEBE (MUST) comparar el rol por su cuenta.

#### Scenario: Sin comparaciones de rol dispersas
- **CUANDO** se buscan en el código de la aplicación (excluidas las pruebas) comparaciones con el rol de la identidad o con valores de rol
- **ENTONCES** solo aparecen en el módulo del mecanismo de autorización y en la definición del tipo de rol

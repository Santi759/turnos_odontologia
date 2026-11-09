# Spec Delta: proteccion-csrf

## Purpose
Impedir que otro sitio haga que el navegador de un usuario autenticado cambie estado en la API, mediante validación estricta de `Origin` y un token CSRF ligado a la sesión, sin excepciones para pruebas ni clientes sin navegador (DA-11).

Convenciones de los escenarios: las mismas de `autenticacion-sesion` (el login lleva `Content-Type: application/json` salvo que el escenario diga lo contrario). Orígenes permitidos: exactamente los de `CORS_ALLOWED_ORIGINS` (`http://localhost:5173` en los escenarios); origen ajeno de ejemplo `http://otro-origen.invalid`. "Cuerpo de solicitud rechazada" es exactamente `{"detail": "Solicitud rechazada."}`. "Método que cambia estado" es todo método distinto de `GET`, `HEAD` y `OPTIONS`.

## ADDED Requirements

### Requirement: Origin obligatorio y permitido en métodos que cambian estado
Toda petición con un método que cambia estado, incluido el login, DEBE (MUST) traer una cabecera `Origin` igual, carácter por carácter, a uno de los orígenes de `CORS_ALLOWED_ORIGINS`. Si falta, es `null` o no está permitido, DEBE (MUST) responder 403 con el cuerpo de solicitud rechazada sin ejecutar la operación.

#### Scenario: Login sin Origin
- **CUANDO** se hace `POST /api/auth/login` con credenciales correctas y sin cabecera `Origin`
- **ENTONCES** la respuesta es 403 con el cuerpo de solicitud rechazada
- **Y** no se crea sesión ni se registra un fallo

#### Scenario: Login desde un origen ajeno
- **CUANDO** se hace el login con credenciales correctas y `Origin: http://otro-origen.invalid`
- **ENTONCES** la respuesta es 403 con el cuerpo de solicitud rechazada

#### Scenario: Origin null
- **CUANDO** se hace el login con `Origin: null`
- **ENTONCES** la respuesta es 403 con el cuerpo de solicitud rechazada

#### Scenario: Referer no reemplaza a Origin
- **CUANDO** se hace el login sin `Origin` y con `Referer: http://localhost:5173/login`
- **ENTONCES** la respuesta es 403 con el cuerpo de solicitud rechazada

#### Scenario: Origen con diferencias mínimas
- **CUANDO** se hace el login con `Origin: http://localhost:5173/` o `Origin: http://LOCALHOST:5173`
- **ENTONCES** la respuesta es 403 con el cuerpo de solicitud rechazada

#### Scenario: Formulario de otro sitio
- **CUANDO** se hace el login con `Origin: http://otro-origen.invalid`, `Content-Type: application/x-www-form-urlencoded` y credenciales correctas en el cuerpo
- **ENTONCES** la respuesta es 403 con el cuerpo de solicitud rechazada
- **Y** no se crea sesión ni se registra un fallo

#### Scenario: Logout sin Origin
- **DADO** una sesión válida y su token CSRF
- **CUANDO** se hace `POST /api/auth/logout` con la cookie y `X-CSRF-Token` pero sin `Origin`
- **ENTONCES** la respuesta es 403 con el cuerpo de solicitud rechazada
- **Y** la sesión sigue siendo válida

### Requirement: Token CSRF en peticiones autenticadas que cambian estado
Toda petición autenticada con un método que cambia estado DEBE (MUST) traer, además de un `Origin` permitido, la cabecera `X-CSRF-Token` con el token de su propia sesión, comparado en tiempo constante. Si falta o no corresponde, DEBE (MUST) responder 403 con el cuerpo de solicitud rechazada sin ejecutar la operación.

#### Scenario: Logout sin token CSRF
- **DADO** una sesión válida
- **CUANDO** se hace `POST /api/auth/logout` con la cookie y `Origin` permitido pero sin `X-CSRF-Token`
- **ENTONCES** la respuesta es 403 con el cuerpo de solicitud rechazada
- **Y** la sesión sigue siendo válida

#### Scenario: Token CSRF de otra sesión
- **DADO** dos sesiones válidas `S1` y `S2`
- **CUANDO** se hace logout con la cookie de `S1` y el token CSRF de `S2`
- **ENTONCES** la respuesta es 403 y ambas sesiones siguen siendo válidas

#### Scenario: Token CSRF alterado
- **CUANDO** se hace logout con la cookie válida y un token CSRF con un carácter cambiado
- **ENTONCES** la respuesta es 403 y la sesión sigue siendo válida

#### Scenario: Logout con token válido y origen ajeno
- **CUANDO** se hace logout con la cookie válida, su token CSRF y `Origin: http://otro-origen.invalid`
- **ENTONCES** la respuesta es 403 y la sesión sigue siendo válida

### Requirement: Entrega del token CSRF
Las respuestas 200 de `POST /api/auth/login` y `GET /api/auth/me` DEBEN (MUST) incluir la cabecera `X-CSRF-Token` con el token de la sesión, expuesta por CORS. El token DEBE (MUST) derivarse con `AUTH_SECRET_KEY` de la sesión, ser distinto del token de sesión, no aparecer en el cuerpo JSON y dejar de servir cuando la sesión se revoca o vence.

#### Scenario: Token en la cabecera del login y de /me
- **CUANDO** el login es exitoso y luego se hace `GET /api/auth/me` con la cookie
- **ENTONCES** ambas respuestas traen la misma cabecera `X-CSRF-Token` no vacía
- **Y** su valor es distinto del de la cookie `turnos_session` y no figura en ningún cuerpo

#### Scenario: Token legible desde un origen permitido
- **DADO** una sesión válida
- **CUANDO** se hace `GET /api/auth/me` con la cookie y `Origin: http://localhost:5173`
- **ENTONCES** la respuesta 200 trae `X-CSRF-Token`, `Access-Control-Allow-Origin: http://localhost:5173` y `Access-Control-Allow-Credentials: true`
- **Y** `Access-Control-Expose-Headers` contiene `X-CSRF-Token`

#### Scenario: Token distinto por sesión
- **CUANDO** se hacen dos logins exitosos del mismo usuario
- **ENTONCES** los tokens CSRF de ambas sesiones son distintos

#### Scenario: Token de una sesión revocada
- **DADO** el token CSRF de una sesión revocada y una cookie de otra sesión válida
- **CUANDO** se hace logout con la cookie válida y ese token
- **ENTONCES** la respuesta es 403

### Requirement: Métodos seguros sin token CSRF
Las peticiones `GET`, `HEAD` y `OPTIONS` NO DEBEN (MUST NOT) requerir `Origin` ni token CSRF y NO DEBEN (MUST NOT) cambiar datos de negocio; solo pueden renovar el último uso de la sesión.

#### Scenario: /me sin Origin ni token
- **DADO** una sesión válida
- **CUANDO** se hace `GET /api/auth/me` con la cookie, sin `Origin` ni `X-CSRF-Token`
- **ENTONCES** la respuesta es 200

### Requirement: Toda ruta que cambia estado está protegida
Toda ruta registrada con un método que cambia estado DEBE (MUST) aplicar la validación de `Origin`, y las que requieren sesión DEBEN (MUST) aplicar también la del token CSRF. NO DEBE (MUST NOT) existir configuración, variable de entorno, modo de pruebas ni excepción para clientes como `curl` que desactive estas validaciones.

#### Scenario: Recorrido de rutas que cambian estado
- **CUANDO** se recorren todas las rutas registradas con métodos que cambian estado
- **ENTONCES** cada una responde 403 con el cuerpo de solicitud rechazada si se invoca sin `Origin`
- **Y** cada una que requiere sesión responde 403 si se invoca con una sesión válida y `Origin` permitido pero sin `X-CSRF-Token`

#### Scenario: Sin interruptor de desactivación
- **CUANDO** se inspeccionan los campos de la configuración de la aplicación
- **ENTONCES** ninguno permite desactivar la validación de `Origin` ni la del token CSRF

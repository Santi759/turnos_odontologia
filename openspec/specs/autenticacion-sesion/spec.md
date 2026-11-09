# autenticacion-sesion Specification

## Purpose
Autenticar a los usuarios de un consultorio con código de consultorio, email y contraseña, mantener su sesión del lado del servidor con vencimiento y cierre real, y derivar la identidad, el rol y el consultorio de cada petición exclusivamente de esa sesión (US-001, RN-AU-01, RN-AU-02, RN-AU-04, RN-AU-06, RN-MT-02).

Convenciones de los escenarios: datos ficticios únicamente (D1). Consultorios ficticios A (código `ficticio-a`, nombre "Consultorio Ficticio A") y B (código `ficticio-b`); usuario `persona.ficticia@example.test` con rol `secretaria` y contraseña `contrasena-ficticia-a1` en A. Origen permitido `http://localhost:5173`. Toda petición `POST` de los escenarios lleva `Origin: http://localhost:5173` y, en el login, `Content-Type: application/json`, salvo que el escenario diga lo contrario. Las pruebas usan `APP_ENV=test` salvo indicación expresa. Las pruebas con base se ejecutan contra PostgreSQL real en `db-test` (X2); el reloj de la aplicación es inyectable en las pruebas. La dirección del cliente se inyecta siempre de forma explícita con direcciones de documentación (`203.0.113.0/24`, `2001:db8::/32`; por defecto `203.0.113.7`), porque el host por defecto de `TestClient` (`testclient`) no es una dirección IP (ver `control-intentos-login`). "Cuerpo de rechazo de login" es exactamente `{"detail": "No se pudo iniciar sesión."}` y "cuerpo de no autenticado" es exactamente `{"detail": "No autenticado."}`.

## Requirements

### Requirement: Inicio de sesión con código de consultorio, email y contraseña
`POST /api/auth/login` DEBE (MUST) recibir un cuerpo JSON con `codigo_consultorio`, `email` y `contrasena`, normalizar el código y el email (sin espacios en los extremos y en minúsculas), normalizar la contraseña solo con NFKC (la misma normalización que al establecerla) y, si las credenciales son válidas y el usuario y su consultorio están activos, responder 200, crear una sesión nueva y emitir la cookie de sesión.

#### Scenario: Inicio de sesión exitoso
- **DADO** el usuario `persona.ficticia@example.test` de A, activo, con su credencial establecida
- **CUANDO** se hace `POST /api/auth/login` con `{"codigo_consultorio": "ficticio-a", "email": "persona.ficticia@example.test", "contrasena": "contrasena-ficticia-a1"}`
- **ENTONCES** la respuesta tiene estado 200
- **Y** incluye una cabecera `Set-Cookie` para `turnos_session`
- **Y** existe exactamente una sesión nueva, no revocada, de ese usuario en A

#### Scenario: Código y email se normalizan
- **DADO** el mismo usuario de A
- **CUANDO** el login envía `codigo_consultorio` `" FICTICIO-A "` y email `" Persona.Ficticia@Example.TEST "` con la contraseña correcta
- **ENTONCES** la respuesta tiene estado 200

#### Scenario: La contraseña no se normaliza
- **CUANDO** el login envía la contraseña correcta en mayúsculas o con un espacio final
- **ENTONCES** la respuesta tiene estado 401 con el cuerpo de rechazo de login

#### Scenario: NFKC al verificar
- **DADO** un usuario de A cuya credencial se estableció con `contraseña-de-prueba-ñ1` escrita con `ñ` compuesta (U+00F1)
- **CUANDO** el login envía esa contraseña con `ñ` descompuesta (`n` + U+0303)
- **ENTONCES** la respuesta tiene estado 200

#### Scenario: El login no aplica la política de contraseñas nuevas
- **DADO** un usuario de A cuya credencial válida corresponde a una contraseña de 12 caracteres establecida antes de la política
- **CUANDO** el login envía esa contraseña
- **ENTONCES** la respuesta tiene estado 200
- **Y** un login con una contraseña incorrecta de 3 caracteres responde 401 con el mismo cuerpo de rechazo de login que una incorrecta de 20

### Requirement: Respuesta de identidad mínima
Las respuestas exitosas de `POST /api/auth/login` y `GET /api/auth/me` DEBEN (MUST) tener exactamente el cuerpo `{"usuario": {"nombre", "email", "rol"}, "consultorio": {"nombre"}}`. NO DEBEN (MUST NOT) incluir el hash, el token de sesión, identificadores internos, secretos ni datos de otros consultorios (DA-13).

#### Scenario: Cuerpo del login exitoso
- **CUANDO** el login de `persona.ficticia@example.test` en A es exitoso
- **ENTONCES** el cuerpo es exactamente `{"usuario": {"nombre": "<nombre del usuario>", "email": "persona.ficticia@example.test", "rol": "secretaria"}, "consultorio": {"nombre": "Consultorio Ficticio A"}}`
- **Y** el cuerpo no contiene el valor de la cookie `turnos_session`, el texto `$argon2`, ni ningún `id` de usuario, consultorio o sesión

#### Scenario: Cuerpo de /me
- **DADO** una sesión válida de `persona.ficticia@example.test` en A
- **CUANDO** se hace `GET /api/auth/me` con esa cookie
- **ENTONCES** la respuesta tiene estado 200 y el mismo cuerpo que el login exitoso

### Requirement: Rechazo genérico del inicio de sesión
Todo login con credenciales que no autentican DEBE (MUST) responder 401 con el cuerpo de rechazo de login, idéntico en todos los casos, sin emitir cookie de sesión ni crear sesión, sin revelar cuál dato falló (US-001, DA-09).

#### Scenario: Contraseña incorrecta
- **CUANDO** el login de `persona.ficticia@example.test` en A envía `otra-contrasena-ficticia`
- **ENTONCES** la respuesta es 401 con el cuerpo de rechazo de login y sin `Set-Cookie` de `turnos_session`

#### Scenario: Email inexistente en el consultorio
- **CUANDO** el login envía `nadie@example.test` en A
- **ENTONCES** la respuesta es 401 con el mismo cuerpo de rechazo de login

#### Scenario: Código de consultorio inexistente
- **CUANDO** el login envía el código `no-existe` con un email y una contraseña cualesquiera
- **ENTONCES** la respuesta es 401 con el mismo cuerpo de rechazo de login

#### Scenario: Usuario inactivo con contraseña correcta
- **DADO** el usuario de A con `activo = false`
- **CUANDO** el login envía su contraseña correcta
- **ENTONCES** la respuesta es 401 con el mismo cuerpo de rechazo de login

#### Scenario: Consultorio inactivo con contraseña correcta
- **DADO** el consultorio A con `activo = false`
- **CUANDO** su usuario activo envía la contraseña correcta
- **ENTONCES** la respuesta es 401 con el mismo cuerpo de rechazo de login

#### Scenario: Usuario sin credencial
- **DADO** un usuario de A con `credencial` nula
- **CUANDO** el login envía cualquier contraseña, incluida la cadena `"null"`
- **ENTONCES** la respuesta es 401 con el mismo cuerpo de rechazo de login

#### Scenario: Credencial con formato no admitido
- **DADO** un usuario de A cuya `credencial` es `$argon2i$v=19$m=65536,t=3,p=4$...` o un texto que no es un hash
- **CUANDO** el login envía cualquier contraseña
- **ENTONCES** la respuesta es 401 con el mismo cuerpo de rechazo de login

#### Scenario: Verificación de contraseña en todos los casos evaluados
- **CUANDO** se evalúa un login con email inexistente, con usuario sin credencial o con usuario inactivo
- **ENTONCES** el verificador de contraseñas se ejecuta exactamente una vez, contra la credencial real o contra un hash ficticio con los mismos parámetros

### Requirement: Cuerpo de login estricto
El cuerpo del login DEBE (MUST) derivar de la base común de esquemas de entrada: un campo no declarado, como `consultorio_id`, un campo faltante o una contraseña de más de 128 puntos de código, medidos sobre la entrada sin normalizar, DEBEN (MUST) responder 422 sin evaluar credenciales, crear sesión ni registrar un fallo.

#### Scenario: consultorio_id en el cuerpo rechazado
- **CUANDO** el login envía las credenciales correctas de A más `"consultorio_id": "<id de B>"`
- **ENTONCES** la respuesta es 422 y el error identifica `consultorio_id`
- **Y** no se crea ninguna sesión ni se registra un intento fallido

#### Scenario: Campo faltante
- **CUANDO** el login omite `codigo_consultorio`
- **ENTONCES** la respuesta es 422 y no se crea ninguna sesión

#### Scenario: Contraseña demasiado larga
- **CUANDO** el login envía una contraseña de 129 caracteres
- **ENTONCES** la respuesta es 422 y el verificador de contraseñas no se ejecuta

#### Scenario: El máximo se mide sobre la entrada sin normalizar
- **CUANDO** el login envía una contraseña de 128 ligaduras `ﬁ` (U+FB01), que tras NFKC tendría 256 puntos de código
- **ENTONCES** la respuesta es 401 con el cuerpo de rechazo de login (no 422)

### Requirement: Login solo con JSON
El login DEBE (MUST) exigir `Content-Type` con tipo de medio `application/json` (sin distinguir mayúsculas, con a lo sumo el parámetro `charset=utf-8`). Cualquier otro tipo o su ausencia DEBE (MUST) responder 415 con el cuerpo exacto `{"detail": "Tipo de contenido no admitido."}`, después de validar `Origin` y la dirección del cliente y antes de analizar el cuerpo, sin evaluar credenciales, crear sesión ni registrar un fallo.

#### Scenario: Content-Type distinto de JSON
- **CUANDO** el login envía un cuerpo JSON con las credenciales correctas y `Content-Type` `text/plain`, `application/x-www-form-urlencoded` o `multipart/form-data`, o sin `Content-Type`
- **ENTONCES** la respuesta es 415 con el cuerpo de tipo de contenido no admitido
- **Y** no se crea sesión, no se registra un fallo y el verificador de contraseñas no se ejecuta

#### Scenario: JSON con charset admitido
- **CUANDO** el login envía las credenciales correctas con `Content-Type: application/json; charset=utf-8`
- **ENTONCES** la respuesta es 200

### Requirement: Aislamiento de cuentas entre consultorios
La cuenta autenticada DEBE (MUST) ser la del par (código de consultorio, email) enviado; la contraseña de una cuenta de otro consultorio con el mismo email NO DEBE (MUST NOT) autenticar. Una sesión DEBE (MUST) producir siempre el contexto de su propio consultorio.

#### Scenario: Mismo email en A y B con contraseñas distintas
- **DADO** `persona.ficticia@example.test` en A con `contrasena-ficticia-a1` y en B con `contrasena-ficticia-b1`
- **CUANDO** el login envía el código `ficticio-a` con `contrasena-ficticia-b1`
- **ENTONCES** la respuesta es 401 con el cuerpo de rechazo de login
- **Y** con el código `ficticio-b` y `contrasena-ficticia-b1` la respuesta es 200 con el consultorio "Consultorio Ficticio B"

#### Scenario: La sesión de A nunca da contexto de B
- **DADO** una sesión válida de A
- **CUANDO** una ruta protegida de prueba devuelve el `consultorio_id` del contexto resuelto, aunque la petición incluya `consultorio_id` de B en la query y en una cabecera `X-Consultorio-Id`
- **ENTONCES** el contexto es el de A

### Requirement: Cookie de sesión
La sesión DEBE (MUST) transportarse solo en la cookie `turnos_session` con `HttpOnly`, `SameSite=Lax`, `Path=/`, sin `Domain`, `Secure` salvo configuración local explícita, y `Max-Age` igual a `AUTH_SESSION_MAX_HOURS` en segundos. El token DEBE (MUST) ser aleatorio de al menos 256 bits y no aparecer en ningún cuerpo JSON.

#### Scenario: Atributos por defecto
- **DADO** la configuración por defecto (`AUTH_COOKIE_SECURE` sin definir y `AUTH_SESSION_MAX_HOURS = 12`)
- **CUANDO** el login es exitoso
- **ENTONCES** `Set-Cookie` de `turnos_session` incluye `HttpOnly`, `SameSite=Lax`, `Secure`, `Path=/` y `Max-Age=43200`
- **Y** no incluye `Domain`

#### Scenario: Cookie sin Secure solo en local explícito
- **DADO** `APP_ENV=local` y `AUTH_COOKIE_SECURE=false`
- **CUANDO** el login es exitoso
- **ENTONCES** `Set-Cookie` de `turnos_session` no incluye `Secure` y conserva los demás atributos

#### Scenario: Tokens distintos e impredecibles
- **CUANDO** se hacen dos logins exitosos del mismo usuario
- **ENTONCES** los valores de las cookies son distintos y cada uno tiene 43 caracteres del alfabeto base64url

### Requirement: Token de sesión almacenado solo como HMAC
La base DEBE (MUST) guardar de cada sesión solo el HMAC-SHA256 del token calculado con `AUTH_SECRET_KEY`, nunca el token. Una sesión DEBE (MUST) resolverse comparando ese HMAC; cambiar `AUTH_SECRET_KEY` DEBE (MUST) invalidar todas las sesiones existentes.

#### Scenario: El token no está en la base
- **DADO** un login exitoso con token `T`
- **CUANDO** se leen todas las columnas de la sesión creada
- **ENTONCES** ninguna contiene `T` y la columna del HMAC tiene exactamente 32 bytes

#### Scenario: Cambio de clave invalida las sesiones
- **DADO** una sesión creada con una clave ficticia
- **CUANDO** la aplicación se configura con otra `AUTH_SECRET_KEY` y se hace `GET /api/auth/me` con la misma cookie
- **ENTONCES** la respuesta es 401 con el cuerpo de no autenticado

#### Scenario: Cookie con formato inválido
- **CUANDO** se hace `GET /api/auth/me` con `turnos_session` vacía, de 10 caracteres o con caracteres fuera de base64url
- **ENTONCES** la respuesta es 401 con el cuerpo de no autenticado y no se consulta la tabla de sesiones

### Requirement: Contexto de consultorio derivado de la sesión
En cada petición protegida, la identidad DEBE (MUST) resolverse desde la cookie a una sesión no revocada y no vencida de un usuario activo de un consultorio activo, y de ella DEBEN (MUST) salir el usuario, el rol y el `ContextoConsultorio`. Ningún dato del cliente DEBE (MUST) alterar ese contexto.

#### Scenario: Identidad resuelta desde la sesión
- **DADO** una sesión válida de `persona.ficticia@example.test` en A
- **CUANDO** una ruta protegida de prueba devuelve la identidad resuelta
- **ENTONCES** contiene el `id` de ese usuario, el rol `secretaria` y un `ContextoConsultorio` con el `id` de A

#### Scenario: Sin cookie
- **CUANDO** se hace `GET /api/auth/me` sin cookie
- **ENTONCES** la respuesta es 401 con el cuerpo de no autenticado

#### Scenario: Cookie desconocida limpia la cookie
- **CUANDO** se hace `GET /api/auth/me` con un token bien formado que no corresponde a ninguna sesión
- **ENTONCES** la respuesta es 401 con el cuerpo de no autenticado
- **Y** incluye `Set-Cookie` que borra `turnos_session` (`Max-Age=0`, mismos `Path`, `SameSite`, `HttpOnly` y `Secure`)

### Requirement: Vencimiento por inactividad
Una sesión DEBE (MUST) dejar de ser válida cuando transcurren `AUTH_SESSION_MINUTES` minutos desde su último uso registrado. Cada petición autenticada válida DEBE (MUST) renovar el último uso, como máximo una vez por minuto.

#### Scenario: Sesión inactiva vencida
- **DADO** `AUTH_SESSION_MINUTES = 30` y una sesión cuyo último uso fue hace 31 minutos según el reloj de la aplicación
- **CUANDO** se hace `GET /api/auth/me` con esa cookie
- **ENTONCES** la respuesta es 401 con el cuerpo de no autenticado

#### Scenario: La actividad renueva la sesión
- **DADO** una sesión creada en `t0`
- **CUANDO** se hace `GET /api/auth/me` en `t0 + 20 min` y otra vez en `t0 + 45 min`
- **ENTONCES** ambas respuestas son 200

#### Scenario: Renovación acotada a una por minuto
- **DADO** una sesión cuyo último uso fue hace 30 segundos
- **CUANDO** se hace `GET /api/auth/me`
- **ENTONCES** la respuesta es 200 y el último uso registrado no cambia

### Requirement: Vencimiento absoluto
Toda sesión DEBE (MUST) vencer a las `AUTH_SESSION_MAX_HOURS` horas de su creación aunque tenga actividad, y la renovación por actividad NUNCA DEBE (MUST NOT) extenderla más allá de ese instante.

#### Scenario: Sesión activa vencida por tiempo absoluto
- **DADO** `AUTH_SESSION_MAX_HOURS = 12` y una sesión creada en `t0` usada cada 10 minutos
- **CUANDO** se hace `GET /api/auth/me` en `t0 + 12 h`
- **ENTONCES** la respuesta es 401 con el cuerpo de no autenticado

#### Scenario: La renovación no supera el vencimiento absoluto
- **DADO** una sesión creada en `t0` con vencimiento absoluto `t0 + 12 h`
- **CUANDO** se usa en `t0 + 11 h 50 min`
- **ENTONCES** la respuesta es 200, el vencimiento absoluto sigue siendo `t0 + 12 h` y en `t0 + 12 h` la sesión ya no es válida

### Requirement: Cierre de sesión
`POST /api/auth/logout` con una sesión válida, el token CSRF y un `Origin` permitido DEBE (MUST) revocar la sesión al instante, responder 204 y borrar la cookie. Sin sesión válida DEBE (MUST) responder 401 con el cuerpo de no autenticado y borrar la cookie; el efecto es idempotente.

#### Scenario: Logout invalida la sesión
- **DADO** una sesión válida y su token CSRF
- **CUANDO** se hace `POST /api/auth/logout` con la cookie, `X-CSRF-Token` y `Origin` permitido
- **ENTONCES** la respuesta es 204 con `Set-Cookie` que borra `turnos_session`
- **Y** la sesión queda revocada en la base
- **Y** un `GET /api/auth/me` posterior con la cookie anterior responde 401

#### Scenario: Segundo logout con la misma cookie
- **DADO** una sesión ya revocada por logout
- **CUANDO** se repite `POST /api/auth/logout` con la cookie anterior
- **ENTONCES** la respuesta es 401 con el cuerpo de no autenticado y borra la cookie
- **Y** ninguna otra sesión del usuario cambia

#### Scenario: Logout revoca solo su sesión
- **DADO** dos sesiones válidas del mismo usuario
- **CUANDO** se hace logout con la primera
- **ENTONCES** la segunda sigue siendo válida

### Requirement: Usuario o consultorio desactivado pierde el acceso
Si el usuario o su consultorio pasan a `activo = false`, la siguiente petición con cualquiera de sus sesiones DEBE (MUST) responder 401 con el cuerpo de no autenticado (RN-AU-06, DA-09).

#### Scenario: Usuario desactivado con sesión abierta
- **DADO** una sesión válida de un usuario de A
- **CUANDO** el usuario pasa a `activo = false` y se hace `GET /api/auth/me` con esa cookie
- **ENTONCES** la respuesta es 401 con el cuerpo de no autenticado

#### Scenario: Consultorio desactivado con sesión abierta
- **DADO** una sesión válida de un usuario de A
- **CUANDO** A pasa a `activo = false` y se hace `GET /api/auth/me` con esa cookie
- **ENTONCES** la respuesta es 401 con el cuerpo de no autenticado

### Requirement: Rotación de sesión al iniciar sesión
Un login exitoso DEBE (MUST) crear siempre un token nuevo y, si la petición trae una cookie de una sesión válida, DEBE (MUST) revocar esa sesión anterior.

#### Scenario: Login con una sesión previa
- **DADO** una sesión válida `S1` cuya cookie acompaña la petición
- **CUANDO** se hace un login exitoso
- **ENTONCES** la cookie nueva es distinta de la de `S1` y `S1` queda revocada

### Requirement: Rutas no públicas protegidas
Toda ruta de la aplicación DEBE (MUST) responder 401 con el cuerpo de no autenticado a una petición sin sesión, salvo la lista blanca exacta, que depende del entorno (RN-AU-01): `GET /api/health` y `POST /api/auth/login` siempre, y además `GET /docs`, `GET /redoc` y `GET /openapi.json` solo con `APP_ENV=local` (ver "Documentación de la API solo en local"). Una ruta inexistente bajo `/api/` DEBE (MUST) seguir respondiendo 404.

#### Scenario: Recorrido de todas las rutas registradas
- **CUANDO** se recorren todas las rutas registradas en la aplicación y se invoca cada una que no esté en la lista blanca, sin cookie y con `Origin` permitido
- **ENTONCES** cada una responde 401 con el cuerpo de no autenticado

#### Scenario: Lista blanca exacta
- **CUANDO** se comparan las rutas registradas que no dependen de la identidad autenticada con la lista blanca, en una aplicación con `APP_ENV=test` y en otra con `APP_ENV=local`
- **ENTONCES** con `APP_ENV=test` coinciden exactamente con `GET /api/health` y `POST /api/auth/login`
- **Y** con `APP_ENV=local` coinciden exactamente con esas dos más `GET /docs`, `GET /redoc` y `GET /openapi.json`
- **Y** en ninguna existe la ruta `/docs/oauth2-redirect`

#### Scenario: Health sigue público
- **CUANDO** se hace `GET /api/health` sin cookie
- **ENTONCES** la respuesta es 200 con `{"status": "ok"}`

### Requirement: Documentación de la API solo en local
La documentación de la API (`/docs`, `/redoc` y `/openapi.json`) DEBE (MUST) publicarse solo con `APP_ENV=local`; con cualquier otro valor de `APP_ENV` NO DEBE (MUST NOT) registrarse (denegada por defecto). La ruta `/docs/oauth2-redirect` NO DEBE (MUST NOT) existir en ningún entorno.

#### Scenario: Documentación deshabilitada fuera de local
- **DADO** una aplicación con `APP_ENV=test`
- **CUANDO** se hace `GET /docs`, `GET /redoc` y `GET /openapi.json` sin cookie
- **ENTONCES** las tres respuestas son 404

#### Scenario: Documentación disponible en local
- **DADO** una aplicación con `APP_ENV=local`
- **CUANDO** se hace `GET /docs`, `GET /redoc` y `GET /openapi.json` sin cookie
- **ENTONCES** las tres respuestas son 200 y `GET /docs/oauth2-redirect` responde 404

### Requirement: Contraseñas con Argon2id y rehash
Las credenciales DEBEN (MUST) guardarse como hash Argon2id en formato PHC con los parámetros fijados por la aplicación. Tras un login exitoso con un hash de parámetros distintos, la credencial DEBE (MUST) reemplazarse por un hash con los parámetros vigentes. Solo el formato `$argon2id$` DEBE (MUST) admitirse.

#### Scenario: Formato del hash
- **CUANDO** se establece una credencial con el comando local
- **ENTONCES** la `credencial` guardada empieza con `$argon2id$v=19$m=65536,t=3,p=4$`

#### Scenario: Rehash al cambiar parámetros
- **DADO** un usuario cuya credencial es un hash Argon2id válido con `t=2`
- **CUANDO** inicia sesión con la contraseña correcta
- **ENTONCES** la respuesta es 200 y su `credencial` pasa a un hash con `m=65536,t=3,p=4`
- **Y** la contraseña sigue autenticando

#### Scenario: Sin rehash si los parámetros son vigentes
- **DADO** un usuario con un hash de los parámetros vigentes
- **CUANDO** inicia sesión con la contraseña correcta
- **ENTONCES** su `credencial` no cambia

### Requirement: Verificaciones de contraseña simultáneas acotadas
Cada proceso de la API DEBE (MUST) ejecutar como máximo 4 verificaciones Argon2 simultáneas (incluidas las del hash ficticio y el rehash), mediante un mecanismo acotado. Un login evaluado que no obtiene cupo dentro del tiempo de espera (3 segundos) DEBE (MUST) responder 503 con el cuerpo exacto `{"detail": "Servicio ocupado. Intente más tarde."}` y `Retry-After: 5`, sin registrar un fallo, sin crear sesión y con la misma respuesta para cuentas existentes e inexistentes.

#### Scenario: Límite de cuatro verificaciones simultáneas
- **DADO** un verificador de prueba que se bloquea hasta recibir una señal y registra cuántas verificaciones corren a la vez
- **CUANDO** se lanzan 8 logins concurrentes desde 8 direcciones IP distintas sobre 8 pares distintos y luego se libera la señal
- **ENTONCES** el máximo de verificaciones simultáneas observado es exactamente 4
- **Y** los 8 logins terminan con 401 dentro del tiempo de espera

#### Scenario: Saturación produce una respuesta controlada
- **DADO** los 4 cupos ocupados por verificaciones bloqueadas y un tiempo de espera inyectado de 0,2 segundos
- **CUANDO** se hace un login de una cuenta existente y otro de (`ficticio-a`, `nadie@example.test`)
- **ENTONCES** ambos responden 503 con el cuerpo de servicio ocupado, `Retry-After: 5` y `Cache-Control: no-store`
- **Y** ninguno ejecutó el verificador, creó sesión ni registró un fallo

#### Scenario: Cupo liberado ante errores
- **DADO** un verificador de prueba que lanza una excepción
- **CUANDO** se hacen 4 logins seguidos que terminan en esa excepción
- **ENTONCES** después quedan 4 cupos disponibles y un login siguiente con el verificador normal se evalúa sin esperar

#### Scenario: Cupo liberado ante cancelación
- **DADO** un verificador de prueba que lanza una cancelación (`asyncio.CancelledError`) y otro caso en que la espera de cupo se cancela antes de obtenerlo
- **CUANDO** se producen 4 cancelaciones seguidas de cada tipo
- **ENTONCES** después quedan 4 cupos disponibles y ningún cupo se liberó dos veces

### Requirement: Respuestas de autenticación no almacenables
Todas las respuestas de `POST /api/auth/login`, `GET /api/auth/me` y `POST /api/auth/logout`, incluidas las de error, DEBEN (MUST) incluir `Cache-Control: no-store`.

#### Scenario: Login exitoso y rechazado
- **CUANDO** se hace un login exitoso, uno con contraseña incorrecta, uno sin `Origin`, uno con `Content-Type: text/plain` y uno con un campo no declarado
- **ENTONCES** las respuestas 200, 401, 403, 415 y 422 incluyen `Cache-Control: no-store`

#### Scenario: /me con y sin sesión
- **CUANDO** se hace `GET /api/auth/me` con una sesión válida y sin cookie
- **ENTONCES** las respuestas 200 y 401 incluyen `Cache-Control: no-store`

#### Scenario: Logout exitoso y rechazado
- **CUANDO** se hace un logout válido y otro sin `X-CSRF-Token`
- **ENTONCES** las respuestas 204 y 403 incluyen `Cache-Control: no-store`

#### Scenario: Login bloqueado
- **DADO** el par bloqueado por intentos fallidos
- **CUANDO** se hace el login de ese par
- **ENTONCES** la respuesta 429 incluye `Cache-Control: no-store`

### Requirement: Datos sensibles fuera de respuestas y registros
Ninguna respuesta, mensaje de error ni registro de la autenticación DEBE (MUST) contener contraseñas, hashes, tokens de sesión o CSRF, `AUTH_SECRET_KEY`, emails, códigos de consultorio ni direcciones IP (X1).

#### Scenario: Registros de un login fallido y uno exitoso
- **DADO** la captura de registros de la aplicación en nivel `DEBUG`
- **CUANDO** se hacen un login fallido y uno exitoso
- **ENTONCES** ningún registro contiene la contraseña, el email, el código `ficticio-a`, el token, el texto `$argon2` ni la clave configurada

### Requirement: Tabla de sesiones ligada al usuario de su consultorio
La tabla `sesion` DEBE (MUST) referenciar al usuario mediante la clave foránea compuesta `(consultorio_id, usuario_id)` hacia `usuario (consultorio_id, id)`, de modo que una sesión no pueda apuntar a un usuario de otro consultorio, y su HMAC de token DEBE (MUST) ser único.

#### Scenario: Sesión con consultorio que no es el del usuario
- **DADO** un usuario de A
- **CUANDO** se inserta directamente una sesión con `consultorio_id` de B y `usuario_id` de ese usuario
- **ENTONCES** la inserción falla por violación de clave foránea

#### Scenario: HMAC duplicado rechazado
- **CUANDO** se insertan dos sesiones con el mismo HMAC de token
- **ENTONCES** la segunda falla por violación de unicidad

#### Scenario: Vencimientos coherentes
- **CUANDO** se inserta una sesión cuyo vencimiento absoluto no es posterior a su creación
- **ENTONCES** la inserción falla por violación de una restricción `CHECK`

### Requirement: Limpieza acotada de sesiones
Cada login exitoso DEBE (MUST) borrar, como máximo, 100 sesiones revocadas o vencidas (por inactividad o absolutas) de cualquier usuario, sin afectar sesiones válidas. La limpieza masiva queda a cargo del comando local de mantenimiento (capacidad `mantenimiento-local`). NO DEBE (MUST NOT) existir un límite de sesiones simultáneas por usuario: lo acotan los vencimientos, la revocación y la limpieza.

#### Scenario: Sesiones vencidas eliminadas
- **DADO** 3 sesiones revocadas, 2 vencidas y 1 válida
- **CUANDO** se hace un login exitoso
- **ENTONCES** solo quedan la sesión válida previa y la nueva

#### Scenario: Límite por ejecución
- **DADO** 150 sesiones vencidas
- **CUANDO** se hace un login exitoso
- **ENTONCES** se borran exactamente 100

### Requirement: Migración de autenticación reversible
La migración `0003` DEBE (MUST) depender de `0002` y crear `sesion` e `intento_login` vacías y la columna `consultorio.codigo` con su backfill. Su reversión a `0002` DEBE (MUST) eliminar exactamente esos objetos y dejar `consultorio` y `usuario` como en `0002`, y solo DEBE (MUST) ejecutarse contra la base de pruebas.

#### Scenario: Cadena de revisiones con 0003
- **CUANDO** se inspecciona el historial de migraciones
- **ENTONCES** la revisión `head` es `0003` y su revisión anterior es `0002`

#### Scenario: Subida desde 0002 con datos previos
- **DADO** la base de pruebas en `0002` con 2 consultorios y 3 usuarios ficticios
- **CUANDO** se sube a `0003`
- **ENTONCES** existen `sesion` e `intento_login` con cero filas
- **Y** los usuarios conservan todas sus columnas sin cambios y siguen siendo 3

#### Scenario: Bajada a 0002
- **DADO** la base de pruebas en `0003` con consultorios
- **CUANDO** se baja a `0002`
- **ENTONCES** no existen `sesion`, `intento_login`, la columna `codigo` ni las restricciones `uq_consultorio_codigo` y `ck_consultorio_codigo_formato`
- **Y** los consultorios y usuarios siguen existiendo con las mismas columnas y valores que en `0002`

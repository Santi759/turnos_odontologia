# control-intentos-login Specification

## Purpose
Limitar los intentos fallidos de inicio de sesión por cuenta y por dirección IP, con bloqueo temporal y respuesta 429, sin distinguir cuentas existentes de inexistentes ni guardar datos personales en claro (RN-AU-05, DA-05, PD-03).

Convenciones de los escenarios: las mismas de `autenticacion-sesion` (consultorios A `ficticio-a` y B `ficticio-b`, usuario `persona.ficticia@example.test`, `Origin: http://localhost:5173`, `Content-Type: application/json`, reloj inyectable, PostgreSQL real en `db-test`). "Fallo" es un login evaluado que responde 401. "Cuerpo de demasiados intentos" es exactamente `{"detail": "Demasiados intentos. Intente más tarde."}`. La dirección del cliente es la de la conexión directa que recibe la aplicación; las pruebas la inyectan y usan solo direcciones de documentación (`203.0.113.0/24` y `2001:db8::/32`). Salvo que el escenario diga otra cosa, los intentos de un escenario provienen de la misma dirección `203.0.113.7`. Las pruebas inyectan siempre la dirección de forma explícita: el host por defecto de Starlette `TestClient` es `testclient`, que no es una dirección IP. "Cuerpo de solicitud no procesable" es exactamente `{"detail": "No se pudo procesar la solicitud."}`.

## Requirements

### Requirement: Bloqueo por cuenta tras cinco fallos en quince minutos
Cuando el par (código normalizado, email normalizado) acumula 5 fallos en 15 minutos, todo login de ese par DEBE (MUST) responder 429 con el cuerpo de demasiados intentos y `Retry-After` en segundos durante 15 minutos desde el quinto fallo, incluso con la contraseña correcta, sin evaluar la contraseña.

#### Scenario: Sexto intento bloqueado aun con la contraseña correcta
- **DADO** 5 fallos del par (`ficticio-a`, `persona.ficticia@example.test`) en los últimos 10 minutos, el último en `t5`
- **CUANDO** se hace el login con la contraseña correcta en `t5 + 1 min`
- **ENTONCES** la respuesta es 429 con el cuerpo de demasiados intentos y `Retry-After: 840`
- **Y** no se crea sesión y el verificador de contraseñas no se ejecuta

#### Scenario: Fin del bloqueo
- **DADO** el bloqueo anterior
- **CUANDO** se hace el login con la contraseña correcta en `t5 + 15 min`
- **ENTONCES** la respuesta es 200

#### Scenario: Fallos fuera de la ventana no cuentan
- **DADO** 4 fallos del par hace 20 minutos y 1 fallo hace 1 minuto
- **CUANDO** se hace el login con la contraseña correcta
- **ENTONCES** la respuesta es 200

#### Scenario: Los intentos bloqueados no prolongan el bloqueo
- **DADO** el par bloqueado desde `t5`
- **CUANDO** se hacen 3 logins más del par durante el bloqueo, todos respondidos con 429
- **ENTONCES** el bloqueo sigue terminando en `t5 + 15 min`

### Requirement: Éxito reinicia los fallos de la cuenta
Un login exitoso DEBE (MUST) descartar, para el conteo de su par (código, email), los fallos acumulados de ese par. NO DEBE (MUST NOT) borrarlos ni reducir el conteo por dirección IP: los contadores de cuenta y de IP son independientes y los fallos descartados para la cuenta siguen contando para el límite por IP.

#### Scenario: Fallos previos descartados
- **DADO** 4 fallos del par
- **CUANDO** se hace un login exitoso y luego 4 fallos más del par
- **ENTONCES** el siguiente login con la contraseña correcta responde 200

#### Scenario: El éxito marca los fallos del par sin borrarlos
- **DADO** 3 fallos del par (`ficticio-a`, `persona.ficticia@example.test`) y 2 fallos de otro par, todos desde `203.0.113.7`
- **CUANDO** se hace el login exitoso del par
- **ENTONCES** la respuesta es 200 y siguen existiendo las 5 filas de fallos
- **Y** las 3 del par tienen la marca de descarte para la cuenta verdadera y las 2 del otro par la tienen falsa

#### Scenario: El éxito no reinicia el contador de IP
- **DADO** 29 fallos desde `203.0.113.7` en los últimos 10 minutos, 4 de ellos del par (`ficticio-a`, `persona.ficticia@example.test`) y el resto de otros pares
- **CUANDO** se hace desde esa dirección el login exitoso de ese par y luego 1 fallo de otro par
- **ENTONCES** el login exitoso responde 200 y siguen registrados los 29 fallos previos
- **Y** el siguiente login desde `203.0.113.7`, de cualquier par y con la contraseña correcta, responde 429

### Requirement: Mismo comportamiento para cuentas inexistentes
El conteo y el bloqueo DEBEN (MUST) aplicarse al par enviado sin importar si la cuenta existe, de modo que las respuestas no permitan distinguir cuentas existentes de inexistentes.

#### Scenario: Cuenta inexistente bloqueada igual
- **CUANDO** se hacen 6 logins seguidos con (`ficticio-a`, `nadie@example.test`)
- **ENTONCES** los 5 primeros responden 401 con el cuerpo de rechazo de login y el sexto 429 con el cuerpo de demasiados intentos

#### Scenario: Consultorio inexistente bloqueado igual
- **CUANDO** se hacen 6 logins seguidos con (`no-existe`, `persona.ficticia@example.test`)
- **ENTONCES** los 5 primeros responden 401 y el sexto 429

### Requirement: El bloqueo afecta solo al par atacado
El bloqueo por cuenta DEBE (MUST) afectar únicamente al par (código, email) que acumuló los fallos; otro email del mismo consultorio y el mismo email en otro consultorio NO DEBEN (MUST NOT) quedar bloqueados por él.

#### Scenario: Mismo email en otro consultorio
- **DADO** el par (`ficticio-a`, `persona.ficticia@example.test`) bloqueado
- **CUANDO** se hace el login correcto de (`ficticio-b`, `persona.ficticia@example.test`)
- **ENTONCES** la respuesta es 200

#### Scenario: Otro email del mismo consultorio
- **DADO** el mismo par bloqueado
- **CUANDO** se hace el login correcto de otro usuario de A
- **ENTONCES** la respuesta es 200

### Requirement: Límite por dirección IP
Cuando una misma dirección IP acumula 30 fallos en 15 minutos, sobre cualquier cuenta, todo login desde esa dirección DEBE (MUST) responder 429 con el cuerpo de demasiados intentos y `Retry-After` durante 15 minutos desde el trigésimo fallo, sin evaluar la contraseña; los intentos bloqueados NO DEBEN (MUST NOT) prolongar el bloqueo.

#### Scenario: Rociado de contraseñas desde una IP
- **DADO** 30 fallos desde `203.0.113.7` sobre 30 pares distintos en 10 minutos, el último en `t30`
- **CUANDO** se hace desde esa dirección en `t30 + 1 min` el login correcto de un par sin fallos
- **ENTONCES** la respuesta es 429 con el cuerpo de demasiados intentos y `Retry-After: 840`
- **Y** el verificador de contraseñas no se ejecuta

#### Scenario: Por debajo del límite por IP
- **DADO** 29 fallos desde `203.0.113.7` sobre 29 pares distintos en 10 minutos
- **CUANDO** se hace desde esa dirección el login correcto de un par sin fallos
- **ENTONCES** la respuesta es 200

#### Scenario: Otra dirección no queda afectada
- **DADO** la dirección `203.0.113.7` bloqueada
- **CUANDO** se hace el login correcto desde `203.0.113.8`
- **ENTONCES** la respuesta es 200

#### Scenario: Fin del bloqueo por IP sin prolongación
- **DADO** la dirección `203.0.113.7` bloqueada desde `t30`
- **CUANDO** se hacen 5 logins más desde esa dirección durante el bloqueo, todos respondidos con 429, y luego el login correcto en `t30 + 15 min`
- **ENTONCES** este último responde 200

#### Scenario: Red compartida
- **DADO** dos usuarios legítimos de A detrás de la misma dirección pública `203.0.113.7` y 30 fallos de otros pares desde esa dirección
- **CUANDO** cualquiera de ellos intenta iniciar sesión con su contraseña correcta desde esa dirección
- **ENTONCES** la respuesta es 429 (riesgo residual documentado de redes compartidas)
- **Y** desde `203.0.113.8` el mismo login responde 200

### Requirement: Dirección IP normalizada para el límite
Para el límite por IP, una dirección IPv4 DEBE (MUST) identificarse por la dirección completa, una IPv4 mapeada en IPv6 (`::ffff:a.b.c.d`) DEBE (MUST) tratarse como la IPv4 `a.b.c.d`, y una dirección IPv6 DEBE (MUST) identificarse por su prefijo /64.

#### Scenario: IPv6 agrupada por prefijo /64
- **DADO** 30 fallos desde direcciones distintas de `2001:db8:1:2::/64` (por ejemplo `2001:db8:1:2::1` a `2001:db8:1:2::1e`) sobre 30 pares distintos
- **CUANDO** se hace el login correcto de un par sin fallos desde `2001:db8:1:2:ffff:ffff:ffff:ffff`
- **ENTONCES** la respuesta es 429
- **Y** el mismo login desde `2001:db8:1:3::1` responde 200

#### Scenario: IPv4 mapeada normalizada
- **DADO** 30 fallos desde `::ffff:203.0.113.7` sobre 30 pares distintos
- **CUANDO** se hace el login correcto de un par sin fallos desde `203.0.113.7`
- **ENTONCES** la respuesta es 429

### Requirement: Dirección del cliente no determinable
Si `request.client` es nulo o su host no es una dirección IP según `ipaddress`, `POST /api/auth/login` DEBE (MUST) responder 400 con el cuerpo de solicitud no procesable y `Cache-Control: no-store`, después de validar `Origin` y antes de validar `Content-Type`, sin buscar credenciales, ejecutar Argon2, registrar intentos ni emitir cookie. Logout y `/me` NO DEBEN (MUST NOT) depender de la dirección.

#### Scenario: Cliente ausente
- **DADO** una petición de login con las credenciales correctas cuyo `scope` ASGI no tiene cliente (`client` nulo)
- **CUANDO** se procesa el login
- **ENTONCES** la respuesta es 400 con el cuerpo de solicitud no procesable y `Cache-Control: no-store`, sin `Set-Cookie`
- **Y** no se agregó ninguna fila a `intento_login`, no se creó sesión y el verificador de contraseñas no se ejecutó

#### Scenario: Host que no es una dirección IP
- **CUANDO** se hace el login con las credenciales correctas desde el host `testclient` (valor por defecto de `TestClient`)
- **ENTONCES** la respuesta es 400 con el cuerpo de solicitud no procesable
- **Y** no se agregó ninguna fila a `intento_login` y el verificador de contraseñas no se ejecutó

#### Scenario: Direcciones IPv4 e IPv6 válidas continúan
- **CUANDO** se hace el login con las credenciales correctas desde `203.0.113.7` y desde `2001:db8:1:2::1`
- **ENTONCES** ambas respuestas son 200

#### Scenario: Orden respecto de Origin y Content-Type
- **CUANDO** se hace un login sin cliente y sin `Origin`, y otro sin cliente con `Origin` permitido y `Content-Type: text/plain`
- **ENTONCES** el primero responde 403 y el segundo 400

#### Scenario: Registro técnico sin datos
- **DADO** la captura de registros en nivel `DEBUG`
- **CUANDO** se hace un login sin cliente
- **ENTONCES** se registra el código `direccion_cliente_no_determinable` y ningún registro contiene el email, la contraseña ni el código del consultorio

#### Scenario: Logout y /me no dependen de la dirección
- **DADO** una sesión válida obtenida desde `203.0.113.7`
- **CUANDO** se hacen `GET /api/auth/me` y luego el logout con su token CSRF desde el host `testclient`
- **ENTONCES** las respuestas son 200 y 204

### Requirement: El bloqueo de IP no afecta sesiones abiertas
El bloqueo por IP solo DEBE (MUST) afectar a nuevos inicios de sesión: las sesiones abiertas, también las usadas desde la dirección bloqueada, NO DEBEN (MUST NOT) verse afectadas.

#### Scenario: El bloqueo de IP no afecta sesiones abiertas
- **DADO** una sesión válida obtenida desde `203.0.113.7` y luego 30 fallos desde esa dirección
- **CUANDO** se hace `GET /api/auth/me` desde esa dirección con la cookie de la sesión
- **ENTONCES** la respuesta es 200
- **Y** el logout de esa sesión con su token CSRF responde 204

### Requirement: Cabeceras de reenvío ignoradas
La dirección IP del límite DEBE (MUST) ser la de la conexión directa. `X-Forwarded-For`, `X-Real-IP` y `Forwarded` NO DEBEN (MUST NOT) influir, y el arranque del servicio `api` NO DEBE (MUST NOT) habilitar el procesamiento de cabeceras de proxy.

#### Scenario: X-Forwarded-For variable desde la misma conexión
- **CUANDO** se hacen 30 fallos desde la misma conexión sobre 30 pares distintos, cada uno con un `X-Forwarded-For` distinto
- **ENTONCES** el login correcto siguiente desde esa conexión, de un par sin fallos, responde 429

#### Scenario: Arranque sin cabeceras de proxy
- **CUANDO** se inspecciona el comando de arranque efectivo del servicio `api` en la configuración resuelta de Docker Compose
- **ENTONCES** incluye `--no-proxy-headers`

### Requirement: Conteo atómico ante intentos concurrentes
El conteo de fallos y la decisión de bloqueo DEBEN (MUST) ser atómicos por par y por dirección IP: intentos concurrentes NO DEBEN (MUST NOT) permitir evaluar más de 5 contraseñas de un par ni más de 30 desde una dirección dentro de la ventana.

#### Scenario: Diez intentos concurrentes del mismo par
- **CUANDO** se lanzan 10 logins concurrentes con contraseña incorrecta para el mismo par, sin fallos previos
- **ENTONCES** exactamente 5 responden 401 y 5 responden 429
- **Y** quedan registrados exactamente 5 fallos del par

#### Scenario: Cuarenta intentos concurrentes desde la misma IP
- **CUANDO** se lanzan 40 logins concurrentes con contraseña incorrecta desde `203.0.113.7`, sobre 40 pares distintos y sin fallos previos
- **ENTONCES** exactamente 30 responden 401 y 10 responden 429
- **Y** quedan registrados exactamente 30 fallos de esa dirección

### Requirement: Solo cuentan los intentos evaluados
Las peticiones rechazadas antes de evaluar credenciales (por `Origin`, por dirección del cliente no determinable, por `Content-Type`, por validación del cuerpo, por un bloqueo vigente o por saturación del verificador de contraseñas) NO DEBEN (MUST NOT) registrarse como fallos.

#### Scenario: Rechazos previos no cuentan
- **CUANDO** se hacen 10 logins del par sin `Origin`, 10 sin dirección del cliente, 10 con `Content-Type: text/plain` y 10 con un campo no declarado
- **ENTONCES** no hay fallos registrados y el login correcto siguiente responde 200

### Requirement: Intentos sin datos personales en claro
La tabla `intento_login` DEBE (MUST) guardar solo claves HMAC con `AUTH_SECRET_KEY` del par (código, email) y de la dirección IP normalizada, el instante del fallo y la marca de descarte para la cuenta; NO DEBE (MUST NOT) guardar el código, el email, la dirección IP ni la contraseña en claro.

#### Scenario: Fila de un fallo
- **CUANDO** se registra un fallo de (`ficticio-a`, `persona.ficticia@example.test`) desde `203.0.113.7`
- **ENTONCES** la fila no contiene `ficticio-a`, el email ni la dirección del cliente, cada clave tiene exactamente 32 bytes y la marca de descarte para la cuenta es falsa

### Requirement: Limpieza acotada de intentos
Cada login evaluado DEBE (MUST) borrar, como máximo, 100 fallos con más de 24 horas de antigüedad.

#### Scenario: Intentos viejos eliminados
- **DADO** 30 fallos de hace 25 horas y 2 de hace 5 minutos
- **CUANDO** se evalúa un login
- **ENTONCES** quedan solo los 2 fallos recientes más el que haya producido ese login

#### Scenario: Límite por ejecución
- **DADO** 150 fallos de hace 25 horas
- **CUANDO** se evalúa un login
- **ENTONCES** se borran exactamente 100 de ellos

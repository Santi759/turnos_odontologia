# Spec Delta: autenticacion-sesion

## MODIFIED Requirements

### Requirement: Aislamiento de cuentas entre consultorios
La cuenta autenticada DEBE (MUST) ser la del par (código de consultorio, email) enviado; la contraseña de una cuenta de otro consultorio con el mismo email NO DEBE (MUST NOT) autenticar. Una sesión DEBE (MUST) producir siempre el contexto de su propio consultorio. Desde C-04, un `consultorio_id` enviado por el cliente en la query o en la cabecera `X-Consultorio-Id` se rechaza (capacidad `validacion-entrada`), y ningún dato del cliente deriva el contexto.

#### Scenario: Mismo email en A y B con contraseñas distintas
- **DADO** `persona.ficticia@example.test` en A con `contrasena-ficticia-a1` y en B con `contrasena-ficticia-b1`
- **CUANDO** el login envía el código `ficticio-a` con `contrasena-ficticia-b1`
- **ENTONCES** la respuesta es 401 con el cuerpo de rechazo de login
- **Y** con el código `ficticio-b` y `contrasena-ficticia-b1` la respuesta es 200 con el consultorio "Consultorio Ficticio B"

#### Scenario: La sesión de A nunca da contexto de B
Se conserva el nombre del escenario de C-03 (OpenSpec no admite renombrar escenarios en una delta) con contenido actualizado por la decisión DA-06 de C-04: el consultorio del cliente ya no se ignora, se rechaza.
- **DADO** una sesión válida de A
- **CUANDO** una ruta protegida de prueba devuelve el `consultorio_id` del contexto resuelto, sin `consultorio_id` en la query ni cabeceras de consultorio
- **ENTONCES** el contexto es el de A
- **Y** si la petición incluye `consultorio_id` de B en la query, o la cabecera `X-Consultorio-Id` con el `id` de B, la respuesta es el rechazo de `validacion-entrada` y la ruta no se ejecuta

### Requirement: Contexto de consultorio derivado de la sesión
En cada petición protegida, la identidad DEBE (MUST) resolverse desde la cookie a una sesión no revocada y no vencida de un usuario activo de un consultorio activo, y de ella DEBEN (MUST) salir el usuario, el rol tipado y el `ContextoConsultorio`. Ese contexto DEBE (MUST) aplicarse a las transacciones de la base de esa petición (capacidad `aislamiento-base-de-datos`). Ningún dato del cliente DEBE (MUST) alterar ese contexto.

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

#### Scenario: Contexto aplicado a la base
- **DADO** una sesión válida de A y una ruta protegida de prueba que lee `current_setting('app.consultorio_id', true)` en su transacción
- **CUANDO** se invoca la ruta
- **ENTONCES** el valor es el `id` de A

### Requirement: Verificaciones de contraseña simultáneas acotadas
Cada proceso de la API DEBE (MUST) ejecutar como máximo 4 verificaciones Argon2 simultáneas (incluidas las del hash ficticio), mediante un mecanismo acotado. Un login evaluado que no obtiene cupo dentro del tiempo de espera (3 segundos) DEBE (MUST) responder 503 con el cuerpo exacto `{"detail": "Servicio ocupado. Intente más tarde."}` y `Retry-After: 5`, sin registrar un fallo, sin crear sesión y con la misma respuesta para cuentas existentes e inexistentes.

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

### Requirement: Migración de autenticación reversible
La migración `0003` DEBE (MUST) depender de `0002` y crear `sesion` e `intento_login` vacías y la columna `consultorio.codigo` con su backfill. Su reversión a `0002` DEBE (MUST) eliminar exactamente esos objetos y dejar `consultorio` y `usuario` como en `0002`, y solo DEBE (MUST) ejecutarse contra la base de pruebas. Desde C-04, la revisión siguiente es `0004`.

#### Scenario: Cadena de revisiones con 0003
- **CUANDO** se inspecciona el historial de migraciones
- **ENTONCES** la revisión `0003` tiene como revisión anterior `0002` y como siguiente `0004`

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

## REMOVED Requirements

### Requirement: Contraseñas con Argon2id y rehash
**Reason**: Decisión del autor en la segunda revisión de C-04 (R2-01): el login verifica contraseñas y crea sesiones, pero NUNCA modifica `usuario.credencial`. Con el rehash, quien controlara el camino de login (rol `turnos_login`) podía reemplazar el hash de una cuenta conocida por uno propio y tomarla; sin rehash, ningún rol del camino de login tiene privilegio de escritura sobre `usuario`. Limitación aceptada: los hashes ya no se actualizan automáticamente al iniciar sesión.
**Migration**: El formato Argon2id y la verificación pasan al requisito "Contraseñas con Argon2id sin rehash en el login". Un hash con parámetros anteriores sigue autenticando sin cambios; para llevarlo a los parámetros vigentes, el administrador lo detecta con `python -m app.credenciales --revisar-hashes` y restablece la contraseña con `--reemplazar` (capacidad `credenciales-locales`). Las pruebas de C-03 que esperaban el rehash pasan a esperar la credencial idéntica.

## ADDED Requirements

### Requirement: Contraseñas con Argon2id sin rehash en el login
Las credenciales DEBEN (MUST) guardarse como hash Argon2id en formato PHC con los parámetros fijados por la aplicación, y solo el formato `$argon2id$` DEBE (MUST) admitirse. El login DEBE (MUST) verificar la contraseña contra el hash almacenado aunque sus parámetros sean anteriores, y NO DEBE (MUST NOT) modificar `usuario.credencial` en ningún caso: ni tras un éxito, ni tras un rechazo, ni por un cambio de parámetros. Limitación aceptada: el login no actualiza hashes.

#### Scenario: Formato del hash
- **CUANDO** se establece una credencial con el comando local
- **ENTONCES** la `credencial` guardada empieza con `$argon2id$v=19$m=65536,t=3,p=4$`

#### Scenario: Parámetros anteriores sin rehash
- **DADO** un usuario cuya credencial es un hash Argon2id válido con `t=2`
- **CUANDO** inicia sesión con la contraseña correcta
- **ENTONCES** la respuesta es 200 y su `credencial` es idéntica, byte a byte, a la anterior
- **Y** un segundo login con la misma contraseña también responde 200 sin cambiarla

#### Scenario: Parámetros vigentes sin cambios
- **DADO** un usuario con un hash de los parámetros vigentes
- **CUANDO** inicia sesión con la contraseña correcta
- **ENTONCES** su `credencial` no cambia

#### Scenario: Login rechazado sin cambios en la credencial
- **DADO** un usuario con un hash Argon2id válido con `t=2`
- **CUANDO** inicia sesión con una contraseña incorrecta
- **ENTONCES** la respuesta es 401 y su `credencial` no cambia

#### Scenario: Ninguna escritura sobre usuario durante el login
- **DADO** un registro de todas las sentencias enviadas a la base durante la petición
- **CUANDO** se hacen un login exitoso con un hash de `t=2`, uno exitoso con un hash vigente y uno rechazado
- **ENTONCES** ninguna sentencia de esas peticiones modifica `usuario` y la versión de la fila del usuario (`xmin`) es la misma antes y después

#### Scenario: Credencial reemplazada durante el login
- **DADO** un login del usuario de A en curso que ya leyó su credencial
- **CUANDO** el comando local reemplaza la credencial antes de que el login termine
- **ENTONCES** la `credencial` final es la establecida por el comando y el login no la modifica

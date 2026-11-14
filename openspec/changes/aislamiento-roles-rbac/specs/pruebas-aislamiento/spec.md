# Spec Delta: pruebas-aislamiento

## Purpose

Probar de forma automatizada, con conexiones reales de los roles de aplicación y de login, que ningún usuario de un consultorio accede a datos de otro por ninguna ruta protegida, y obligar a que cada ruta protegida nueva agregue su prueba de acceso cruzado (RN-MT-06).

Convenciones de los escenarios: las pruebas de `tests/isolation/` se ejecutan contra `db-test` (X2) con datos ficticios de dos consultorios A y B (D1), con conexiones autenticadas como `turnos_app` y `turnos_login` y nunca contra la base de desarrollo. "Registro de aislamiento" es la tabla de rutas protegidas del arnés.

## ADDED Requirements

### Requirement: Arnés con conexiones reales de los roles de conexión
Las pruebas de aislamiento DEBEN (MUST) conectarse a la base de pruebas como el rol de aplicación y como el rol de login, verificar antes de empezar que cada `current_user` es el rol esperado, que no es superusuario y que la base es la de pruebas, y fallar (nunca omitirse) si algo no se cumple o falta una contraseña. Los datos de A y B DEBEN (MUST) confirmarse con el rol de administración y eliminarse al terminar.

#### Scenario: Conexión verificada
- **CUANDO** la preparación del arnés abre las conexiones de los roles de aplicación y de login
- **ENTONCES** sus `current_user` son `turnos_app` y `turnos_login`, ninguno es superusuario y `current_database()` termina en `_test`

#### Scenario: Contraseña ausente
- **DADO** que falta `TURNOS_LOGIN_TEST_PASSWORD`
- **CUANDO** se prepara el arnés
- **ENTONCES** la suite falla, no se omite, y el error no contiene contraseñas

#### Scenario: Guardia ante la base de desarrollo
- **DADO** una URL de pruebas igual a `DATABASE_URL`, `DATABASE_LOGIN_URL` o `DATABASE_MIGRATION_URL` en host, puerto y base
- **CUANDO** se prepara el arnés
- **ENTONCES** falla antes de abrir conexiones y el error no contiene contraseñas

#### Scenario: Limpieza al terminar
- **CUANDO** termina la sesión de pruebas de aislamiento
- **ENTONCES** `consultorio`, `usuario`, `sesion` e `intento_login` quedan sin filas

### Requirement: Registro obligatorio de rutas protegidas
Toda ruta de la aplicación real que dependa de la identidad autenticada DEBE (MUST) figurar en el registro de aislamiento con su prueba de acceso cruzado o con la justificación de que solo opera sobre la sesión propia. Una ruta protegida ausente del registro, o una entrada sin ruta, DEBE (MUST) hacer fallar la suite.

#### Scenario: Registro completo
- **CUANDO** se recorren las rutas registradas en la aplicación real que dependen de la identidad
- **ENTONCES** coinciden exactamente con las entradas del registro de aislamiento

#### Scenario: Ruta nueva sin registro
- **DADO** una aplicación de prueba con una ruta protegida adicional que no está en el registro
- **CUANDO** se ejecuta la verificación del registro sobre esa aplicación
- **ENTONCES** la verificación falla nombrando el método y la ruta

### Requirement: Acceso cruzado por ruta
Cada entrada del registro DEBE (MUST) ejecutarse con un usuario de B contra datos de A: una ruta con recurso por identificador DEBE (MUST) responder como recurso inexistente; una ruta de sesión propia DEBE (MUST) devolver o afectar solo datos de la sesión de B.

#### Scenario: Identidad propia
- **DADO** sesiones válidas de A y de B
- **CUANDO** el usuario de B hace `GET /api/auth/me`
- **ENTONCES** la respuesta contiene solo su usuario y el nombre del consultorio B

#### Scenario: Cierre de sesión propia
- **DADO** sesiones válidas de A y de B
- **CUANDO** el usuario de B hace `POST /api/auth/logout` con su token CSRF
- **ENTONCES** solo la sesión de B queda revocada y la de A sigue válida

#### Scenario: Recurso de otro consultorio por identificador
- **DADO** la ruta de prueba que obtiene un usuario por su `id`
- **CUANDO** el usuario de B la invoca con el `id` de un usuario de A
- **ENTONCES** la respuesta es idéntica a la de un UUID inexistente

### Requirement: Regresión de autenticación con los roles efectivos
Los flujos de C-03 DEBEN (MUST) funcionar en la aplicación real con conexiones reales del rol de aplicación y del rol de login, no solo del superusuario: login, rechazos genéricos, `GET /api/auth/me`, logout, renovación, login con hash de parámetros anteriores sin modificar la credencial, límites de intentos, descarte tras éxito, revocación de la sesión entrante y CSRF.

#### Scenario: Flujo completo de sesión
- **CUANDO** el usuario de A inicia sesión, consulta `/api/auth/me`, se renueva su sesión pasado un minuto y cierra sesión
- **ENTONCES** las respuestas son 200, 200, 200 y 204 y la sesión queda revocada

#### Scenario: Parámetros anteriores sin rehash con el rol de login
- **DADO** el usuario de A con una credencial Argon2id de parámetros anteriores
- **CUANDO** inicia sesión con la contraseña correcta
- **ENTONCES** la respuesta es 200 y la credencial y la versión de la fila del usuario no cambian

#### Scenario: Límite de intentos con el rol de login
- **CUANDO** se hacen seis intentos fallidos del mismo par desde la misma dirección
- **ENTONCES** los cinco primeros responden 401 y el sexto 429 con `Retry-After`

#### Scenario: Rechazos genéricos con los roles efectivos
- **CUANDO** se hacen logins con contraseña incorrecta, email inexistente, código inexistente, usuario inactivo, consultorio inactivo y usuario sin credencial
- **ENTONCES** todos responden 401 con el mismo cuerpo de rechazo de login y sin cookie

#### Scenario: Descarte tras un éxito con el rol de login
- **DADO** cuatro fallos recientes del par de A
- **CUANDO** el usuario de A inicia sesión con la contraseña correcta y luego falla cuatro veces
- **ENTONCES** ninguno de esos intentos responde 429

#### Scenario: CSRF con el rol de aplicación
- **CUANDO** el usuario de A hace `POST /api/auth/logout` sin token CSRF
- **ENTONCES** la respuesta es 403 y la sesión sigue válida

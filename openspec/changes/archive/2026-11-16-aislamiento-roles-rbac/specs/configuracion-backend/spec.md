# Spec Delta: configuracion-backend

## MODIFIED Requirements

### Requirement: Configuración desde variables de entorno
El sistema DEBE (MUST) leer desde variables de entorno, y validar al cargar la configuración, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, `APP_ENV` y `AUTH_SECRET_KEY` (obligatorias) y `AUTH_SESSION_MINUTES`, `AUTH_SESSION_MAX_HOURS`, `AUTH_COOKIE_SECURE`, `TEST_DATABASE_URL` (solo pruebas), `DATABASE_LOGIN_URL` (solo el login) y `DATABASE_MIGRATION_URL` (migraciones de desarrollo y comandos locales) como opcionales. `APP_ENV` DEBE (MUST) aceptar solo `local` o `test`.

#### Scenario: Carga de valores válidos
- **DADO** que `DATABASE_URL` es `postgresql+psycopg://app:app@db:5432/turnos`, `CORS_ALLOWED_ORIGINS` es `http://localhost:5173`, `APP_ENV` es `local` y `AUTH_SECRET_KEY` es una clave ficticia generada al ejecutar la prueba con `secrets.token_urlsafe(48)` (64 caracteres base64url, 48 bytes)
- **CUANDO** se carga la configuración
- **ENTONCES** la configuración expone esos valores, con la clave como valor secreto que no se muestra al representarla
- **Y** la clave HMAC disponible para la aplicación tiene 48 bytes
- **Y** la lista de orígenes permitidos es exactamente `["http://localhost:5173"]`
- **Y** `AUTH_SESSION_MINUTES` vale 30, `AUTH_SESSION_MAX_HOURS` vale 12 y `AUTH_COOKIE_SECURE` vale `true`

#### Scenario: Falta DATABASE_URL
- **DADO** que `DATABASE_URL` no está definida y las demás variables son válidas
- **CUANDO** se carga la configuración
- **ENTONCES** la carga falla con un error de validación que menciona `DATABASE_URL`

#### Scenario: APP_ENV con valor no admitido
- **DADO** que `APP_ENV` es `produccion` y las demás variables son válidas
- **CUANDO** se carga la configuración
- **ENTONCES** la carga falla con un error de validación que menciona `APP_ENV`

#### Scenario: El error no revela la contraseña
- **DADO** que `DATABASE_URL` es `postgresql+psycopg://app:clave-ficticia@db:5432/turnos` y `APP_ENV` es `produccion`
- **CUANDO** se carga la configuración y falla
- **ENTONCES** el texto del error no contiene `clave-ficticia`

#### Scenario: Credencial de administración opcional y secreta
- **DADO** valores válidos y `DATABASE_MIGRATION_URL` con la contraseña ficticia `clave-admin-ficticia`
- **CUANDO** se carga la configuración y se representa como texto
- **ENTONCES** la carga es válida y la representación no contiene `clave-admin-ficticia`
- **Y** sin `DATABASE_MIGRATION_URL` la carga también es válida

#### Scenario: Credencial de login opcional y secreta
- **DADO** valores válidos y `DATABASE_LOGIN_URL` del usuario `turnos_login` con la contraseña ficticia `clave-login-ficticia`
- **CUANDO** se carga la configuración y se representa como texto
- **ENTONCES** la carga es válida y la representación no contiene `clave-login-ficticia`
- **Y** sin `DATABASE_LOGIN_URL` la carga también es válida

### Requirement: Plantilla de variables sin secretos y .env fuera de Git
El repositorio DEBE (MUST) incluir `.env.example` con todas las variables que usan los servicios locales (`DATABASE_URL`, `DATABASE_LOGIN_URL`, `DATABASE_MIGRATION_URL`, `TEST_DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, `APP_ENV`, `AUTH_SECRET_KEY`, `AUTH_SESSION_MINUTES`, `AUTH_SESSION_MAX_HOURS`, `AUTH_COOKIE_SECURE`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` y `VITE_API_BASE_URL`), solo con valores locales evidentemente ficticios. El archivo `.env` DEBE (MUST) estar ignorado por Git.

#### Scenario: .env ignorado por Git
- **CUANDO** se consulta a Git si `.env` está ignorado
- **ENTONCES** Git indica que `.env` está ignorado

#### Scenario: Plantilla completa con valores ficticios
- **CUANDO** se inspecciona `.env.example`
- **ENTONCES** declara cada una de las variables listadas en el requisito
- **Y** `POSTGRES_PASSWORD` tiene el valor local ficticio `app`
- **Y** un comentario junto a `AUTH_SECRET_KEY` contiene `secrets.token_urlsafe(48)`
- **Y** la configuración cargada con los valores de la plantilla se rechaza con un error que menciona `AUTH_SECRET_KEY`
- **Y** la configuración cargada con los valores de la plantilla, reemplazando solo `AUTH_SECRET_KEY` por una clave generada al ejecutar la prueba, es válida
- **Y** no declara variables de servicios externos (`EMAIL_*`)
- **Y** el usuario de `DATABASE_URL` es `turnos_app`, el de `DATABASE_LOGIN_URL` es `turnos_login` y el de `DATABASE_MIGRATION_URL` es `app`

## ADDED Requirements

### Requirement: Roles distintos para la API, el login y la administración
Dos de `DATABASE_URL`, `DATABASE_LOGIN_URL` y `DATABASE_MIGRATION_URL` con el mismo usuario de PostgreSQL DEBEN (MUST) hacer fallar la carga con un error que nombre ambas variables sin valores, aunque difieran host o puerto; el mismo servidor con roles distintos se admite. La API DEBE (MUST) usar `DATABASE_URL` para su motor general y `DATABASE_LOGIN_URL` solo para el motor de login, NO DEBE (MUST NOT) usar `DATABASE_MIGRATION_URL` y NO DEBE (MUST NOT) crearse sin `DATABASE_LOGIN_URL`.

#### Scenario: Mismo rol rechazado
- **DADO** dos de las tres variables con el mismo usuario, para cada uno de los tres pares posibles, con el mismo host y también con hosts distintos
- **CUANDO** se carga la configuración
- **ENTONCES** la carga falla con un error que menciona las dos variables y no contiene contraseñas

#### Scenario: Mismo servidor con roles distintos admitido
- **DADO** las tres variables con el mismo host, puerto y base y los usuarios `turnos_app`, `turnos_login` y `app`
- **CUANDO** se carga la configuración
- **ENTONCES** la carga es válida

#### Scenario: La API no usa la credencial de administración
- **DADO** valores válidos con `DATABASE_LOGIN_URL` definida y sin `DATABASE_MIGRATION_URL`
- **CUANDO** se crea la aplicación
- **ENTONCES** su motor general usa la URL de `DATABASE_URL` y su motor de login usa la de `DATABASE_LOGIN_URL`
- **Y** con `DATABASE_MIGRATION_URL` definida la creación se rechaza (requisito "La aplicación web rechaza credenciales de administración")

#### Scenario: La API exige la credencial de login
- **DADO** valores válidos sin `DATABASE_LOGIN_URL`
- **CUANDO** se crea la aplicación
- **ENTONCES** la creación falla con un error que menciona `DATABASE_LOGIN_URL` sin abrir conexiones

### Requirement: La aplicación web rechaza credenciales de administración
La creación de la aplicación web (`crear_app`) DEBE (MUST) fallar antes de crear motores si la configuración o el entorno del proceso contienen `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD` o `PGPASSWORD`, con un mensaje fijo que nombre las variables sin sus valores. La guardia NO DEBE (MUST NOT) aplicarse a los comandos administrativos, que no crean la aplicación web.

#### Scenario: Configuración con la credencial de administración
- **DADO** valores válidos y `DATABASE_MIGRATION_URL` con la contraseña ficticia `clave-admin-ficticia`
- **CUANDO** se crea la aplicación
- **ENTONCES** la creación falla con un error que menciona `DATABASE_MIGRATION_URL` y no contiene `clave-admin-ficticia`
- **Y** no se crearon motores ni se abrieron conexiones

#### Scenario: Variable de administración en el entorno del proceso
- **DADO** valores válidos sin `DATABASE_MIGRATION_URL` en la configuración y, en el entorno del proceso, una de `DATABASE_MIGRATION_URL`, `POSTGRES_PASSWORD` o `PGPASSWORD` con un valor ficticio, para cada una de las tres
- **CUANDO** se crea la aplicación
- **ENTONCES** la creación falla con un error que nombra esa variable y no contiene su valor

#### Scenario: Entorno sin credenciales de administración
- **DADO** valores válidos y un entorno del proceso sin ninguna de esas variables
- **CUANDO** se crea la aplicación
- **ENTONCES** la creación es válida

#### Scenario: Los comandos administrativos no usan la guardia
- **DADO** el entorno del servicio administrativo, con `DATABASE_MIGRATION_URL` y `POSTGRES_PASSWORD`
- **CUANDO** se inspeccionan los módulos de Alembic, seed, credenciales, roles y mantenimiento
- **ENTONCES** ninguno crea la aplicación web y todos abren su sesión con la credencial de administración

#### Scenario: La aplicación web no arranca con el entorno administrativo
- **DADO** el entorno efectivo del servicio administrativo
- **CUANDO** se intenta crear la aplicación web en ese contenedor
- **ENTONCES** la creación falla con un error que nombra solo variables, sin valores

### Requirement: Variables opcionales vacías toman su valor por defecto
La carga de la configuración DEBE (MUST) tratar una variable definida con valor vacío como no definida: una opcional vacía toma su valor por defecto y una obligatoria vacía hace fallar la carga.

#### Scenario: Opcionales vacías
- **DADO** valores válidos y `AUTH_SESSION_MINUTES`, `AUTH_SESSION_MAX_HOURS`, `AUTH_COOKIE_SECURE` y `TEST_DATABASE_URL` definidas con valor vacío
- **CUANDO** se carga la configuración
- **ENTONCES** la carga es válida con 30 minutos, 12 horas, cookie `Secure` y sin URL de pruebas

#### Scenario: Obligatoria vacía
- **DADO** valores válidos y `DATABASE_URL` definida con valor vacío
- **CUANDO** se carga la configuración
- **ENTONCES** la carga falla con un error que menciona `DATABASE_URL`

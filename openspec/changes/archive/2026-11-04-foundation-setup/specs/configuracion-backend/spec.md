# Spec Delta: configuracion-backend

## Purpose

Definir cómo el backend obtiene y valida su configuración desde variables de entorno, cómo restringe los orígenes CORS y qué contiene la plantilla de variables, para que ningún secreto ni valor real quede en el repositorio.

Convenciones de los escenarios: valores locales y ficticios (D1); origen del frontend de desarrollo `http://localhost:5173`; origen ajeno de ejemplo `http://otro-origen.invalid`.

## ADDED Requirements

### Requirement: Configuración desde variables de entorno
El sistema DEBE (MUST) leer `DATABASE_URL`, `CORS_ALLOWED_ORIGINS` y `APP_ENV` (obligatorias) y `TEST_DATABASE_URL` (opcional, solo para pruebas y migraciones de pruebas) desde variables de entorno y validarlas al cargar la configuración. `APP_ENV` DEBE (MUST) aceptar solo `local` o `test`. Si falta una variable obligatoria o un valor es inválido, la carga DEBE (MUST) fallar con un error de validación que nombre la variable sin mostrar su valor.

#### Scenario: Carga de valores válidos
- **DADO** que `DATABASE_URL` es `postgresql+psycopg://app:app@db:5432/turnos`, `CORS_ALLOWED_ORIGINS` es `http://localhost:5173` y `APP_ENV` es `local`
- **CUANDO** se carga la configuración
- **ENTONCES** la configuración expone esos tres valores
- **Y** la lista de orígenes permitidos es exactamente `["http://localhost:5173"]`

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

### Requirement: Orígenes CORS restringidos a la lista configurada
El sistema DEBE (MUST) permitir solicitudes de origen cruzado solo desde los orígenes listados en `CORS_ALLOWED_ORIGINS` (separados por comas). La configuración DEBE (MUST) rechazar el comodín `*` y una lista vacía.

#### Scenario: Origen permitido
- **DADO** que `CORS_ALLOWED_ORIGINS` es `http://localhost:5173`
- **CUANDO** llega `GET /api/health` con cabecera `Origin: http://localhost:5173`
- **ENTONCES** la respuesta incluye `Access-Control-Allow-Origin: http://localhost:5173`

#### Scenario: Origen no permitido
- **DADO** que `CORS_ALLOWED_ORIGINS` es `http://localhost:5173`
- **CUANDO** llega `GET /api/health` con cabecera `Origin: http://otro-origen.invalid`
- **ENTONCES** la respuesta no incluye la cabecera `Access-Control-Allow-Origin`

#### Scenario: Varios orígenes separados por comas
- **DADO** que `CORS_ALLOWED_ORIGINS` es `http://localhost:5173,http://127.0.0.1:5173`
- **CUANDO** se carga la configuración
- **ENTONCES** la lista de orígenes permitidos es exactamente `["http://localhost:5173", "http://127.0.0.1:5173"]`

#### Scenario: Comodín rechazado
- **DADO** que `CORS_ALLOWED_ORIGINS` es `*`
- **CUANDO** se carga la configuración
- **ENTONCES** la carga falla con un error de validación que menciona `CORS_ALLOWED_ORIGINS`

#### Scenario: Lista vacía rechazada
- **DADO** que `CORS_ALLOWED_ORIGINS` es una cadena vacía
- **CUANDO** se carga la configuración
- **ENTONCES** la carga falla con un error de validación que menciona `CORS_ALLOWED_ORIGINS`

### Requirement: Plantilla de variables sin secretos y .env fuera de Git
El repositorio DEBE (MUST) incluir `.env.example` con todas las variables que usan los servicios locales (`DATABASE_URL`, `TEST_DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, `APP_ENV`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `VITE_API_BASE_URL`), solo con valores locales ficticios. El archivo `.env` DEBE (MUST) estar ignorado por Git.

#### Scenario: .env ignorado por Git
- **CUANDO** se consulta a Git si `.env` está ignorado
- **ENTONCES** Git indica que `.env` está ignorado

#### Scenario: Plantilla completa con valores ficticios
- **CUANDO** se inspecciona `.env.example`
- **ENTONCES** declara cada una de las variables listadas en el requisito
- **Y** `POSTGRES_PASSWORD` tiene el valor local ficticio `app`
- **Y** no declara variables de autenticación ni de servicios externos (`AUTH_*`, `EMAIL_*`)

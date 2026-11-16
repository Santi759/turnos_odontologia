# Spec Delta: seed-ficticio

## MODIFIED Requirements

### Requirement: Guardia de entorno del seed
El comando de seed DEBE (MUST) negarse a ejecutar, sin abrir ninguna conexión, si `APP_ENV` no es `local`, y DEBE (MUST) terminar con código distinto de cero indicando el motivo. Con `APP_ENV=local` DEBE (MUST) usar únicamente la credencial de administración `DATABASE_MIGRATION_URL`, nunca `DATABASE_URL` ni `DATABASE_LOGIN_URL` (roles de la API), y fallar sin conectar si falta.

#### Scenario: Entorno de pruebas rechazado
- **DADO** `APP_ENV=test` y `DATABASE_URL` apuntando a `host-inexistente.invalid`
- **CUANDO** se ejecuta el comando de seed
- **ENTONCES** termina con código distinto de cero y un mensaje que menciona `APP_ENV`
- **Y** no se intentó ninguna conexión a la base

#### Scenario: Entorno local admitido
- **DADO** `APP_ENV=local`
- **CUANDO** se evalúa la guardia de entorno del seed
- **ENTONCES** la guardia no rechaza la ejecución

#### Scenario: Usa la credencial de administración
- **DADO** `APP_ENV=local`, `DATABASE_URL` apuntando a `host-api.invalid` y `DATABASE_MIGRATION_URL` apuntando a `host-admin.invalid`
- **CUANDO** se abre la sesión de base por defecto del seed
- **ENTONCES** el motor apunta a `host-admin.invalid`
- **Y** sin `DATABASE_MIGRATION_URL` el seed falla sin conectar con un mensaje que la menciona

## ADDED Requirements

### Requirement: Seed mediante el servicio administrativo
El comando DEBE (MUST) documentarse y ejecutarse con `docker compose run --rm --no-deps admin python -m app.seed`, el único servicio que recibe `DATABASE_MIGRATION_URL`. Ejecutado con el servicio `api`, que no la recibe, DEBE (MUST) terminar con código distinto de cero y el mensaje que la menciona, sin abrir conexiones.

#### Scenario: Comando documentado con admin
- **CUANDO** se inspeccionan `README.md` y la ayuda del módulo `app.seed`
- **ENTONCES** el comando se indica con el servicio `admin` y no con `api`

#### Scenario: Ejecutado con el entorno de la API
- **DADO** `APP_ENV=local` y el entorno de la API, sin `DATABASE_MIGRATION_URL`
- **CUANDO** se ejecuta el comando
- **ENTONCES** termina con código distinto de cero y un mensaje que menciona `DATABASE_MIGRATION_URL`, sin abrir conexiones

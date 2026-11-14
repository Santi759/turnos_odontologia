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

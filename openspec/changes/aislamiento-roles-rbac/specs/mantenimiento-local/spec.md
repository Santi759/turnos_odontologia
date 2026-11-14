# Spec Delta: mantenimiento-local

## MODIFIED Requirements

### Requirement: Limpieza solo en el entorno local
El comando de mantenimiento DEBE (MUST) negarse a ejecutar, sin abrir ninguna conexión, si `APP_ENV` no es `local`, y con `APP_ENV=local` DEBE (MUST) operar solo con la credencial de administración `DATABASE_MIGRATION_URL`, nunca con `DATABASE_URL` ni `DATABASE_LOGIN_URL`, y fallar sin conectar si falta. Los argumentos DEBEN (MUST) validarse antes de conectar: solo se admite el subcomando `limpiar` y la opción `--max-lotes` con un entero entre 1 y 1000 (por defecto 100).

#### Scenario: Entorno de pruebas rechazado
- **DADO** `APP_ENV=test` y `DATABASE_URL` apuntando a `host-inexistente.invalid`
- **CUANDO** se ejecuta `python -m app.mantenimiento limpiar`
- **ENTONCES** termina con código distinto de cero y un mensaje que menciona `APP_ENV`
- **Y** no se intentó ninguna conexión a la base

#### Scenario: Argumentos inválidos rechazados antes de conectar
- **CUANDO** se ejecuta con `--max-lotes 0`, `--max-lotes 1001`, `--max-lotes abc` o con un subcomando distinto de `limpiar`
- **ENTONCES** el comando falla y no se intentó ninguna conexión a la base

#### Scenario: Valor por defecto y límites de --max-lotes
- **CUANDO** se analizan los argumentos `limpiar`, `limpiar --max-lotes 1` y `limpiar --max-lotes 1000`
- **ENTONCES** se aceptan con un máximo de lotes efectivo de 100, 1 y 1000 respectivamente

#### Scenario: Usa la credencial de administración
- **DADO** `APP_ENV=local`, `DATABASE_URL` apuntando a `host-api.invalid` y `DATABASE_MIGRATION_URL` apuntando a `host-admin.invalid`
- **CUANDO** se abre la sesión de base por defecto del comando
- **ENTONCES** el motor apunta a `host-admin.invalid`
- **Y** sin `DATABASE_MIGRATION_URL` el comando falla sin conectar con un mensaje que la menciona

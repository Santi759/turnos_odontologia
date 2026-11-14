# Spec Delta: credenciales-locales

## MODIFIED Requirements

### Requirement: Comando solo en el entorno local
El comando de credenciales DEBE (MUST) negarse a ejecutar, sin abrir ninguna conexión, si `APP_ENV` no es `local`, y con `APP_ENV=local` DEBE (MUST) operar solo con la credencial de administración `DATABASE_MIGRATION_URL`, nunca con `DATABASE_URL` ni `DATABASE_LOGIN_URL` (roles de la API), y fallar sin conectar si falta.

#### Scenario: Entorno de pruebas rechazado
- **DADO** `APP_ENV=test` y `DATABASE_URL` apuntando a `host-inexistente.invalid`
- **CUANDO** se ejecuta el comando de credenciales
- **ENTONCES** termina con código distinto de cero y un mensaje que menciona `APP_ENV`
- **Y** no se intentó ninguna conexión a la base

#### Scenario: Sin credencial de administración
- **DADO** `APP_ENV=local` sin `DATABASE_MIGRATION_URL`
- **CUANDO** se ejecuta el comando de credenciales
- **ENTONCES** termina con código distinto de cero y un mensaje que menciona `DATABASE_MIGRATION_URL`, sin abrir conexiones

#### Scenario: Usa la credencial de administración
- **DADO** `APP_ENV=local`, `DATABASE_URL` apuntando a `host-api.invalid` y `DATABASE_MIGRATION_URL` apuntando a `host-admin.invalid`
- **CUANDO** se abre la sesión de base por defecto del comando
- **ENTONCES** el motor apunta a `host-admin.invalid`

## ADDED Requirements

### Requirement: Revisión local de hashes sin modificar credenciales
Con `--revisar-hashes` (incompatible con `--reemplazar`), el comando DEBE (MUST) clasificar en una transacción de solo lectura cada credencial como vigente, con parámetros anteriores (Argon2id con otros parámetros), con formato no admitido o nula, e informar solo textos fijos, una cantidad por clase y los `id` de consultorio y usuario de cada cuenta a restablecer. NO DEBE (MUST NOT) modificar filas ni mostrar hashes, emails ni códigos.

#### Scenario: Clasificación de los hashes
- **DADO** usuarios ficticios con un hash vigente, uno con `t=2`, uno con `m=19456`, uno `$argon2i$`, uno `$argon2d$`, uno que no es un hash y uno con credencial nula
- **CUANDO** se ejecuta el comando con `--revisar-hashes`
- **ENTONCES** termina con código 0 e informa 1 vigente, 2 con parámetros anteriores, 3 con formato no admitido y 1 sin credencial
- **Y** lista los identificadores de las 5 cuentas a restablecer y no los de la vigente ni la nula

#### Scenario: Revisión sin escrituras
- **CUANDO** se ejecuta el comando con `--revisar-hashes`
- **ENTONCES** ninguna sentencia enviada modifica filas, la transacción es de solo lectura y las credenciales y sesiones no cambian

#### Scenario: Salida de la revisión sin datos sensibles
- **CUANDO** se ejecuta el comando con `--revisar-hashes` sobre los usuarios del escenario de clasificación
- **ENTONCES** la salida no contiene `$argon2`, `@`, `ficticio-a` ni `postgresql`

#### Scenario: Opciones incompatibles
- **CUANDO** se ejecuta el comando con `--revisar-hashes --reemplazar`
- **ENTONCES** el comando falla sin abrir conexiones y sin pedir contraseñas

### Requirement: Escritura condicionada a la credencial leída
El comando DEBE (MUST) escribir la credencial nueva solo si la credencial almacenada sigue siendo la que leyó en la misma ejecución (comparación e intercambio dentro de su transacción de administración); si cambió, DEBE (MUST) fallar con un mensaje fijo, sin escribir la credencial y sin revocar sesiones. El hash nuevo DEBE (MUST) usar los parámetros vigentes.

#### Scenario: Credencial cambiada entre la lectura y la escritura
- **DADO** el comando con `--reemplazar` que ya leyó la credencial del usuario de A
- **CUANDO** otra transacción confirmada cambia esa credencial antes de la escritura
- **ENTONCES** el comando falla con el mensaje `la credencial cambió desde que se leyó; reintente`
- **Y** la credencial es la de la otra transacción y las sesiones del usuario siguen válidas

#### Scenario: Restablecimiento de un hash con parámetros anteriores
- **DADO** el usuario de A con un hash de `t=2` informado por la revisión
- **CUANDO** el administrador ejecuta el comando con `--reemplazar`, una contraseña nueva confirmada y `REEMPLAZAR`
- **ENTONCES** la credencial empieza con `$argon2id$v=19$m=65536,t=3,p=4$`, las sesiones previas quedan revocadas y una nueva revisión ya no lista esa cuenta

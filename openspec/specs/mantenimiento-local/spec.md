# mantenimiento-local Specification

## Purpose
Ofrecer un comando local explícito que elimine por lotes acotados las sesiones vencidas o revocadas y los intentos de login fuera de la retención, para complementar la limpieza oportunista del login sin tocar sesiones activas ni intentos recientes (DA-14, PD-08). No es un servicio ni una tarea programada: antes de cualquier despliegue fuera de local hará falta un mantenimiento periódico autorizado.

Convenciones de los escenarios: el comando es `python -m app.mantenimiento limpiar [--max-lotes N]`. Se prueba con la sesión de base y el reloj inyectados; las pruebas con base usan solo `db-test` (X2) y datos ficticios (D1). "Sesión vencida" es una sesión revocada, con su vencimiento absoluto alcanzado o con más de `AUTH_SESSION_MINUTES` minutos desde su último uso; "intento vencido" es un fallo con más de 24 horas de antigüedad. "El comando falla" significa que termina con código distinto de cero sin borrar ninguna fila.

## Requirements

### Requirement: Limpieza solo en el entorno local
El comando de mantenimiento DEBE (MUST) negarse a ejecutar, sin abrir ninguna conexión, si `APP_ENV` no es `local`, y con `APP_ENV=local` DEBE (MUST) operar solo sobre `DATABASE_URL`. Los argumentos DEBEN (MUST) validarse antes de conectar: solo se admite el subcomando `limpiar` y la opción `--max-lotes` con un entero entre 1 y 1000 (por defecto 100).

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

### Requirement: Borrado solo de filas vencidas
El comando DEBE (MUST) borrar únicamente sesiones vencidas e intentos vencidos, según el reloj de la aplicación y la configuración vigente. NO DEBE (MUST NOT) borrar sesiones válidas ni intentos dentro de la retención de 24 horas, ni modificar ninguna otra tabla.

#### Scenario: Sesiones activas e intentos recientes intactos
- **DADO** 3 sesiones revocadas, 2 vencidas por inactividad, 1 vencida por tiempo absoluto, 2 válidas, 4 fallos de hace 25 horas y 3 fallos de hace 23 horas y 59 minutos
- **CUANDO** se ejecuta `limpiar`
- **ENTONCES** quedan exactamente las 2 sesiones válidas y los 3 fallos recientes
- **Y** `consultorio` y `usuario` no cambian

### Requirement: Lotes acotados por ejecución
El comando DEBE (MUST) borrar en lotes de como máximo 1000 filas, cada uno en su propia transacción, y por cada tabla DEBE (MUST) detenerse al alcanzar `--max-lotes` lotes o cuando un lote borra menos de 1000 filas.

#### Scenario: Máximo de lotes respetado
- **DADO** 2500 intentos vencidos
- **CUANDO** se ejecuta `limpiar --max-lotes 2`
- **ENTONCES** se borran exactamente 2000 intentos y quedan 500
- **Y** ninguna sentencia de borrado afectó más de 1000 filas

#### Scenario: Cada lote en su propia transacción
- **DADO** 2500 intentos vencidos y un error inyectado al ejecutar el tercer lote
- **CUANDO** se ejecuta `limpiar`
- **ENTONCES** el comando termina con código distinto de cero
- **Y** quedan borrados exactamente los 2000 intentos de los dos primeros lotes confirmados y quedan 500

#### Scenario: Ejecución completa con el valor por defecto
- **DADO** 2500 intentos vencidos y 1200 sesiones vencidas
- **CUANDO** se ejecuta `limpiar` sin `--max-lotes`
- **ENTONCES** se borran los 2500 intentos y las 1200 sesiones en lotes de como máximo 1000 filas

#### Scenario: Sin filas vencidas
- **DADO** solo sesiones válidas e intentos recientes
- **CUANDO** se ejecuta `limpiar`
- **ENTONCES** termina con código 0 y no borra ninguna fila

### Requirement: Salida del mantenimiento solo con cantidades
La salida y los errores del comando DEBEN (MUST) contener solo cantidades y textos fijos; NO DEBEN (MUST NOT) incluir identificadores, emails, códigos de consultorio, claves HMAC, `AUTH_SECRET_KEY` ni URLs de conexión (X1).

#### Scenario: Resumen de una ejecución
- **DADO** 3 sesiones vencidas y 4 intentos vencidos
- **CUANDO** se ejecuta `limpiar`
- **ENTONCES** la salida es exactamente `sesiones eliminadas: 3; intentos eliminados: 4`
- **Y** no contiene `@`, `postgresql` ni ningún `id` de sesión

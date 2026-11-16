# credenciales-locales Specification

## Purpose
Ofrecer un comando administrativo local e interactivo para establecer o reemplazar la credencial de un usuario existente, sin que la contraseña pase por argumentos, archivos, variables de entorno ni registros, como único medio de obtener credenciales en C-03 (DA-07, DA-10, PA-11), aplicando la política de contraseñas nuevas aprobada (PD-04).

Convenciones de los escenarios: el comando se prueba con la entrada interactiva, la lectura oculta de la contraseña y la sesión de base inyectadas; las pruebas con base usan solo `db-test` (X2) y datos ficticios (D1): consultorio `ficticio-a` con nombre "Consultorio Ficticio A", usuario `persona.ficticia@example.test` con nombre "Persona Ficticia", contraseña `clave-de-prueba-a1` (no contiene términos del contexto: una contraseña con `ficticia` se rechazaría). "Forma compacta" de un texto: NFKC, `casefold`, NFKD sin marcas combinantes y solo caracteres alfanuméricos. "El comando falla" significa que termina con código distinto de cero sin modificar ninguna fila. "Longitud" es la cantidad de puntos de código Unicode del texto normalizado con NFKC.

## Requirements

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

### Requirement: Contraseña solo por entrada interactiva oculta
El comando DEBE (MUST) pedir la contraseña dos veces con lectura sin eco desde una terminal interactiva, y NO DEBE (MUST NOT) aceptarla por argumentos, variables de entorno, archivos ni entrada redirigida. Si las dos lecturas difieren, DEBE (MUST) fallar sin cambios.

#### Scenario: Entrada no interactiva rechazada
- **DADO** que la entrada estándar no es una terminal
- **CUANDO** se ejecuta el comando
- **ENTONCES** el comando falla con un mensaje que pide una terminal interactiva, antes de pedir la contraseña

#### Scenario: Argumentos de contraseña no admitidos
- **CUANDO** se ejecuta el comando con `--contrasena clave-de-prueba-a1` o `--password clave-de-prueba-a1`
- **ENTONCES** el comando falla por argumento no reconocido y la salida no contiene `clave-de-prueba-a1`

#### Scenario: Confirmación distinta
- **CUANDO** la primera lectura oculta es `clave-de-prueba-a1` y la segunda `clave-de-prueba-a2`
- **ENTONCES** el comando falla y la credencial del usuario no cambia

#### Scenario: Lectura sin eco
- **CUANDO** se ejecuta el comando
- **ENTONCES** ambas lecturas de la contraseña usan la función de lectura sin eco y ninguna usa la lectura visible

### Requirement: Por defecto solo completa credenciales nulas
Sin `--reemplazar`, el comando DEBE (MUST) establecer la credencial solo si el usuario identificado por código de consultorio y email tiene `credencial` nula; si ya tiene una, DEBE (MUST) fallar sin cambios indicando que se requiere `--reemplazar`.

#### Scenario: Usuario sin credencial
- **DADO** el usuario de A con `credencial` nula
- **CUANDO** se ejecuta el comando con código `ficticio-a`, el email y la contraseña confirmada
- **ENTONCES** termina con código 0, la `credencial` es un hash `$argon2id$` y el login con esa contraseña responde 200

#### Scenario: Usuario con credencial sin --reemplazar
- **DADO** el usuario de A con una credencial establecida
- **CUANDO** se ejecuta el comando sin `--reemplazar`
- **ENTONCES** el comando falla con un mensaje que menciona `--reemplazar` y la credencial no cambia

### Requirement: Reemplazo explícito de credenciales
Con `--reemplazar`, el comando DEBE (MUST) pedir una confirmación explícita adicional, reemplazar la credencial y revocar todas las sesiones activas de ese usuario. Sin la confirmación DEBE (MUST) fallar sin cambios.

#### Scenario: Reemplazo confirmado
- **DADO** el usuario de A con credencial y dos sesiones válidas
- **CUANDO** se ejecuta el comando con `--reemplazar`, una contraseña nueva confirmada y la confirmación `REEMPLAZAR`
- **ENTONCES** termina con código 0, la contraseña anterior deja de autenticar, la nueva autentica
- **Y** las dos sesiones previas quedan revocadas

#### Scenario: Reemplazo no confirmado
- **CUANDO** se ejecuta con `--reemplazar` y la confirmación es `no`
- **ENTONCES** el comando falla, la credencial no cambia y las sesiones siguen válidas

### Requirement: Política mínima de contraseñas
El comando DEBE (MUST) normalizar la contraseña con NFKC antes de evaluarla y de calcular el hash, y DEBE (MUST) rechazar, sin cambios, contraseñas cuya longitud sea menor que 15 o mayor que 128 puntos de código y contraseñas formadas solo por espacios en blanco. DEBE (MUST) admitir espacios y cualquier carácter Unicode y NO DEBE (MUST NOT) aplicar reglas de composición. La política solo se aplica a contraseñas nuevas.

#### Scenario: Contraseña corta
- **CUANDO** la contraseña confirmada tiene 14 puntos de código
- **ENTONCES** el comando falla con un mensaje que indica la longitud mínima y la credencial no cambia

#### Scenario: Contraseña larga
- **CUANDO** la contraseña confirmada tiene 129 puntos de código
- **ENTONCES** el comando falla y la credencial no cambia

#### Scenario: Longitudes límite aceptadas
- **CUANDO** la contraseña confirmada tiene 15 o 128 puntos de código, sin términos del contexto ni entradas de la lista
- **ENTONCES** el comando termina con código 0

#### Scenario: La longitud se mide tras NFKC
- **CUANDO** la contraseña confirmada son 8 ligaduras `ﬁ` (U+FB01) seguidas de `-2026` (13 puntos de código sin normalizar, 21 tras NFKC)
- **ENTONCES** el comando termina con código 0

#### Scenario: Solo espacios
- **CUANDO** la contraseña confirmada son 20 espacios
- **ENTONCES** el comando falla y la credencial no cambia

#### Scenario: Espacios y Unicode admitidos
- **CUANDO** la contraseña confirmada es `una frase larga con ñandú 2026`
- **ENTONCES** el comando termina con código 0

#### Scenario: Equivalencia NFKC al establecer y al verificar
- **DADO** que el comando estableció la contraseña `contraseña-de-prueba-ñ1` ingresada con `ñ` descompuesta (`n` + U+0303)
- **CUANDO** se hace el login con la misma contraseña escrita con `ñ` compuesta (U+00F1)
- **ENTONCES** la respuesta es 200

### Requirement: Contraseñas comunes rechazadas
El comando DEBE (MUST) rechazar, sin cambios, contraseñas cuya forma compacta coincida con la de una entrada de la lista local versionada de contraseñas comunes. La lista DEBE (MUST) ser de elaboración propia del proyecto y documentar en su cabecera fuente, licencia, criterios de selección y SHA-256; NO DEBE (MUST NOT) incluir listas externas ni consultar servicios externos.

#### Scenario: Contraseña común rechazada
- **CUANDO** la contraseña confirmada es una entrada de la lista local de contraseñas comunes, por ejemplo `123456789012345`, o la misma entrada con otras mayúsculas
- **ENTONCES** el comando falla con un mensaje que indica que es una contraseña común, sin repetirla, y la credencial no cambia

#### Scenario: Lista local documentada
- **CUANDO** se inspecciona el archivo versionado de contraseñas comunes
- **ENTONCES** su cabecera indica la fuente "elaboración propia del proyecto", la licencia, los criterios de selección y el resumen SHA-256 del contenido, y el resumen coincide con el contenido
- **Y** todas sus entradas tienen al menos 15 puntos de código tras NFKC

### Requirement: Términos del contexto rechazados
El comando DEBE (MUST) rechazar, sin cambios, una contraseña si y solo si su forma compacta contiene la forma compacta de un término del contexto: código del consultorio; parte local del email y sus tokens de ≥ 4 caracteres; etiquetas del dominio, tokens del nombre del consultorio y del usuario de ≥ 4 caracteres que no estén en la lista versionada de términos genéricos; y `turnos`, `odontologia`, `consultorio` y el nombre del sistema.

#### Scenario: Término del contexto rechazado
- **CUANDO** la contraseña confirmada es `mi-clave-ficticio-a-2026` (contiene el código del consultorio), `persona.ficticia-de-verano` (contiene la parte local del email), `verano-ficticia-2026-largo` (contiene un token de la parte local), `TURNOS de la tarde 2026` o `odontología-del-barrio` (contienen términos del sistema)
- **ENTONCES** el comando falla en cada caso con un mensaje que indica que contiene un término del contexto, sin repetirlo, y la credencial no cambia

#### Scenario: Sin distinguir mayúsculas, diacríticos ni separadores
- **CUANDO** la contraseña confirmada es `mañana-PÉRSONA-libre-26` o `O.D.O.N.T.O.L.O.G.I.A-2026-x`
- **ENTONCES** el comando falla en ambos casos por contener un término del contexto (`persona` y `odontologia`)

#### Scenario: Términos genéricos del dominio no rechazan
- **DADO** el usuario `persona.ficticia@example.test`
- **CUANDO** la contraseña confirmada es `mi example de test largo 2026`, que no es común ni contiene otro término
- **ENTONCES** el comando termina con código 0: `example` y `test` están en la lista de términos genéricos y no son términos del contexto

#### Scenario: Los términos fijos del sistema no se excluyen
- **DADO** que `consultorio` figura en la lista de términos genéricos como palabra de nombres de consultorios
- **CUANDO** la contraseña confirmada es `mi consultorio preferido 2026`
- **ENTONCES** el comando falla por contener un término del contexto

#### Scenario: Comprobación determinista
- **DADO** una contraseña y un conjunto de términos del contexto
- **CUANDO** la comprobación se ejecuta dos veces con los mismos datos y con los términos en dos órdenes distintos
- **ENTONCES** el resultado es el mismo en todas las ejecuciones

#### Scenario: Lista de términos genéricos documentada
- **CUANDO** se inspecciona el archivo versionado de términos genéricos
- **ENTONCES** su cabecera indica la fuente "elaboración propia del proyecto", la licencia, los criterios de inclusión y el resumen SHA-256 del contenido
- **Y** incluye `example`, `test`, `invalid`, `localhost`, `gmail` y `dental`, y no incluye `turnos` ni `odontologia`

### Requirement: Cuenta inexistente
Si no existe un usuario con el código de consultorio y el email indicados, el comando DEBE (MUST) fallar con un mensaje genérico, sin crear usuarios ni consultorios.

#### Scenario: Email inexistente
- **CUANDO** se ejecuta el comando con `ficticio-a` y `nadie@example.test`
- **ENTONCES** el comando falla con el mensaje `no se encontró la cuenta indicada` y no se crea ninguna fila

### Requirement: Salida del comando sin datos sensibles
La salida y los errores del comando NO DEBEN (MUST NOT) incluir la contraseña, el hash, el email, el código de consultorio, `AUTH_SECRET_KEY` ni URLs de conexión (X1).

#### Scenario: Salida de una ejecución exitosa y una fallida
- **CUANDO** se ejecuta el comando una vez con éxito, otra con confirmación distinta y otra con una contraseña rechazada por contener el código del consultorio
- **ENTONCES** ninguna salida contiene la contraseña, `$argon2`, `@`, `ficticio-a` ni `postgresql`

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

### Requirement: Comando de credenciales mediante el servicio administrativo
El comando DEBE (MUST) documentarse y ejecutarse con `docker compose run --rm -it --no-deps admin python -m app.credenciales`, el único servicio que recibe `DATABASE_MIGRATION_URL`. Ejecutado con el servicio `api`, que no la recibe, DEBE (MUST) terminar con código distinto de cero y el mensaje que la menciona, sin abrir conexiones.

#### Scenario: Comando documentado con admin
- **CUANDO** se inspeccionan `README.md` y la ayuda del módulo `app.credenciales`
- **ENTONCES** el comando se indica con el servicio `admin` y no con `api`

#### Scenario: Ejecutado con el entorno de la API
- **DADO** `APP_ENV=local` y el entorno de la API, sin `DATABASE_MIGRATION_URL`
- **CUANDO** se ejecuta el comando
- **ENTONCES** termina con código distinto de cero y un mensaje que menciona `DATABASE_MIGRATION_URL`, sin abrir conexiones

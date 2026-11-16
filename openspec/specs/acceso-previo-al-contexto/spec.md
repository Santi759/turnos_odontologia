# acceso-previo-al-contexto Specification

## Purpose
Permitir que el login y la resolución de la sesión funcionen antes de conocer el consultorio, bajo RLS y con roles de conexión sin privilegios, mediante un conjunto mínimo de funciones de la base repartidas entre un rol de login y el rol de aplicación, con entradas validadas, sin selectores de identificadores libres, sin que el rol de aplicación pueda leer ni escribir credenciales y sin que ningún rol del camino de login pueda escribirlas.

Convenciones de los escenarios: PostgreSQL 18 real en `db-test` (X2) y datos ficticios (D1). "Funciones de acceso" son las funciones del esquema `acceso`; "rol de aplicación" es `turnos_app`; "rol de login" es `turnos_login`; "funciones de login" son `buscar_cuenta`, `registrar_fallo`, `fallos_de_cuenta`, `fallos_de_ip`, `descartar_fallos_de_cuenta` y `limpiar_intentos`, del dueño `turnos_acceso_login`; "funciones de sesión" son `resolver_sesion`, `renovar_sesion`, `revocar_sesion_por_token` y `limpiar_sesiones`, del dueño `turnos_acceso_previo`. "Clave HMAC" es un valor de exactamente 32 bytes. "Versión de la fila" es su `xmin`, que cambia con cualquier `UPDATE`. Los escenarios con un rol usan conexiones reales autenticadas como ese rol.

## Requirements

### Requirement: Funciones de acceso con privilegios mínimos
Cada función de acceso DEBE (MUST) estar en el esquema `acceso`, ser `SECURITY DEFINER` de su dueño, fijar `search_path` a `pg_catalog, pg_temp`, nombrar los objetos con su esquema y no usar SQL dinámico. `PUBLIC` NO DEBE (MUST NOT) poder ejecutarlas ni crear objetos en `acceso`; cada función DEBE (MUST) conceder `EXECUTE` a exactamente un rol, y el conjunto de funciones DEBE (MUST) ser exactamente el de las convenciones.

#### Scenario: Catálogo de las funciones
- **CUANDO** se consultan en el catálogo las funciones del esquema `acceso`
- **ENTONCES** cada una tiene el dueño que le corresponde, `prosecdef` verdadero y `proconfig` con `search_path=pg_catalog, pg_temp`
- **Y** su lista de control de acceso no concede `EXECUTE` a `PUBLIC` y lo concede a un único rol

#### Scenario: Conjunto exacto de funciones
- **CUANDO** se listan las funciones del esquema `acceso`
- **ENTONCES** son exactamente las 6 funciones de login y las 4 funciones de sesión

#### Scenario: Rol sin concesión rechazado
- **DADO** un rol de prueba con `LOGIN` sin concesiones creado para la prueba
- **CUANDO** ejecuta cualquier función de acceso
- **ENTONCES** falla por falta de privilegios

#### Scenario: Esquema sin creación de objetos
- **CUANDO** el rol de aplicación o el rol de login intentan crear una función en el esquema `acceso`
- **ENTONCES** falla por falta de privilegios

### Requirement: Funciones repartidas entre el rol de login y el rol de aplicación
Solo el rol de login DEBE (MUST) ejecutar las funciones de login, y solo el rol de aplicación las funciones de sesión. El dueño de las funciones de sesión NO DEBE (MUST NOT) tener privilegios sobre `usuario.credencial` ni sobre `intento_login`, de modo que ninguna función que ejecute el rol de aplicación pueda leer ni escribir credenciales.

#### Scenario: El rol de aplicación no ejecuta funciones de login
- **CUANDO** el rol de aplicación ejecuta cada una de las 6 funciones de login con argumentos válidos
- **ENTONCES** cada llamada falla por falta de privilegios y no cambia ninguna fila

#### Scenario: El rol de login no ejecuta funciones de sesión
- **CUANDO** el rol de login ejecuta cada una de las 4 funciones de sesión con argumentos válidos
- **ENTONCES** cada llamada falla por falta de privilegios

#### Scenario: Dueño de las funciones de sesión sin credenciales
- **CUANDO** se consultan en el catálogo los privilegios de `turnos_acceso_previo`
- **ENTONCES** no tiene `SELECT` ni `UPDATE` sobre `usuario.credencial` ni ningún privilegio sobre `intento_login`

### Requirement: Funciones sin identificadores libres y de una fila
Las funciones de acceso NO DEBEN (MUST NOT) recibir identificadores de consultorio, usuario ni sesión: seleccionan por código y email, HMAC del token o clave HMAC de intento. Cada llamada DEBE (MUST) devolver como máximo una fila, y una clave HMAC de longitud distinta de 32 bytes DEBE (MUST) producir un error sin efectos.

#### Scenario: Sin parámetros de identificador
- **CUANDO** se consultan los tipos de los parámetros de entrada de las funciones de acceso
- **ENTONCES** ninguna tiene parámetros `uuid` y ninguna devuelve un conjunto de filas (`proretset` falso)

#### Scenario: HMAC de longitud inválida
- **CUANDO** el rol de aplicación resuelve una sesión, o el rol de login registra un fallo, con un valor de 31 o de 33 bytes
- **ENTONCES** la llamada falla con un error y no se modifica ninguna fila

### Requirement: Búsqueda de cuenta sin credenciales de cuentas no utilizables
La búsqueda de cuenta por código de consultorio y email, ejecutable solo por el rol de login, DEBE (MUST) devolver como máximo una cuenta con su consultorio y su usuario, y su credencial solo si el usuario y el consultorio están activos y la credencial no es nula; en otro caso la credencial DEBE (MUST) volver nula y el login DEBE (MUST) verificar igualmente contra el hash ficticio.

#### Scenario: Cuenta activa con credencial
- **CUANDO** el rol de login busca la cuenta de `persona.ficticia@example.test` en A, activa y con credencial
- **ENTONCES** obtiene una fila con el `id` de A, el `id` del usuario, su rol, su estado y su credencial

#### Scenario: Cuenta inactiva
- **DADO** el usuario de A desactivado
- **CUANDO** se busca su cuenta
- **ENTONCES** la fila devuelta tiene la credencial nula y el login responde con el rechazo genérico

#### Scenario: Consultorio inactivo
- **DADO** el consultorio A desactivado y su usuario activo con credencial
- **CUANDO** se busca la cuenta del usuario
- **ENTONCES** la fila devuelta tiene la credencial nula

#### Scenario: Cuenta sin credencial con verificación ficticia
- **DADO** un usuario de A con credencial nula
- **CUANDO** se evalúa su login
- **ENTONCES** el verificador se ejecuta exactamente una vez contra el hash ficticio y la respuesta es el rechazo genérico

#### Scenario: Cuenta inexistente
- **CUANDO** se busca una cuenta con un código o un email que no existen
- **ENTONCES** no se devuelve ninguna cuenta

### Requirement: Camino de login sin escritura de credenciales
Ninguna función ejecutable por el rol de login DEBE (MUST) escribir `usuario`, y ni el rol de login ni el dueño de esas funciones DEBEN (MUST) tener `INSERT`, `UPDATE` ni `DELETE` sobre `usuario` (tampoco por columna sobre `credencial`). La función de rehash de la primera revisión NO DEBE (MUST NOT) existir. El rol de login solo DEBE (MUST) leer el hash mediante la búsqueda de cuenta, y la escritura de credenciales DEBE (MUST) quedar fuera de la API.

#### Scenario: Dueño de las funciones de login sin escritura en usuario
- **CUANDO** se consultan en el catálogo los privilegios de `turnos_acceso_login` y de `turnos_login` sobre `usuario`
- **ENTONCES** ninguno tiene `INSERT`, `UPDATE` ni `DELETE` de tabla ni `UPDATE` de la columna `credencial`

#### Scenario: Ninguna función ejecutable por el rol de login escribe usuario
- **CUANDO** se recorren en `pg_proc` todas las funciones que el rol de login puede ejecutar y se evalúan los privilegios de su dueño
- **ENTONCES** ningún dueño tiene `UPDATE` sobre `usuario` ni sobre `usuario.credencial` y ninguna es la función de rehash

#### Scenario: Función de rehash inexistente
- **CUANDO** se busca `acceso.reemplazar_credencial_por_rehash` en el catálogo y el rol de login intenta ejecutarla
- **ENTONCES** no existe y la llamada falla sin cambiar ninguna fila

#### Scenario: Administración de credenciales fuera de la API
- **CUANDO** se buscan en el código de la aplicación las sentencias que escriben `usuario.credencial` y los módulos que las importan
- **ENTONCES** solo existen en el módulo de consultas de los comandos locales y ninguna ruta, dependencia ni módulo de autenticación lo importa

#### Scenario: Credencial intacta tras logins con los roles de conexión
- **DADO** el usuario de A con un hash Argon2id con `t=2`
- **CUANDO** inicia sesión con la contraseña correcta y luego con una incorrecta
- **ENTONCES** las respuestas son 200 y 401, y la credencial y la versión de la fila del usuario no cambian

### Requirement: Sesión resuelta por el HMAC del token
Resolver, renovar y revocar una sesión antes de conocer el consultorio DEBE (MUST) hacerse solo por el HMAC del token y solo con el rol de aplicación. La resolución NO DEBE (MUST NOT) devolver el HMAC ni la credencial. Ni el rol de aplicación ni el rol de login DEBEN (MUST) poder leer `sesion.token_hmac` directamente.

#### Scenario: Sesión existente
- **DADO** una sesión de A
- **CUANDO** el rol de aplicación la resuelve por el HMAC de su token sin contexto
- **ENTONCES** obtiene una fila con la sesión, su usuario, rol y consultorio, sin `token_hmac` ni credencial

#### Scenario: HMAC desconocido
- **CUANDO** el rol de aplicación resuelve un HMAC de 32 bytes que no corresponde a ninguna sesión
- **ENTONCES** no obtiene ninguna fila

#### Scenario: Revocación de la sesión entrante de otro consultorio
- **DADO** una sesión válida de B en la cookie y un login exitoso en A
- **CUANDO** termina el login
- **ENTONCES** la sesión de B queda revocada como en C-03

### Requirement: Intentos de login solo mediante funciones
Registrar, contar, descartar y limpiar intentos DEBE (MUST) hacerse solo mediante funciones de login, ejecutadas por el rol de login. Contar DEBE (MUST) devolver solo los instantes recientes de la clave HMAC indicada, como máximo 5 por cuenta y 30 por IP, sin claves ni filas de otras claves. Ningún rol de conexión DEBE (MUST) acceder a `intento_login` directamente.

#### Scenario: Sin acceso directo a la tabla
- **CUANDO** el rol de aplicación o el rol de login consultan, insertan, modifican o borran en `intento_login`
- **ENTONCES** cada sentencia falla por falta de privilegios

#### Scenario: Conteo limitado a la clave indicada
- **DADO** 7 fallos recientes de la clave de cuenta K1 y 3 de K2
- **CUANDO** el rol de login cuenta los fallos de K1
- **ENTONCES** obtiene solo los 5 instantes más recientes de K1, sin claves

#### Scenario: Control de intentos de C-03 conservado
- **CUANDO** se ejecutan con los roles de conexión el bloqueo por cuenta, el límite por IP y el descarte tras un éxito
- **ENTONCES** las respuestas y los conteos coinciden con los de `control-intentos-login`

### Requirement: Instantes acotados en funciones de escritura
Las funciones que registran fallos, renuevan o revocan sesiones o limpian filas DEBEN (MUST) rechazar un instante posterior en más de 5 minutos al reloj de la base, y la limpieza DEBE (MUST) borrar como máximo 100 filas por llamada.

#### Scenario: Instante futuro rechazado
- **CUANDO** el rol de login limpia intentos, o el rol de aplicación limpia sesiones, con un instante una hora posterior al reloj de la base
- **ENTONCES** la llamada falla con un error y no borra filas

#### Scenario: Límite por llamada
- **DADO** 150 intentos de más de 24 horas
- **CUANDO** el rol de login limpia intentos con el instante actual
- **ENTONCES** se borran exactamente 100

### Requirement: Contexto fijado solo tras verificar la contraseña
Durante el login, el contexto de la base DEBE (MUST) permanecer vacío hasta que la contraseña se verifique con éxito para una cuenta activa; entonces DEBE (MUST) fijarse, solo en la transacción que crea la sesión, al consultorio que devolvió la búsqueda de esa cuenta. Un login rechazado NO DEBE (MUST NOT) fijar contexto.

#### Scenario: Sesión creada en el consultorio de la cuenta
- **CUANDO** el usuario de A inicia sesión con los roles de conexión
- **ENTONCES** la sesión creada tiene el `consultorio_id` de A

#### Scenario: Login rechazado sin contexto
- **CUANDO** un login con contraseña incorrecta termina con 401
- **ENTONCES** ninguna sentencia de esa petición se ejecutó con contexto distinto de vacío y no se abrió la transacción de sesión

### Requirement: Login en dos transacciones con roles distintos
El login DEBE (MUST) evaluar bloqueos, buscar la cuenta, verificar la contraseña con los locks de cuenta e IP tomados, registrar fallos y descartarlos en una transacción del rol de login, y confirmarla antes de crear la sesión en otra transacción del rol de aplicación. Las dos transacciones NO DEBEN (MUST NOT) compartir conexión ni coexistir, y la de sesión solo DEBE (MUST) abrirse tras una verificación exitosa.

#### Scenario: Rol de cada transacción
- **CUANDO** se registra el `current_user` de cada sentencia de un login exitoso
- **ENTONCES** las de credenciales e intentos usan `turnos_login`, las de sesión usan `turnos_app` y las primeras terminan antes de que empiecen las segundas

#### Scenario: Fallo al crear la sesión
- **DADO** cuatro fallos recientes del par de A y un fallo inyectado en la creación de la sesión tras una verificación exitosa
- **CUANDO** termina el login
- **ENTONCES** la respuesta es un error genérico sin cookie ni sesión creada, los cuatro fallos quedan descartados para la cuenta y la credencial no cambia
- **Y** un login posterior con la misma contraseña responde 200

#### Scenario: Sin contaminación entre logins
- **DADO** motores con una sola conexión en cada pool
- **CUANDO** se hacen dos logins seguidos de A y de B
- **ENTONCES** cada sesión queda en su consultorio y ninguna conexión de los pools conserva un contexto

#### Scenario: Verificación con los locks tomados
- **DADO** un verificador de prueba que registra, al ejecutarse, los locks consultivos que tiene la conexión del rol de login
- **CUANDO** se evalúa un login
- **ENTONCES** la verificación corre dentro de la transacción del rol de login con los locks de cuenta y de IP tomados, y sin ninguna conexión del rol de aplicación abierta por la petición

#### Scenario: Conteo atómico con los roles de conexión
- **CUANDO** se lanzan 10 logins concurrentes con contraseña incorrecta del mismo par desde la misma dirección con los roles de conexión
- **ENTONCES** exactamente 5 responden 401 y 5 responden 429, y quedan 5 fallos registrados

### Requirement: Pool de conexiones del login acotado
El rol de login DEBE (MUST) usar un pool de conexiones propio y acotado, separado del de la aplicación. Si un login no obtiene conexión de ese pool dentro de su tiempo de espera, DEBE (MUST) responder 503 con el cuerpo de servicio ocupado, `Retry-After: 5` y `Cache-Control: no-store` y revertir su transacción, y NO DEBE (MUST NOT) registrar un fallo ni crear sesión. Al terminar los logins NO DEBEN (MUST NOT) quedar conexiones prestadas ni locks consultivos tomados.

#### Scenario: Pool de login agotado
- **DADO** un motor de login de prueba con una sola conexión, sin desborde, un tiempo de espera de 0,2 segundos y su única conexión retenida por la prueba
- **CUANDO** se hace un login con contraseña incorrecta de una cuenta existente
- **ENTONCES** responde 503 con el cuerpo de servicio ocupado, `Retry-After: 5` y `Cache-Control: no-store`
- **Y** no se ejecutó el verificador, no hay filas nuevas en `intento_login` ni sesión creada
- **Y** liberada la conexión, un login siguiente se evalúa y responde 401

#### Scenario: Concurrencia con la configuración real de los pools
- **DADO** la API con la configuración real de los pools de login y de aplicación y conexiones reales de los roles
- **CUANDO** se lanzan 40 logins concurrentes con contraseña incorrecta desde la misma dirección sobre 40 pares distintos, sin fallos previos
- **ENTONCES** exactamente 30 responden 401 y 10 responden 429

#### Scenario: Sin conexiones ni locks retenidos
- **DADO** la API con la configuración real de los pools
- **CUANDO** terminan logins concurrentes que responden 401, 429 y 503
- **ENTONCES** ninguno de los dos pools tiene conexiones prestadas y no queda ningún lock consultivo tomado por los roles de conexión

# modelo-consultorios-usuarios Specification

## Purpose
Definir el modelo base multi-consultorio persistido en PostgreSQL: las tablas `consultorio` y `usuario`, sus valores por defecto, identificadores y restricciones de integridad, sobre las que se construyen la autenticación (C-03) y el aislamiento entre consultorios (C-04).

Convenciones de los escenarios: todas las pruebas de esta capacidad se ejecutan contra PostgreSQL 18 real en la base de pruebas efímera `db-test`, nunca contra un sustituto (X2), y solo con datos ficticios (D1), por ejemplo el consultorio "Consultorio Ficticio A" y el email `persona.ficticia@example.test`. Cada prueba deshace sus cambios al terminar.

## Requirements

### Requirement: Consultorio con valores por defecto
La base DEBE (MUST) tener una tabla `consultorio` con `id`, `nombre`, `codigo`, `zona_horaria`, `anticipacion_cancelacion_horas`, `activo` y `creado_en`, todos obligatorios. Si una inserción indica `nombre` y `codigo`, la base DEBE (MUST) completar `id` con un UUIDv7 generado por PostgreSQL, `zona_horaria = 'America/Argentina/Buenos_Aires'`, `anticipacion_cancelacion_horas = 24`, `activo = true` y `creado_en` con el instante actual con zona horaria (RN-GL-01).

#### Scenario: Valores por defecto al insertar solo el nombre
Se conserva el nombre del escenario de C-02 con contenido actualizado: desde C-03 `codigo` es obligatorio y sin valor por defecto, así que la inserción indica `nombre` y `codigo`.
- **DADO** que se aplicaron las migraciones en la base de pruebas
- **CUANDO** se inserta un consultorio indicando solo `nombre = 'Consultorio Ficticio A'` y `codigo = 'ficticio-a'`
- **ENTONCES** la fila tiene `zona_horaria = 'America/Argentina/Buenos_Aires'`, `anticipacion_cancelacion_horas = 24` y `activo = true`
- **Y** `creado_en` es de tipo `timestamp with time zone` y no es nulo
- **Y** `id` es un UUID de versión 7 y `codigo` conserva `ficticio-a`

#### Scenario: La zona horaria por defecto es válida para PostgreSQL
- **CUANDO** se busca el valor por defecto de `zona_horaria` en `pg_timezone_names`
- **ENTONCES** figura exactamente una vez

#### Scenario: Nombre obligatorio
- **CUANDO** se inserta un consultorio con `codigo = 'ficticio-a'` y sin `nombre`
- **ENTONCES** la inserción falla por violación de `NOT NULL` en la columna `nombre`

### Requirement: Anticipación de cancelación no negativa
La base DEBE (MUST) rechazar un consultorio con `anticipacion_cancelacion_horas` menor que cero y DEBE (MUST) aceptar el valor cero.

#### Scenario: Anticipación negativa rechazada
- **CUANDO** se inserta un consultorio con `anticipacion_cancelacion_horas = -1`
- **ENTONCES** la inserción falla por violación de una restricción `CHECK`

#### Scenario: Anticipación cero aceptada
- **CUANDO** se inserta un consultorio con `anticipacion_cancelacion_horas = 0`
- **ENTONCES** la inserción es exitosa

### Requirement: Identificadores UUIDv7 generados por la base
Los `id` de `consultorio` y `usuario` DEBEN (MUST) ser de tipo `uuid` y, si la inserción no los indica, DEBEN (MUST) ser generados por PostgreSQL como UUID versión 7. Los identificadores no secuenciales NO DEBEN (MUST NOT) considerarse una barrera de autorización ni de aislamiento.

#### Scenario: Id de consultorio generado por el servidor
- **CUANDO** se inserta un consultorio sin indicar `id`
- **ENTONCES** el `id` devuelto es un UUID de versión 7

#### Scenario: Id de usuario generado por el servidor
- **DADO** un consultorio existente
- **CUANDO** se inserta un usuario de ese consultorio sin indicar `id`
- **ENTONCES** el `id` devuelto es un UUID de versión 7
- **Y** es distinto del `id` del consultorio

### Requirement: Usuario perteneciente a un único consultorio
La base DEBE (MUST) tener una tabla `usuario` con `id`, `consultorio_id`, `email`, `nombre`, `credencial`, `rol`, `activo` y `creado_en`. `consultorio_id` DEBE (MUST) ser obligatorio y referenciar un consultorio existente; borrar un consultorio con usuarios DEBE (MUST) fallar. Cada usuario pertenece a un solo consultorio (SU-02); `activo` vale `true` y `creado_en` el instante actual si no se indican.

#### Scenario: Usuario con consultorio inexistente rechazado
- **CUANDO** se inserta un usuario con un `consultorio_id` que no existe
- **ENTONCES** la inserción falla por violación de clave foránea

#### Scenario: Usuario sin consultorio rechazado
- **CUANDO** se inserta un usuario sin `consultorio_id`
- **ENTONCES** la inserción falla por violación de `NOT NULL`

#### Scenario: Borrado de consultorio con usuarios restringido
- **DADO** un consultorio con un usuario
- **CUANDO** se borra el consultorio
- **ENTONCES** el borrado falla por violación de clave foránea
- **Y** el consultorio y el usuario siguen existiendo

#### Scenario: Valores por defecto del usuario
- **DADO** un consultorio existente
- **CUANDO** se inserta un usuario indicando solo `consultorio_id`, `email`, `nombre` y `rol`
- **ENTONCES** la fila tiene `activo = true`, `credencial` nula y `creado_en` no nulo de tipo `timestamp with time zone`

### Requirement: Ancla compuesta de consultorio e identificador
La tabla `usuario` DEBE (MUST) tener una restricción de unicidad sobre `(consultorio_id, id)` para que futuras tablas puedan referenciar a un usuario con una clave foránea compuesta que garantice el mismo consultorio (RN-MT-03).

#### Scenario: Restricción de unicidad compuesta presente
- **CUANDO** se consultan las restricciones `UNIQUE` de la tabla `usuario` en el catálogo
- **ENTONCES** existe una cuyas columnas son exactamente `consultorio_id` e `id`, en ese orden

### Requirement: Rol restringido a los valores admitidos
La columna `rol` DEBE (MUST) ser texto y aceptar solo `administrador`, `secretaria` u `odontologo`, en minúsculas y sin tildes. Cualquier otro valor DEBE (MUST) rechazarse en la base.

#### Scenario: Roles admitidos aceptados
- **DADO** un consultorio existente
- **CUANDO** se insertan tres usuarios con rol `administrador`, `secretaria` y `odontologo`
- **ENTONCES** las tres inserciones son exitosas

#### Scenario: Rol no admitido rechazado
- **CUANDO** se inserta un usuario con rol `secretaría` (con tilde), `Administrador` o `paciente`
- **ENTONCES** cada inserción falla por violación de una restricción `CHECK`

### Requirement: Email único por consultorio y normalizado
El `email` de un usuario DEBE (MUST) almacenarse normalizado (sin espacios al inicio o al final, en minúsculas y no vacío) y DEBE (MUST) ser único dentro de cada consultorio. El mismo email DEBE (MUST) poder existir en consultorios distintos como cuentas separadas (DC-06).

#### Scenario: Mismo email en dos consultorios
- **DADO** los consultorios ficticios A y B
- **CUANDO** se inserta un usuario con `persona.ficticia@example.test` en A y otro con el mismo email en B
- **ENTONCES** ambas inserciones son exitosas

#### Scenario: Email repetido en el mismo consultorio rechazado
- **DADO** un usuario con `persona.ficticia@example.test` en el consultorio A
- **CUANDO** se inserta otro usuario con el mismo email en A
- **ENTONCES** la inserción falla por violación de unicidad

#### Scenario: Email no normalizado rechazado por la base
- **CUANDO** se inserta directamente un usuario con email `Persona.Ficticia@Example.test`, ` persona.ficticia@example.test` o la cadena vacía
- **ENTONCES** cada inserción falla por violación de una restricción `CHECK`

### Requirement: Usuario sin credencial utilizable
La base DEBE (MUST) permitir un usuario **sin credencial**, con `credencial` nula, y DEBE (MUST) rechazar una credencial vacía. Una credencial no nula DEBE (MUST) ser un hash de contraseña, nunca texto plano; solo la escribe el comando local de credenciales; ningún rol de la API la modifica (C-04). La base NO DEBE (MUST NOT) restringir el prefijo del hash con un `CHECK`: los formatos los valida la aplicación (DA-08). Un usuario sin credencial DEBE (MUST) tratarse como imposible de autenticar.

#### Scenario: Usuario sin credencial aceptado
- **DADO** un consultorio existente
- **CUANDO** se inserta un usuario sin `credencial`
- **ENTONCES** la inserción es exitosa y `credencial` es nula

#### Scenario: Credencial vacía rechazada
- **CUANDO** se inserta un usuario con `credencial = ''`
- **ENTONCES** la inserción falla por violación de una restricción `CHECK`

#### Scenario: Sin restricción de prefijo en la base
- **CUANDO** se listan las restricciones `CHECK` de `usuario` en el catálogo
- **ENTONCES** ninguna menciona `argon2`

### Requirement: Migración del modelo base reversible y sin datos
La migración del modelo base DEBE (MUST) tener la revisión `0002` y depender de `0001`; DEBE (MUST) crear ambas tablas sin insertar filas y su reversión a `0001` DEBE (MUST) eliminarlas conservando `btree_gist`. La reversión solo DEBE (MUST) ejecutarse contra la base de pruebas. Desde C-03, la revisión siguiente es `0003`.

#### Scenario: Cadena de revisiones
- **CUANDO** se inspecciona el historial de migraciones del repositorio
- **ENTONCES** la revisión `0002` tiene como revisión anterior `0001` y como siguiente `0003`

#### Scenario: Subida desde 0001 crea las tablas vacías
- **DADO** la base de pruebas en la revisión `0001`
- **CUANDO** se sube a `head`
- **ENTONCES** existen las tablas `consultorio` y `usuario`
- **Y** ambas tienen cero filas

#### Scenario: Bajada a 0001 elimina las tablas y conserva la extensión
- **DADO** la base de pruebas en `head`
- **CUANDO** se baja a la revisión `0001`
- **ENTONCES** no existen las tablas `consultorio` ni `usuario`
- **Y** `btree_gist` sigue instalada
- **Y** al volver a subir a `head` las tablas existen de nuevo

### Requirement: Modelos coherentes con la migración
Los modelos de la aplicación DEBEN (MUST) describir exactamente las tablas, columnas, claves y restricciones que crean las migraciones (`consultorio`, `usuario`, `sesion` e `intento_login`), de modo que una comparación automática entre los modelos registrados y la base migrada no encuentre diferencias. Los nombres de las restricciones DEBEN (MUST) seguir la convención de nombres del proyecto. `Consultorio.codigo` DEBE (MUST) declararse obligatorio y sin valor por defecto de servidor.

#### Scenario: Sin diferencias entre modelos y base migrada
- **DADO** la base de pruebas en `head`
- **CUANDO** se comparan los metadatos de los modelos registrados con la base
- **ENTONCES** la comparación no informa diferencias

#### Scenario: Nombres de restricciones según la convención
- **CUANDO** se listan las restricciones de `consultorio`, `usuario`, `sesion` e `intento_login` en el catálogo
- **ENTONCES** la clave primaria se llama `pk_<tabla>`, las claves foráneas empiezan con `fk_`, las de unicidad con `uq_` y las de verificación con `ck_`

### Requirement: Código de consultorio indicado en cada inserción
Desde C-03, `consultorio.codigo` NO DEBE (MUST NOT) tener valor por defecto en la base ni completarse con disparadores o funciones: toda inserción DEBE (MUST) indicarlo (la aplicación con la función compartida de derivación, el seed con literales explícitos o una prueba con un valor ficticio).

#### Scenario: Código obligatorio
- **CUANDO** se inserta un consultorio indicando solo `nombre = 'Consultorio Ficticio A'`
- **ENTONCES** la inserción falla por violación de `NOT NULL` en la columna `codigo`

### Requirement: Código de consultorio único y normalizado
`consultorio.codigo` DEBE (MUST) ser obligatorio, único y normalizado: entre 3 y 40 caracteres, solo minúsculas ASCII, dígitos y guiones, sin guion al inicio ni al final. La base DEBE (MUST) rechazar un código que no cumpla el formato (`ck_consultorio_codigo_formato`) o que esté repetido (`uq_consultorio_codigo`). El código identifica al consultorio en el login; no es un secreto ni una barrera de autorización.

#### Scenario: Código válido aceptado
- **CUANDO** se insertan consultorios con códigos `ficticio-a`, `c01` y uno de 40 caracteres válidos
- **ENTONCES** las tres inserciones son exitosas

#### Scenario: Código con formato inválido rechazado
- **CUANDO** se inserta un consultorio con código `Ficticio-A`, ` ficticio-a`, `-ficticio`, `ficticio-`, `fi`, `ficticio_a`, `ficticio.a` o uno de 41 caracteres
- **ENTONCES** cada inserción falla por violación de una restricción `CHECK`

#### Scenario: Código repetido rechazado
- **DADO** un consultorio con código `ficticio-a`
- **CUANDO** se inserta otro con el mismo código
- **ENTONCES** la inserción falla por violación de `uq_consultorio_codigo`

#### Scenario: Código explícito respetado
- **CUANDO** se inserta un consultorio indicando `codigo = 'ficticio-a'`
- **ENTONCES** conserva `ficticio-a`

### Requirement: Código de consultorio derivado del identificador
La aplicación DEBE (MUST) derivar el código con una única función pura compartida: corto = `c-` + los últimos 12 dígitos hexadecimales en minúsculas del `id`; largo = `c-` + sus 32 dígitos hexadecimales. La regla NO DEBE (MUST NOT) depender del nombre ni de otros datos y DEBE (MUST) coincidir con la expresión SQL del backfill de `0003`. La base NO DEBE (MUST NOT) tener disparadores ni funciones propias para el código.

#### Scenario: Código derivado corto y largo
- **CUANDO** se derivan los códigos del `id` `01a1a95a-dd90-73e7-9496-c7d08d776d19`
- **ENTONCES** el corto es `c-c7d08d776d19` y el largo es `c-01a1a95add9073e79496c7d08d776d19`

#### Scenario: Equivalencia SQL/Python
- **DADO** 1000 UUID aleatorios de versión 4 y de versión 7
- **CUANDO** se calcula para cada uno el código corto y el largo con la función de la aplicación y con las expresiones SQL del backfill de `0003` en la base de pruebas
- **ENTONCES** ambos resultados coinciden para todos los UUID

#### Scenario: Sin disparadores ni funciones para el código
- **DADO** la base de pruebas en `head`
- **CUANDO** se consultan en el catálogo los disparadores de `consultorio` y las funciones del esquema `public` que no pertenecen a una extensión
- **ENTONCES** no hay ninguno

### Requirement: Alta de consultorio con reintento ante colisión
El alta de consultorios de la aplicación DEBE (MUST) obtener el `id` de PostgreSQL (`uuidv7()`) e insertar `id`, `nombre` y el código corto juntos dentro de un savepoint. Si la inserción viola `uq_consultorio_codigo` (SQLSTATE `23505` con ese nombre), DEBE (MUST) revertir el savepoint y reintentar una única vez con el código largo; si este también la viola, DEBE (MUST) fallar con un error controlado sin insertar filas. La transacción del llamador DEBE (MUST) seguir utilizable.

#### Scenario: Alta asigna el código corto
- **CUANDO** se da de alta un consultorio con nombre `Consultorio Ficticio A`
- **ENTONCES** su `id` es un UUID de versión 7 generado por PostgreSQL y su código es el código corto derivado de ese `id`

#### Scenario: El nombre no influye
- **CUANDO** se dan de alta dos consultorios con el mismo nombre
- **ENTONCES** cada uno recibe el código corto derivado de su propio `id` y los códigos son distintos

#### Scenario: Alta con colisión reintenta con el código largo
- **DADO** un consultorio existente con código `c-c7d08d776d19`
- **CUANDO** se da de alta un consultorio cuyo `id` (fuente de ids inyectada en la prueba) es `01a1a95a-dd90-7000-8000-c7d08d776d19`
- **ENTONCES** su código es `c-01a1a95add9070008000c7d08d776d19`
- **Y** el consultorio existente no cambia
- **Y** una consulta posterior en la misma transacción se ejecuta sin error

#### Scenario: Colisión también del código largo
- **DADO** un consultorio con código `c-c7d08d776d19` y otro con código `c-01a1a95add9070008000c7d08d776d19`
- **CUANDO** se da de alta un consultorio cuyo `id` inyectado es `01a1a95a-dd90-7000-8000-c7d08d776d19`
- **ENTONCES** el alta falla con el error controlado de código no disponible
- **Y** no existe ningún consultorio con ese `id`, los existentes no cambian y la transacción del llamador sigue utilizable

### Requirement: Solo la colisión de código provoca el reintento
Cualquier violación de integridad del alta distinta de `uq_consultorio_codigo` (clave primaria, otra unicidad, `CHECK`, `NOT NULL` o clave foránea) DEBE (MUST) propagarse sin cambios y sin reintento con el código largo.

#### Scenario: Otra violación de integridad no se confunde con colisión
- **DADO** un consultorio existente con `id` `01a1a95a-dd90-73e7-9496-c7d08d776d19`
- **CUANDO** se da de alta un consultorio cuyo `id` inyectado es ese mismo `id`
- **ENTONCES** se propaga la violación de integridad original, con la restricción `pk_consultorio`
- **Y** no se intentó la inserción con el código largo y no se agregó ninguna fila
- **Y** un alta con `nombre` nulo propaga la violación de `NOT NULL` sin reintento

### Requirement: Backfill determinista del código en la migración 0003
Al subir a `0003`, cada consultorio existente DEBE (MUST) recibir el código derivado de su `id` con la misma regla, expresada en SQL en línea sin crear funciones ni disparadores; ante colisiones del código corto, el consultorio de menor `id` conserva el corto y los demás reciben el largo. El resultado DEBE (MUST) ser único, cumplir el formato y no depender de nombres ni registros del seed.

#### Scenario: Backfill de consultorios existentes
- **DADO** la base de pruebas en `0002` con los consultorios de `id` `01a1a95a-dd90-73e7-9496-c7d08d776d19` y `01a1a95a-dd90-73e7-9496-c7d1647cab52`
- **CUANDO** se sube a `0003`
- **ENTONCES** sus códigos son `c-c7d08d776d19` y `c-c7d1647cab52`

#### Scenario: Backfill con colisión resuelta de forma determinista
- **DADO** la base de pruebas en `0002` con consultorios de `id` `01a1a95a-dd90-73e7-9496-c7d08d776d19` y `01a1a95a-dd90-7000-8000-c7d08d776d19`
- **CUANDO** se sube a `0003`
- **ENTONCES** el de menor `id` (`01a1a95a-dd90-7000-8000-c7d08d776d19`) tiene `c-c7d08d776d19` y el otro tiene `c-01a1a95add9073e79496c7d08d776d19`
- **Y** repetir la bajada y la subida produce exactamente los mismos códigos

#### Scenario: Backfill sin consultorios
- **DADO** la base de pruebas en `0002` sin consultorios
- **CUANDO** se sube a `0003`
- **ENTONCES** la migración termina sin errores y `consultorio` sigue vacía

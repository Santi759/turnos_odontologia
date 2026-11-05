# Spec Delta: modelo-consultorios-usuarios

## Purpose

Definir el modelo base multi-consultorio persistido en PostgreSQL: las tablas `consultorio` y `usuario`, sus valores por defecto, identificadores y restricciones de integridad, sobre las que se construyen la autenticación (C-03) y el aislamiento entre consultorios (C-04).

Convenciones de los escenarios: todas las pruebas de esta capacidad se ejecutan contra PostgreSQL 18 real en la base de pruebas efímera `db-test`, nunca contra un sustituto (X2), y solo con datos ficticios (D1), por ejemplo el consultorio "Consultorio Ficticio A" y el email `persona.ficticia@example.test`. Cada prueba deshace sus cambios al terminar.

## ADDED Requirements

### Requirement: Consultorio con valores por defecto
La base DEBE (MUST) tener una tabla `consultorio` con `id`, `nombre`, `zona_horaria`, `anticipacion_cancelacion_horas`, `activo` y `creado_en`, todos obligatorios. Si una inserción solo indica `nombre`, la base DEBE (MUST) completar `zona_horaria = 'America/Argentina/Buenos_Aires'`, `anticipacion_cancelacion_horas = 24`, `activo = true` y `creado_en` con el instante actual con zona horaria (RN-GL-01).

#### Scenario: Valores por defecto al insertar solo el nombre
- **DADO** que se aplicaron las migraciones en la base de pruebas
- **CUANDO** se inserta un consultorio indicando solo `nombre = 'Consultorio Ficticio A'`
- **ENTONCES** la fila tiene `zona_horaria = 'America/Argentina/Buenos_Aires'`, `anticipacion_cancelacion_horas = 24` y `activo = true`
- **Y** `creado_en` es de tipo `timestamp with time zone` y no es nulo

#### Scenario: La zona horaria por defecto es válida para PostgreSQL
- **CUANDO** se busca el valor por defecto de `zona_horaria` en `pg_timezone_names`
- **ENTONCES** figura exactamente una vez

#### Scenario: Nombre obligatorio
- **CUANDO** se inserta un consultorio sin `nombre`
- **ENTONCES** la inserción falla por violación de `NOT NULL`

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
La base DEBE (MUST) permitir un usuario **sin credencial**, representado con `credencial` nula, y DEBE (MUST) rechazar una credencial vacía. Este Change NO DEBE (MUST NOT) almacenar contraseñas ni hashes. Un usuario sin credencial DEBE (MUST) tratarse como imposible de autenticar.

#### Scenario: Usuario sin credencial aceptado
- **DADO** un consultorio existente
- **CUANDO** se inserta un usuario sin `credencial`
- **ENTONCES** la inserción es exitosa y `credencial` es nula

#### Scenario: Credencial vacía rechazada
- **CUANDO** se inserta un usuario con `credencial = ''`
- **ENTONCES** la inserción falla por violación de una restricción `CHECK`

### Requirement: Migración del modelo base reversible y sin datos
La migración del modelo base DEBE (MUST) tener la revisión `0002` y depender de `0001`; DEBE (MUST) crear ambas tablas sin insertar filas y su reversión a `0001` DEBE (MUST) eliminarlas conservando `btree_gist`. La reversión solo DEBE (MUST) ejecutarse contra la base de pruebas.

#### Scenario: Cadena de revisiones
- **CUANDO** se inspecciona el historial de migraciones del repositorio
- **ENTONCES** la revisión `head` es `0002` y su revisión anterior es `0001`

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
Los modelos de la aplicación DEBEN (MUST) describir exactamente las tablas, columnas, claves y restricciones que crea la migración, de modo que una comparación automática entre los modelos registrados y la base migrada no encuentre diferencias. Los nombres de las restricciones DEBEN (MUST) seguir la convención de nombres del proyecto.

#### Scenario: Sin diferencias entre modelos y base migrada
- **DADO** la base de pruebas en `head`
- **CUANDO** se comparan los metadatos de los modelos registrados con la base
- **ENTONCES** la comparación no informa diferencias

#### Scenario: Nombres de restricciones según la convención
- **CUANDO** se listan las restricciones de `consultorio` y `usuario` en el catálogo
- **ENTONCES** la clave primaria se llama `pk_<tabla>`, las claves foráneas empiezan con `fk_`, las de unicidad con `uq_` y las de verificación con `ck_`

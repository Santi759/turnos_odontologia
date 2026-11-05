# Spec Delta: base-de-datos-local

Justificación de la modificación: en C-01 la única migración era de infraestructura y el contrato exigía que no hubiera tablas de dominio ("Sin tablas de dominio": la única tabla es `alembic_version`). C-02 agrega la migración `0002` del modelo base (`consultorio` y `usuario`, capacidad `modelo-consultorios-usuarios`), por lo que ese contrato deja de ser verdadero por diseño. Se reemplaza por uno más estricto en lo que importa: las tablas que existen tras migrar son exactamente las del modelo aprobado, las migraciones no insertan datos y no ejecutan el seed. El resto del requisito (comando explícito, el arranque de la API no migra) no cambia.

## MODIFIED Requirements

### Requirement: Migraciones aplicadas solo por comando explícito
Las migraciones DEBEN (MUST) aplicarse únicamente mediante un comando explícito documentado; el arranque de la API NO DEBE (MUST NOT) ejecutarlas. Desde C-02 las migraciones son la de infraestructura (`0001`, habilitar `btree_gist`) y la del modelo base (`0002`, tablas `consultorio` y `usuario`); NO DEBEN (MUST NOT) crear otras tablas, NO DEBEN (MUST NOT) insertar filas en las tablas del modelo y NO DEBEN (MUST NOT) ejecutar el seed, que tiene su propio comando explícito.

#### Scenario: El comando explícito deja la base al día
- **DADO** una base sin migraciones aplicadas o con migraciones parciales
- **CUANDO** se ejecuta el comando explícito de migración
- **ENTONCES** la revisión actual registrada en la base coincide con la última revisión del repositorio

#### Scenario: El arranque de la API no migra
- **CUANDO** se inspecciona el comando de arranque efectivo del servicio `api` en la configuración resuelta de Docker Compose
- **ENTONCES** no invoca migraciones

#### Scenario: Sin tablas de dominio
Se conserva el nombre del escenario de C-01 (OpenSpec no admite renombrar escenarios en una delta) con contenido actualizado: "dominio" se refiere a las tablas de agenda, pacientes y turnos de Changes posteriores; `consultorio` y `usuario` son el modelo base aprobado en C-02.
- **DADO** que se aplicaron las migraciones
- **CUANDO** se listan las tablas del esquema `public`
- **ENTONCES** las tablas son exactamente `alembic_version`, `consultorio` y `usuario`

#### Scenario: Tablas del modelo base vacías tras migrar
- **DADO** que se aplicaron las migraciones
- **CUANDO** se cuentan las filas de `consultorio` y `usuario`
- **ENTONCES** ambas tienen cero filas

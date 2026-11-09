# Spec Delta: base-de-datos-local

## MODIFIED Requirements

### Requirement: Migraciones aplicadas solo por comando explícito
Las migraciones DEBEN (MUST) aplicarse solo mediante un comando explícito documentado; el arranque de la API NO DEBE (MUST NOT) ejecutarlas. Desde C-03 son `0001` (habilitar `btree_gist`), `0002` (tablas `consultorio` y `usuario`) y `0003` (columna `consultorio.codigo` y tablas `sesion` e `intento_login`, sin funciones ni disparadores). NO DEBEN (MUST NOT) crear otras tablas, insertar filas en ninguna tabla ni ejecutar el seed, que tiene su propio comando explícito.

#### Scenario: El comando explícito deja la base al día
- **DADO** una base sin migraciones aplicadas o con migraciones parciales
- **CUANDO** se ejecuta el comando explícito de migración
- **ENTONCES** la revisión actual registrada en la base coincide con la última revisión del repositorio

#### Scenario: El arranque de la API no migra
- **CUANDO** se inspecciona el comando de arranque efectivo del servicio `api` en la configuración resuelta de Docker Compose
- **ENTONCES** no invoca migraciones

#### Scenario: Sin tablas de dominio
Se conserva el nombre del escenario de C-01 (OpenSpec no admite renombrar escenarios en una delta) con contenido actualizado: "dominio" se refiere a las tablas de agenda, pacientes y turnos de Changes posteriores; `consultorio` y `usuario` son el modelo base de C-02, y `sesion` e `intento_login` son las tablas de autenticación de C-03.
- **DADO** que se aplicaron las migraciones
- **CUANDO** se listan las tablas del esquema `public`
- **ENTONCES** las tablas son exactamente `alembic_version`, `consultorio`, `intento_login`, `sesion` y `usuario`

#### Scenario: Tablas del modelo base vacías tras migrar
- **DADO** que se aplicaron las migraciones desde `base`
- **CUANDO** se cuentan las filas de `consultorio`, `usuario`, `sesion` e `intento_login`
- **ENTONCES** las cuatro tienen cero filas

## ADDED Requirements

### Requirement: Backfill de la migración 0003 limitado a la columna nueva
La única modificación de datos existentes que admiten las migraciones DEBE (MUST) ser el backfill de `consultorio.codigo` de `0003`, que solo escribe esa columna nueva (justificación: DA-03, aprobada por el autor el 2026-11-05). Aplicar `0003` sobre la base de desarrollo requiere autorización explícita del autor.

#### Scenario: El backfill solo escribe la columna nueva
- **DADO** la base de pruebas en `0002` con consultorios y usuarios ficticios
- **CUANDO** se sube a `0003`
- **ENTONCES** cada columna de `consultorio` existente en `0002` y cada columna de `usuario` conserva su valor
- **Y** la cantidad de filas de `consultorio` y de `usuario` no cambia

### Requirement: Plantilla de variables montada de solo lectura en api
El servicio `api` de Docker Compose DEBE (MUST) montar únicamente `.env.example` de solo lectura en `/repo/.env.example`, fuera de `/app`, para las pruebas de la plantilla. NO DEBE (MUST NOT) montar `.env` ni otro archivo de secretos.

#### Scenario: Montaje de solo lectura
- **CUANDO** se inspecciona la configuración resuelta de Compose
- **ENTONCES** `api` monta `.env.example` en `/repo/.env.example` con `read_only` verdadero
- **Y** ningún servicio monta `.env`

#### Scenario: Escritura rechazada
- **CUANDO** un proceso del contenedor `api` intenta escribir en `/repo/.env.example`
- **ENTONCES** la escritura falla por sistema de archivos de solo lectura

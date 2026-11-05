# Diseño: modelo-base-consultorios-seed

## Contexto

Motivación y alcance: ver `proposal.md`. Requisitos y escenarios: ver `specs/*/spec.md` (tres capacidades nuevas y la delta de `base-de-datos-local`).

Estado actual observado en el repositorio (2026-11-04, rama `main`, HEAD `188f064`, árbol limpio; C-01 archivado):

- `backend/app/models/base.py`: `Base(DeclarativeBase)` con `MetaData(naming_convention=CONVENCION_DE_NOMBRES)`; la convención de `uq` es `uq_%(table_name)s_%(column_0_name)s` (solo la primera columna) y la de `ck` usa `%(constraint_name)s`. `app/models/__init__.py` está vacío; no hay modelos.
- `backend/alembic/env.py` importa `app.models.base.Base` y usa `target_metadata = Base.metadata`; delega la URL en `resolver_url_de_migracion` (guardia de C-01). Única revisión: `0001` (`CREATE EXTENSION IF NOT EXISTS btree_gist`), con identificadores legibles.
- `backend/app/core/database.py`: `crear_engine`, `crear_engine_desde_url`, `verificar_conexion`, `validar_url_de_pruebas`. No hay fábrica de sesiones (C-01 DF-08 la dejó para el primer repositorio).
- `backend/app/core/config.py`: `Settings` con `database_url`, `test_database_url`, `cors_allowed_origins` y `app_env: Literal["local", "test"]`.
- `backend/app/schemas/base.py`: `EsquemaEntrada` con `extra="forbid"`. `app/repositories/` solo tiene `__init__.py`; `tests/isolation/` está vacía.
- `backend/tests/integration/`: `conftest.py` (fixture de sesión `motor` contra `db-test` con la guardia), `test_base_de_datos.py` (4 pruebas) y `test_migraciones.py` (5 pruebas, entre ellas `test_el_comando_explicito_deja_la_base_al_dia`, que baja a `base` y sube a `head`, y `test_sin_tablas_de_dominio`, que exige `["alembic_version"]` y **fallará** al existir `0002`).
- `scripts/test.ps1`: autoprueba → build → unitarias (`--no-deps`) → `db-test` → `alembic -x target=test upgrade head` → integración → typecheck → Vitest. Línea base de C-01: 97 pruebas (86 unitarias, entre ellas las 19 de superposición; 9 de integración; 2 de Vitest).
- Entorno verificado en el Explore (Engram #29): PostgreSQL 18.6 (`uuidv7()` nativo), Python 3.14.10 (`uuid.uuid7()`), SQLAlchemy 2.1.6, psycopg 3.3.6. El rol `app` de `db` y `db-test` es **superusuario con `BYPASSRLS`**.

## Objetivos / No objetivos

**Objetivos de diseño:**

- Tablas y restricciones que hagan cumplir en la base lo que no debe depender del código: integridad referencial, unicidad del email por consultorio, roles y anticipación válidos, credencial nunca vacía.
- Un único punto por el que pasa el consultorio en el acceso a datos (`ContextoConsultorio`), listo para que C-03 lo construya desde la identidad autenticada sin cambiar los repositorios.
- Seed reproducible y seguro de ejecutar en cualquier momento sobre la base de desarrollo, sin tocar datos que no creó.
- Cero cambios de infraestructura y conservación de las 97 pruebas existentes.

**No objetivos de diseño** (además de los de `proposal.md`):

- Unidad de trabajo o dependencias de FastAPI por petición (no hay endpoints; llegan con C-03).
- Claves foráneas compuestas efectivas (no hay todavía tablas que referencien a `usuario`; C-02 solo deja el ancla).
- Validación de formato de email más allá de la normalización (llega con los esquemas de entrada de C-05).

## Decisiones adoptadas por el autor (Engram #30, aprobadas el 2026-11-04)

| Id | Decisión | Cómo se refleja en este diseño |
|---|---|---|
| DC-01 | `id` UUIDv7 generado por PostgreSQL 18 con `uuidv7()` (`server_default`) en `consultorio` y `usuario` | DDL (DM-01); escenario "Identificadores UUIDv7 generados por la base" |
| DC-02 | Ancla `UNIQUE (consultorio_id, id)` en `usuario` desde C-02 | `uq_usuario_consultorio_id_id` (DM-01, DM-02) |
| DC-03 | C-02 implementa repositorios acotados; las políticas RLS son de C-04 | DM-05; sin RLS en `0002` |
| DC-04 | Nota para C-04: usuario de base de la aplicación sin privilegios administrativos, distinto del de migraciones. No se crea ahora ni se toca la infraestructura | Sección "Impacto en Changes siguientes"; sin cambios en `docker-compose.yml`, `.env.example` ni `Settings` |
| DC-05 | Email único **dentro de cada consultorio**, normalizado a minúsculas; el login de C-03 deberá identificar también el consultorio | DM-03 |
| DC-06 | v0.1: un usuario pertenece a exactamente un consultorio; la misma persona puede tener cuentas separadas; sin membresías | `consultorio_id NOT NULL`, sin tabla de membresías |
| DC-07 | Seed por comando explícito separado de las migraciones; idempotente, seguro y no destructivo | DM-07, DM-08 |
| DC-08 | Usuarios del seed sin credenciales utilizables, con una representación que no pueda autenticar por accidente | DM-04 (credencial nula = "sin credencial") |
| DC-09 | `rol` como texto con `CHECK IN ('administrador','secretaria','odontologo')` | DM-01; grafía de la KB 04 §Usuario, sin tildes |
| DC-10 | Repositorios acotados con base reutilizable; consultorio desde un contexto de identidad confiable, nunca de un parámetro del cliente | DM-05, DM-06 |
| DC-11 | Migración `0002_modelo_base_consultorios` con `down_revision = "0001"`; la numeración de `CHANGES.md` no se toca hasta el Archive | DM-02; nota de numeración |
| DC-12 | PA-05 = "solo seed" en la v0.1; PA-03 y PA-11 diferidos a C-03 y C-05 | Sin endpoint de alta de consultorio; sin autenticación |

**Nota de numeración (DC-11):** `CHANGES.md` dice "Migración 001" para C-02 y "migración 002" para C-04, escritos antes de que C-01 ocupara `0001` con `btree_gist`. Las revisiones reales son `0002` (C-02) y, previsiblemente, `0003` (C-04). Corrección a aplicar en `CHANGES.md` **al archivar** este Change, no ahora.

**Advertencia explícita (precaución 8 del autor):** los UUIDv7 dificultan la enumeración y los repositorios acotados filtran por consultorio, pero **ninguno de los dos es autorización** (RBAC, C-04) **ni barrera en la base** (RLS, C-04). RN-MT-06 sigue exigiendo ambas.

## Decisiones derivadas

### DM-01. Esquema de las tablas (boceto de DDL)

```sql
CREATE TABLE consultorio (
    id                              uuid        NOT NULL DEFAULT uuidv7(),
    nombre                          text        NOT NULL,
    zona_horaria                    text        NOT NULL DEFAULT 'America/Argentina/Buenos_Aires',
    anticipacion_cancelacion_horas  integer     NOT NULL DEFAULT 24,
    activo                          boolean     NOT NULL DEFAULT true,
    creado_en                       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_consultorio PRIMARY KEY (id),
    CONSTRAINT ck_consultorio_anticipacion_no_negativa
        CHECK (anticipacion_cancelacion_horas >= 0)
);

CREATE TABLE usuario (
    id              uuid        NOT NULL DEFAULT uuidv7(),
    consultorio_id  uuid        NOT NULL,
    email           text        NOT NULL,
    nombre          text        NOT NULL,
    credencial      text        NULL,          -- NULL = sin credencial (DM-04)
    rol             text        NOT NULL,
    activo          boolean     NOT NULL DEFAULT true,
    creado_en       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_usuario PRIMARY KEY (id),
    CONSTRAINT fk_usuario_consultorio_id_consultorio
        FOREIGN KEY (consultorio_id) REFERENCES consultorio (id) ON DELETE RESTRICT,
    CONSTRAINT uq_usuario_consultorio_id_id    UNIQUE (consultorio_id, id),     -- ancla DC-02
    CONSTRAINT uq_usuario_consultorio_id_email UNIQUE (consultorio_id, email),  -- DC-05
    CONSTRAINT ck_usuario_rol_valido
        CHECK (rol IN ('administrador', 'secretaria', 'odontologo')),
    CONSTRAINT ck_usuario_email_normalizado
        CHECK (email = lower(btrim(email)) AND email <> ''),
    CONSTRAINT ck_usuario_credencial_no_vacia
        CHECK (credencial IS NULL OR credencial <> '')
);
```

- `text` en lugar de `varchar(n)`: PostgreSQL no gana nada con el límite y no hay evidencia en la KB para fijar longitudes.
- `creado_en` con `timestamptz` y `now()` (RN-GL-01). Sin `actualizado_en`: la KB no lo pide.
- No hacen falta índices adicionales: las dos restricciones `UNIQUE` empiezan por `consultorio_id`, así que cubren las búsquedas por consultorio y la clave foránea.
- `ON DELETE RESTRICT` (pedido del autor) en lugar de `NO ACTION`: falla de inmediato, incluso dentro de una transacción con restricciones diferidas.
- **Zona horaria sin `CHECK` en la base.** Un `CHECK` no puede consultar `pg_timezone_names` (no admite subconsultas) y envolverla en una función `IMMUTABLE` sería falso: el catálogo cambia con cada actualización de tzdata y podría invalidar filas existentes. En C-02 no hay camino de alta de consultorios salvo el seed (PA-05), que usa el valor por defecto; una prueba de integración verifica que ese valor existe en `pg_timezone_names`. Si un Change futuro permite editar la zona, la valida en la aplicación. Alternativa descartada: tipo de dominio con `CHECK` contra una lista fija (duplica tzdata y se desactualiza).
- **Nombre del consultorio sin `UNIQUE`**: la KB no lo exige; queda como decisión pendiente DP-01.

### DM-02. Migración `0002` escrita a mano y nombres de restricciones

- Archivo `backend/alembic/versions/0002_modelo_base_consultorios.py`, `revision = "0002"`, `down_revision = "0001"`. `upgrade` crea `consultorio` y luego `usuario` con `op.create_table`; `downgrade` borra `usuario` y luego `consultorio` (no toca `btree_gist`, que pertenece a `0001`). El comentario del `downgrade` repite la advertencia de `0001`: solo se ejecuta contra la base de pruebas efímera.
- La migración no contiene `INSERT` ni importa nada de `app.seed` (DC-07).
- **Nombres explícitos de restricciones** envueltos en `op.f(...)` en la migración y declarados en los modelos. Motivo: la convención de C-01 para `uq` solo usa la primera columna, de modo que `UNIQUE (consultorio_id, id)` y `UNIQUE (consultorio_id, email)` recibirían ambas `uq_usuario_consultorio_id` y chocarían. Los nombres elegidos respetan los prefijos y el estilo de la convención (`pk_`, `fk_<tabla>_<columna>_<tabla_ref>`, `uq_<tabla>_<columnas>`, `ck_<tabla>_<nombre>`). En los modelos, los `CheckConstraint` llevan el nombre corto (`rol_valido`, etc.) y la convención les antepone `ck_<tabla>_`; los `UniqueConstraint` llevan el nombre completo, que SQLAlchemy respeta porque la plantilla de `uq` no usa `%(constraint_name)s`.
- Alternativa descartada: cambiar la convención a `%(column_0_N_name)s` en `app/models/base.py`. Sería más automático, pero modifica un archivo de C-01 sin necesidad y cambia nombres futuros de forma global; se puede proponer aparte si se repite el caso.
- Coherencia modelos ↔ migración: una prueba de integración ejecuta `alembic.autogenerate.compare_metadata` sobre la base migrada y exige una lista vacía. Como Alembic no compara `CHECK` ni `server_default` por defecto, los nombres y la existencia de los `CHECK` se verifican además contra el catálogo (`pg_constraint`).

### DM-03. Email: normalizado al guardar + `CHECK` + `UNIQUE (consultorio_id, email)` (DC-05)

Opciones evaluadas:

| Opción | Ventajas | Desventajas |
|---|---|---|
| **A. Guardar normalizado (`lower(btrim(...))`) + `CHECK` + `UNIQUE (consultorio_id, email)`** (elegida) | Restricción `UNIQUE` real, que funciona con `ON CONFLICT DO NOTHING` sin inferir índices de expresión; la comparación es una igualdad simple; la base rechaza cualquier email sin normalizar aunque alguien inserte por fuera del repositorio | Hay que normalizar en la aplicación antes de guardar y de buscar (una función pura, probada) |
| B. Índice único funcional `(consultorio_id, lower(email))` | Conserva el email tal como se escribió | No es una restricción (no sirve como objetivo de claves foráneas ni aparece como `UNIQUE` en el catálogo); toda búsqueda debe usar `lower(email)` para aprovechar el índice; `ON CONFLICT` necesita repetir la expresión |
| C. Extensión `citext` | Comparación sin mayúsculas automática | Agrega otra extensión a la cadena de migraciones; semántica menos explícita |

- La aplicación normaliza con `normalizar_email(email) = email.strip().lower()` (función pura en el módulo del modelo de usuario), y el repositorio la usa en `crear` y `buscar_por_email`. El `CHECK` es la red de seguridad: si la normalización de Python y la de PostgreSQL difirieran, la inserción falla (falla cerrada, no un duplicado).
- El escenario "sin distinguir mayúsculas" se cumple porque `PERSONA.FICTICIA@example.test` se normaliza antes de insertar y choca con la restricción `UNIQUE`.

### DM-04. Credencial: nula significa "sin credencial" (DC-08)

Opciones evaluadas:

| Opción | Falla cerrada | Desventajas |
|---|---|---|
| **A. `credencial` nullable; `NULL` = sin credencial; `CHECK (credencial IS NULL OR credencial <> '')`** (elegida) | Sí: no hay ningún valor que un verificador de hash pueda aceptar; el contrato de C-03 es simple ("NULL ⇒ rechazar") y verificable con una prueba | La columna admite nulos, a diferencia de "credencial como hash" de `CHANGES.md` (desvío señalado abajo) |
| B. Centinela no válido como hash (por ejemplo, `!` al estilo de `/etc/shadow`) | Depende de que el verificador de C-03 rechace el formato; un verificador permisivo o un algoritmo futuro podría interpretarlo | El "dato" parece una credencial; más difícil de auditar con una consulta |
| C. Columna `credencial` obligatoria + bandera `credencial_habilitada` | Sí, si C-03 revisa la bandera | Dos fuentes de verdad; habría que inventar un valor para la columna obligatoria |

- **Contrato que C-03 debe respetar** (se copia en el Archive como nota para C-03): (1) un usuario con `credencial IS NULL` no puede autenticarse nunca; el login lo rechaza **antes** de invocar al verificador de hash, con el mismo mensaje genérico que una credencial inválida (US-001) y, si C-03 lo decide, con tiempo de respuesta equivalente; (2) una credencial no nula solo puede contener lo que produzca el algoritmo elegido en PA-03; (3) C-03 define el mecanismo local para asignar credenciales ficticias de demostración a los usuarios del seed, que nunca se versiona ni forma parte del seed de C-02.
- C-02 no expone ninguna operación que escriba `credencial`: `UsuarioRepositorio.crear` no la recibe y la deja nula.
- **Desvío respecto de KB/CHANGES** (señalado según lo pedido): KB 04 §Usuario dice "`credencial` (por ejemplo, hash de contraseña; depende de PA-03)" y `CHANGES.md` C-02 dice "`credencial` como hash". Este diseño mantiene la columna como el lugar del hash, pero la hace **nullable** con la semántica "sin credencial". No contradice "nunca se almacena la contraseña en texto plano". Se pide confirmación en DP-02.

### DM-05. Contexto confiable y repositorio base (DC-03, DC-10)

- `app/repositories/contexto.py`: `ContextoConsultorio`, `@dataclass(frozen=True, slots=True)` con `consultorio_id: UUID`; `__post_init__` lanza `TypeError` si no es `uuid.UUID`. No es un esquema de Pydantic ni deriva de `EsquemaEntrada`, así que no puede llegar desde un cuerpo, query ni encabezado. En C-02 lo construyen solo las pruebas; en C-03 lo construirá la dependencia `contexto_consultorio` a partir de la identidad autenticada (RN-MT-02). La regla "solo en el servidor" es una convención de arquitectura respaldada por tipos y pruebas, no una barrera técnica: por eso RN-MT-06 sigue exigiendo RLS y pruebas de acceso cruzado (C-04).
- `app/repositories/base.py`: `RepositorioAcotado[M]` (genérico de Python 3.14) con `modelo: ClassVar[type[M]]`, constructor `(sesion: Session, contexto: ContextoConsultorio)` que rechaza con `TypeError` cualquier otra cosa como contexto, y `_seleccionar()` que devuelve `select(modelo).where(modelo.consultorio_id == contexto.consultorio_id)`; toda lectura parte de ahí y toda modificación usa `update(...)`/`delete(...)` con la misma condición más la de `id`. Los repositorios no hacen `commit`: el llamador controla la transacción.
- `app/repositories/usuarios.py`: `UsuarioRepositorio(RepositorioAcotado[Usuario])` con `listar()`, `obtener_por_id(usuario_id) -> Usuario | None`, `buscar_por_email(email) -> Usuario | None`, `crear(datos: NuevoUsuario) -> Usuario` (asigna `consultorio_id` del contexto, normaliza el email, deja `credencial` nula, hace `flush` para obtener el `id` generado por la base) y `desactivar(usuario_id) -> bool` (`UPDATE ... WHERE consultorio_id = :ctx AND id = :id`; `False` si no afectó filas, igual para inexistente y ajeno, RN-MT-05). `desactivar` es la única escritura además de `crear`, para poder verificar el escenario de modificación cruzada; la gestión completa de usuarios es C-05.
- `NuevoUsuario`: `@dataclass(frozen=True, slots=True)` con `email: str`, `nombre: str`, `rol: Rol`; sin `consultorio_id` (pasarlo es `TypeError`). `Rol` es un `StrEnum` con los tres valores de DC-09, usado por el modelo y por el `CHECK`.
- `app/repositories/consultorios.py`: `ConsultorioRepositorio(sesion, contexto)` con una sola operación `obtener_actual() -> Consultorio | None` (`select(Consultorio).where(Consultorio.id == contexto.consultorio_id)`). No deriva de `RepositorioAcotado` porque `consultorio` no tiene `consultorio_id`: el acotamiento es por su propio `id`. Devuelve el consultorio aunque esté inactivo; qué significa un consultorio inactivo para el acceso es DP-03.
- Las pruebas de comportamiento de los repositorios van en `tests/integration/` (necesitan PostgreSQL real, X2). `tests/isolation/` queda para el arnés de acceso cruzado por endpoint de C-04. Las pruebas unitarias cubren lo que es puro: el contexto, `NuevoUsuario`, `normalizar_email` y el SQL compilado de cada lectura (que contiene `consultorio_id` con el valor del contexto).

### DM-06. Esquemas de entrada sin `consultorio_id`

Prueba unitaria que importa los módulos de `app.schemas`, recorre recursivamente `EsquemaEntrada.__subclasses__()` (excluidas las clases definidas en módulos de pruebas) y exige que ninguna declare `consultorio_id` en `model_fields`. En C-02 no hay esquemas de entrada de dominio, así que la prueba es preventiva: protege a C-03 en adelante. C-04 la puede reutilizar.

### DM-07. Seed: identificadores fijos e `INSERT ... ON CONFLICT DO NOTHING` (DC-07, precaución 5)

- Paquete `app/seed/`: `datos.py` (datos ficticios como tuplas inmutables de dataclasses), `aplicar.py` (`aplicar_seed(sesion: Session) -> ResumenSeed`) y `__main__.py` (`main() -> int`, comando `python -m app.seed`).
- **Identificadores fijos UUIDv7 literales.** Cada consultorio y usuario del seed tiene un `id` constante, generado una sola vez en Apply con `uuid.uuid7()` de Python 3.14 y escrito como literal en `datos.py`. Así todos los `id` del sistema siguen siendo versión 7 (DC-01) y el seed es determinista. Alternativa sugerida por el autor: `uuid5` sobre un espacio de nombres del proyecto (también determinista, pero versión 5, distinta del resto). Se pide confirmación en DP-04.
- **Inserción no destructiva**: `INSERT INTO consultorio (...) VALUES (...) ON CONFLICT DO NOTHING RETURNING id` y lo mismo para `usuario`, sin destino de conflicto, para que cualquier restricción de unicidad (clave primaria o `(consultorio_id, email)`) haga omitir la fila. El seed **nunca** ejecuta `UPDATE` ni `DELETE`. Las filas devueltas por `RETURNING` se cuentan como insertadas y el resto como omitidas.
- Comportamiento ante conflictos con datos que no son del seed: si ya existe un usuario con el mismo email en ese consultorio (por ejemplo, creado a mano), la fila del seed se **omite** y se informa en la cantidad de omitidas, sin detalle de qué fila (X1); nunca se sobrescribe. Si un consultorio del seed fue renombrado, se conserva el nombre nuevo.
- Todo en una transacción: si algo falla (por ejemplo, migraciones sin aplicar), se revierte, se informa un mensaje sin URLs ni datos ("aplicar primero las migraciones" si falta la tabla) y el comando termina con código 1.
- `ResumenSeed` tiene solo enteros (`consultorios_insertados`, `consultorios_omitidos`, `usuarios_insertados`, `usuarios_omitidos`) y su texto de salida solo muestra esos números.
- Datos (D1): "Consultorio Demo A" y "Consultorio Demo B" (KB 04 §Seed); usuarios "Administración Demo A", "Secretaría Demo A", "Odontología Demo A" (y los de B), con emails `administracion.a@example.test`, `secretaria.a@example.test`, `odontologia.a@example.test` (y `.b`). `.test` es un dominio de nivel superior reservado (RFC 6761): no puede pertenecer a nadie. Valores de consultorio: los por defecto de la base (no se indican en el `INSERT`).
- Las pruebas aplican `aplicar_seed` sobre una sesión de `db-test` dentro de una transacción que se revierte; el comando `main()` nunca se ejecuta contra `db-test`.

### DM-08. Guardia de entorno del seed

- `validar_entorno_de_seed(settings)` (pura) lanza un error si `settings.app_env != "local"`, con un mensaje que nombra `APP_ENV` sin mostrar otras variables.
- `main()`: `cargar_configuracion()` → `validar_entorno_de_seed` → recién entonces `crear_engine(settings)` (solo `DATABASE_URL`) → sesión → `aplicar_seed` → `commit` → imprime el resumen. La guardia va antes de crear el motor: con `APP_ENV=test` no se intenta ninguna conexión (se verifica con el listener `do_connect` de `Engine`, como en C-01 DF-07).
- No hay modo para apuntar el comando a `db-test` ni a una URL arbitraria: las pruebas usan la función, no el comando. `Settings.app_env` solo admite `local` y `test`; cualquier otro valor ya falla al cargar la configuración.
- En Apply, ejecutar el seed sobre la base de **desarrollo** (que antes requiere `alembic upgrade head` sobre `db`) solo se hace con autorización del autor (DP-05).

### DM-09. Fábrica de sesiones

`crear_fabrica_de_sesiones(engine: Engine) -> sessionmaker[Session]` en `app/core/database.py`, con `expire_on_commit=False`. La usa el seed; C-03 la usará para la sesión por petición. No se crea ninguna instancia global al importar (igual que C-01).

### DM-10. Modelos SQLAlchemy y registro

- `app/models/consultorio.py` y `app/models/usuario.py` con `Mapped[...]` y `mapped_column` (`Uuid`, `Text`, `Integer`, `Boolean`, `DateTime(timezone=True)`), `server_default=text("uuidv7()")`, `server_default=text("now()")`, etc., y `__table_args__` con las restricciones de DM-01.
- `app/models/__init__.py` importa `Consultorio` y `Usuario`. Como `env.py` importa `app.models.base`, Python ejecuta primero `app/models/__init__.py`, de modo que ambos modelos quedan registrados en `Base.metadata` **sin tocar `env.py`**. Una prueba unitaria verifica que `Base.metadata.tables` contiene `consultorio` y `usuario`.
- Sin relaciones ORM (`relationship`) en C-02: no hacen falta y evitan cargas implícitas que salteen el acotamiento.

### DM-11. Pruebas de integración con base compartida

- Se mueve el fixture `base_migrada` a `tests/integration/conftest.py` y se agrega `sesion`: abre una conexión, inicia una transacción, crea `Session(bind=conexion, join_transaction_mode="create_savepoint")` y al terminar revierte. Así ninguna prueba deja filas y "las tablas quedan vacías tras migrar" se puede comprobar en cualquier orden.
- Las inserciones que deben fallar se ejecutan dentro de `sesion.begin_nested()` para que el error no invalide la transacción exterior; se verifica el `sqlstate` (`23502` NOT NULL, `23503` FK, `23505` UNIQUE, `23514` CHECK).
- Las pruebas de subida y bajada (`0001` ↔ `0002`) usan la API de Alembic sobre `db-test`, como `test_el_comando_explicito_deja_la_base_al_dia`, y terminan siempre en `head`.
- **`test_sin_tablas_de_dominio`** se conserva con su nombre y pasa a exigir `sorted(tablas) == ["alembic_version", "consultorio", "usuario"]`; se agrega una prueba de tablas vacías. Justificación: la delta MODIFIED de `base-de-datos-local`.
- `scripts/test.ps1` no cambia. La autoprueba (`scripts/tests/autoprueba.ps1`) agrega la comprobación de que el comando del servicio `api` no contiene `app.seed` (escenario "El arranque de la API no ejecuta el seed"), junto a la existente de `alembic`.

## Riesgos / Trade-offs

- [El rol `app` de `db` y `db-test` es superusuario con `BYPASSRLS`] → irrelevante en C-02 (no hay RLS); C-04 debe introducir el usuario de aplicación sin privilegios (DC-04) antes de confiar en RLS. Documentado para C-04.
- [Confundir los repositorios acotados o los UUIDv7 con una barrera suficiente] → advertencia explícita en el diseño y en las specs; RN-MT-06 se completa en C-04.
- [`ContextoConsultorio` puede construirse desde cualquier código del servidor] → convención + tipos + prueba de esquemas; C-03 centraliza su construcción en una dependencia; C-04 agrega RLS y pruebas de acceso cruzado.
- [UUIDv7 revela el instante de creación] → aceptado: no es un dato personal del paciente ni un secreto; los `id` no se usan como autorización.
- [`uuidv7()` ata el esquema a PostgreSQL 18+] → ya fijado por C-01 (requisito "Versión mayor del servidor"); documentado.
- [Diferencias entre `str.lower()` de Python y `lower()` de PostgreSQL en caracteres no ASCII] → el `CHECK` rechaza en lugar de duplicar (falla cerrada); la validación de formato de email llega con C-05.
- [Pruebas de integración que comparten `db-test` y dejan datos] → transacción revertida por prueba (DM-11) y prueba de tablas vacías.
- [`downgrade` destructivo] → solo se ejecuta contra `db-test` (guardia de C-01 para URLs explícitas y `-x target=test`); comentario en la migración; nunca se documenta un `downgrade` para desarrollo.
- [El seed se ejecuta sobre una base con datos manuales] → `ON CONFLICT DO NOTHING`, sin `UPDATE`/`DELETE`, con escenario de fila ajena.
- [Identificadores fijos del seed publicados en el repositorio] → son datos ficticios de una base local; no otorgan acceso.
- [El seed corre en un entorno indebido] → guardia `APP_ENV=local` antes de conectar; el comando solo usa `DATABASE_URL`.
- [Romper las 97 pruebas existentes] → red de seguridad al inicio de Apply y comando único al final; solo cambia `test_sin_tablas_de_dominio`, con justificación.

## Plan de migración

- **Base de pruebas**: `scripts/test.ps1` aplica `0001 → 0002` en cada ejecución sobre `db-test` (efímera).
- **Base de desarrollo** (en Apply, con autorización del autor, DP-05): `docker compose run --rm api alembic upgrade head` y luego `docker compose run --rm api python -m app.seed` dos veces, verificando 2 consultorios y 6 usuarios. Solo datos ficticios.
- **Reversión**: en desarrollo no se ejecuta `downgrade`; si hiciera falta volver atrás, `docker compose down -v` borra el volumen local (solo datos ficticios) y se migra de nuevo. En Git, eliminar los archivos nuevos y restaurar los modificados sin reescribir historial (G1).

## Impacto en Changes siguientes

- **C-03 `autenticacion-sesion`**: respetar el contrato de credencial de DM-04 (NULL ⇒ rechazo genérico antes del verificador); el login debe identificar el consultorio además del email (DC-05; el mecanismo es parte de PA-03 y no puede apoyarse en `consultorio.nombre` mientras DP-01 no lo haga único); construir `ContextoConsultorio` desde la identidad en la dependencia `contexto_consultorio`; rechazar usuarios con `activo = false` (RN-AU-06) y decidir el efecto de un consultorio inactivo (DP-03); definir cómo obtienen credenciales de demostración los usuarios del seed; resolver PA-03.
- **C-04 `aislamiento-roles-rbac`**: migración `0003` (no "002"); políticas RLS sobre `usuario` y tablas siguientes; usuario de base de la aplicación sin privilegios ni `BYPASSRLS`, distinto del de migraciones (DC-04), lo que sí cambiará `docker-compose.yml`, `.env.example` y `Settings`; resolver el choque entre la búsqueda de login y RLS (función `SECURITY DEFINER` o camino dedicado, Engram #29); claves foráneas compuestas contra `uq_usuario_consultorio_id_id`; arnés de acceso cruzado por endpoint en `tests/isolation/`; reutilizar la prueba de esquemas sin `consultorio_id`.
- **C-05 `gestion-usuarios`**: construir sobre `UsuarioRepositorio` (`crear`, `desactivar`, más cambio de rol); validación de formato de email en `EsquemaEntrada`; unicidad por consultorio y cuentas separadas por consultorio (DC-06); PA-11.
- **C-07 en adelante**: toda tabla con `consultorio_id` usa `RepositorioAcotado` y, para referencias a usuario (por ejemplo, Profesional ↔ Usuario, SU-03), una clave foránea compuesta `(consultorio_id, usuario_id)`.
- **C-23 `seed-demo-y-cierre-nucleo`**: amplía `app/seed/` con el mismo patrón (identificadores fijos, `ON CONFLICT DO NOTHING`, guardia y resumen sin datos personales).

## Decisiones pendientes para el autor

Ninguna resuelve una pregunta abierta de la KB (PA-xx, P-xx, NE-xx): PA-01, PA-03, PA-04 (más allá de DC-01 a DC-03), PA-06 (más allá de DC-05/DC-06) y PA-11 siguen abiertas para sus Changes (D6).

| Id | Decisión | Propuesta del diseño | Estado |
|---|---|---|---|
| DP-01 | ¿`consultorio.nombre` es único? | **No** en C-02: la KB no lo exige y el seed no depende de eso. Si C-03 decide identificar el consultorio en el login por un dato legible, conviene un identificador propio (por ejemplo, un código corto único) antes que el nombre visible | **Resuelta (autor, 2026-11-04):** `consultorio.nombre` NO es único; el consultorio se identifica por su UUIDv7 y el login futuro (C-03) usará un identificador inequívoco, no el nombre visible |
| DP-02 | Representación "sin credencial" | `credencial` nullable con `NULL` = sin credencial y `CHECK` de no vacía (DM-04); desvío de "credencial como hash" de `CHANGES.md` | **Resuelta (autor, 2026-11-04):** `credencial` nullable (`NULL` = cuenta sin credenciales); cadena vacía prohibida por `CHECK`. C-03 debe garantizar que `NULL` nunca inicia sesión |
| DP-03 | ¿Qué implica `consultorio.activo = false`? | C-02 solo lo almacena y lo devuelve; el efecto sobre el acceso lo decide C-03 | **Resuelta (autor, 2026-11-04):** el comportamiento ante un consultorio inactivo se decide en C-03; C-02 solo persiste `activo` |
| DP-04 | Identificadores del seed | UUIDv7 literales fijos (DM-07) en lugar de `uuid5` | **Resuelta (autor, 2026-11-04):** UUIDv7 literales fijos y válidos en el seed; una prueba verifica `version == 7` para cada id del seed |
| DP-05 | Ejecutar en Apply `alembic upgrade head` y el seed sobre la base de **desarrollo** | Sí, solo para la verificación manual de idempotencia, con datos ficticios y autorización expresa en Apply | **Resuelta (autor, 2026-11-04):** la migración `0002` y el seed se ejecutan SOLO sobre `db-test`; NO se autoriza ejecutarlos sobre la base de desarrollo (la tarea 4.8 queda sin marcar) |
| DP-06 | Validación de formato del email | Fuera de C-02 (solo normalización y no vacío); en los esquemas de entrada de C-05 | **Resuelta (autor, 2026-11-04):** la validación completa de formato de email se difiere a C-05; en C-02 se mantienen normalización (`lower`/`btrim`), no vacío y unicidad por consultorio |

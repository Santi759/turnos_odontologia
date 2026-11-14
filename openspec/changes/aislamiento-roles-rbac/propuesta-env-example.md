# Propuesta para la tarea 1.6: cambios a `.env.example` (NO aplicados)

> Apply no modifica `.env.example` sin autorizacion especifica del autor. Este archivo solo redacta el contenido propuesto. No contiene valores reales; los marcadores son evidentemente ficticios.

## Variables a cambiar o agregar

```dotenv
# Rol de la API (turnos_app): privilegios minimos y RLS (C-04). Los roles se crean con
#   docker compose run --rm -it api python -m app.roles_postgres crear
# y las contrasenas las elige el autor (no se versionan).
DATABASE_URL=postgresql+psycopg://turnos_app:REEMPLAZAR_clave_de_turnos_app@db:5432/turnos

# Rol de login (turnos_login): solo lo usa POST /api/auth/login.
DATABASE_LOGIN_URL=postgresql+psycopg://turnos_login:REEMPLAZAR_clave_de_turnos_login@db:5432/turnos

# Rol de administracion (el de siempre, `app`): Alembic y los comandos locales
# (seed, credenciales, mantenimiento, roles_postgres). Nunca lo usa la API.
DATABASE_MIGRATION_URL=postgresql+psycopg://app:REEMPLAZAR_clave_de_administracion@db:5432/turnos
```

## Pruebas asociadas que habria que ajustar al aplicar la propuesta

- `backend/tests/unit/test_plantilla_env.py` (y `test_plantilla_ausente.py` si corresponde): la plantilla debe declarar las tres URLs con usuarios distintos y marcadores con `REEMPLAZAR`/ficticios, y cargar con `Settings`.
- `scripts/tests/autoprueba.ps1`, caso "Plantilla completa con valores ficticios": incorporar `DATABASE_LOGIN_URL` y `DATABASE_MIGRATION_URL`.

## Consecuencia mientras no se aplique

El runner (`scripts/test.ps1`) no depende de `.env.example`; las pruebas con base usan URLs derivadas en `db-test`. Si alguna prueba de la plantilla cambia por esta tarea, queda pendiente de la autorizacion.

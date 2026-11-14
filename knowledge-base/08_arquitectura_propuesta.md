# Arquitectura Propuesta

> Fuentes: stack e infraestructura elegidos por el autor el 2026-10-13 (DD-10, DD-11); reglas de `05_reglas_de_negocio.md`; RG1 y RG3 de `discovery/discovery.md`; buenas prácticas de seguridad propuestas por esta KB. La Ley 25.326 (arts. 9 y 10, Discovery §9) fija un deber general de seguridad y confidencialidad, pero no prescribe los mecanismos técnicos que aquí se proponen. No es asesoramiento legal. Etiquetas: ver [README](README.md#convenciones).
>
> Todo este archivo es **[PROP]**, salvo lo marcado como [DEC]. Es la arquitectura inicial que se confirma o ajusta en los Changes del roadmap. Los puntos de autenticación y aislamiento son de **gobernanza crítica**: requieren aprobación explícita del autor antes de implementarse.

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| Arquitectura en capas: routers → servicios de dominio → repositorios | Backend FastAPI | Las reglas de agenda (R1–R4) quedan en servicios que se prueban sin HTTP ni base de datos; los routers solo traducen peticiones |
| Inyección de dependencias de FastAPI para el **contexto de consultorio** | Toda ruta autenticada | Un único punto deriva usuario, consultorio y rol de la identidad (RN-MT-02); los servicios lo reciben y no lo leen de la petición |
| Repositorios acotados al consultorio | Acceso a datos con SQLAlchemy 2 | Cada repositorio recibe el consultorio y lo aplica en todas sus consultas; evita filtros olvidados (RG3). No es suficiente por sí solo (RN-MT-06) |
| Integridad en la base de datos | PostgreSQL | La restricción de exclusión por profesional y rango horario garantiza R2 ante concurrencia (RN-AG-03); las referencias del mismo consultorio se refuerzan en la base (PA-04) |
| Esquemas de entrada y salida separados | Pydantic | La entrada nunca acepta `consultorio_id` ni campos de control (evita la asignación masiva); la salida no expone datos innecesarios (RN-PA-03) |
| Transacción por operación de escritura | Servicios de dominio | Atomicidad de turnos y reprogramaciones (RN-GL-02) |
| Organización por funcionalidad | Frontend React | Cada épica de `06_funcionalidades.md` tiene su carpeta; facilita los Changes incrementales |
| Desarrollo guiado por pruebas | Backend y frontend | El autor trabaja con TDD estricto; pytest y Vitest ([DEC] DD-10) |

## Estructura de directorios

```
turnos_odontologia/
├── backend/
│   ├── app/
│   │   ├── main.py              # creación de la app FastAPI, CORS, routers
│   │   ├── core/                # configuración (variables de entorno), seguridad, contexto de consultorio
│   │   ├── api/                 # routers por recurso (turnos, pacientes, agenda, ...)
│   │   ├── schemas/             # modelos Pydantic de entrada y salida
│   │   ├── domain/              # servicios y reglas: disponibilidad, validación de turnos
│   │   ├── repositories/        # acceso a datos acotado al consultorio
│   │   └── models/              # modelos SQLAlchemy 2
│   ├── alembic/                 # migraciones
│   └── tests/
│       ├── unit/                # reglas de dominio sin base de datos
│       ├── integration/         # repositorios y restricciones contra PostgreSQL real
│       └── isolation/           # pruebas de acceso cruzado entre consultorios, por endpoint
├── frontend/
│   └── src/
│       ├── features/            # auth, agenda, turnos, pacientes, configuración
│       ├── shared/              # componentes, cliente HTTP, utilidades de fechas
│       └── pages/
├── docker-compose.yml           # db + api + frontend para desarrollo local
├── .env.example                 # variables sin valores reales
├── knowledge-base/
├── discovery/  docs/            # Discovery (fuentes de esta KB)
└── openspec/                    # specs y Changes
```

## Estrategia de pruebas

| Nivel | Herramienta | Qué cubre | Origen |
|---|---|---|---|
| Unitario de dominio | pytest | R1–R4: cálculo de fin, franjas, bloqueos, superposición, bordes de intervalos semiabiertos | RN-AG |
| Integración con la base | pytest contra PostgreSQL en Docker | Restricción de exclusión, migraciones, concurrencia (dos inserciones simultáneas) | RN-AG-03 |
| Aislamiento | pytest | Por cada endpoint con datos de consultorio: un usuario de A no lee, modifica ni referencia datos de B | RN-MT-06, RG3 |
| Autorización | pytest | Matriz de `03_actores_y_roles.md`: cada rol solo accede a lo permitido | RN-AU-03 |
| Frontend | Vitest | Componentes y lógica de presentación (formatos de fecha y hora, estados de turno) | DD-10 |

Las pruebas de integración usan una base PostgreSQL real, no un sustituto en memoria: la restricción de exclusión y `btree_gist` no existen en otros motores.

## Seguridad

### Autenticación — requisitos y alternativas, sin decisión

[ABIERTA] PA-03. Requisitos en RN-AU-01 a RN-AU-07: los derivados de Discovery son [REQ] y las buenas prácticas son requisitos técnicos propuestos, a aprobar en el Change de acceso. Alternativas a evaluar en ese Change, con aprobación del autor:

| Alternativa | A favor | En contra |
|---|---|---|
| Sesión del servidor con cookie `HttpOnly` y `SameSite` | Revocación inmediata; el token no queda accesible a JavaScript | Requiere almacenar sesiones y proteger contra CSRF; CORS con credenciales entre frontend y API |
| Token de acceso de vida corta más token de renovación | Habitual con frontend y API separados | Revocación más compleja; riesgo si el token se guarda en un almacenamiento accesible a JavaScript |
| Librería de autenticación para FastAPI (por ejemplo, fastapi-users) | Menos código propio en un dominio crítico | Dependencia externa; hay que verificar mantenimiento y encaje con el modelo de consultorio |

Prácticas propuestas para cualquier alternativa: algoritmo robusto de derivación de contraseñas, vencimiento, límite de intentos, verificación de rol en el servidor y secretos fuera del repositorio.

### Aislamiento multi-consultorio — defensa en profundidad

[DEC] D2: aislamiento por consultorio. Principio [REQ] RN-MT-06: **el filtro por consultorio no alcanza solo**. Capas adoptadas en C-04 (PA-04 resuelta; ver la capacidad `aislamiento-base-de-datos`):

1. **Contexto derivado de la identidad** (RN-MT-02): obligatorio.
2. **Repositorios acotados** al consultorio: obligatorio.
3. **Referencias del mismo consultorio garantizadas por la base**, por ejemplo con claves foráneas compuestas que incluyen `consultorio_id` (RN-MT-03): adoptada en C-04 (convención `(consultorio_id, id)`, DD-08, verificada por prueba de esquema).
4. **Seguridad a nivel de fila (RLS) de PostgreSQL**, con el consultorio de la sesión como variable: adoptada en C-04 (RLS habilitada y forzada, contexto transaccional, falla cerrada sin contexto, DD-03). [MERCADO] Odonto.ar declara RLS en su política de privacidad (informe §6.1; la fuente sigue pendiente de verificación personal, §8.1, fila 8); esto es evidencia de que un competidor la usa, no prueba de que sea necesaria aquí.
5. **Pruebas automatizadas de acceso cruzado** por endpoint: obligatorias.
6. **Identificadores no secuenciales** para dificultar la enumeración: adoptada (UUIDv7 generado por PostgreSQL, DC-01; capa de PA-04 resuelta en C-04).

Riesgos documentados en `05_reglas_de_negocio.md` (dominio RN-MT).

### Validación de entrada

- Pydantic valida tipos, rangos (duración mayor que cero, `inicio < fin`) y enumeraciones en cada endpoint.
- Las reglas de negocio se validan en el dominio y, para R2, también en la base.
- Los esquemas de entrada excluyen campos de control: `consultorio_id`, `estado` cuando no corresponde, campos de auditoría.

### Datos personales y sensibles

Sin carácter de asesoramiento legal; preguntas 6 a 11 para asesoría.

- **Prestación del turno como posible dato sensible** (D9): fuera de los logs técnicos y de los mensajes externos (RN-PA-03).
- **Datos ficticios** en desarrollo y pruebas (RN-PA-08).
- **Sin datos clínicos** (D3).
- **Despliegue futuro**: alojar datos en un proveedor externo o fuera de Argentina abre las preguntas 7, 8 y 10 (Ley 25.326, art. 25; Decreto 1558/2001). Por eso el despliegue es [ABIERTA] PA-02.

### Gestión de secretos

Variables de entorno; `.env` fuera del control de versiones; `.env.example` con valores de ejemplo no reales (RN-AU-07).

## Infraestructura

[DEC] DD-11: desarrollo y pruebas **locales** con Docker Compose como base. No se contratan ni configuran servicios externos en esta etapa. El despliegue en la nube es una posibilidad futura, sujeta a lo que exija la entrega ([ABIERTA] PA-02).

| Servicio de Docker Compose | Rol |
|---|---|
| `db` | PostgreSQL con la extensión `btree_gist`; volumen local; solo datos ficticios |
| `api` | FastAPI; aplica las migraciones de Alembic al iniciar o mediante un comando explícito ([PROP]) |
| `frontend` | Servidor de desarrollo de Vite |

Para que un despliegue futuro no requiera reescribir: toda la configuración por variables de entorno, orígenes CORS configurables y ninguna dependencia de rutas locales.

## Variables de entorno

[PROP] Lista inicial; los nombres definitivos se fijan en el primer Change.

| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|---|
| `DATABASE_URL` | Conexión a PostgreSQL (el driver se elige en el primer Change) | `postgresql+<driver>://app:app@db:5432/turnos` | Y |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciales del contenedor de base de datos | `app` / `cambiar` / `turnos` | Y (contraseña) |
| `AUTH_SECRET_KEY` | Clave de firma de sesiones o tokens (depende de PA-03) | valor aleatorio largo | Y |
| `AUTH_SESSION_MINUTES` | Duración de la sesión o del token de acceso | `30` | N |
| `CORS_ALLOWED_ORIGINS` | Orígenes permitidos para el frontend | `http://localhost:5173` | N |
| `APP_ENV` | Entorno (`local`, `test`) | `local` | N |
| `DEFAULT_TIMEZONE` | Zona horaria por defecto de un consultorio nuevo | `America/Argentina/Buenos_Aires` | N |
| `VITE_API_BASE_URL` | URL de la API para el frontend | `http://localhost:8000` | N |
| `EMAIL_*` | Proveedor de email | — | Solo si se aprueba D5; no se configura en esta etapa |

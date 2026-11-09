# Diseño: autenticacion-sesion (C-03)

> Governance **CRITICO**. Este diseño aplica las decisiones DA-01 a DA-14 aprobadas por el autor el 2026-11-05 y las decisiones PD-01 a PD-06 y PD-08 que el autor aprobó el mismo día después de la revisión de arquitectura (Engram `opsx/autenticacion-sesion/decisions-pd`), más la corrección del alcance de DA-10 (Engram `opsx/autenticacion-sesion/decisions-correccion-da10`), y las decisiones del punto de control del 2026-11-06 (PD-09 y PD-10 cerradas, dirección del cliente no determinable y términos del contexto deterministas; ver "Decisiones del punto de control del 2026-11-06"). Las decisiones derivadas (DD-xx) son propuestas técnicas dentro de ese marco; lo que sigue abierto figura en "Decisiones pendientes para el autor" (D6). Ninguna parte de este documento autoriza ejecutar la migración 0003, el comando de credenciales ni el comando de mantenimiento sobre la base de desarrollo.

## Contexto

Ver `proposal.md` (Why). Estado observado en el código (HEAD 6258bbc):

- `backend/app/main.py`: `crear_app(settings)` registra solo `salud.router` y `CORSMiddleware` con `allow_methods=["GET"]`, `allow_headers=["Content-Type"]`, `allow_credentials=False`. No hay sesión de base por petición: el health no toca la base (spec `salud-api`). FastAPI publica hoy `/docs`, `/redoc` y `/openapi.json` con los valores por defecto; ninguna prueba existente los usa.
- `app/core/config.py`: `Settings` con `DATABASE_URL` (SecretStr), `TEST_DATABASE_URL`, `CORS_ALLOWED_ORIGINS` (rechaza `*` y vacío) y `APP_ENV: Literal["local", "test"]`. No hay entorno productivo.
- `app/models/`: `Consultorio` (sin código) y `Usuario` (`credencial` nullable con `CHECK credencial IS NULL OR credencial <> ''`, `UNIQUE (consultorio_id, id)` y `UNIQUE (consultorio_id, email)`). Convención de nombres `pk_`, `fk_`, `uq_`, `ck_`, `ix_`.
- `app/repositories/contexto.py`: `ContextoConsultorio(consultorio_id: UUID)` inmutable; hoy solo lo construyen las pruebas. Los repositorios acotados no asignan credenciales.
- `app/seed/`: `datos.py` declara `ConsultorioSeed(id, nombre)` con ids UUIDv7 fijos (`01a1a95a-dd90-73e7-9496-c7d08d776d19` y `...-c7d1647cab52`); `aplicar.py` usa `INSERT ... ON CONFLICT DO NOTHING` sin destino, sin `commit` propio, y nunca `UPDATE` ni `DELETE`. El seed nunca escribe `credencial`.
- Migraciones `0001` (btree_gist) y `0002` (modelo base). La base de desarrollo está en `0002` con 2 consultorios, 6 usuarios y 6 credenciales nulas (Explore #37).
- Pruebas que insertan consultorios solo con `nombre` (7 puntos de edición en 2 archivos): los helpers `_consultorio` de `tests/integration/test_modelo_base.py` y de `tests/integration/test_repositorios_acotados.py`, y 5 `INSERT INTO consultorio` directos en `test_modelo_base.py` (uno de ellos, `INSERT INTO consultorio (activo) VALUES (true)`, prueba el `NOT NULL` de `nombre`).
- `docker-compose.yml`: `api` arranca con `uvicorn --factory app.main:crear_app --host 0.0.0.0 --port 8000 --reload`. Uvicorn procesa cabeceras de proxy por defecto para los pares en `--forwarded-allow-ips` (por defecto `127.0.0.1`).
- `scripts/test.ps1` (191 pruebas: 127 unitarias, 62 de integración, 2 de Vitest) y `scripts/tests/autoprueba.ps1`, que hoy **prohíbe** variables `AUTH_*` en `.env.example`.
- `frontend/vite.config.ts`: sin proxy; el frontend (`http://localhost:5173`) y la API (`http://localhost:8000`) son del mismo sitio (`localhost`) pero de distinto origen.

## Objetivos / No objetivos

**Objetivos**: cumplir las capacidades nuevas (`autenticacion-sesion`, `control-intentos-login`, `proteccion-csrf`, `credenciales-locales`, `mantenimiento-local`) y las deltas de las cinco capacidades modificadas; dejar un único punto de construcción del contexto y un único módulo de consultas previas al contexto, listos para RLS en C-04; no romper C-01 ni C-02 más allá de los ajustes justificados que se listan en "Compatibilidad".

**No objetivos**: RBAC y `require_rol` (C-04), RLS y usuario de aplicación sin privilegios (C-04, DC-04), endpoints de usuarios y cambio de contraseña (C-05), endpoint de alta de consultorios, UI de login y cliente HTTP (C-06), recuperación por email (PA-11, fuera de la v0.1), auditoría de accesos (C-30), endpoints públicos de reserva (D4), CAPTCHA, MFA, límite de sesiones por usuario, mantenimiento periódico o servicio de producción.

## Decisiones adoptadas (aprobadas por el autor el 2026-11-05)

| Id | Decisión | Condiciones del autor y cómo se cumplen |
|---|---|---|
| DA-01 | Sesiones en PostgreSQL con token opaco aleatorio en cookie HttpOnly | La base guarda solo `HMAC-SHA256(AUTH_SECRET_KEY, token)` (DD-02); el logout revoca de verdad (`revocada_en`). |
| DA-02 | `consultorio.codigo` único y normalizado; login con código + email + contraseña | El código solo identifica la cuenta. El cuerpo usa `EsquemaEntrada` (`extra='forbid'`): `consultorio_id` → 422. Después del login el contexto sale **solo** de la sesión validada. |
| DA-03 | Migración 0003 con backfill genérico y determinista | Independiente de nombres y registros del seed (regla derivada del `id`, DD-13); sin recrear la base ni `down -v`; solo escribe la columna nueva; unicidad demostrada y formato con `CHECK`; documentado y especificado; no se ejecuta en desarrollo sin autorización. C-04 pasa a `0004` (corrección de `CHANGES.md` en el Archive de C-03). |
| DA-04 | CORS con credenciales y orígenes explícitos | `allow_credentials=True`, sin comodín (ya validado), métodos `GET` y `POST`, cabeceras `Content-Type` y `X-CSRF-Token`, expone `X-CSRF-Token` y `Retry-After`. Compatible con un futuro proxy de Vite (DD-26). Sin trabajo de C-06. |
| DA-05 | 5 fallos por par (código, email) en 15 min → bloqueo de 15 min; límite por IP | Valores por IP en DD-10 (PD-03 resuelta); 429 + `Retry-After`; no se confía en `X-Forwarded-For` (DD-19); mismo trato para cuentas inexistentes; análisis del bloqueo intencional, concurrencia, vencimiento y limpieza en "Control de intentos". |
| DA-06 | 30 min de inactividad (`AUTH_SESSION_MINUTES`) y 12 h absolutas (`AUTH_SESSION_MAX_HOURS`) | Configurables; logout inmediato; usuario o consultorio desactivado pierde el acceso en la siguiente petición; la renovación nunca supera el vencimiento absoluto (DD-04). `Max-Age` de la cookie = vencimiento absoluto. |
| DA-07 | Sin recuperación por email en la v0.1 | En C-03 solo el comando local de credenciales; gestión por administradores y cambio de la propia contraseña → C-05; sin endpoints de reset. |
| DA-08 | Argon2id con `argon2-cffi` | Parámetros documentados (DD-15); rehash al iniciar sesión; hash ficticio para igualar tiempos; `NULL` nunca autentica; **sin** `CHECK` de prefijo en la base; formatos admitidos validados en la aplicación: solo PHC `$argon2id$`. Concurrencia acotada por proceso (DD-29). |
| DA-09 | Consultorio o usuario inactivo | Bloquea logins nuevos e invalida sesiones en la siguiente petición; errores genéricos sin causa. |
| DA-10 | Comando interactivo con `getpass`, solo local | Por defecto solo completa `NULL`; `--reemplazar` explícito, documentado y solo local; sin contraseñas por argumentos, archivos, variables ni registros; doble ingreso; política de contraseñas (DD-16, PD-04 resuelta); pruebas solo contra `db-test` con entradas inyectadas. **Condición literal del autor**: "No modificar el comando seed de C-02 para que sobrescriba contraseñas." La condición prohíbe que el seed sobrescriba credenciales; no prohíbe adaptarlo para insertar `consultorio.codigo` sin `UPDATE` (corrección registrada en Engram #40). C-03 adapta el seed solo para indicar el código (DD-13) y el seed sigue sin escribir `credencial`, sin `UPDATE` ni `DELETE`. |
| DA-11 | CSRF: `Origin` + `X-CSRF-Token` ligado a la sesión | Diseño de las cinco cuestiones en "Protección CSRF" (PD-02 resuelta); sin excepciones para pruebas ni `curl`. |
| DA-12 | Cookie `turnos_session` HttpOnly, SameSite=Lax, Secure | `Secure=false` solo con `APP_ENV=local` y `AUTH_COOKIE_SECURE=false` (validador); `Path=/`, sin `Domain`, `Max-Age` coherente; borrado con los mismos atributos; nunca `localStorage`. |
| DA-13 | Login y `/me` devuelven solo nombre, email, rol y nombre del consultorio | Sin hash, sin token en el JSON, sin secretos, sin datos de otros consultorios; el id interno no es selector. El token CSRF viaja en la cabecera `X-CSRF-Token`, no en el JSON (DD-07). |
| DA-14 | Una migración 0003 (`codigo`, `sesion`, `intento_login`) | Limpieza oportunista acotada (DD-21) con cota relativa corregida, más el comando local explícito de limpieza (DD-28); lo no automatizado queda como deuda técnica explícita (DT-02). |

### Decisiones de la revisión de arquitectura (aprobadas por el autor el 2026-11-05)

| Id | Decisión aprobada | Dónde se aplica |
|---|---|---|
| PD-01 | Alternativa A2, **sin disparadores ni funciones en la base**: el `id` sale de `SELECT uuidv7()` de PostgreSQL (DC-01 se conserva), una función pura de Python deriva el código y la aplicación inserta `id` y `codigo` juntos; PostgreSQL garantiza `uq_consultorio_codigo` y `ck_consultorio_codigo_formato`; ante colisión, savepoint y reintento con el código largo distinguiendo esa violación de cualquier otra; el backfill de 0003 solo completa los existentes; el seed de C-02 inserta códigos explícitos sin `UPDATE`, `DELETE` ni sobrescritura; se adaptan los 7 puntos de prueba; prueba de equivalencia Python == SQL; la base de desarrollo no se toca todavía. | DD-13, DD-27, esbozo SQL, specs `modelo-consultorios-usuarios`, `seed-ficticio`, `autenticacion-sesion` |
| PD-02 | `X-CSRF-Token` en la cabecera de login y `/me`; `Cache-Control: no-store` en login, `/me` y logout; `Content-Type: application/json` obligatorio en el login; CORS con `X-CSRF-Token` en `allow_headers` y `expose_headers`; logout con `Origin` + sesión + token; login sin sesión con `Origin` exacto permitido, limitaciones documentadas y rechazos probados; sin excepciones para `curl` ni pruebas. | DD-07, DD-30, "Protección CSRF", specs `proteccion-csrf`, `autenticacion-sesion`, `configuracion-backend` |
| PD-03 | 30 fallos / 15 min por IP → bloqueo de 15 min; se mantiene 5 por par; IPv6 por prefijo /64; IPv4 mapeada normalizada a IPv4; `X-Forwarded-For` ignorada; el bloqueo de IP no afecta sesiones abiertas; un éxito no reinicia el contador de IP; los intentos bloqueados no prolongan el bloqueo; riesgo de redes compartidas documentado. | DD-09, DD-10, DD-19, DT-10, spec `control-intentos-login` |
| PD-04 | Mínimo 15 y máximo 128 puntos de código; espacios y Unicode admitidos; NFKC al establecer y al verificar; sin reglas de composición; rechazo de contraseñas solo con espacios; lista local versionada de contraseñas comunes y términos del contexto, con fuente y licencia documentadas; sin servicios externos; la política solo se aplica a contraseñas nuevas y el login no la revela. | DD-16, PD-09, specs `credenciales-locales`, `autenticacion-sesion` |
| PD-05 | `AUTH_SECRET_KEY` generada con CSPRNG, base64url de ≥ 32 bytes; rechazo de vacía, trivial, de baja diversidad, periódica, mal codificada, con marcadores o igual a la plantilla; nunca se muestra; comando de generación documentado; `.env` fuera de Git; las pruebas generan la clave al ejecutarse; el formato no demuestra entropía. | DD-17, "Configuración", DT-07, spec `configuracion-backend` |
| PD-06 | `/docs`, `/redoc` y `/openapi.json` solo con `APP_ENV=local`; deshabilitadas por defecto en cualquier otro entorno. | DD-18, spec `autenticacion-sesion` |
| PD-08 | Cota de DD-21 corregida (relativa, no absoluta); se mantiene la limpieza oportunista y se agrega `python -m app.mantenimiento limpiar`, solo local, en lotes de ≤ 1000 filas con máximo de lotes configurable; antes de cualquier despliegue fuera de local hace falta un mantenimiento periódico autorizado. | DD-21, DD-28, DT-02, spec `mantenimiento-local` |
| Argon2 | Máximo 4 verificaciones simultáneas por proceso, con espera acotada y respuesta controlada ante saturación. | DD-29, modelo de amenazas, DT-11 |
| Sesiones | **Sin** límite de sesiones por usuario; se mantienen vencimientos y revocación. | DT-09 (riesgo aceptado) |

### Decisiones del punto de control del 2026-11-06 (aprobadas por el autor)

| Id | Decisión aprobada | Dónde se aplica |
|---|---|---|
| PC-01 | 415 para el login con `Content-Type` no admitido; se mantienen la verificación de `Origin` y las respuestas genéricas. | DD-30, spec `autenticacion-sesion` |
| PC-02 | Saturación de Argon2: 503 con `Retry-After: 5` tras una espera máxima de 3 s; no cuenta como fallo; el cupo se libera **siempre**, también ante errores y ante cancelación. | DD-29, spec `autenticacion-sesion`, tarea 3.5 |
| PC-03 | `--max-lotes` 1–1000, por defecto 100; cada lote borra hasta 1000 filas vencidas en su propia transacción; nunca borra sesiones activas ni intentos recientes. | DD-28, spec `mantenimiento-local` |
| PC-04 | `intento_login.descartado_para_cuenta`, con contadores de cuenta y de IP independientes: el éxito reinicia la cuenta y no la IP. | DD-09, DD-10, spec `control-intentos-login` |
| PC-05 | **Cambio**: se elimina el balde compartido para direcciones no analizables. Si la dirección de la conexión directa no puede determinarse, el login se rechaza con 400 **antes** de buscar credenciales, verificar Argon2 o registrar intentos. El estado 400 (PD-10) fue presentado y aprobado por el autor el 2026-11-06: cerrada. | DD-19, DD-23, DD-30, secuencia de login, spec `control-intentos-login` |
| PC-06 | **Cambio**: se mantienen 15–128 puntos de código tras NFKC y el rechazo de contraseñas comunes; la comprobación de términos del contexto pasa a un algoritmo determinista con forma compacta y lista versionada de términos genéricos (DD-16). | DD-16, DD-22, spec `credenciales-locales` |
| PD-09 | Lista inicial de contraseñas comunes **propia**, pequeña y versionada, con criterios de selección, fuente ("elaboración propia del proyecto"), licencia y SHA-256 en la cabecera. No se descargan ni incluyen listas externas. Cerrada. | DD-16, tarea 3.3 |
| PD-10 | Estado HTTP del login por dirección del cliente no determinable: 400 con `{"detail": "No se pudo procesar la solicitud."}` y `Cache-Control: no-store`, sin búsqueda de credenciales, Argon2 ni fila de intento, sin `X-Forwarded-For` no confiable. Cerrada. | DD-19, spec `control-intentos-login` |
| D2 | `docker-compose.yml` monta **solo** `.env.example`, de solo lectura, en el servicio `api` en `/repo/.env.example` (fuera de `/app`); nunca `.env` ni otros secretos. Lo usan las pruebas unitarias de la plantilla (tarea 2.4). | spec `base-de-datos-local`, tarea 2.4 |
| D3 | `scripts/test.ps1` genera en cada ejecución una `AUTH_SECRET_KEY` efímera (CSPRNG, 48 bytes, base64url sin relleno), solo en el entorno del proceso, pasada a los contenedores por nombre (`-e AUTH_SECRET_KEY`), nunca como literal, nunca mostrada ni escrita, y quitada en `finally`. Solo la reciben las pruebas unitarias, `alembic` sobre `db-test` y las de integración. Funciona aunque el `.env` del autor no la tenga; la aplicación normal sigue exigiendo una clave real y no se relaja `config.py`. El valor de `-e NAME` prevalece sobre `env_file` (precedencia de Compose: `run -e` > `environment` > `env_file`). | spec `ejecucion-de-pruebas`, tarea 2.5 |

## Decisiones derivadas

### DD-01. Módulos y punto único de consultas previas al contexto
Paquete nuevo `backend/app/auth/`:
- `claves.py`: generación del token, HMAC con etiquetas de dominio, token CSRF, normalización de la dirección IP con la excepción `DireccionClienteNoDeterminable` (DD-19) y claves de intentos (puro, sin I/O).
- `contrasenas.py`: `PasswordHasher` con parámetros fijos, hash ficticio, verificación uniforme, `necesita_rehash`, validación de formato admitido, normalización NFKC compartida, forma compacta de comparación y política de contraseñas nuevas (DD-16).
- `concurrencia.py`: límite de verificaciones Argon2 simultáneas (DD-29).
- `acceso_previo.py`: **único** módulo que consulta o escribe `consultorio`, `usuario`, `sesion` e `intento_login` sin `ContextoConsultorio` (buscar cuenta por código + email, resolver sesión por HMAC, crear/renovar/revocar sesiones, registrar/contar/descartar intentos, escribir credenciales, alta de consultorio con código derivado (DD-13), limpieza por lotes). C-04 lo adaptará a RLS (DD-27).
- `intentos.py`: política de bloqueo (pura) y orquestación con locks consultivos.
- `servicio.py`: casos de uso `iniciar_sesion`, `resolver_identidad`, `cerrar_sesion`.
- `dependencias.py`: `verificar_origen`, `exigir_direccion_cliente` (DD-19), `exigir_json`, `identidad_actual`, `contexto_consultorio`, `exigir_csrf`; único lugar del código de la aplicación que construye `ContextoConsultorio`.
- `cookies.py`: emisión y borrado de la cookie.
- `reloj.py`: reloj inyectable (UTC).
Además `app/models/codigo.py` (funciones puras `codigo_corto(id)` y `codigo_largo(id)`, compartidas por la aplicación, el seed y las pruebas), `app/api/auth.py` (router), `app/schemas/auth.py` (`EntradaLogin(EsquemaEntrada)` y salidas), `app/credenciales/__main__.py` (comando), `app/mantenimiento/__main__.py` (comando de limpieza, DD-28), `app/models/sesion.py`, `app/models/intento_login.py` y los recursos versionados `app/auth/recursos/contrasenas_comunes.txt` y `app/auth/recursos/terminos_genericos.txt` (DD-16).
*Alternativa descartada*: dispersar las consultas sin contexto en repositorios; obligaría a C-04 a rastrearlas y debilitaría la regla "todo acceso de consultorio pasa por un repositorio acotado".

### DD-02. Token de sesión y HMAC con etiquetas de dominio
Token: `secrets.token_urlsafe(32)` (256 bits, 43 caracteres base64url). Se valida el formato `^[A-Za-z0-9_-]{43}$` antes de consultar la base. La clave HMAC `K` son los **bytes decodificados** de `AUTH_SECRET_KEY` (DD-17). Con esa sola clave se derivan valores distintos mediante etiquetas:
- `token_hmac = HMAC-SHA256(K, b"turnos:sesion:v1\x00" + token)`
- `csrf = base64url(HMAC-SHA256(K, b"turnos:csrf:v1\x00" + sesion.id.bytes))`
- `clave_cuenta = HMAC-SHA256(K, b"turnos:intento-cuenta:v1\x00" + codigo + b"\x00" + email)` (normalizados)
- `clave_ip = HMAC-SHA256(K, b"turnos:intento-ip:v1\x00" + ip_normalizada)` (DD-19)
La búsqueda por igualdad del HMAC (índice único) no filtra información temporal útil: el atacante no controla el HMAC. Rotar `AUTH_SECRET_KEY` invalida todas las sesiones y reinicia los contadores (documentado).
*Alternativas*: SHA-256 sin clave (una fuga de la base permitiría verificar tokens adivinados; con 256 bits es inviable igual, pero el HMAC agrega defensa ante fuga de la base sin la clave); HKDF por subclave (más correcto formalmente, sin beneficio práctico aquí; deuda DT-06).

### DD-03. Reloj de la aplicación inyectable
Todas las comparaciones de vencimiento y ventanas usan `reloj.ahora()` (UTC, `timestamptz`) pasado a las consultas, no `now()` de la base, para poder probar vencimientos sin esperar. *Alternativa*: `now()` de PostgreSQL (un solo reloj, pero las pruebas requerirían manipular filas o esperar). Riesgo: desfase entre réplicas de la API → irrelevante con un solo proceso local (DT-05).

### DD-04. Cálculo de vencimientos
`sesion` guarda `creada_en`, `ultimo_uso_en`, `vence_absoluto_en = creada_en + AUTH_SESSION_MAX_HOURS` y `revocada_en`. Una sesión es válida si `revocada_en IS NULL AND ahora < vence_absoluto_en AND ahora < ultimo_uso_en + AUTH_SESSION_MINUTES`, más usuario y consultorio activos. La inactividad se calcula con el valor **vigente** de la variable (reducirla acorta las sesiones abiertas); el absoluto queda fijo desde la creación. Renovación de `ultimo_uso_en` solo si pasaron ≥ 60 s (reduce escrituras; la inactividad efectiva queda entre 29 y 30 min). La renovación no toca `vence_absoluto_en`, por lo que nunca lo supera. Cookie persistente con `Max-Age = AUTH_SESSION_MAX_HOURS × 3600`, emitida solo en el login.
*Alternativas*: guardar `vence_inactividad_en` (más escrituras y no reacciona a cambios de configuración); cookie de sesión sin `Max-Age` (se pierde al cerrar el navegador; DA-12 pide `Max-Age` coherente).

### DD-05. Logout sin sesión válida → 401
`POST /api/auth/logout` sin sesión válida responde 401 con el cuerpo de no autenticado y borra la cookie. El efecto es idempotente (no queda sesión), y la ruta queda fuera de la lista blanca, coherente con RN-AU-01. *Alternativa*: 204 siempre (más cómodo para el cliente, pero agrega una ruta "pública" que cambia estado).

### DD-06. Rotación de sesión en el login
Todo login exitoso crea un token nuevo; si la petición trae una cookie de sesión válida, esa sesión se revoca en la misma transacción. Evita fijación de sesión y acumulación.

### DD-07. Token CSRF derivado y entregado por cabecera (PD-02 resuelta)
El token CSRF no se almacena: se deriva de `sesion.id` con la clave (DD-02) y se compara con `hmac.compare_digest`. Viaja en la cabecera de respuesta `X-CSRF-Token` del login y de `GET /api/auth/me`, expuesta por CORS (`expose_headers`), no en el JSON, para respetar literalmente DA-13. Un cliente de otro origen permitido (por ejemplo `http://localhost:5173` contra `http://localhost:8000`) puede leerla porque CORS la expone con credenciales.

### DD-08. `Origin` estricto, sin alternativa por `Referer`
Ver "Protección CSRF".

### DD-09. Algoritmo de bloqueo por cuenta
Se registran solo los fallos evaluados. Para el par: se leen los últimos 5 fallos **no descartados para la cuenta** (`descartado_para_cuenta = false`) con `ocurrido_en > ahora − 30 min`. Bloqueado si hay 5, `más_reciente − más_antiguo ≤ 15 min` y `ahora < más_reciente + 15 min`; `Retry-After = ceil(más_reciente + 15 min − ahora)` (mínimo 1). Durante el bloqueo no se evalúa la contraseña ni se registra el intento, así que los intentos bloqueados no prolongan el bloqueo. Un login exitoso **marca** los fallos de su par con `descartado_para_cuenta = true` (no los borra): reinicia el contador de la cuenta sin reducir el contador por IP (DD-10). Los contadores de cuenta y de IP son independientes (PC-04): el de cuenta filtra por `clave_cuenta` y `descartado_para_cuenta = false`; el de IP filtra solo por `clave_ip` y nunca mira la marca.
*Alternativa descartada*: borrar los fallos del par al tener éxito (diseño anterior). Esas filas también cuentan para la IP, así que un atacante con una cuenta válida propia podría reiniciar su contador de IP iniciando sesión cada 29 fallos; contradice la decisión "un éxito no reinicia el contador de IP".

### DD-10. Límite por IP: 30 fallos en 15 min → 15 min (PD-03 resuelta)
Mismo algoritmo que DD-09 con 30 en lugar de 5, sobre **todos** los fallos de la clave de IP (incluidos los descartados para la cuenta). Justificación: un consultorio comparte típicamente una IP pública (NAT) entre 3 a 10 personas; 30 fallos en 15 min admite varios errores de tipeo de todo el equipo sin bloquearlo, y a la vez limita un ataque de rociado desde una IP a ≤ 120 contraseñas por hora sobre cualquier cantidad de cuentas (frente a ilimitado sin el límite). El límite por cuenta (5) es más estricto para el ataque dirigido. El bloqueo de IP solo afecta a `POST /api/auth/login`: las sesiones abiertas desde esa IP siguen funcionando (`/me`, logout y rutas protegidas no consultan intentos). Un éxito no reinicia el contador de IP (DD-09). Localmente todas las peticiones del host llegan desde la puerta de enlace de Docker (una sola IP): aceptable para la v0.1; las pruebas inyectan la dirección del cliente. Valores como constantes del módulo (no variables de entorno) para no abrir superficie de configuración; las pruebas inyectan la política. Riesgo residual de redes compartidas en DT-10.

### DD-11. Intentos sin datos en claro
`intento_login` guarda solo `clave_cuenta` y `clave_ip` (HMAC, 32 bytes), `ocurrido_en` y la marca `descartado_para_cuenta` (booleano, DD-09). No tiene `consultorio_id` ni FK: el par puede no existir. Permite contar por igualdad sin almacenar emails, códigos ni IPs (X1).

### DD-12. Qué cuenta como fallo
Todo login evaluado que responde 401: contraseña incorrecta, cuenta o consultorio inexistentes, credencial nula o de formato no admitido, usuario o consultorio inactivos. Así la respuesta y el conteo no distinguen causas. No cuentan: 403 por `Origin`, 400 por dirección del cliente no determinable (DD-19), 415 por `Content-Type`, 422 por cuerpo, 429 por bloqueo y 503 por saturación de Argon2 (DD-29), porque en ninguno se evaluó la contraseña.

### DD-13. Código de consultorio derivado del `id` en la aplicación (PD-01 resuelta, A2 sin disparadores)
Regla única, definida como funciones puras en `app/models/codigo.py`:
- `codigo_corto(id) = "c-" + id.hex[-12:]` (14 caracteres).
- `codigo_largo(id) = "c-" + id.hex` (34 caracteres).
`uuid.UUID.hex` da 32 dígitos hexadecimales en minúsculas, por lo que ambos cumplen `^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$`. En UUIDv7 de PostgreSQL los últimos 48 bits son aleatorios (`rand_b`); para los ids del seed (generados con `uuid.uuid7()` de Python) incluyen contador y bits aleatorios y son distintos entre sí.
- **Alta de consultorios en la aplicación** (`acceso_previo.insertar_consultorio(sesion, nombre)`; en C-03 no hay endpoint que la use, la usan las pruebas y un Change futuro): (1) `SELECT uuidv7()` en PostgreSQL (el `id` sigue generándolo la base, DC-01; la fuente de ids es inyectable solo en pruebas); (2) `codigo = codigo_corto(id)`; (3) `INSERT` de `id`, `nombre` y `codigo` juntos dentro de un savepoint (`Session.begin_nested()`); (4) si falla con `IntegrityError` cuyo `orig.sqlstate == "23505"` **y** `orig.diag.constraint_name == "uq_consultorio_codigo"`, se revierte el savepoint y se repite una sola vez con `codigo_largo(id)` en otro savepoint; (5) si el largo también viola `uq_consultorio_codigo`, se revierte y se lanza `CodigoConsultorioNoDisponible` (fallo seguro, sin tercer intento ni código inventado). Cualquier otra violación de integridad (clave primaria `pk_consultorio`, otra unicidad, `CHECK`, `NOT NULL`, FK) se propaga sin cambios y sin reintento. El savepoint deja usable la transacción del llamador en todos los casos.
- **Backfill** (0003): la misma regla expresada en SQL en línea, sin crear funciones: corto = `'c-' || right(replace(id::text,'-',''),12)`, largo = `'c-' || replace(id::text,'-','')`; `row_number() OVER (PARTITION BY corto ORDER BY id)`; orden 1 → corto, resto → largo. Solo completa `consultorio.codigo` en las filas existentes.
- **Seed de C-02**: `datos.py` declara el código de cada consultorio como **literal explícito** (`c-c7d08d776d19` y `c-c7d1647cab52`), igual a `codigo_corto(id)` (una prueba unitaria lo verifica); `aplicar.py` agrega `codigo` al `INSERT ... ON CONFLICT DO NOTHING` existente. Sigue sin `UPDATE`, sin `DELETE`, sin escribir `credencial` y sin sobrescribir filas (la prueba de inspección de sentencias se mantiene). Una base que ya tenía el seed obtiene los mismos códigos por el backfill. Si el código de un consultorio del seed ya estuviera ocupado por un consultorio ajeno, `ON CONFLICT DO NOTHING` omite el consultorio, la inserción de sus usuarios falla por FK y el llamador revierte la transacción: el seed falla sin modificar filas (fallo seguro, escenario en `seed-ficticio`).
- **Equivalencia**: una prueba en `db-test` compara, para 1000 UUID aleatorios (v4 y v7), las funciones de Python con las expresiones SQL del backfill.
- **Unicidad (demostración)**: (a) el backfill da el corto solo al orden 1 de cada partición, así que dos cortos iguales no quedan; (b) los largos son inyectivos porque `id` es clave primaria; (c) un corto y un largo nunca coinciden porque tienen longitudes distintas (14 y 34); (d) en altas posteriores, la unicidad la garantiza `uq_consultorio_codigo` en la base, también ante altas concurrentes: la segunda recibe la violación y reintenta con el largo (probabilidad de colisión del corto 2⁻⁴⁸ por par).
- **Determinismo**: la regla depende solo de los `id`; repetir bajada y subida da el mismo resultado.
*Alternativas descartadas*: (1) función + disparador `BEFORE INSERT` en la base (propuesta anterior; rechazada por el autor: mecanismo nuevo en la base y comprobación de existencia frágil bajo RLS); (2) columna generada (`GENERATED ALWAYS AS ... STORED`): no admite códigos explícitos legibles en el futuro ni el fallback de colisión; (3) códigos por nombre (`demo-a`): prohibido por DA-03; (4) valor por defecto de servidor para `codigo`: no puede resolver colisiones.

### DD-14. Clave foránea de `sesion` con `ON DELETE CASCADE`
Las sesiones son datos derivados: si algún día se borra físicamente un usuario, sus sesiones deben desaparecer. Hoy nadie borra usuarios (RN, PA-16). *Alternativa*: `RESTRICT` como en C-02 (obligaría a limpiar sesiones antes; sin beneficio).

### DD-15. Parámetros Argon2id
`time_cost=3`, `memory_cost=65536` KiB (64 MiB), `parallelism=4`, `hash_len=32`, `salt_len=16`, tipo `ID`, fijados en el código (no se depende del valor por defecto de la librería). Corresponde al perfil "segunda recomendación / poca memoria" de RFC 9106 §4 y supera el mínimo de OWASP Password Storage Cheat Sheet (m=19 MiB, t=2, p=1 o equivalentes). Costo estimado: decenas a ~100 ms y 64 MiB por verificación en un equipo de desarrollo; la concurrencia está acotada por DD-29. Hash ficticio: se calcula una vez al iniciar el servicio con los mismos parámetros y una contraseña aleatoria descartada. Formatos admitidos: solo cadenas PHC que empiezan con `$argon2id$` y que la librería puede analizar; cualquier otro valor → se verifica contra el hash ficticio y se rechaza. `check_needs_rehash` tras un login exitoso → `UPDATE usuario SET credencial = :nuevo WHERE id = :id AND credencial = :anterior` (el rehash se calcula dentro del mismo cupo de DD-29).
Versiones: `argon2-cffi==25.1.0` (requires_python ≥ 3.8) y `argon2-cffi-bindings==26.1.0` (requires_python ≥ 3.10; wheels `cp310-abi3` para manylinux x86_64/aarch64 y win_amd64, publicados el 2026-08-20; cubren CPython 3.14 de la imagen `python:3.14.10-slim-trixie`). Para Python 3.14 requiere `cffi>=2` (última vista: 2.1.1) y `pycparser`: Apply fija versiones exactas tras verificar en PyPI, solo lectura, que haya wheels para cp314 o abi3 en Linux.

### DD-16. Política de contraseñas (PD-04 resuelta)
- **Normalización**: `unicodedata.normalize("NFKC", texto)` en una sola función de `contrasenas.py`, usada al establecer (comando de credenciales; C-05 la reutilizará) y al verificar (login). Se hashea y se verifica el texto normalizado. No se recortan espacios ni se cambian mayúsculas.
- **Login**: el único control es el máximo de 128 puntos de código sobre la **entrada sin normalizar** (defensa ante entradas enormes; 422 sin verificar). El login no aplica mínimo, lista ni términos del contexto: no revela la política ni produce diferencias observables entre cuentas. Limitación conocida: una contraseña cercana a 128 puntos de código tecleada en forma descompuesta podría superar el máximo en bruto; con entradas habituales (formas compuestas de los navegadores) no ocurre.
- **Contraseñas nuevas** (solo al establecerlas): sobre el texto normalizado con NFKC, 15 a 128 puntos de código; se rechaza si está formada solo por espacios en blanco; espacios y cualquier carácter Unicode admitidos; sin reglas de composición (NIST SP 800-63B); se rechaza si su forma compacta coincide con la forma compacta de una entrada de la lista local de contraseñas comunes o si **contiene** la forma compacta de algún término del contexto (algoritmo siguiente, PC-06).
- **Forma compacta** (función única `forma_compacta(texto)`, usada para la contraseña, los términos y las entradas de las listas): (1) NFKC; (2) `str.casefold()`; (3) NFKD y eliminación de los caracteres de categoría combinante (`unicodedata.combining(c) != 0`); (4) se conservan solo los caracteres con `str.isalnum()`. Ejemplos: `Odontología-del Barrio` → `odontologiadelbarrio`; `ficticio-a` → `ficticioa`; `PÉRSONA` → `persona`. Los **tokens** de un texto son las secuencias maximales de caracteres alfanuméricos del resultado del paso (3), es decir, el texto partido por cualquier carácter no alfanumérico.
- **Términos del contexto** (todos en forma compacta; los vacíos se descartan):
  - (a) el código del consultorio completo;
  - (b) la parte local completa del email y sus tokens de ≥ 4 caracteres;
  - (c) las etiquetas del dominio del email de ≥ 4 caracteres, **salvo** las que figuran en la lista de términos genéricos;
  - (d) los tokens de ≥ 4 caracteres del nombre del consultorio (`consultorio.nombre`) y del nombre del usuario (`usuario.nombre`, campo existente y obligatorio en el modelo de C-02), **salvo** los de la lista de términos genéricos;
  - (e) los términos fijos del sistema `turnos`, `odontologia`, `consultorio` y el nombre del sistema `turnosodontologia` (forma compacta de `turnos odontologia`, `turnos_odontologia` y `turnos-odontologia`). La lista de términos genéricos **no** elimina estos términos.
- **Regla de rechazo**: la contraseña se rechaza por contexto si y solo si su forma compacta contiene como subcadena la forma compacta de al menos un término. El conjunto de términos se trata como conjunto (sin orden ni duplicados), así que el resultado no depende del orden en que se calculan ni se recorren los términos. Función pura y determinista: mismas entradas → mismo resultado; probada con casos de mayúsculas, diacríticos, separadores y orden.
- **Lista de términos genéricos**: archivo versionado `app/auth/recursos/terminos_genericos.txt` (un término por línea, ya en forma compacta, ordenado, sin duplicados), con cabecera que documenta fuente ("elaboración propia del proyecto"), licencia del repositorio, SHA-256 del contenido y estos criterios de inclusión: dominios y etiquetas reservados o de documentación (`example`, `test`, `invalid`, `localhost`, `local`); proveedores de correo comunes (`gmail`, `hotmail`, `outlook`, `yahoo`, `live`, `icloud`); etiquetas DNS genéricas (`com`, `net`, `org`, `edu`, `gob`, `mail`, …); palabras genéricas de nombres de consultorios (por ejemplo `clinica`, `centro`, `dental`, `consultorio`; este último sigue rechazándose por ser término fijo del sistema). Evita rechazos indiscriminados por fragmentos de dominio genéricos: con el email `persona.ficticia@example.test`, `example` y `test` no son términos del contexto. Algunas entradas de la lista tienen < 4 caracteres (`com`): no afectan porque solo se aplican a etiquetas y tokens de ≥ 4.
- **Lista de contraseñas comunes (PD-09 cerrada)**: archivo versionado `app/auth/recursos/contrasenas_comunes.txt`, inicial, pequeño y de **elaboración propia del proyecto** (licencia del repositorio), con cabecera que registra fuente, licencia, fecha, criterios de selección y SHA-256 del contenido; solo entradas de ≥ 15 puntos de código tras NFKC (las más cortas ya las rechaza el mínimo). Criterios de selección: secuencias numéricas y de teclado (`123456789012345`, `qwertyuiopasdfgh`), palabras de contraseña con sufijos numéricos en español (`contraseña123456`), repeticiones de un carácter o de una palabra corta y frases comunes de bienvenida o de acceso. No se descargan ni se incluyen listas externas; sin servicios externos en ejecución.
- **Mensajes**: el comando local indica qué regla falló (longitud, solo espacios, común, término del contexto) sin repetir la contraseña ni el término.
- La política solo se aplica a contraseñas nuevas; las credenciales existentes no se revalidan.

### DD-17. Rangos de configuración y validación de `AUTH_SECRET_KEY` (PD-05 resuelta)
`AUTH_SESSION_MINUTES` 5–480, `AUTH_SESSION_MAX_HOURS` 1–24, inactividad ≤ absoluto. `AUTH_SECRET_KEY` (SecretStr), validada en este orden y siempre sin mostrar el valor:
1. no vacía y sin espacios en blanco;
2. alfabeto base64url `^[A-Za-z0-9_-]+={0,2}$` con relleno opcional y correcto; se decodifica en modo estricto (otro alfabeto, `+`, `/`, `.` o relleno incorrecto → "mal codificada");
3. ≥ 32 bytes decodificados (≥ 43 caracteres sin relleno); la clave HMAC son esos bytes;
4. ≥ 20 caracteres distintos en el texto codificado (diversidad);
5. no periódica: el texto no es la repetición de un bloque más corto (cualquier período `p ≤ len/2` con `s == (s[:p] * k)[:len(s)]`);
6. sin marcadores, sin distinguir mayúsculas: `cambiar`, `reemplazar`, `ficticio`, `ficticia`, `example`, `ejemplo`, `changeme`, `secret`, `password`, `contrasena` (todos de ≥ 6 caracteres: la probabilidad de que aparezcan por azar en una clave generada es < 10⁻⁶);
7. distinta del valor exacto de `.env.example` (constante compartida; una prueba verifica que coincide con la plantilla).
Errores: un mensaje fijo por regla que nombra `AUTH_SECRET_KEY` (`input` oculto en el error de Pydantic). Comando de generación documentado: `python -c "import secrets; print(secrets.token_urlsafe(48))"` (64 caracteres, 48 bytes). Las pruebas generan la clave al ejecutarse con `secrets.token_urlsafe(48)` y nunca usan literales. La validación de formato y longitud **no demuestra entropía**: un valor elegido a mano que cumpla todas las reglas pasa (DT-07 reducida).
*Alternativa*: aceptar texto arbitrario de ≥ 32 caracteres (diseño anterior; dejaba pasar el valor de ejemplo).

### DD-18. Documentación de la API solo en local (PD-06 resuelta)
`crear_app` construye `FastAPI(docs_url=None, redoc_url=None, openapi_url=None, swagger_ui_oauth2_redirect_url=None)` salvo con `APP_ENV=local`, donde habilita `/docs`, `/redoc` y `/openapi.json` (sin `/docs/oauth2-redirect`, porque no hay OAuth). Denegado por defecto: cualquier valor futuro de `APP_ENV` las deja deshabilitadas. La lista blanca de rutas públicas es condicional (spec `autenticacion-sesion`). Las pruebas usan `APP_ENV=test` (404 para las tres) y construyen una app con `APP_ENV=local` solo para comprobar que existen.
*Observación (no bloqueante, X3)*: Swagger UI y ReDoc de FastAPI cargan sus recursos desde el CDN `cdn.jsdelivr.net` en el navegador del desarrollador. No se contrata ni configura ningún servicio, pero es una petición externa en local; servir esos recursos desde el propio backend queda como deuda (DT-12).

### DD-19. Dirección del cliente sin cabeceras de proxy, normalización y rechazo si no es determinable (PC-05)
La IP es `request.client.host`. El servicio `api` arranca con `--no-proxy-headers`, para que uvicorn no reescriba la dirección desde `X-Forwarded-For` aunque el par sea `127.0.0.1`. Normalización antes del HMAC (`claves.normalizar_ip`, con `ipaddress.ip_address`): IPv4 → `v4:<dirección>`; IPv4 mapeada en IPv6 (`::ffff:a.b.c.d`) → la misma IPv4 (`v4:a.b.c.d`); IPv6 → `v6:<prefijo /64>` (por ejemplo `v6:2001:db8:1:2::/64`), porque un mismo cliente controla típicamente su /64 completo.
- **Dirección no determinable**: si `request.client` es `None`, o su `host` no se analiza como dirección IP con `ipaddress` (por ejemplo `testclient`, cadena vacía o un nombre de host), `claves.normalizar_ip` lanza `DireccionClienteNoDeterminable` (no devuelve ningún balde). La dependencia `exigir_direccion_cliente` del login la traduce, **antes** de buscar credenciales, adquirir un cupo de Argon2 o registrar intentos, en: HTTP 400, cuerpo exacto `{"detail": "No se pudo procesar la solicitud."}`, `Cache-Control: no-store`, sin `Set-Cookie`, sin filas en `intento_login` y una línea de registro técnica con el código fijo `direccion_cliente_no_determinable`, sin IP, email ni contraseña (DD-25).
- **Por qué no es una evasión**: nunca se evalúan credenciales sin una dirección determinable, así que no puede usarse para esquivar el límite por IP ni el de cuenta; con la dirección directa de uvicorn sin cabeceras de proxy, el caso solo aparece por un transporte o una configuración anómalos. Se descarta el balde compartido anterior (`otra`): mezclaba clientes no relacionados en un mismo contador y permitía que uno bloqueara a todos.
- **Alcance**: solo `POST /api/auth/login` usa la dirección; `POST /api/auth/logout`, `GET /api/auth/me` y las rutas protegidas no dependen de ella.
- **Estado 400** (PD-10, cerrada): aprobado por el autor el 2026-11-06 (petición que el servidor no puede procesar por una condición de la conexión, sin revelar detalle). Nunca se usa un `X-Forwarded-For` no confiable; no hay búsqueda de credenciales, Argon2 ni fila en `intento_login`. Se prueban dirección inválida, ausente y válida; el orden de rechazos se mantiene.
Detrás de un proxy real haría falta configurar explícitamente los proxies de confianza (DT-04).

### DD-20. Sesión de base por petición
`crear_app` crea el motor con `crear_engine(settings)` (sin conectar; DM-09) y una fábrica en `app.state`; la dependencia `obtener_sesion_db` abre y cierra una `Session` por petición. El health no la usa, así que sigue sin conectar. Las pruebas sustituyen el motor por el de `db-test` mediante la fábrica de la app, sin `dependency_overrides` que eviten las validaciones.

### DD-21. Limpieza oportunista acotada (cota corregida, PD-08)
- En cada login evaluado: `DELETE FROM intento_login WHERE id IN (SELECT id FROM intento_login WHERE ocurrido_en < ahora − 24 h ORDER BY ocurrido_en LIMIT 100)`.
- En cada login exitoso: hasta 100 sesiones revocadas o vencidas (absoluta o por inactividad).
**Cota (relativa, no absoluta)**: cada login evaluado inserta como máximo 1 fila y borra hasta 100 vencidas, así que mientras haya logins el remanente viejo se drena a razón de hasta 99 filas por intento; en régimen, `intento_login` queda acotada aproximadamente por el doble de los fallos de las últimas 24 h (los de la ventana vigente más un remanente de la anterior aún no drenado), y la cota depende del caudal de logins evaluados. No hay cota absoluta: un ataque distribuido desde muchas IP puede insertar filas al ritmo que permitan los límites (30 por IP cada 15 min) multiplicado por la cantidad de IP. `sesion` crece como máximo una fila por login exitoso y cada login exitoso borra hasta 100 inválidas. Si no hay logins, las tablas no crecen pero tampoco se drenan: para eso existe el comando explícito (DD-28). Retención de 24 h de fallos: la ventana máxima consultada es 30 min; el margen permite diagnóstico sin datos personales. Sin tarea programada (DT-02).

### DD-22. Comando de credenciales
`docker compose run --rm -it api python -m app.credenciales [--reemplazar]`. Flujo: guardia `APP_ENV=local` sin conectar → exigir `sys.stdin.isatty()` → pedir código y email con `input()` (no son secretos) → buscar la cuenta en `acceso_previo` (incluye `usuario.nombre` y `consultorio.nombre`) → si tiene credencial y no hay `--reemplazar`, fallar → contraseña dos veces con `getpass.getpass` → normalización NFKC y política de contraseñas nuevas con los términos del contexto calculados a partir del código, el email, el nombre del consultorio y el nombre del usuario (DD-16) → con `--reemplazar`, pedir escribir `REEMPLAZAR` → hash y `UPDATE` de `credencial` → con `--reemplazar`, revocar todas las sesiones activas del usuario → `commit`. Salida solo con textos fijos (`credencial establecida`, `credencial reemplazada; sesiones revocadas: N`). `argparse` solo declara `--reemplazar`; cualquier otro argumento falla. Costuras de prueba: `leer_visible`, `leer_oculto`, `es_interactivo`, `abrir_sesion` (como `main()` del seed). Se permite establecer credenciales de usuarios inactivos (el login sigue bloqueado por DA-09). El hash del comando corre en un proceso aparte y no consume cupos de DD-29.

### DD-23. Respuestas exactas
- Login 401: `{"detail": "No se pudo iniciar sesión."}`.
- Sin sesión: `{"detail": "No autenticado."}`.
- 403 de `Origin` o CSRF: `{"detail": "Solicitud rechazada."}`.
- 400 del login por dirección del cliente no determinable: `{"detail": "No se pudo procesar la solicitud."}` (DD-19; estado aprobado, PD-10 cerrada).
- 415 del login: `{"detail": "Tipo de contenido no admitido."}` (DD-30).
- 429: `{"detail": "Demasiados intentos. Intente más tarde."}` + `Retry-After` en segundos.
- 503 por saturación de Argon2: `{"detail": "Servicio ocupado. Intente más tarde."}` + `Retry-After: 5` (DD-29).
- 422: el formato estándar de FastAPI (identifica el campo; no contiene valores sensibles porque los esquemas no reflejan la contraseña: `hide_input` en el manejador de validación de la ruta de login).
- Todas las respuestas de login, `/me` y logout, incluidas las de error, llevan `Cache-Control: no-store` (DD-30).

### DD-24. Pruebas sin atajos
Las pruebas de API usan `TestClient(app, base_url="https://testserver")` para que httpx envíe cookies `Secure`, y siempre envían `Origin: http://localhost:5173` y `Content-Type: application/json` salvo en los escenarios de rechazo. No existe ningún interruptor que desactive `Origin`, CSRF, `Content-Type`, límites ni `Secure`; tampoco hay excepciones para `curl`. La dirección del cliente se inyecta siempre de forma explícita (parámetro `client` de `TestClient` o el `scope` ASGI de la petición de prueba) con direcciones de documentación válidas (`203.0.113.0/24` y `2001:db8::/32`): el valor por defecto de Starlette `TestClient` es el host `testclient`, que **no** es una dirección IP y haría responder 400 a todo login (DD-19). Solo los escenarios de dirección no determinable usan `testclient` o `client=None` a propósito. La concurrencia se prueba con hilos y conexiones reales a `db-test`.

### DD-25. Registros
La autenticación no registra datos de la petición. Si se registra algo, son códigos de evento fijos (`login_rechazado`, `credencial_formato_no_admitido`, `verificacion_saturada`, `direccion_cliente_no_determinable`) sin email, código, IP, ids ni tokens. Se prueba con `caplog` en `DEBUG`.

### DD-26. Compatibilidad con un futuro proxy de Vite
Con proxy (`/api` → `http://api:8000`), el navegador ve un único origen `http://localhost:5173` y sigue enviando `Origin: http://localhost:5173` en los `POST`; la validación de `Origin` y la cookie (`Path=/`, sin `Domain`) funcionan sin cambios. Sin proxy, `SameSite=Lax` permite la cookie porque `localhost:5173` y `localhost:8000` son el mismo sitio, y CORS con credenciales autoriza la lectura y expone `X-CSRF-Token`. C-06 elige; C-03 no toca el frontend.

### DD-27. Preparación para RLS (C-04)
Las consultas de `acceso_previo` necesitan leer `usuario`, `consultorio` y `sesion` antes de conocer el consultorio. C-04 podrá: ejecutar ese módulo con un rol con `BYPASSRLS` limitado, o funciones `SECURITY DEFINER` acotadas, o fijar la variable de sesión del consultorio inmediatamente después de resolver la sesión. Concentrar el acceso en un módulo deja una sola superficie a adaptar. El código de consultorio no depende de disparadores ni de consultas de existencia: la unicidad la impone `uq_consultorio_codigo`, que PostgreSQL verifica sin aplicar políticas RLS, así que la detección de colisión de DD-13 sigue funcionando bajo RLS. El alta de consultorios y la limpieza (DD-28) también pasan por `acceso_previo`.

### DD-28. Comando local de limpieza (PD-08 resuelta; parámetros confirmados en PC-03)
`docker compose run --rm api python -m app.mantenimiento limpiar [--max-lotes N]`. Flujo: `argparse` valida el subcomando y `--max-lotes` (entero 1–1000, por defecto 100) **antes** de conectar → guardia `APP_ENV=local` sin conectar → por cada tabla, lotes de **1000** filas como máximo, cada uno en su propia transacción: `DELETE ... WHERE id IN (SELECT id ... WHERE <vencida> ORDER BY ... LIMIT 1000)`; se detiene al llegar a `--max-lotes` lotes en esa tabla o cuando un lote borra menos de 1000. Criterios (con `reloj.ahora()` y la configuración vigente): sesiones revocadas, con vencimiento absoluto alcanzado o con inactividad mayor que `AUTH_SESSION_MINUTES`; intentos con más de 24 h. Nunca borra sesiones válidas ni intentos recientes. Salida solo con cantidades: `sesiones eliminadas: N; intentos eliminados: M`. El máximo de lotes es una opción de línea de comandos y no una variable de entorno, para no ampliar la configuración de la API; por ejecución borra como máximo `1000 × N` filas por tabla. Índice `ix_sesion_revocada_en` para el criterio de revocación. Costuras de prueba: `abrir_sesion` y reloj (como el comando de credenciales). Antes de cualquier despliegue fuera de local será obligatorio un mecanismo de mantenimiento periódico autorizado (DT-02); C-03 no crea servicio ni tarea programada.

### DD-29. Concurrencia acotada de Argon2 (aprobada)
`concurrencia.py` mantiene un `threading.BoundedSemaphore(4)` **por proceso**. Cada login evaluado adquiere un cupo con `acquire(timeout=3)` justo antes de la verificación (después de evaluar bloqueos y buscar la cuenta) y lo libera después de la verificación y del rehash eventual. Como el hash ficticio también consume un cupo, cuentas existentes e inexistentes se comportan igual. Si no obtiene cupo en 3 s: `ROLLBACK` sin escrituras, 503 con `Retry-After: 5` y el cuerpo de DD-23; no se registra fallo, no se crea sesión y no se revela nada de la cuenta.
- **Liberación garantizada (PC-02)**: el cupo se toma con un administrador de contexto cuyo `finally` lo libera exactamente una vez ante cualquier salida: éxito, excepción del verificador o del rehash, error de base y cancelación (`BaseException`, incluidas `asyncio.CancelledError` y `KeyboardInterrupt`, o la desconexión del cliente). Si la cancelación ocurre durante la espera de `acquire`, no se toma cupo y no hay nada que liberar. `BoundedSemaphore` convierte una liberación doble en error, así que una fuga o una doble liberación se detectan en las pruebas.
- **Por qué 4**: 4 × 64 MiB = 256 MiB de pico por proceso, compatible con un equipo de desarrollo; `parallelism=4` ya usa varios hilos por verificación.
- **Por qué 3 s**: con ~50–100 ms por verificación y 4 cupos, una espera de 3 s absorbe una cola de ~120–240 verificaciones (picos legítimos) y a la vez acota cuánto tiempo un hilo del pool queda retenido.
- **Por qué 503 y no 429**: 429 indica un límite por cliente; la saturación es global del proceso y puede afectar a usuarios legítimos que no excedieron nada. 503 con `Retry-After` (RFC 9110 §15.6.4) describe una sobrecarga temporal del servicio.
- **Alcance**: el límite es por proceso; con varios workers o réplicas el pico de memoria se multiplica y habrá que dimensionar recursos globales (DT-11). Los logins desde una misma IP ya quedan serializados por el lock consultivo de IP (DD-10), así que solo varias IP pueden competir por los cupos.
- **Pruebas**: un verificador inyectado que se bloquea hasta una señal y registra la concurrencia máxima observada (nunca > 4 con 8 logins concurrentes de IP distintas), un tiempo de espera inyectado corto para probar el 503, y verificadores que lanzan una excepción común y una cancelación (`asyncio.CancelledError`) en 4 llamadas seguidas: después, los 4 cupos siguen disponibles.

### DD-30. `Content-Type` del login y respuestas no almacenables (PD-02 resuelta)
- **415**: `exigir_json` (después de `verificar_origen` y `exigir_direccion_cliente`, antes de la validación del cuerpo) exige que el tipo de medio de `Content-Type` sea `application/json` (sin distinguir mayúsculas) con, a lo sumo, el parámetro `charset=utf-8`; cualquier otro valor o su ausencia → 415. Se elige 415 y no 422 porque el problema es el tipo de medio, no el contenido de un cuerpo JSON (RFC 9110 §15.5.16), y así el rechazo ocurre antes de analizar el cuerpo. Defensa: `text/plain`, `application/x-www-form-urlencoded` y `multipart/form-data` son los tipos de una petición "simple" que un formulario de otro sitio puede enviar sin preflight; exigir JSON obliga al preflight CORS. Orden de los rechazos del login: 403 (`Origin`) → 400 (dirección del cliente no determinable, DD-19) → 415 → 422 → 429 → 503 → 401.
- **`Cache-Control: no-store`** en todas las respuestas de `POST /api/auth/login`, `GET /api/auth/me` y `POST /api/auth/logout`, incluidas las de error (400, 401, 403, 415, 422, 429, 503), porque llevan identidad, `Set-Cookie` o `X-CSRF-Token`. Se aplica por ruta (dependencia y manejadores de error de esas rutas), no globalmente.

## Modelo de datos (esbozo de la migración 0003)

```sql
-- revision 0003, down_revision 0002. Una sola transacción (DDL transaccional de PostgreSQL).
-- Sin funciones ni disparadores (PD-01, A2).
ALTER TABLE consultorio ADD COLUMN codigo text NULL;

-- Backfill genérico y determinista: único UPDATE de 0003, solo sobre la columna nueva.
UPDATE consultorio AS c
   SET codigo = CASE WHEN o.orden = 1
                     THEN 'c-' || right(replace(c.id::text, '-', ''), 12)
                     ELSE 'c-' || replace(c.id::text, '-', '') END
  FROM (SELECT id,
               row_number() OVER (PARTITION BY right(replace(id::text, '-', ''), 12)
                                  ORDER BY id) AS orden
          FROM consultorio) AS o
 WHERE o.id = c.id;

ALTER TABLE consultorio ALTER COLUMN codigo SET NOT NULL;   -- sin valor por defecto
ALTER TABLE consultorio ADD CONSTRAINT uq_consultorio_codigo UNIQUE (codigo);
ALTER TABLE consultorio ADD CONSTRAINT ck_consultorio_codigo_formato
  CHECK (codigo ~ '^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$');

CREATE TABLE sesion (
  id                uuid        NOT NULL DEFAULT uuidv7(),
  consultorio_id    uuid        NOT NULL,
  usuario_id        uuid        NOT NULL,
  token_hmac        bytea       NOT NULL,
  creada_en         timestamptz NOT NULL,
  ultimo_uso_en     timestamptz NOT NULL,
  vence_absoluto_en timestamptz NOT NULL,
  revocada_en       timestamptz NULL,
  CONSTRAINT pk_sesion PRIMARY KEY (id),
  CONSTRAINT uq_sesion_token_hmac UNIQUE (token_hmac),
  CONSTRAINT fk_sesion_consultorio_id_usuario FOREIGN KEY (consultorio_id, usuario_id)
    REFERENCES usuario (consultorio_id, id) ON DELETE CASCADE,
  CONSTRAINT ck_sesion_token_hmac_longitud CHECK (octet_length(token_hmac) = 32),
  CONSTRAINT ck_sesion_vencimientos_coherentes
    CHECK (creada_en < vence_absoluto_en AND ultimo_uso_en >= creada_en AND ultimo_uso_en <= vence_absoluto_en),
  CONSTRAINT ck_sesion_revocacion_posterior CHECK (revocada_en IS NULL OR revocada_en >= creada_en)
);
CREATE INDEX ix_sesion_consultorio_id_usuario_id ON sesion (consultorio_id, usuario_id);
CREATE INDEX ix_sesion_vence_absoluto_en ON sesion (vence_absoluto_en);
CREATE INDEX ix_sesion_ultimo_uso_en ON sesion (ultimo_uso_en);
CREATE INDEX ix_sesion_revocada_en ON sesion (revocada_en);

CREATE TABLE intento_login (
  id                     bigint      GENERATED ALWAYS AS IDENTITY,
  clave_cuenta           bytea       NOT NULL,
  clave_ip               bytea       NOT NULL,
  ocurrido_en            timestamptz NOT NULL,
  descartado_para_cuenta boolean     NOT NULL DEFAULT false,
  CONSTRAINT pk_intento_login PRIMARY KEY (id),
  CONSTRAINT ck_intento_login_claves_longitud
    CHECK (octet_length(clave_cuenta) = 32 AND octet_length(clave_ip) = 32)
);
CREATE INDEX ix_intento_login_clave_cuenta_ocurrido_en ON intento_login (clave_cuenta, ocurrido_en);
CREATE INDEX ix_intento_login_clave_ip_ocurrido_en ON intento_login (clave_ip, ocurrido_en);
CREATE INDEX ix_intento_login_ocurrido_en ON intento_login (ocurrido_en);
```

`downgrade()` (solo `db-test`): borra `intento_login`, `sesion`, las restricciones y la columna `codigo`, en orden inverso. No toca `usuario` ni `btree_gist`. Nunca `down -v` ni recreación de la base.

Modelos: `Consultorio.codigo: Mapped[str]` con `nullable=False` y **sin** `server_default` ni `FetchedValue` (siempre lo indica quien inserta), `UniqueConstraint` y `CheckConstraint` con los mismos nombres; `Sesion` e `IntentoLogin` con las restricciones e índices anteriores (`descartado_para_cuenta` con `server_default=false()`). La comparación automática de C-02 (`compare_metadata`) debe seguir sin diferencias, y una prueba de catálogo comprueba que 0003 no deja disparadores en `consultorio` ni funciones propias en `public` (fuera de las de extensiones).

`intento_login.id` es `bigint` de identidad porque nunca se expone; `sesion.id` es UUIDv7 por coherencia y porque alimenta el token CSRF.

## Secuencias

**Login** (`POST /api/auth/login`):
1. `verificar_origen` → 403 si `Origin` falta, es `null` o no está en la lista.
2. `exigir_direccion_cliente` → normalizar la IP (DD-19); 400 si `request.client` es `None` o su `host` no es una dirección IP, sin buscar credenciales, sin Argon2 y sin registrar intentos.
3. `exigir_json` → 415 si el tipo de medio no es `application/json` (DD-30).
4. Validación de `EntradaLogin` (`extra='forbid'`, `contrasena` ≤ 128 puntos de código sin normalizar) → 422.
5. Normalizar código y email; normalizar la contraseña con NFKC; calcular `clave_cuenta` y `clave_ip` (con la IP ya normalizada en el paso 2).
6. Transacción (READ COMMITTED): `pg_advisory_xact_lock(k_cuenta)` y luego `pg_advisory_xact_lock(k_ip)` (siempre en ese orden; `k` = primeros 8 bytes de cada clave como `bigint`).
7. Evaluar bloqueo de cuenta y de IP (DD-09, DD-10) → si hay bloqueo, `COMMIT` sin escrituras y 429 con el mayor `Retry-After`.
8. `acceso_previo.buscar_cuenta(codigo, email)`: `usuario JOIN consultorio` por `consultorio.codigo` y `usuario.email`.
9. Adquirir un cupo de Argon2 (DD-29) → sin cupo en 3 s: `ROLLBACK` y 503. Desde aquí el cupo se libera en un `finally` ante cualquier salida, también ante errores y cancelación (PC-02).
10. Una sola verificación Argon2id: contra la credencial si existe y su formato es admitido; si no, contra el hash ficticio. Éxito = verificación correcta con credencial real **y** usuario activo **y** consultorio activo.
11. Fallo → liberar cupo, `INSERT intento_login`, limpieza de intentos (DD-21), `COMMIT`, 401.
12. Éxito → rehash si corresponde y liberar cupo; marcar los fallos del par como descartados para la cuenta (DD-09); revocar la sesión de la cookie entrante si es válida (DD-06); `INSERT sesion`; limpiezas; `COMMIT`; 200 con `Set-Cookie`, `X-CSRF-Token` y el cuerpo de DA-13.
Todas las respuestas llevan `Cache-Control: no-store`.

**Petición protegida** (`identidad_actual`):
1. Leer `turnos_session`; formato inválido o ausente → 401 (y borrar cookie si venía).
2. `acceso_previo.resolver_sesion(HMAC)`: `sesion JOIN usuario JOIN consultorio`.
3. Validar revocación, vencimientos (DD-04) y `activo` de usuario y consultorio → 401 + borrar cookie.
4. Si `ahora − ultimo_uso_en ≥ 60 s`: `UPDATE sesion SET ultimo_uso_en = :ahora WHERE id = :id AND revocada_en IS NULL` y `COMMIT` propio.
5. Devolver `IdentidadAutenticada(sesion_id, usuario_id, rol, contexto=ContextoConsultorio(consultorio_id))`. `contexto_consultorio` devuelve `identidad.contexto`. No consulta intentos: un bloqueo de IP no afecta esta secuencia.

**Logout**: `verificar_origen` (403) → `identidad_actual` (401 + borrar cookie) → `exigir_csrf` (403) → `UPDATE sesion SET revocada_en = :ahora WHERE id = :id AND revocada_en IS NULL` → `COMMIT` → 204 con `Set-Cookie: turnos_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax[; Secure]` y `Cache-Control: no-store`.

## Protección CSRF (DA-11, PD-02)

1. **Token inicial**: el cliente lo obtiene de la cabecera `X-CSRF-Token` de la respuesta 200 del login y de `GET /api/auth/me` (para recuperarlo tras recargar la página), expuesta por CORS. Es distinto del token de sesión: se deriva con la clave de `sesion.id`, no permite resolver la sesión ni autenticarse y no sirve sin la cookie HttpOnly. No va en el JSON (DA-13). Las respuestas que lo llevan son `no-store`.
2. **Login sin sesión**: no hay token posible antes de la sesión; la protección es `Origin` obligatorio e igual a un origen permitido, `Content-Type: application/json` obligatorio (fuerza el preflight CORS: un formulario de otro sitio no puede enviarlo), y `SameSite=Lax`. Un "login CSRF" (forzar a la víctima a entrar en la cuenta del atacante) exige un `POST` cross-origin desde el navegador de la víctima, que siempre envía un `Origin` no permitido → 403. **Limitaciones documentadas**: (a) la defensa se apoya en que los navegadores envían `Origin` en todo `POST`; un navegador antiguo que no lo hiciera queda rechazado igual (403), nunca aceptado; (b) un cliente fuera del navegador puede falsificar `Origin`, pero no tiene las cookies de la víctima, así que no puede montarse sobre su sesión: solo puede iniciar sesión con credenciales que ya conoce, lo que ya acota el control de intentos; (c) `Origin` no autentica a nadie: es una defensa contra peticiones cruzadas del navegador, no un control de acceso. Un token pre-sesión no agregaría protección frente a navegadores modernos y complicaría el flujo; se descarta. Pruebas de rechazo: sin `Origin`, `Origin: null`, origen ajeno, solo `Referer`, diferencias mínimas de mayúsculas o barra, y formulario cross-site.
3. **Logout**: requiere `Origin` permitido, sesión válida y `X-CSRF-Token` de esa sesión; evita que otro sitio cierre sesiones ajenas.
4. **Clientes sin `Origin` (curl, pruebas)**: política estricta para métodos que cambian estado: sin `Origin` → 403, sin alternativa por `Referer` (puede faltar o estar recortado por `Referrer-Policy`, y agregar una segunda vía amplía la superficie). Las pruebas y `curl` deben enviar `-H "Origin: http://localhost:5173"` y `-H "Content-Type: application/json"`. No hay modo de pruebas ni excepción que lo desactive.
5. **Por qué la falta de `Origin` no es una evasión**: los navegadores actuales envían `Origin` en toda petición cross-origin y en todo `POST` (también same-origin), así que una petición sin `Origin` no proviene de un navegador engañado; y un cliente fuera del navegador no tiene la cookie de la víctima. Además se rechaza: rechazar en lugar de aceptar elimina el único caso dudoso.

Comparación de `Origin`: igualdad exacta de cadena contra `CORS_ALLOWED_ORIGINS` (sin normalizar mayúsculas ni barras). Las rutas `GET` nunca cambian datos de negocio (solo la renovación de `ultimo_uso_en`, que no es explotable por CSRF).

## Control de intentos (DA-05, PD-03)

- **Concurrencia**: los locks consultivos de transacción por cuenta y por IP serializan los intentos del mismo par o IP; con READ COMMITTED, cada transacción ve los fallos confirmados por la anterior antes de decidir. Orden fijo (cuenta → IP) para evitar interbloqueos. Colisiones de los 64 bits de lock solo agregan serialización. El lock se mantiene durante la verificación Argon2 (~100 ms) y, en el peor caso, durante la espera de un cupo (≤ 3 s, DD-29): aceptable.
- **Vencimiento**: los bloqueos no se guardan; se calculan desde los fallos (DD-09, DD-10). No hay estado que limpiar al vencer. Los intentos bloqueados no se registran y no prolongan ningún bloqueo.
- **Éxito**: reinicia solo el contador de la cuenta (marca `descartado_para_cuenta`); el de IP sigue contando esos fallos (DD-09).
- **Sesiones abiertas**: un bloqueo de IP o de cuenta solo afecta a nuevos logins; las sesiones existentes siguen válidas hasta su vencimiento o logout.
- **Limpieza**: DD-21 y DD-28.
- **Bloqueo intencional de cuentas ajenas**: quien conozca el código del consultorio y un email puede bloquear ese par 15 min con 5 intentos, y repetirlo. Mitigaciones: solo se bloquea ese par (no la cuenta en todos lados ni el consultorio); el usuario legítimo de otro consultorio con el mismo email no se ve afectado; el límite por IP frena a un atacante desde una sola dirección sobre muchas cuentas; respuestas genéricas que no confirman existencia; el código no es público, aunque no es secreto; las sesiones abiertas no se ven afectadas. Riesgo residual documentado (DT-03).
- **Redes compartidas**: todas las personas detrás de una misma IP pública (NAT del consultorio, CGNAT del proveedor) comparten el contador de IP: 30 fallos de cualquiera de ellas, o de un atacante que comparta esa IP, bloquean los logins nuevos desde esa IP durante 15 min. Las sesiones abiertas no se ven afectadas. Riesgo residual documentado (DT-10).
- **Cuentas inexistentes**: mismo conteo, mismo bloqueo, misma verificación Argon2 (hash ficticio) y mismo consumo de cupo, por lo que ni el código ni el tiempo distinguen existencia.

## Configuración

| Variable | Tipo | Defecto | Validación |
|---|---|---|---|
| `AUTH_SECRET_KEY` | SecretStr | — (obligatoria) | base64url (relleno opcional) que decodifica a ≥ 32 bytes; ≥ 20 caracteres distintos; no periódica; sin marcadores; distinta de la plantilla; nunca se muestra en errores (DD-17) |
| `AUTH_SESSION_MINUTES` | int | 30 | 5–480; ≤ `AUTH_SESSION_MAX_HOURS × 60` |
| `AUTH_SESSION_MAX_HOURS` | int | 12 | 1–24 |
| `AUTH_COOKIE_SECURE` | bool | `true` | `false` solo con `APP_ENV=local` |

`.env.example` (valores ficticios): `AUTH_SECRET_KEY=REEMPLAZAR_generar_con_secrets_token_urlsafe_48` (marcador que la configuración **rechaza** a propósito), con el comentario `# Generar con: python -c "import secrets; print(secrets.token_urlsafe(48))"`; `AUTH_SESSION_MINUTES=30`, `AUTH_SESSION_MAX_HOURS=12`, `AUTH_COOKIE_SECURE=true` y un comentario que indica que `AUTH_COOKIE_SECURE=false` solo se permite en desarrollo local por HTTP. El autor genera su clave con ese comando y la agrega a su `.env` local (no versionado, ignorado por Git) para ejecutar la aplicación; `scripts/test.ps1` ya no la necesita (D3: usa una clave efímera propia). Apply no lee ni escribe `.env` y nunca ve el valor.

## Modelo de amenazas

| Amenaza | Mitigación | Residual |
|---|---|---|
| Fuerza bruta en línea sobre una cuenta | 5 fallos / 15 min por par; Argon2id | Bloqueo intencional (DT-03) |
| Rociado de contraseñas y relleno de credenciales | Límite por IP 30 / 15 min (IPv6 por /64, IPv4 mapeada normalizada); el éxito no reinicia el contador de IP; claves HMAC | Botnets con muchas IP; redes compartidas (DT-10) |
| Enumeración de cuentas o consultorios | Respuesta, conteo, tiempo y consumo de cupo uniformes (hash ficticio); la política de contraseñas no se aplica en el login | Diferencias de microsegundos en la consulta |
| Agotamiento de memoria por verificaciones Argon2 concurrentes (64 MiB cada una) | Semáforo de 4 cupos por proceso (≤ 256 MiB), espera ≤ 3 s y 503; serialización por IP; contraseña ≤ 128; límites de intentos | Varios workers multiplican el pico (DT-11); un ataque distribuido puede provocar 503 a usuarios legítimos (disponibilidad, sin pérdida de confidencialidad) |
| Robo de sesión por XSS | Cookie HttpOnly; token fuera del JSON y de `localStorage` | XSS puede actuar dentro de la sesión (C-06) |
| Fuga de la base | Solo HMAC del token; Argon2id para contraseñas; intentos sin datos en claro | Fuga conjunta de base y `AUTH_SECRET_KEY` |
| Fijación de sesión | Token nuevo en cada login y revocación del previo | — |
| CSRF desde otro origen | `Origin` estricto + `X-CSRF-Token` ligado a la sesión + `SameSite=Lax` | — |
| Login CSRF | `Origin` estricto y `Content-Type: application/json` obligatorio en el login | Navegadores que no envían `Origin` quedan rechazados (no aceptados) |
| Respuestas con identidad o token CSRF guardadas en cachés | `Cache-Control: no-store` en login, `/me` y logout | — |
| CORS permisivo | Orígenes explícitos, sin `*`, métodos y cabeceras mínimos | Error de configuración del operador |
| Falsificación de IP con `X-Forwarded-For` | Dirección directa; `--no-proxy-headers` | Detrás de un proxy real (DT-04) |
| Evasión de límites con una dirección del cliente ausente o no analizable | Login rechazado con 400 antes de evaluar credenciales, sin Argon2 ni registro de intentos; sin balde compartido (DD-19) | — |
| Confusión de consultorio (`consultorio_id` del cliente) | Esquema estricto (422); contexto solo desde la sesión; FK compuesta de `sesion` | RLS en C-04 |
| Usuario o consultorio desactivado con sesión abierta | Verificación de `activo` en cada petición | — |
| Contraseña filtrada por historial, argumentos o registros | `getpass`, TTY obligatorio, sin argumentos; salida y registros sin datos | Captura de teclado del equipo local |
| Contraseñas débiles o predecibles | Mínimo 15, lista local propia de comunes, términos del contexto con forma compacta determinista, NFKC | Contraseñas débiles fuera de la lista; términos genéricos excluidos a propósito |
| Secretos versionados o débiles | `.env` ignorado; plantilla con un marcador rechazado; validación de formato, longitud, diversidad, periodicidad y marcadores | Valor elegido a mano que cumple el formato (DT-07) |
| Exposición de la documentación de la API | `/docs`, `/redoc` y `/openapi.json` solo con `APP_ENV=local` | Recursos de Swagger UI desde un CDN en local (DT-12) |
| Comparación de tokens por tiempo | `compare_digest` para CSRF; búsqueda por HMAC | — |
| Degradación de formato de hash | Solo `$argon2id$` admitido; otros nunca autentican | — |
| Crecimiento de tablas | Limpieza oportunista acotada (DD-21) y comando local por lotes (DD-28) | Sin mantenimiento periódico (DT-02) |
| Acumulación de sesiones por usuario | Vencimientos por inactividad y absoluto, revocación y limpieza | Sin límite por usuario (DT-09, riesgo aceptado) |

## Compatibilidad con C-01 y C-02

Ajustes previstos sobre código y pruebas existentes, cada uno justificado por una delta de este Change:
- `tests/unit/conftest.py` (`fabrica_settings`) y `tests/unit/test_config.py`: agregar `AUTH_SECRET_KEY` generada al ejecutar con `secrets.token_urlsafe(48)` y los escenarios nuevos (delta `configuracion-backend`).
- `tests/unit/test_cors.py`: credenciales, métodos y cabeceras (delta `configuracion-backend`).
- `tests/integration/test_migraciones.py`: `head` = `0003`, lista de tablas, tablas vacías (deltas `base-de-datos-local` y `modelo-consultorios-usuarios`).
- **7 puntos de edición en 2 archivos de prueba** (delta `modelo-consultorios-usuarios`: `codigo` pasa a ser obligatorio y sin valor por defecto): los helpers `_consultorio` de `tests/integration/test_modelo_base.py` y `tests/integration/test_repositorios_acotados.py`, y los 5 `INSERT INTO consultorio` directos de `test_modelo_base.py`. Cada uno agrega un `codigo` explícito, válido, ficticio y único; el que prueba el `NOT NULL` de `nombre` agrega `codigo` para seguir aislando la falta de `nombre`. No cambia la intención de ninguna prueba.
- `tests/integration/test_modelo_base.py`: además, restricciones nuevas y comparación de metadatos con las tablas nuevas.
- **Seed** (`app/seed/datos.py` y `app/seed/aplicar.py`, delta `seed-ficticio`): `ConsultorioSeed` gana el campo `codigo` con los literales `c-c7d08d776d19` y `c-c7d1647cab52`, y el `INSERT ... ON CONFLICT DO NOTHING` incluye `codigo`. Sin `UPDATE`, sin `DELETE`, sin escribir `credencial`: cumple la condición literal de DA-10.
- `tests/integration/test_seed.py` y su prueba unitaria de datos: códigos del seed y equivalencia con `codigo_corto` (delta `seed-ficticio`).
- `scripts/tests/autoprueba.ps1`: el caso "Plantilla completa con valores ficticios" deja de prohibir `AUTH_*` (sigue prohibiendo `EMAIL_*`), exige el marcador de `AUTH_SECRET_KEY` y el comentario con el comando de generación, y se agrega el caso `--no-proxy-headers`.
- `crear_app`: la documentación de la API deja de publicarse con `APP_ENV=test`; ninguna prueba existente la usa.
- Sin cambios: `tests/unit/test_superposicion_turnos.py` (19 pruebas; spec `ejecucion-de-pruebas`), los repositorios acotados y `ContextoConsultorio`.
- `GET /api/health` y `GET /api/no-existe` (404) mantienen su comportamiento: la protección se aplica con dependencias por ruta, no con un middleware global.

## Impacto en Changes posteriores

- **C-04 `aislamiento-roles-rbac`**: usará la migración **0004** (corregir `CHANGES.md` y la referencia del archivo de C-02 en el Archive de C-03); `require_rol` sobre `IdentidadAutenticada.rol`; adaptar `acceso_previo` (incluidos el alta de consultorios y la limpieza) a RLS (DD-27); sumar la ruta de prueba de identidad al arnés de acceso cruzado; nuevos métodos (`PATCH`, `DELETE`) requieren ampliar CORS y heredan `verificar_origen` + `exigir_csrf`.
- **C-05 `gestion-usuarios`**: alta de usuarios con contraseña inicial y cambio de la propia contraseña (reutiliza `contrasenas.py`, NFKC y la política de DD-16); desactivar un usuario ya corta el acceso en la siguiente petición; al cambiar contraseña o desactivar conviene revocar sus sesiones (índice `ix_sesion_consultorio_id_usuario_id`); posible desbloqueo de intentos por administrador (DT-03).
- **C-06 `frontend-base-sesion`**: `fetch` con `credentials: 'include'` y `Content-Type: application/json`, guardar el token CSRF en memoria (nunca en `localStorage`), enviarlo en `X-CSRF-Token` en cada `POST`, pedir `/me` al cargar, manejar 401 (ir al login), 429 y 503 (`Retry-After`); decidir proxy de Vite o CORS (DD-26).

## Riesgos / Trade-offs

- [La migración 0003 es BREAKING para la base de desarrollo] → se prueba completa en `db-test` (subida con datos previos, colisiones, bajada); se aplica en desarrollo solo con autorización explícita, sin `down -v`.
- [`codigo` sin valor por defecto obliga a indicarlo en toda inserción] → una sola función compartida (`app/models/codigo.py`), alta de consultorios centralizada en `acceso_previo` y 7 puntos de prueba adaptados; prueba de equivalencia con el backfill.
- [Argon2 con 64 MiB por verificación] → semáforo de 4 cupos por proceso con 503 ante saturación (DD-29); límites de intentos; contraseña ≤ 128.
- [Todas las peticiones locales comparten la IP de la puerta de enlace de Docker; los consultorios comparten IP por NAT] → límite por IP amplio (30); las pruebas inyectan direcciones; documentado (DT-10).
- [`ultimo_uso_en` se actualiza en `GET`] → escritura acotada a 1 por minuto por sesión.
- [Ajuste de pruebas existentes y del seed] → listado y justificado; las 19 de superposición no se tocan.
- [La clave de la plantilla se rechaza] → un `.env` recién copiado falla al cargar la aplicación hasta generar la clave: es intencional y la tarea 0.3 lo resuelve. `scripts/test.ps1` no depende de esa clave (D3).

## Plan de migración

1. Apply implementa todo y lo prueba solo en `db-test` (`scripts/test.ps1`, que migra con `-x target=test`).
2. El autor genera su `AUTH_SECRET_KEY` con `python -c "import secrets; print(secrets.token_urlsafe(48))"` y agrega las variables `AUTH_*` a su `.env`.
3. Con autorización explícita del autor: `docker compose run --rm api alembic upgrade head` sobre desarrollo (0002 → 0003); verificar con consultas de solo lectura que los 2 consultorios tienen `c-c7d08d776d19` y `c-c7d1647cab52` y que usuarios y credenciales no cambiaron.
4. Solo después de Verify y con autorización explícita del autor (PD-07 sigue pendiente): `docker compose run --rm -it api python -m app.credenciales` para cada usuario de demostración que el autor elija, con contraseñas que el autor teclea.
5. Opcional, con autorización explícita del autor: `docker compose run --rm api python -m app.mantenimiento limpiar` sobre desarrollo; registrar solo cantidades.
6. Reversión: solo en `db-test` (`alembic -x target=test downgrade 0002`). En desarrollo no se planifica bajada; si hiciera falta, requiere decisión del autor.

## Deuda técnica

- **DT-01**: advertencia `StarletteDeprecationWarning` de `TestClient` (heredada de C-01).
- **DT-02**: limpieza oportunista (DD-21) más un comando local manual (DD-28), sin mantenimiento periódico ni tarea programada; la cota de crecimiento es relativa al caudal. Antes de cualquier despliegue fuera de local es obligatorio un mecanismo de mantenimiento periódico autorizado.
- **DT-03**: bloqueo intencional de cuentas conocidas sin desbloqueo administrativo ni CAPTCHA (C-05 o posterior).
- **DT-04**: sin configuración de proxies de confianza; requerida antes de cualquier despliegue detrás de un proxy (PA-02).
- **DT-05**: reloj de la aplicación sin sincronización entre procesos (un solo proceso local).
- **DT-06**: una sola `AUTH_SECRET_KEY` con etiquetas de dominio, sin rotación gradual (rotar invalida todas las sesiones).
- **DT-07** (reducida): la validación de `AUTH_SECRET_KEY` comprueba formato, longitud, diversidad, periodicidad, marcadores y el valor de la plantilla, pero no puede demostrar entropía: un valor elegido a mano que cumpla las reglas pasa. El rechazo del valor de ejemplo, que motivaba la deuda original, queda resuelto.
- **DT-08**: los registros de acceso de uvicorn incluyen la IP del cliente (comportamiento previo, fuera del alcance de C-03).
- **DT-09**: sin límite de sesiones simultáneas por usuario; riesgo aceptado por el autor el 2026-11-05, acotado por vencimientos, revocación y limpieza.
- **DT-10**: redes compartidas (NAT del consultorio, CGNAT): 30 fallos desde una IP compartida bloquean los logins nuevos de todos sus usuarios durante 15 min (las sesiones abiertas siguen); localmente todo el tráfico comparte la IP de la puerta de enlace de Docker. Mitigaciones futuras: desbloqueo administrativo, CAPTCHA.
- **DT-11**: el límite de 4 verificaciones Argon2 es por proceso; con varios workers o réplicas hay que dimensionar memoria y límites globales.
- **DT-12**: Swagger UI y ReDoc cargan recursos desde `cdn.jsdelivr.net` en local (observación frente a X3, no bloqueante); servirlos desde el backend queda para más adelante.

## Decisiones pendientes para el autor

PD-01 a PD-06 y PD-08 quedaron resueltas por el autor el 2026-11-05 (ver "Decisiones de la revisión de arquitectura") y PD-09 y PD-10 el 2026-11-06 (ver "Decisiones del punto de control del 2026-11-06"). Sigue abierta:

| Id | Pregunta | Propuesta del diseño | Cuándo |
|---|---|---|---|
| PD-07 | Qué usuarios del seed reciben credenciales de demostración en desarrollo | Los que el autor elija al ejecutar el comando con autorización. No se establece ninguna contraseña de demostración hasta que el comando esté implementado, probado y verificado (grupo 14) y el autor lo autorice expresamente (tarea 13.2) | Después de Verify |

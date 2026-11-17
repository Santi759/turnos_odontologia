# Evidencia del ensayo de autenticación de la API local

> Evidencia para el TPI de Metodología I. Registra el ensayo en vivo de la API de sesión de C-03 y C-04 antes de grabar la demostración. Está saneada: no incluye la contraseña, la cookie de sesión, el token CSRF ni valores de configuración.

## Identificación

| Campo | Valor |
|---|---|
| Fecha | 2026-11-17 |
| Commit del repositorio | `e0e1f4f0500a1b4a3e411f8a68110765a72123f1` (`main`) |
| Entorno | API local de desarrollo (`http://localhost:8000`, publicada solo en `127.0.0.1`), con `APP_ENV=local` |
| Servicios | `api` y `db` en ejecución. No se recreó, reinició ni detuvo ningún contenedor |
| Usuario de demostración | `administracion.a@example.test`, rol `administrador`, "Consultorio Demo A" (código `c-c7d08d776d19`). Usuario ficticio del seed; su credencial se asignó con el comando local de credenciales el 2026-11-15 |

## Resultados

### Comprobaciones sin credenciales

Ejecutadas por el agente con `curl.exe` y un cuerpo inválido (`{}`):

| Solicitud | Código | Interpretación |
|---|---|---|
| `GET /api/health` | 200 | `{"status":"ok"}` |
| `GET /docs` | 200 | Swagger UI disponible (`APP_ENV=local`) |
| `POST /api/auth/login` sin `Origin` | 403 | Rechazada antes de leer el cuerpo (defensa CSRF) |
| `POST /api/auth/login` con `Origin: http://localhost:5173` | 422 | Origen permitido; rechazada por el cuerpo inválido |
| `POST /api/auth/login` con `Origin: http://localhost:8000` | 403 | El origen de Swagger no está permitido |
| `GET /api/auth/me` sin sesión | 401 | Requiere sesión |

### Flujo de autenticación

Ejecutado manualmente por el autor en su terminal, con la contraseña ingresada de forma oculta:

| Paso | Código |
|---|---|
| `POST /api/auth/login` | **200** |
| `GET /api/auth/me` con la cookie de sesión | **200** |
| `POST /api/auth/logout` con `Origin`, cookie y `X-CSRF-Token` | **204** |
| `GET /api/auth/me` con la cookie revocada | **401** |

## Procedimiento

1. El agente comprobó las precondiciones sin modificar nada:
   - rama `main` y commit `e0e1f4f`;
   - estado de los contenedores con `docker compose ps`;
   - el contenedor `api` es el mismo desplegado en la transición de C-04.
2. Hizo las comprobaciones sin credenciales de la tabla anterior. Ninguna llegó a la verificación de credenciales ni registró intentos de login.
3. El autor ejecutó el flujo de autenticación con el procedimiento del README (sección "Demostración para el TPI"):
   - login con `Invoke-WebRequest` y la contraseña leída con `Read-Host -AsSecureString`;
   - consulta de `/me`, logout y nueva consulta de `/me` con `curl.exe`, enviando explícitamente la cookie de sesión y, en el logout, `Origin` y `X-CSRF-Token`.
4. Se hizo un solo intento de login. La sesión de demostración quedó revocada por el logout.

## Observación

Durante el ensayo, la consulta de `/me` con `Invoke-WebRequest`, enviando la cookie en las cabeceras, respondió **401**. La misma consulta con `curl.exe` respondió **200**. Por eso la demostración usa `curl.exe` para los pasos autenticados. La causa no se investigó; una explicación posible es que Windows PowerShell 5.1 maneje la cabecera `Cookie` de forma distinta, pero no está confirmado.

## Limitaciones

- El flujo de autenticación lo ejecutó el autor. El agente no vio la contraseña, la cookie ni el token, y registra los códigos que informó el autor.
- Las comprobaciones sin credenciales usaron solicitudes HTTP, no "Try it out" de Swagger en el navegador.
- El ensayo solo cubre la API de sesión: no hay endpoints de negocio. El aislamiento entre consultorios se demuestra con las pruebas de aislamiento y con [`revision-c04-skill.md`](revision-c04-skill.md).
- No se ejecutó la suite de pruebas. Los resultados de las suites son los históricos registrados en C-04.
- El login y el logout crearon y revocaron una sesión en la base de desarrollo. Es el efecto normal del flujo, y la sesión revocada se puede eliminar con el comando local de mantenimiento.

# Descripción General

> Fuentes: respuestas del autor en la Etapa 3 (2026-10-13) para stack e infraestructura; `discovery/discovery.md` §8 y §9 para integraciones y restricciones; `docs/discovery/informe-discovery.md` §5 y §6.3 para la evidencia de mercado. Etiquetas: ver [README](README.md#convenciones).

## Stack tecnológico

[DEC] Elegido por el autor el 2026-10-13 (opción D de la ronda de preguntas de la Etapa 3; ver DD-10 en `09_decisiones_y_supuestos.md`). Las versiones exactas no se fijaron en Discovery ni en la Etapa 3: se fijan al crear el proyecto y se registran en el primer Change.

| Capa | Tecnologías | Versión mínima | Estado |
|---|---|---|---|
| Frontend | React con Vite | A definir al iniciar | [DEC] |
| Componente de agenda (vistas diaria y semanal) | Librería de calendario para React (por ejemplo, FullCalendar) | A definir | [PROP] candidata, no elegida |
| Backend (API REST) | FastAPI | A definir al iniciar | [DEC] |
| Acceso a datos | SQLAlchemy 2 | 2.x | [DEC] |
| Migraciones | Alembic | A definir | [DEC] |
| Validación y esquemas | Pydantic | A definir | [DEC] |
| Base de datos | PostgreSQL | A definir | [DEC] |
| Pruebas del backend | pytest | A definir | [DEC] |
| Pruebas del frontend | Vitest | A definir | [DEC] |
| Entorno local | Docker Compose | A definir | [DEC] preferido por el autor |
| Autenticación | **Sin definir** (requisitos en `08_arquitectura_propuesta.md`) | — | [ABIERTA] PA-03 |

Justificación resumida (DD-10):

- El autor ya tiene experiencia con React y FastAPI. Es el factor de mayor peso para una sola persona con fecha incierta (RG1).
- FastAPI genera documentación OpenAPI automáticamente, útil como evidencia académica y para probar la API sin frontend.
- PostgreSQL permite que la propia base de datos rechace turnos superpuestos mediante restricciones de exclusión sobre rangos de tiempo, de modo que R2 se cumpla aun con reservas concurrentes. El mecanismo concreto es [PROP] y se confirma en el Change de turnos.
- Costo aceptado: dos aplicaciones (frontend y API) con CORS entre ellas, autenticación sin solución incluida y pantallas de administración propias.

## Arquitectura general

[PROP] Arquitectura inicial propuesta. Se detalla en `08_arquitectura_propuesta.md` y se confirma en los Changes del roadmap.

```
 Navegador (React + Vite)
   │  HTTPS en un despliegue futuro; HTTP en local
   ▼
 API REST (FastAPI)
   ├── Autenticación  → identidad del usuario            (PA-03, sin definir)
   ├── Contexto de consultorio → derivado de la identidad, nunca del cliente (RN-MT)
   ├── Routers  → Servicios de dominio → Repositorios (SQLAlchemy 2)
   └── Validación de entrada y salida con Pydantic
   ▼
 PostgreSQL
   ├── Datos de todos los consultorios en una misma base, con identificador de consultorio
   └── Restricciones de integridad (incluida la exclusión de turnos solapados por profesional)

 Entorno local: Docker Compose (db + api + frontend), solo datos ficticios
```

Decisiones de alto nivel y su origen:

| Aspecto | Planteo | Origen | Estado |
|---|---|---|---|
| Modelo multi-consultorio | Una base compartida, con aislamiento lógico por consultorio | D2, R6 (implicancia: "toda entidad del consultorio lleva su identificador") | [DEC] D2 decidida; el mecanismo de defensa en profundidad es [ABIERTA] PA-04 |
| Separación frontend y API | Dos aplicaciones | DD-10 | [DEC] |
| Reglas de agenda en el servidor | Toda validación de R1–R4 se ejecuta en la API y, para R2, también en la base de datos | R1–R4; RG3 | [PROP] |
| Sin datos clínicos | El modelo no incluye historia clínica ni odontograma | D3 | [DEC] |
| Prestación del turno como dato sensible | Acceso restringido y minimización de datos | D9 (propuesta de criterio prudente) | [PROP] |

## Integraciones externas

[DEC] **El núcleo del MVP no tiene integraciones externas obligatorias** (Discovery §8). Tampoco se contratan ni configuran servicios externos en esta etapa (autor, 2026-10-13).

| Servicio | Propósito | Tipo | Estado | Origen y notas |
|---|---|---|---|---|
| Ninguno | — | — | [DEC] MVP núcleo | Discovery §8 |
| Envío de email (por ejemplo, Resend o Amazon SES) | Confirmación o aviso de turno | API o SMTP | [PROP] D5; proveedor no elegido | Precios leídos el 2026-10-10 (Resend: 3.000 emails/mes gratis, máximo 100/día; SES: USD 0,10 a 0,16 por 1.000). Entregabilidad y dominio [PEND] |
| Enlace wa.me | Mensaje prearmado de WhatsApp desde la lista diaria, sin API | Enlace web | [PROP] D6 | Formato oficial del enlace [PEND] |
| WhatsApp Cloud API (Meta) | Recordatorios automáticos | REST y webhooks | Segunda etapa (D7) | Cobro por mensaje entregado desde el 1/7/2025; tarifa para Argentina [PEND] (pregunta 17) |
| SMS | Recordatorios | REST | Segunda etapa (D7) | Tarifa en Argentina [PEND] (pregunta 18) |
| Mercado Pago | Seña al reservar | REST y webhooks | Segunda etapa | [MERCADO] 1 de 18 sistemas lo evidencia (Turnito) |
| Google Calendar | Sincronización | REST | Segunda etapa | [MERCADO] Turnito y MR Dental Cloud |
| ARCA, obras sociales y prepagas | Facturación y cobertura | — | Fuera de alcance (D8) | [MERCADO] ARCA en 1 de 18 (DentalTec); obras sociales en los 4 odontológicos argentinos |

La recuperación de contraseña por email entra en tensión con "sin integraciones externas" (IN-06, PA-11).

## API REST

[PROP] Resumen inicial de recursos, sin rutas definitivas. Todas las rutas, salvo las públicas, operan **dentro del consultorio del usuario autenticado**: el consultorio no se recibe como parámetro libre del cliente (RN-MT-02). Los contratos definitivos se definen en cada Change y quedan publicados en el OpenAPI que genera FastAPI.

| Recurso | Operaciones principales | Roles | Origen |
|---|---|---|---|
| Sesión | Iniciar y cerrar sesión; usuario actual | Todos | PA-03 |
| Consultorio | Ver y editar los datos del propio consultorio | Administrador | CU1 |
| Usuarios del consultorio | Alta, edición, desactivación y asignación de rol | Administrador | Discovery §2 |
| Profesionales | Alta, edición y desactivación | Administrador | CU1 |
| Prestaciones | Alta, edición, desactivación y duración | Administrador | CU1, R1 |
| Horarios de atención | Definir franjas por profesional y día | Administrador | CU1, R3 |
| Bloqueos | Crear, listar y eliminar períodos sin atención | Administrador | R4 |
| Disponibilidad | Consultar horarios libres de un profesional para una prestación y una fecha | Secretaría, administrador (y paciente si se aprueba D4) | R1–R4 |
| Pacientes | Alta, edición, búsqueda y consulta | Secretaría, administrador | CU4 |
| Turnos | Crear, modificar o reprogramar, cancelar, cambiar estado y listar por fecha o profesional | Secretaría, administrador | CU2 |
| Agenda del profesional | Ver los propios turnos por día y semana | Odontólogo | CU3 |
| Lista diaria de contacto | Turnos del día con enlace wa.me | Secretaría | [PROP] D6 |
| Reserva pública | Ver disponibilidad y reservar en un consultorio | Paciente o invitado | [PROP] D4, preguntas 3 y 5 |

## Restricciones de contexto

Discovery §9 y autor, 2026-10-13.

- Trabajo individual, MVP académico, fecha de entrega sin definir (pregunta 1).
- Desarrollo y pruebas locales con Docker Compose; despliegue en la nube como posibilidad futura (PA-02).
- Solo datos ficticios en desarrollo y pruebas.
- Prioridades del autor: investigación rigurosa, documentación sólida y MVP realista.

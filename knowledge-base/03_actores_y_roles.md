# Actores y Roles

> Fuentes: `discovery/discovery.md` §2 (roles planteados por el autor [AUT]) y §3 (CU1–CU5); D2, D4 y D9; `docs/discovery/informe-discovery.md` §5.1. Etiquetas: ver [README](README.md#convenciones).

## Actores del sistema

| Actor | Descripción | Cómo interactúa | Estado en v0.1 | Origen |
|---|---|---|---|---|
| Administrador del consultorio | Configura el consultorio, los profesionales, las prestaciones, los horarios y los bloqueos | Aplicación web autenticada | [REQ] | Discovery §2, CU1 |
| Secretaría o recepción | Crea, modifica, cancela y consulta turnos; administra datos básicos de pacientes | Aplicación web autenticada | [REQ] | Discovery §2, CU2, CU4 |
| Odontólogo | Consulta su agenda y la información necesaria para atender sus turnos | Aplicación web autenticada, solo lectura de su agenda | [REQ] | Discovery §2, CU3 |
| Paciente | Reserva y consulta sus propios turnos | Vista pública del consultorio, con cuenta propia o como invitado (pregunta 3) | [PROP] depende de D4 y de la pregunta 5 | Discovery §2, CU5 |
| Alta de consultorios en la plataforma | Quién crea un consultorio nuevo en el SaaS | Sin definir | [ABIERTA] PA-05 | No surge de Discovery |

[MERCADO] 12 de 18 sistemas de la muestra evidencian roles y permisos (4 de 7 en nivel 1), según el informe §5.1. Es evidencia de práctica habitual, no un requisito.

[SUP] SU-02: en la v0.1 cada usuario pertenece a **un solo consultorio** y tiene **un solo rol** en él. Si un odontólogo trabaja en varios consultorios, tendría una cuenta por consultorio, coherente con el aislamiento de D2. Se valida con PA-06.

[SUP] SU-03: el **profesional** de la agenda es una entidad propia, que puede o no estar vinculada a un usuario con rol odontólogo. Esto permite cargar la agenda de un profesional que todavía no usa el sistema. Se valida con PA-17.

## RBAC — Matriz de permisos

[PROP] Matriz inicial derivada de las descripciones de rol de Discovery §2. Todos los permisos se limitan al **propio consultorio** (D2, R6): ningún rol de consultorio accede a datos de otro.

C = crear · L = leer · M = modificar · B = baja o desactivación · — = sin acceso

| Recurso | Administrador | Secretaría | Odontólogo | Paciente (si se aprueba D4) |
|---|---|---|---|---|
| Datos del consultorio | L M | L | L | L (solo datos públicos: nombre, prestaciones ofrecidas) |
| Usuarios y roles del consultorio | C L M B | — | — | — |
| Profesionales | C L M B | L | L (propio) | L (nombre, para elegir) |
| Prestaciones (con duración) | C L M B | L | L | L (las ofrecidas) |
| Horarios de atención | C L M B | L | L (propios) | — (solo ve horarios libres) |
| Bloqueos de agenda | C L M B | L | L (propios) | — |
| Disponibilidad (horarios libres) | L | L | L (propia) | L |
| Pacientes (ficha básica) | C L M | C L M | L (solo pacientes con turnos propios) | L M (solo sus datos) |
| Turnos | C L M (incluye cancelar y cambiar estado) | C L M (incluye cancelar y cambiar estado) | L (propios) | C L y cancelar (solo los propios, sujeto a R5) |
| Lista diaria de contacto (D6) | L | L | — | — |
| Aviso de privacidad y registro de aceptación | C L M | L | — | L (acepta el propio) |

Notas:

- [PROP] El **odontólogo solo lee** su agenda en la v0.1, según el CU3. Si puede marcar un turno como atendido o ausente es [ABIERTA] PA-07.
- [PROP] La **prestación del turno** se trata como posible dato de salud (D9). Solo la ven los roles del consultorio que la necesitan. En la vista pública solo se muestran las prestaciones que el consultorio ofrece, nunca las de los turnos de otros pacientes.
- [PROP] Ningún rol de consultorio **borra físicamente** pacientes ni turnos en la v0.1. La política de conservación y supresión es [ABIERTA] PA-16, vinculada a la Ley 25.326, art. 14, y a la pregunta 6.
- [ABIERTA] Si la **secretaría puede saltear la anticipación mínima** de R5 (PA-12).
- La autorización se verifica **en el servidor** en cada operación; ocultar botones en el frontend no es control de acceso (RN-AU-03).

## Rutas públicas

Accesibles sin autenticación:

| Ruta o recurso | Propósito | Estado |
|---|---|---|
| Inicio de sesión | Acceso de usuarios del consultorio | [REQ] |
| Documentación de la API (OpenAPI o Swagger) | Desarrollo y evidencia académica | [PROP] solo en el entorno local; en un despliegue futuro se decide si se expone (PA-02) |
| Aviso de privacidad | Información al titular de los datos (Ley 25.326) | [PROP] |
| Vista pública de reserva por consultorio | Disponibilidad y reserva del paciente | [PROP] D4; preguntas 3 y 5 |
| Confirmación o cancelación por enlace (email o wa.me) | Respuesta del paciente sin iniciar sesión | [PROP] D5 y D6. [MERCADO] Dentally permite reservar sin login desde un enlace de recall (informe §5.2). Requiere enlaces no adivinables y con vencimiento |

[PROP] Toda ruta pública que muestre o modifique datos de un consultorio debe limitar la información expuesta al mínimo, por ejemplo mostrando horarios libres sin datos de otros pacientes. También debe resistir la enumeración de identificadores.

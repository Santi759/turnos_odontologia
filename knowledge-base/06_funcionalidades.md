# Funcionalidades

> Fuentes: `discovery/discovery.md` §3 (CU1–CU5), §5 y §6; D1–D9; `docs/discovery/informe-discovery.md` §5 y §6.3. Etiquetas: ver [README](README.md#convenciones).

Organizadas por **épica** y por **historia de usuario** (US-NNN). Cada historia indica su **estado**:

- **Núcleo**: forma parte del núcleo del MVP propuesto por el autor en Discovery §5 y se toma como base de la v0.1. La priorización final se hace en el roadmap.
- **Candidata**: propuesta (D4, D5, D6) o sugerencia del informe §6.3; requiere decisión en el roadmap.
- **Segunda etapa**: fuera de la v0.1.

**Núcleo no significa "obligatorio en el primer Change".** El núcleo es el *perímetro funcional propuesto* para la v0.1. El roadmap lo divide en Changes y decide su orden. Varias historias del núcleo dependen de decisiones abiertas o de propuestas; cada una lo indica en su línea **Depende de**. Una historia condicionada no se implementa como definitiva hasta que se resuelva su dependencia (RN-GL-04).

| Historia del núcleo | Condición | Depende de |
|---|---|---|
| US-001 | Condicionada | PA-03 (mecanismo de autenticación), PA-11 (recuperación de contraseña) |
| US-002 | Condicionada | PA-04 (capas de aislamiento) |
| US-003 | Sin dependencias abiertas propias | Requiere US-001 y US-002 |
| US-004 | **Bloqueada** | PA-05 (alta de consultorios) |
| US-005 | Sin dependencias abiertas propias | Requiere US-001 y US-002; PA-17 para el vínculo con usuarios |
| US-006 | Condicionada | PA-09 (duración por profesional o por turno); SU-05 |
| US-007 | Sin dependencias abiertas propias | PA-18 solo para el cambio de franjas con turnos existentes |
| US-008 | Condicionada | PA-10 (bloqueo de consultorio, turnos afectados) |
| US-009 | **Condicionada: R5 es propuesta** | PA-12 |
| US-010 | Condicionada | PA-08 (granularidad), PA-07 (estados que ocupan agenda) |
| US-011 a US-014 | Condicionadas | PA-07 (estados y transiciones), PA-12 (alcance de R5), PA-19 (registro de cambios) |
| US-015 | Sin dependencias abiertas propias | PA-07 para la presentación de estados |
| US-016 | Condicionada | PA-07 (si el odontólogo marca atendido o ausente) |
| US-017 | Condicionada | PA-14 (datos mínimos); el contacto preferido es [PROP] |
| US-018 | Condicionada | Forma de registro [PROP]; P-06, P-09 y P-11 |
| US-019 | Condicionada | PA-16; la desactivación es [PROP] |

| Épica | Estado | Historias |
|---|---|---|
| E1. Acceso y aislamiento por consultorio | Núcleo (US-004 bloqueada por PA-05) | US-001 a US-004 |
| E2. Configuración de la agenda | Núcleo (US-009 condicionada: R5 propuesta) | US-005 a US-009 |
| E3. Gestión de turnos | Núcleo | US-010 a US-015 |
| E4. Agenda del odontólogo | Núcleo | US-016 |
| E5. Pacientes y privacidad | Núcleo | US-017 a US-019 |
| E6. Reserva online del paciente | Candidata (D4) | US-020 a US-022 |
| E7. Comunicación con el paciente | Candidata (D5, D6) | US-023 y US-024 |
| E8. Trazabilidad de datos | Candidata (informe §6.3) | US-025 y US-026 |
| E9. Segunda etapa | Fuera de la v0.1 | Solo listado |

---

## Épica 1: Acceso y aislamiento por consultorio — Núcleo

### US-001 — Iniciar y cerrar sesión
**Como** usuario del consultorio (administrador, secretaría u odontólogo)
**Quiero** iniciar sesión con mis credenciales y cerrarla
**Para** acceder solo a las funciones de mi rol en mi consultorio

**Criterios de aceptación**:
- [ ] Con credenciales válidas y usuario activo, accedo a mi consultorio.
- [ ] Con credenciales inválidas o usuario inactivo, el acceso se rechaza sin indicar cuál de los dos datos falló.
- [ ] Al cerrar sesión, la sesión o el token dejan de ser válidos.
- [ ] Las rutas no públicas rechazan peticiones sin autenticación.

**Reglas relacionadas**: RN-AU-01, RN-AU-02, RN-AU-04, RN-AU-05, RN-AU-06
**Nota**: el mecanismo (sesión o tokens) y la librería son [ABIERTA] PA-03. La recuperación de contraseña es PA-11.

### US-002 — Aislamiento entre consultorios
**Como** consultorio cliente del SaaS
**Quiero** que ningún usuario de otro consultorio pueda ver ni modificar mis datos
**Para** proteger los datos de mis pacientes (D2)

**Criterios de aceptación**:
- [ ] Un usuario del consultorio A no lista, ve, modifica ni referencia datos del consultorio B en ningún endpoint.
- [ ] Un identificador de B enviado por un usuario de A responde igual que un recurso inexistente.
- [ ] El consultorio de la operación se deriva de la identidad, nunca del cuerpo o los parámetros de la petición.
- [ ] Existe una prueba automatizada de acceso cruzado por cada endpoint con datos de consultorio.
- [ ] Además del filtro por consultorio existe al menos una barrera adicional en la base de datos (mecanismo en PA-04).

**Reglas relacionadas**: RN-MT-01 a RN-MT-06

### US-003 — Gestionar usuarios del consultorio
**Como** administrador
**Quiero** dar de alta, editar, desactivar y asignar rol a los usuarios de mi consultorio
**Para** controlar quién accede y con qué permisos

**Criterios de aceptación**:
- [ ] Puedo crear usuarios con rol administrador, secretaría u odontólogo, solo en mi consultorio.
- [ ] Un usuario desactivado pierde el acceso de inmediato.
- [ ] Un rol distinto de administrador no puede gestionar usuarios.

**Reglas relacionadas**: RN-AU-03, RN-AU-06, RN-MT-02

### US-004 — Alta de un consultorio
**Como** responsable de un consultorio nuevo
**Quiero** que mi consultorio exista en el sistema con un primer administrador
**Para** empezar a configurarlo

**Criterios de aceptación**:
- [ ] Queda definido quién crea consultorios y cómo (PA-05).
- [ ] En la v0.1 local alcanza con los consultorios ficticios del seed data.

**Reglas relacionadas**: RN-MT-01
**Estado**: **bloqueada** por PA-05; el procedimiento está abierto. La historia existe para no ocultar el hueco.

## Épica 2: Configuración de la agenda — Núcleo (CU1)

### US-005 — Gestionar profesionales
**Como** administrador
**Quiero** dar de alta, editar y desactivar profesionales, y opcionalmente vincularlos a un usuario odontólogo
**Para** que la agenda refleje quién atiende

**Criterios de aceptación**:
- [ ] Un profesional inactivo no admite turnos nuevos y conserva sus turnos existentes.
- [ ] Solo puedo vincular usuarios de mi consultorio con rol odontólogo.

**Reglas relacionadas**: RN-AG-10, RN-MT-03

### US-006 — Gestionar prestaciones con duración
**Como** administrador
**Quiero** definir las prestaciones odontológicas con su duración en minutos
**Para** que cada turno ocupe el tiempo real de la prestación (R1)

**Criterios de aceptación**:
- [ ] La duración es un número entero mayor que cero.
- [ ] Cambiar la duración de una prestación no altera los turnos ya creados (SU-05).
- [ ] Una prestación inactiva no se ofrece para turnos nuevos.

**Reglas relacionadas**: RN-AG-01, RN-AG-10, RN-AG-13

### US-007 — Definir horarios de atención
**Como** administrador
**Quiero** configurar los días y franjas horarias de atención de cada profesional
**Para** que solo se den turnos cuando el profesional atiende (R3)

**Criterios de aceptación**:
- [ ] Puedo definir una o más franjas por día de la semana.
- [ ] El sistema rechaza franjas con inicio igual o posterior al fin y franjas solapadas del mismo profesional y día.

**Reglas relacionadas**: RN-AG-05, RN-AG-06

### US-008 — Bloquear períodos sin atención
**Como** administrador
**Quiero** bloquear vacaciones, ausencias, feriados y otros períodos, para un profesional o para todo el consultorio
**Para** que no se den turnos en esos períodos (R4)

**Criterios de aceptación**:
- [ ] Un período bloqueado no aparece como disponible y no admite turnos.
- [ ] [PROP] Si se aprueba el bloqueo de todo el consultorio (PA-10), un feriado se carga una sola vez, sin repetirlo por profesional.
- [ ] Al crear un bloqueo que cubre turnos existentes, el sistema actúa según lo que se decida en PA-10. Hasta entonces, como mínimo informa los turnos afectados.

**Reglas relacionadas**: RN-AG-07, RN-AG-08, RN-AG-09
**Referencia [MERCADO]**: Órbita bloquea vacaciones y feriados "de una vez, no turno por turno" (informe §6.3).

### US-009 — Configurar la anticipación de cancelación
**Como** administrador
**Quiero** definir la anticipación mínima para cancelar o reprogramar, con 24 horas por defecto
**Para** adaptar la regla a mi consultorio (R5)

**Criterios de aceptación**:
- [ ] El valor es configurable por consultorio y comienza en 24 horas.
- [ ] Su aplicación respeta lo que se decida en PA-12.

**Reglas relacionadas**: RN-TU-03
**Estado**: núcleo **condicionado**: R5 es propuesta del autor y no figura en la lista del núcleo de Discovery §5. Depende de PA-12.

## Épica 3: Gestión de turnos — Núcleo (CU2, núcleo del problema)

### US-010 — Consultar disponibilidad
**Como** secretaría
**Quiero** ver los horarios libres de un profesional para una prestación y una fecha
**Para** ofrecerle al paciente opciones válidas sin prueba y error

**Criterios de aceptación**:
- [ ] Solo se ofrecen horarios donde la prestación entra completa en una franja de atención, fuera de bloqueos y sin superponerse con otros turnos del profesional.
- [ ] La granularidad de los horarios ofrecidos sigue lo que se decida en PA-08.

**Reglas relacionadas**: RN-AG-01 a RN-AG-08, RN-AG-11, RN-AG-12

### US-011 — Crear un turno sin superposiciones
**Como** secretaría
**Quiero** crear un turno para un paciente, un profesional, una prestación y un horario
**Para** registrar la cita sin errores de agenda (D1)

**Criterios de aceptación**:
- [ ] El fin del turno se calcula con la duración de la prestación.
- [ ] Se rechaza si se superpone con otro turno que ocupa agenda del mismo profesional, indicando el motivo.
- [ ] Se rechaza si queda fuera de la franja de atención o dentro de un bloqueo.
- [ ] Dos creaciones simultáneas para el mismo profesional y horario: exactamente una tiene éxito (prueba de concurrencia).
- [ ] Turnos consecutivos (uno termina cuando empieza el otro) se aceptan.
- [ ] [PROP] El turno nace en estado `reservado` (PA-07).

**Reglas relacionadas**: RN-AG-01 a RN-AG-08, RN-TU-01, RN-TU-06, RN-GL-02

### US-012 — Modificar o reprogramar un turno
**Como** secretaría
**Quiero** cambiar el horario, el profesional o la prestación de un turno
**Para** reprogramarlo sin crear superposiciones

**Criterios de aceptación**:
- [ ] Se revalidan todas las reglas de agenda, excluyendo al propio turno de la comparación.
- [ ] Si la validación falla, el turno queda como estaba.
- [ ] Se registra quién hizo el último cambio y cuándo. Si hace falta un historial completo es PA-19; la auditoría avanzada es candidata (E8), no núcleo.

**Reglas relacionadas**: RN-TU-02, RN-TU-03, RN-TU-04, RN-TU-09
**Depende de**: PA-07 (estado tras reprogramar), PA-12, PA-19

### US-013 — Cancelar un turno
**Como** secretaría
**Quiero** cancelar un turno
**Para** liberar el horario

**Criterios de aceptación**:
- [ ] El turno pasa a `cancelado` y su horario vuelve a estar disponible ([PROP] RN-TU-05; PA-07).
- [ ] [PROP] Si se permite reactivar un turno cancelado, la reactivación revalida todas las reglas de agenda (PA-07).
- [ ] La aplicación de la anticipación mínima a la secretaría sigue lo que se decida en PA-12.

**Reglas relacionadas**: RN-TU-03, RN-TU-05

### US-014 — Cambiar el estado de un turno
**Como** secretaría
**Quiero** marcar un turno como confirmado, atendido o ausente
**Para** reflejar lo que pasó con la cita

**Criterios de aceptación**:
- [ ] Solo se permiten las transiciones que se aprueben en PA-07 (conjunto inicial [PROP] en RN-TU-04).
- [ ] Marcar `ausente` deja el dato disponible para medir el ausentismo propio en el futuro, sin prometer reducirlo.

**Reglas relacionadas**: RN-TU-04, RN-TU-05, RN-TU-08
**Referencia [MERCADO]**: en Dentally y Bilog el estado cambia según la respuesta del paciente (informe §6.3).

### US-015 — Consultar la agenda del consultorio
**Como** secretaría o administrador
**Quiero** ver los turnos por día y por profesional
**Para** organizar la atención y atender consultas

**Criterios de aceptación**:
- [ ] Vistas diaria y semanal, filtrables por profesional.
- [ ] Los turnos cancelados se distinguen o se pueden ocultar.

**Reglas relacionadas**: RN-MT-01, RN-PA-03

## Épica 4: Agenda del odontólogo — Núcleo (CU3)

### US-016 — Ver mi agenda
**Como** odontólogo
**Quiero** ver mis turnos del día y de la semana
**Para** organizar mi atención

**Criterios de aceptación**:
- [ ] Solo veo mis turnos, con el paciente, la prestación y el horario.
- [ ] No puedo crear, modificar ni cancelar turnos en la v0.1.
- [ ] No veo turnos de otros profesionales ni datos de pacientes sin turnos conmigo.

**Reglas relacionadas**: RN-TU-07, RN-PA-03, RN-AU-03

## Épica 5: Pacientes y privacidad — Núcleo (CU4)

### US-017 — Registrar y editar pacientes
**Como** secretaría
**Quiero** dar de alta y editar la ficha básica de un paciente y buscarlo
**Para** asociarlo a sus turnos

**Criterios de aceptación**:
- [ ] La ficha no tiene campos clínicos (D3).
- [ ] Los campos siguen el principio de datos no excesivos (lista final en PA-14).
- [ ] Puedo registrar un contacto preferido para pacientes sin email.
- [ ] El paciente pertenece a un solo consultorio; la misma persona puede existir en otro consultorio como registro independiente.

**Reglas relacionadas**: RN-PA-01, RN-PA-02, RN-PA-07, RN-MT-04

### US-018 — Registrar la aceptación del aviso de privacidad
**Como** secretaría
**Quiero** registrar que el paciente recibió y aceptó el aviso de privacidad vigente
**Para** cumplir el aviso o consentimiento del núcleo del MVP (Ley 25.326, sin carácter de asesoramiento legal)

**Criterios de aceptación**:
- [ ] Se guarda la versión del aviso, la fecha y el medio.
- [ ] Un cambio de versión del aviso permite registrar una nueva aceptación.

**Reglas relacionadas**: RN-PA-04, RN-PA-05

### US-019 — Desactivar un paciente
**Como** secretaría o administrador
**Quiero** desactivar un paciente
**Para** que no aparezca en las búsquedas habituales

**Criterios de aceptación**:
- [ ] No hay borrado físico en la v0.1; los turnos históricos se conservan.
- [ ] La política de supresión y acceso del titular queda en PA-16.

**Reglas relacionadas**: RN-PA-06

## Épica 6: Reserva online del paciente — Candidata (D4, CU5)

[PROP] D4 sigue como propuesta y se decide en el roadmap (pregunta 5). Suma autenticación del paciente o reserva como invitado, una vista pública por consultorio y concurrencia sobre horarios libres (Discovery §5). [MERCADO] La ofrecen 10 de 18 sistemas y 6 de 7 de nivel 1; referencia de experiencia de usuario: Odeen, página pública de reserva (informe §6.2).

### US-020 — Reservar un turno online
**Como** paciente
**Quiero** elegir prestación, profesional y horario libre en la página del consultorio
**Para** no depender de llamar

**Criterios de aceptación**:
- [ ] Solo veo horarios libres; la reserva pasa por las mismas validaciones y la misma garantía de concurrencia que la secretaría.
- [ ] No veo datos de otros pacientes.

**Reglas relacionadas**: RN-RE-01, RN-RE-02, RN-RE-03, RN-AG-03

### US-021 — Consultar mis turnos
**Como** paciente
**Quiero** ver mis turnos reservados
**Para** recordarlos

**Reglas relacionadas**: RN-RE-02

### US-022 — Cancelar mi turno
**Como** paciente
**Quiero** cancelar un turno con la anticipación mínima del consultorio
**Para** liberar el horario

**Reglas relacionadas**: RN-RE-04, RN-TU-03

## Épica 7: Comunicación con el paciente — Candidata (D5, D6)

### US-023 — Lista diaria con enlaces wa.me
**Como** secretaría
**Quiero** ver la lista de turnos del día siguiente con un enlace que abre WhatsApp con un mensaje prearmado
**Para** avisar o confirmar sin integrar la API de WhatsApp (D6)

**Criterios de aceptación**:
- [ ] El mensaje no incluye la prestación (RN-PA-03).
- [ ] Los pacientes sin teléfono válido se distinguen para contacto por otro medio.

**Reglas relacionadas**: RN-CO-02, RN-PA-03, RN-PA-07
**Estado**: [PROP] por validar; formato oficial del enlace [PEND]. Eficacia no demostrada (RG6).

### US-024 — Email de confirmación o aviso de turno
**Como** paciente con email
**Quiero** recibir un aviso de mi turno, con un enlace para confirmarlo o cancelarlo
**Para** gestionarlo sin llamar (D5)

**Reglas relacionadas**: RN-CO-01, RN-CO-04, RN-CO-05
**Estado**: [PROP]. Requiere un proveedor de email, en tensión con "sin servicios externos en esta etapa" (IN-06). En el ensayo CAIS 2016 el email solo no mostró diferencia significativa en la asistencia; no se promete reducción del ausentismo.

## Épica 8: Trazabilidad de datos — Candidata (informe §6.3)

Sugerencia nueva del informe, no incluida en D1–D9. Sujeta al roadmap; no es una obligación del MVP sin decisión explícita del autor. [MERCADO] Solo 2 de 7 sistemas de nivel 1 evidencian auditoría y exportación (DentalTec y Órbita); referencia: Odeen, "registra los accesos a información clínica sensible" y exportación "sin trámites ni peajes" (informe §5.2).

### US-025 — Exportar los datos de un paciente
**Como** administrador
**Quiero** exportar los datos y turnos de un paciente
**Para** responder un pedido de acceso del titular (relacionado con la Ley 25.326, art. 14; interpretación, no asesoramiento legal)

### US-026 — Registro de auditoría de accesos y cambios
**Como** administrador
**Quiero** consultar quién creó, modificó o canceló turnos y quién accedió a datos de pacientes
**Para** detectar usos indebidos

## Épica 9: Segunda etapa — Fuera de la v0.1

Discovery §5 y D7. Se listan para no perderlas; no tienen historias en esta versión.

| Funcionalidad | Origen | Evidencia de mercado |
|---|---|---|
| Recordatorios automáticos por WhatsApp API o SMS | D7 | 15 de 18 con recordatorios automáticos; 13 de 18 con WhatsApp; los 7 de nivel 1 (informe §5.1). Tensión T-03 |
| Confirmación por respuesta del paciente (vinculada a D7) | Interpretación del informe §5.4, punto 3; no figura como ítem propio en Discovery §5 | 6 de 18 (4 de 7 en nivel 1) |
| Lista de espera | Discovery §5 | 5 de 18 |
| Seña con Mercado Pago | Discovery §5 | 1 de 18 (Turnito) |
| Sincronización con Google Calendar | Discovery §5 | Turnito, MR Dental Cloud |

Fuera de alcance (no son segunda etapa): historia clínica y odontograma (D3); facturación, cobertura e integraciones con obras sociales (D8).

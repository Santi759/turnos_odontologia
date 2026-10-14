# Modelo de Datos

> Fuentes: `discovery/discovery.md` §3 (CU1–CU5), §5 (núcleo del MVP), §7 (R1–R6), §8 (contacto del paciente) y §9 (Ley 25.326); D2, D3, D8 y D9; respuestas del autor del 2026-10-13 (stack y sillones). Etiquetas: ver [README](README.md#convenciones).
>
> Es un **modelo lógico propuesto** ([PROP]): define entidades, relaciones y restricciones necesarias para R1–R6. Los nombres de tablas y columnas, los tipos exactos y las migraciones se fijan en los Changes del roadmap con SQLAlchemy 2 y Alembic.

## Dominios

| Dominio | Contenido | Origen |
|---|---|---|
| Consultorios (multi-tenant) | Consultorio y sus parámetros | D2, R6 |
| Acceso | Usuarios del consultorio y roles | Discovery §2 |
| Agenda | Profesionales, prestaciones, horarios de atención y bloqueos | CU1, R1, R3, R4 |
| Turnos | Turnos y estados | CU2, CU3, R2, R5 |
| Pacientes y privacidad | Ficha básica del paciente y aceptación del aviso de privacidad | CU4, Discovery §5, Ley 25.326 |

**No incluidos en el modelo aprobado:**

- Historia clínica, odontograma y datos clínicos (D3, decidida).
- Obra social o prepaga como dato (pregunta 4, abierta; D8 parcialmente decidida).
- **Sillón o box como recurso de agenda**: por decisión del autor del 2026-10-13 queda como pregunta abierta y no se modela (PA-01). El modelo tampoco debe asumir que no existirá: ver [Extensión posible](#extensión-posible-no-aprobada).
- Registro de auditoría: candidato del informe §6.3, sujeto al roadmap.
- Pagos, señas, lista de espera y recordatorios automáticos: segunda etapa (Discovery §5, D7).

## ERD (Entity Relationship Diagram)

```
Consultorio 1 ──< Usuario                    (rol: administrador | secretaria | odontologo)
Consultorio 1 ──< Profesional >o── 0..1 Usuario   (SU-03: profesional vinculable a un usuario odontólogo)
Consultorio 1 ──< Prestacion                 (duración en minutos, R1)
Profesional 1 ──< HorarioAtencion            (franjas por día de la semana, R3)
Consultorio 1 ──< Bloqueo >o── 0..1 Profesional   (sin profesional = todo el consultorio; PA-10)
Consultorio 1 ──< Paciente                   (aislado por consultorio, R6)
Paciente 1 ──< AceptacionPrivacidad
Turno >── 1 Profesional
Turno >── 1 Paciente
Turno >── 1 Prestacion
Turno >── 1 Consultorio
```

Toda entidad, salvo `Consultorio`, lleva `consultorio_id` (R6, implicancia 1). Una misma persona puede tener registros de paciente independientes en distintos consultorios (R6, implicancia 2).

## Entidades

### Consultorio

- **Atributos:**
  - `id` (tipo de identificador a definir; identificadores no secuenciales son una capa candidata de PA-04)
  - `nombre` (texto)
  - `identificador_publico` (texto único, solo si se aprueba la reserva pública D4)
  - `zona_horaria` (texto; por defecto `America/Argentina/Buenos_Aires`, SU-01)
  - `anticipacion_cancelacion_horas` (entero; por defecto 24, R5)
  - `activo` (booleano)
  - `creado_en` (instante con zona horaria)
- **Relaciones:** 1 a N con todas las entidades del consultorio.
- **Constraints:** `anticipacion_cancelacion_horas >= 0`.
- **Estado:** [REQ] (D2). El alta de consultorios es [ABIERTA] PA-05.

### Usuario

- **Atributos:**
  - `id`
  - `consultorio_id`
  - `email` (identificador de inicio de sesión, [PROP]; si es único en todo el sistema, el alta podría revelar que una persona ya está registrada en otro consultorio: ver PA-06)
  - `nombre` (texto)
  - `credencial` (por ejemplo, hash de contraseña; depende de PA-03)
  - `rol` (enum: `administrador`, `secretaria`, `odontologo`)
  - `activo` (booleano)
  - `creado_en`
- **Relaciones:** N a 1 con Consultorio; 0..1 a 1 con Profesional.
- **Constraints:**
  - Nunca se almacena la contraseña en texto plano.
  - [SUP] SU-02: un usuario pertenece a un solo consultorio con un solo rol (PA-06).
- **Estado:** [REQ]. El mecanismo de credenciales es [ABIERTA] PA-03.

### Profesional

- **Atributos:**
  - `id`
  - `consultorio_id`
  - `nombre` (texto)
  - `usuario_id` (opcional)
  - `activo` (booleano)
- **Relaciones:**
  - N a 1 con Consultorio.
  - 1 a N con HorarioAtencion, Bloqueo y Turno.
- **Constraints:**
  - Si `usuario_id` está presente, el usuario debe tener rol `odontologo` y pertenecer al mismo consultorio.
  - Un profesional inactivo no admite turnos nuevos.
- **Estado:** [REQ] (CU1, R2, R3). Datos profesionales adicionales, como la matrícula, no surgen de Discovery y no se incluyen.
- **Pregunta abierta:** si todos los profesionales realizan todas las prestaciones queda en PA-09.

### Prestacion

- **Atributos:**
  - `id`
  - `consultorio_id`
  - `nombre` (texto)
  - `duracion_minutos` (entero)
  - `activa` (booleano)
- **Relaciones:** 1 a N con Turno.
- **Constraints:**
  - `duracion_minutos > 0`.
  - Nombre único por consultorio ([PROP]).
  - Una prestación inactiva no admite turnos nuevos.
- **Estado:** [REQ] (R1, CU1).
- **Nota:** el nombre de la prestación asociado a un paciente se trata como posible dato de salud (D9).

### HorarioAtencion

- **Atributos:**
  - `id`
  - `consultorio_id`
  - `profesional_id`
  - `dia_semana` (0 a 6)
  - `hora_inicio` y `hora_fin` (hora local del consultorio)
- **Relaciones:** N a 1 con Profesional.
- **Constraints:**
  - `hora_inicio < hora_fin`.
  - Las franjas del mismo profesional y día no se solapan entre sí ([PROP]).
  - Se admiten varias franjas por día, por ejemplo de mañana y de tarde ([PROP]).
- **Estado:** [REQ] (R3).
- **Pregunta abierta:** si hace falta registrar excepciones por fecha además de los bloqueos queda en PA-10.

### Bloqueo

- **Atributos:**
  - `id`
  - `consultorio_id`
  - `profesional_id` (opcional: sin valor significa que bloquea a todo el consultorio)
  - `inicio` y `fin` (instantes con zona horaria)
  - `tipo` (enum: `vacaciones`, `ausencia`, `feriado`, `otro`)
  - `descripcion` (texto corto administrativo, sin datos clínicos)
- **Relaciones:** N a 1 con Consultorio y, opcionalmente, con Profesional.
- **Constraints:** `inicio < fin`.
- **Estado:** [REQ] (R4). El alcance por consultorio y el efecto sobre los turnos ya existentes son [ABIERTA] PA-10.
- **Supuesto:** los feriados se cargan manualmente (SU-08).

### Paciente

- **Atributos:**
  - `id`
  - `consultorio_id`
  - `nombre` y `apellido` (texto)
  - `telefono` (texto)
  - `email` (opcional)
  - `contacto_preferido` (enum opcional: `telefono`, `whatsapp`, `email`; propuesta de Discovery §8 para pacientes sin email)
  - `activo` (booleano)
  - `creado_en`
- **Relaciones:**
  - N a 1 con Consultorio.
  - 1 a N con Turno y AceptacionPrivacidad.
- **Constraints:** los datos mínimos e identificatorios (por ejemplo, si se pide DNI) son [ABIERTA] PA-14, bajo el principio de datos adecuados y no excesivos (Ley 25.326, art. 4).
- **Estado:** [REQ] ficha básica (CU4, D3).
- **Excluidos:** obra social o prepaga (pregunta 4) y cualquier dato clínico (D3).

### AceptacionPrivacidad

- **Atributos:**
  - `id`
  - `consultorio_id`
  - `paciente_id`
  - `version_aviso` (texto)
  - `aceptado_en` (instante)
  - `medio` (enum: `presencial`, `online`)
- **Relaciones:** N a 1 con Paciente.
- **Constraints:** registro inmutable; una nueva versión del aviso genera un registro nuevo.
- **Estado:** [PROP] forma concreta de cumplir el ítem "aviso de privacidad o consentimiento" del núcleo del MVP (Discovery §5). No es asesoramiento legal. Si hace falta consentimiento expreso o alcanza con informar depende de las preguntas 6, 9 y 11.

### Turno

- **Atributos:**
  - `id`
  - `consultorio_id`
  - `profesional_id`, `paciente_id` y `prestacion_id`
  - `inicio` (instante con zona horaria)
  - `fin` (instante; calculado como `inicio + duración de la prestación`, R1)
  - `estado` (enum; conjunto inicial [PROP] en `05_reglas_de_negocio.md`, RN-TU-04)
  - `creado_por` (usuario o "reserva pública")
  - `creado_en`, `actualizado_en`, `actualizado_por` (último cambio, [PROP] RN-TU-09; historial completo en PA-19)
  - `cancelado_en` (opcional)
- **Relaciones:** N a 1 con Consultorio, Profesional, Paciente y Prestacion.
- **Constraints:**
  - `inicio < fin`.
  - Profesional, paciente y prestación pertenecen al **mismo consultorio** que el turno (RN-MT-03).
  - **Exclusión de solapamientos por profesional** (R2): dos turnos activos del mismo profesional no pueden tener intervalos que se intersequen.
    - [PROP] Mecanismo: restricción de exclusión de PostgreSQL sobre `profesional_id` y el rango `[inicio, fin)`, con la extensión `btree_gist`, aplicada solo a los estados que ocupan agenda (RN-AG-02b; propuesta inicial en RN-TU-05).
    - [ABIERTA] PA-07: el conjunto de estados que ocupan agenda define la **condición de la restricción**. Si PA-07 cambia ese conjunto, la restricción se recrea con una migración de Alembic y hay que revisar los datos existentes. La regla firme (RN-AG-02) no cambia.
    - La restricción solo garantiza turno contra turno. Los bloqueos y los horarios de atención se validan en el servicio de dominio; la concurrencia entre ellos y los turnos es [ABIERTA] PA-20.
    - [PROP] Los intervalos son semiabiertos: un turno que termina a las 10:30 no se superpone con otro que empieza a las 10:30.
  - El turno cae completo dentro de un horario de atención del profesional y fuera de todo bloqueo aplicable (R3, R4). Se valida en el servicio de dominio, porque una restricción simple de la base no puede expresarlo.
- **Índices relevantes:** `(consultorio_id, profesional_id, inicio)` para la agenda; `(consultorio_id, inicio)` para la lista diaria; `(consultorio_id, paciente_id)`.
- **Estado:** [REQ] (CU2, R1, R2).
- **Sin campo de texto libre** para el motivo clínico ni para observaciones: [ABIERTA] PA-15 (D3, D9).
- **Supuestos:**
  - SU-04: un turno tiene una sola prestación.
  - SU-05: la duración se toma de la prestación al crear el turno; cambios posteriores en la prestación no alteran los turnos existentes.

### Extensión posible (no aprobada)

Esta sección **no forma parte del modelo aprobado**. Solo registra el impacto que tendría resolver la pregunta abierta PA-01 en el sentido de incluir sillones o boxes.

- [MERCADO] Órbita: "Agenda por sillón. Dos pacientes no pueden caer en el mismo sillón." (https://hiorbita.com/; informe §5.2). Es la única formulación pública del problema en la muestra.
- **Riesgo que queda sin cubrir en la v0.1:** dos profesionales distintos con turnos simultáneos en el mismo sillón. R2 solo impide la superposición del **mismo profesional**.
- **Impacto si se aprobara:** una entidad de recurso físico por consultorio, una referencia opcional desde Turno y una segunda restricción de exclusión por recurso. Como R2 se implementa con una restricción por profesional, agregar otra por recurso no requiere rediseñar el turno. No se crean tablas ni reglas para esto hasta que el autor decida.

## Seed data inicial

[PROP] **Todos los datos son ficticios** (autor, 2026-10-13; SU-09). No se usan datos reales de personas ni de consultorios.

| Dato | Contenido mínimo | Para qué |
|---|---|---|
| Consultorios | Dos consultorios ficticios (por ejemplo, "Consultorio Demo A" y "Consultorio Demo B") | Probar el aislamiento (RG3) |
| Usuarios | Un administrador, una secretaría y un odontólogo por consultorio | Probar los permisos por rol |
| Profesionales | Dos por consultorio, uno vinculado a un usuario | Probar R2 con más de un profesional |
| Prestaciones | Tres o cuatro por consultorio con duraciones distintas | Probar R1. Los nombres y minutos son **valores de ejemplo**, no datos del mercado ni recomendaciones clínicas |
| Horarios | Franjas de mañana y tarde en días hábiles | Probar R3 y los bordes de franja |
| Bloqueos | Un feriado de consultorio y una ausencia de un profesional | Probar R4 |
| Pacientes | Algunos pacientes ficticios por consultorio, uno sin email | Probar CU4 y el contacto preferido |
| Turnos | Turnos en distintos estados, incluidos dos consecutivos sin superposición | Probar R2 en los bordes |
| Aviso de privacidad | Una versión inicial de texto de ejemplo | Probar el registro de aceptación |

# Visión y Objetivos

> Fuentes: `discovery/discovery.md` (aprobado el 2026-10-10), `docs/discovery/informe-discovery.md` (versión final, 2026-10-13) y respuestas del autor en la Etapa 3 (2026-10-13). Etiquetas: ver [README](README.md#convenciones).

## Propósito del sistema

**Evitar errores y superposiciones de turnos en consultorios odontológicos, con una agenda que respete la duración de cada prestación, la disponibilidad de cada profesional y los períodos bloqueados.**

El sistema es un SaaS multi-consultorio: cada consultorio gestiona su agenda, sus profesionales, sus prestaciones y sus pacientes, con los datos aislados del resto (D2). Se construye como **MVP académico** para Metodología I, por una sola persona y con fecha de entrega incierta (restricciones del punto 9 de Discovery).

Contexto del problema:

- [DEC] El problema central es un **planteo del autor**: errores y superposición de agenda; problema secundario, el tiempo perdido coordinando citas (D1, estado: planteo del autor; mercado sin validar).
- [ABIERTA] No hay evidencia externa que lo cuantifique en Argentina ni entrevistas con consultorios (Discovery §1; preguntas 2 y 12; RG2).
- [MERCADO] En la muestra de 18 sistemas, solo 2 documentan públicamente la duración por prestación o los bloqueos (Órbita y Odonto.ar), y solo Órbita formula la imposibilidad de superponer turnos ("Dos pacientes no pueden caer en el mismo sillón") (informe §5.2 y §5.3). Es una interpretación del investigador que el núcleo del problema está poco documentado por el mercado (informe §5.4, punto 1); no prueba que el problema exista ni que no esté resuelto.

## Contexto de mercado

[MERCADO] Resumen del estudio de la Etapa 2 (`docs/discovery/informe-discovery.md` §1, §4 y §6). Es evidencia de lo que publica el mercado; no son decisiones de este producto.

- **Muestra**: 18 sistemas. 7 con presencia comercial comprobada en Argentina (nivel 1: Órbita, Bilog, DentalTec, Odonto.ar, AgendaPro, Doctoralia Pro, Turnito); 8 de Latinoamérica en español (nivel 2: Odeen, Dentalink, MR Dental Cloud, Doctocliq, Clinicorp, DentalSoft+, Dentidesk, XIAgenda); 3 internacionales de referencia (nivel 3: Dentally, NexHealth, DentalPin). Fichas en `discovery/sources/`.
- **Mejores puntajes** (sobre 100, rúbrica de 7 criterios ponderados): Órbita 74 (mejor de nivel 1 y de los 18), Dentally 72 (mejor de nivel 3) y Odeen 70 (mejor de nivel 2). Un puntaje bajo con cobertura baja indica falta de información pública, no necesariamente falta de función.
- **Cinco candidatos para demo** (informe §6.1): Órbita, Bilog, DentalTec, Odonto.ar y Odeen. En cada demo hay que verificar los ítems no evidenciados (NE-01 a NE-12 en `10_preguntas_abiertas.md`).
- **Tres referencias de experiencia de usuario** (informe §6.2):
  - Dentally: confirmación por respuesta y portal del paciente.
  - Odeen: página pública de reserva y precios transparentes.
  - Órbita: confirmar y reprogramar dentro del chat de WhatsApp.
- **Funciones habituales en la muestra**: recordatorios automáticos (15 de 18), historia clínica (15 de 18), WhatsApp (13 de 18), reserva online del paciente (10 de 18).
- **Vacíos en la muestra**:
  - duración por prestación o bloqueos (2 de 18);
  - Mercado Pago y ARCA (1 de 18 cada uno);
  - cumplimiento declarado de la Ley 25.326 (1 de 18);
  - auditoría y exportación (2 de 7 en nivel 1).
- **MVP sugerido** por el informe (§6.3): coincide con el núcleo de Discovery §5 y agrega candidatos y tensiones que se recogen en el alcance de abajo y en `10_preguntas_abiertas.md` (T-01 a T-04).

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios | Origen | Estado en v0.1 |
|---|---|---|---|---|
| Administrador del consultorio | Configurar el consultorio para que la agenda refleje la realidad: profesionales, prestaciones con duración y horarios de atención | Bloquear vacaciones, ausencias y feriados; gestionar usuarios y roles del consultorio | CU1, R1, R3, R4 | [REQ] |
| Secretaría o recepción | Crear, modificar, cancelar y consultar turnos sin superposiciones | Registrar y editar datos básicos de pacientes; preparar la lista diaria de contacto | CU2, CU4, D6 | [REQ] (lista diaria: [PROP]) |
| Odontólogo | Consultar su agenda diaria y semanal | Ver la información necesaria para atender cada turno, sin datos clínicos | CU3, D3 | [REQ] |
| Paciente | Reservar un turno en un horario libre y consultar o cancelar sus reservas | No depender de llamar al consultorio | CU5, D4 | [PROP] candidato con riesgo; se decide en el roadmap (pregunta 5) |

## Alcance v0.1 — MVP académico

### Núcleo del MVP

Propuesto por el autor en Discovery §5 y tomado como base de la v0.1. La priorización final se hace en el roadmap.

- [REQ] Multi-consultorio con datos aislados por consultorio (D2, R6).
- [REQ] Roles por consultorio: administrador, secretaría y odontólogo (Discovery §2).
- [REQ] Profesionales con horarios de atención configurables (R3).
- [REQ] Prestaciones odontológicas con duración; la duración del turno depende de la prestación (R1).
- [REQ] Bloqueos de agenda: vacaciones, ausencias, feriados y otros períodos sin atención (R4).
- [REQ] Validación que impide que un mismo profesional tenga dos turnos superpuestos (R2; confirmado por el autor el 2026-10-13).
- [REQ] Gestión de turnos con estados (Discovery §5; los estados concretos son [PROP], ver `05_reglas_de_negocio.md`).
- [REQ] Ficha básica del paciente, sin datos clínicos (CU4, D3).
- [REQ] Aviso de privacidad o consentimiento (Discovery §5; Ley 25.326, arts. 2, 5 y 7, sin carácter de asesoramiento legal).

Regla del autor que no figura en la lista del núcleo:

- [PROP] Anticipación mínima configurable para cancelar o reprogramar, con 24 horas como valor inicial (R5). No hay evidencia de que sea una regla universal del mercado. Si se aplica solo al paciente o también a la secretaría es pregunta abierta (PA-12).

### Candidatos (no comprometidos)

- [PROP] Reserva online por el paciente (D4, estado: propuesta; se revisa en el roadmap). Es la primera candidata a pasar a la segunda etapa por riesgo de alcance (RG1).
- [PROP] Email de confirmación o aviso de turno, sin promesa sobre el ausentismo (D5).
- [PROP] Lista diaria para secretaría con enlaces wa.me (D6, propuesta por validar).
- [PROP] Exportación de datos y registro de auditoría: sugerencia nueva del informe (§6.3), sujeta al roadmap; no figura en D1–D9 ni es obligación del MVP sin decisión explícita del autor.

### Segunda etapa

Discovery §5, D7.

- Recordatorios automáticos por WhatsApp API o SMS (D7, propuesta).
- Lista de espera.
- Seña con Mercado Pago.
- Sincronización con Google Calendar.

## Fuera de alcance

- [DEC] Historia clínica y odontograma (D3, decidida por el autor).
- [DEC] Facturación, verificación de cobertura e integraciones con obras sociales o prepagas (D8, parcialmente decidida). El **dato** de obra social sigue abierto (pregunta 4).
- [DEC] Despliegue en la nube y contratación de servicios externos en esta etapa (respuesta del autor, 2026-10-13); el despliegue futuro queda como pregunta abierta.
- [ABIERTA] Gestión de sillones o boxes como recurso de agenda: **no forma parte del alcance aprobado**; queda como pregunta abierta (respuesta del autor, 2026-10-13; ver `10_preguntas_abiertas.md`).
- Excluir la historia clínica no elimina las obligaciones de protección de datos personales sobre pacientes y turnos (Ley 25.326; Discovery §9). No es asesoramiento legal.

## Métricas de éxito

Métricas del MVP académico. No se proponen métricas de negocio como la reducción del ausentismo, porque no hay línea de base local (H2, pregunta 13) y la evidencia del email solo es débil (RG6, CAIS 2016).

| Métrica | Cómo se mide | Origen |
|---|---|---|
| Cero superposiciones del mismo profesional | Pruebas automatizadas que intentan crear turnos solapados (incluidos intentos concurrentes) y deben ser rechazados | R2, D1 |
| Turnos siempre dentro del horario y fuera de bloqueos | Pruebas sobre horarios, bordes de bloqueos y feriados | R3, R4 |
| Duración del turno coherente con la prestación | Pruebas de cálculo de fin de turno | R1 |
| Cero accesos cruzados entre consultorios | Pruebas por endpoint con usuarios de dos consultorios ficticios | D2, R6, RG3 |
| Casos de uso CU1–CU4 demostrables de punta a punta | Demostración local con Docker Compose y datos ficticios | Discovery §3; DD-11 |
| Trazabilidad documental | Cada regla y funcionalidad referencia su origen (D#, R#, CU#, informe) | Prioridad del autor: documentación sólida |

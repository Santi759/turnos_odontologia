# Decisiones y Supuestos

> Fuentes: sección "Decisiones provisionales de producto" de `discovery/discovery.md` (D1–D9, aprobado el 2026-10-10); respuestas del autor en la Etapa 3 (2026-10-13); `docs/discovery/informe-discovery.md` §6.3. Etiquetas: ver [README](README.md#convenciones).

**Regla de esta sección:** D1–D9 conservan **textualmente** su enunciado y su estado original. Esta KB no convierte propuestas en decisiones. Cuando Discovery no documenta alternativas o justificación, se indica "No documentado en Discovery" en lugar de reconstruirlas.

| Código | Decisión | Estado original | Fecha |
|---|---|---|---|
| DD-01 (D1) | Problema central: superposición y errores de agenda | Planteo del autor; mercado sin validar | 2026-10-10 |
| DD-02 (D2) | SaaS multi-consultorio con registros de pacientes aislados (opción A) | Decidida por el autor | 2026-10-10 |
| DD-03 (D3) | Historia clínica y odontograma fuera de alcance | Decidida por el autor | 2026-10-10 |
| DD-04 (D4) | Reserva online como candidata al MVP, con riesgo de alcance explícito | Propuesta; se revisa en el roadmap | 2026-10-10 |
| DD-05 (D5) | Email como posible función de comunicación, sin promesa sobre el ausentismo | Propuesta | 2026-10-10 |
| DD-06 (D6) | Lista diaria para secretaría con enlaces wa.me | Propuesta por validar | 2026-10-10 |
| DD-07 (D7) | WhatsApp API y SMS en la segunda etapa | Propuesta | 2026-10-10 |
| DD-08 (D8) | Facturación, cobertura e integraciones con obras sociales fuera del MVP; inclusión del dato de obra social abierta | Parcialmente decidida | 2026-10-10 |
| DD-09 (D9) | Tratar la prestación del turno como dato sensible hasta tener opinión legal | Propuesta de criterio prudente, no conclusión jurídica | 2026-10-10 |
| DD-10 | Stack: React con Vite, FastAPI (SQLAlchemy 2, Alembic, Pydantic), PostgreSQL; pruebas con pytest y Vitest | Decidida por el autor | 2026-10-13 |
| DD-11 | Desarrollo y pruebas locales con Docker Compose; nube como posibilidad futura; sin servicios externos por ahora | Decidida por el autor (el despliegue futuro queda abierto) | 2026-10-13 |
| DD-12 | Sillones o boxes como pregunta abierta; el MVP impide superposiciones del mismo profesional | Decidida por el autor (mantener abierta la política de sillones) | 2026-10-13 |
| DD-13 | Solo datos ficticios en desarrollo y pruebas | Decidida por el autor | 2026-10-13 |
| DD-14 | Clasificación técnica del proyecto: `saas_multi_tenant`, `multi_tenant`, gestión de turnos odontológicos, requiere infraestructura | Confirmada por el autor | 2026-10-13 |

## Decisiones documentadas

### DD-01 — Problema central (D1)
**Decisión**: "Problema central: superposición y errores de agenda."
**Estado**: planteo del autor; mercado sin validar.
**Contexto**: el autor plantea errores y superposición de turnos y, como problema secundario, el tiempo perdido coordinando citas (Discovery §1). No hay evidencia externa ni entrevistas (preguntas 2 y 12; RG2).
**Alternativas consideradas**: No documentado en Discovery. `discovery/discovery.md` registra el problema elegido, pero no las alternativas que se descartaron.
**Justificación**: elección del autor. [MERCADO] Solo Órbita formula públicamente la prevención de superposición y solo 2 de 18 sistemas documentan la duración por prestación o los bloqueos (informe §5.2 y §5.3). Es una interpretación, no una validación.
**Trade-offs aceptados**: se construye sobre un problema no validado; si no fuera real, el valor del MVP cae (RG2).

### DD-02 — Multi-consultorio con pacientes aislados (D2)
**Decisión**: "SaaS multi-consultorio con registros de pacientes aislados (opción A)."
**Estado**: decidida por el autor.
**Contexto**: Discovery §5 y R6. Toda entidad lleva el identificador del consultorio; una misma persona puede tener registros independientes en distintos consultorios.
**Alternativas consideradas**: Discovery registra la elección de la "opción A"; el detalle de las otras opciones no quedó documentado en `discovery/discovery.md`.
**Justificación**: no documentada en Discovery más allá de la elección del autor.
**Trade-offs aceptados**: riesgo de fuga entre consultorios (RG3), mitigado con RN-MT-01 a RN-MT-06; sin cuenta única de paciente entre consultorios (SU-07, a validar).

### DD-03 — Sin historia clínica ni odontograma (D3)
**Decisión**: "Historia clínica y odontograma fuera de alcance."
**Estado**: decidida por el autor.
**Contexto**: Discovery §5.
**Alternativas consideradas**: No documentado en Discovery.
**Justificación**: no documentada más allá de la decisión; coherente con el alcance académico (RG1).
**Trade-offs aceptados**: [MERCADO] tensión T-01: 15 de 18 sistemas tienen historia clínica, 12 de 18 odontograma y los 4 odontológicos argentinos ambos. El producto compite más cerca de una agenda genérica que de un sistema clínico (informe §6.3). Excluirlos evita las obligaciones propias de la historia clínica (Ley 26.529), pero **no** las de protección de datos personales (Ley 25.326). No es asesoramiento legal.

### DD-04 — Reserva online como candidata (D4)
**Decisión**: "Reserva online como candidata al MVP, con riesgo de alcance explícito."
**Estado**: propuesta; se revisa en el roadmap.
**Contexto**: CU5; suma autenticación del paciente o reserva como invitado, una vista pública por consultorio y concurrencia sobre horarios libres (Discovery §5).
**Alternativas consideradas**: incluirla en el MVP o pasarla a la segunda etapa (pregunta 5).
**Justificación**: [MERCADO] la ofrecen 4 de 7 en la muestra inicial y 10 de 18 en el estudio ampliado (6 de 7 en nivel 1), según IN-02.
**Trade-offs aceptados**: primera candidata a pasar a la segunda etapa por RG1. Tensión T-02.

### DD-05 — Email sin promesa sobre el ausentismo (D5)
**Decisión**: "Email como posible función de comunicación, sin promesa sobre el ausentismo."
**Estado**: propuesta.
**Contexto**: Discovery §6 y §8. En el ensayo CAIS 2016 el email solo no mostró diferencia significativa; la revisión Cochrane CD007458, según Discovery, informa el efecto de los SMS y no aporta evidencia sobre el email.
**Alternativas consideradas**: WhatsApp API y SMS, pasados a la segunda etapa (D7).
**Justificación**: costo bajo (precios de Resend y SES leídos el 2026-10-10).
**Trade-offs aceptados**: puede no tener impacto en la asistencia (RG6). Requiere un proveedor externo, en tensión con DD-11 (IN-06).

### DD-06 — Lista diaria con enlaces wa.me (D6)
**Decisión**: "Lista diaria para secretaría con enlaces wa.me."
**Estado**: propuesta por validar.
**Contexto**: alternativa sin API para pacientes sin email (Discovery §8).
**Alternativas consideradas**: llamada telefónica; campo de contacto preferido (Discovery §8).
**Justificación**: sin costo de API. Eficacia no demostrada.
**Trade-offs aceptados**: envío manual; formato oficial del enlace [PEND].

### DD-07 — WhatsApp API y SMS en la segunda etapa (D7)
**Decisión**: "WhatsApp API y SMS en la segunda etapa."
**Estado**: propuesta.
**Contexto**: costo por mensaje y aprobación de plantillas de la Cloud API de Meta; tarifas para Argentina pendientes (preguntas 17 y 18).
**Alternativas consideradas**: incluirlos en el MVP.
**Justificación**: costo, dependencias y plazo.
**Trade-offs aceptados**: [MERCADO] tensión T-03: 15 de 18 sistemas tienen recordatorios automáticos y 13 de 18 WhatsApp (los 7 de nivel 1); el MVP queda por debajo del estándar de la muestra en este punto (informe §6.3).

### DD-08 — Facturación y obras sociales fuera del MVP (D8)
**Decisión**: "Facturación, cobertura e integraciones con obras sociales fuera del MVP; inclusión del dato de obra social abierta."
**Estado**: parcialmente decidida.
**Contexto**: Discovery §5; pregunta 4.
**Alternativas consideradas**: registrar la obra social como dato opcional o dejarla fuera (pregunta 4).
**Justificación**: no documentada más allá de la decisión.
**Trade-offs aceptados**: [MERCADO] tensión T-04: los 4 sistemas odontológicos argentinos gestionan obras sociales; ARCA aparece en 1 de 18 (informe §5.2 y §6.3). La parte abierta sigue abierta (RN-PA-09).

### DD-09 — Prestación como dato sensible (D9)
**Decisión**: "Tratar la prestación del turno como dato sensible hasta tener opinión legal."
**Estado**: propuesta de criterio prudente, no conclusión jurídica.
**Contexto**: Ley 25.326, art. 2 (los datos de salud son sensibles); RG4; pregunta 6.
**Alternativas consideradas**: No documentado en Discovery.
**Justificación**: criterio prudente ante la duda legal.
**Trade-offs aceptados**: restricciones de acceso y de contenido en mensajes (RN-PA-03).

### DD-10 — Stack tecnológico
**Decisión**: frontend React con Vite; backend FastAPI con SQLAlchemy 2, Alembic y Pydantic; base de datos PostgreSQL; pruebas con pytest y Vitest. Versiones a fijar al iniciar el proyecto.
**Estado**: decidida por el autor el 2026-10-13 (opción D de la ronda de preguntas de la Etapa 3).
**Contexto**: Discovery §9: "La cátedra no impone stack; la elección se justificará en la Knowledge Base."
**Alternativas consideradas**: (a) Next.js con TypeScript, Prisma y PostgreSQL; (b) API en Node (NestJS o Express), React y PostgreSQL; (c) Django con su panel de administración y PostgreSQL.
**Justificación**: experiencia previa del autor con React y FastAPI (factor de mayor peso para una sola persona con fecha incierta, RG1); documentación OpenAPI automática; PostgreSQL permite garantizar R2 en la base ante concurrencia.
**Trade-offs aceptados**: dos aplicaciones con CORS; autenticación sin solución incluida (PA-03, dominio crítico); pantallas de administración propias. El autor pidió no asumir que un filtro por consultorio es protección suficiente (RN-MT-06).

### DD-11 — Infraestructura local
**Decisión**: desarrollo y pruebas locales como base, preferentemente con Docker Compose. El despliegue en la nube queda como posibilidad futura y pregunta abierta, sujeta a las exigencias del profesor. No se contratan ni configuran servicios externos todavía.
**Estado**: decidida por el autor el 2026-10-13 (opción D); el despliegue futuro es PA-02.
**Alternativas consideradas**: solo local; local más nube para la entrega; aplicación local con base de datos gestionada.
**Justificación**: costo cero; sin datos personales en terceros; la decisión de despliegue depende de la entrega (pregunta 1).
**Trade-offs aceptados**: la demostración depende de la máquina del autor; la cátedra no puede probar por su cuenta mientras no haya despliegue.

### DD-12 — Sillones o boxes como pregunta abierta
**Decisión**: la asignación de sillones o boxes queda como pregunta abierta. El MVP impide superposiciones de turnos para un mismo profesional. Se documenta el riesgo de conflictos por sillón y la evidencia de Órbita, sin incorporar la entidad Sillón al modelo aprobado ni reglas nuevas obligatorias.
**Estado**: decidida por el autor el 2026-10-13 (opción A).
**Alternativas consideradas**: (b) entidad candidata marcada como pendiente; (c) solo riesgo.
**Justificación**: no hay política de asignación definida en Discovery; se evita aprobar algo no decidido.
**Trade-offs aceptados**: dos profesionales podrían quedar asignados al mismo sillón al mismo tiempo sin que el sistema lo detecte (PA-01; `04_modelo_de_datos.md`, "Extensión posible").

### DD-13 — Datos ficticios
**Decisión**: usar solo datos ficticios durante el desarrollo y las pruebas.
**Estado**: decidida por el autor el 2026-10-13.
**Justificación**: evita tratar datos personales y de salud reales en un MVP académico (Ley 25.326; D9).
**Trade-offs aceptados**: no hay validación con datos ni usuarios reales (RG2).

### DD-14 — Clasificación técnica del proyecto
**Decisión**: `problem`: superposición y errores de agenda en consultorios odontológicos; `system_type`: `saas_multi_tenant`; `scale`: `multi_tenant`; `domain`: gestión de turnos odontológicos; `needs_infra`: `true`; alcance: v0.1 — MVP académico.
**Estado**: confirmada por el autor el 2026-10-13 (valores tomados de Discovery y presentados para confirmación).

## Supuestos inferidos

### SU-01 — Zona horaria argentina
**Supuesto**: todos los consultorios operan en Argentina con la zona `America/Argentina/Buenos_Aires`, configurable por consultorio.
**Origen**: el producto es para Argentina (Discovery); la zona no se discutió.
**Riesgo si es falso**: horarios corridos si se suma un consultorio de otra zona.
**Cómo validar**: confirmar con el autor; los instantes se almacenan con zona horaria de todos modos (RN-GL-01).

### SU-02 — Un usuario, un consultorio, un rol
**Supuesto**: cada usuario pertenece a un solo consultorio con un solo rol en la v0.1.
**Origen**: inferido de D2 y de los roles por consultorio (Discovery §2, §5).
**Riesgo si es falso**: un odontólogo que atiende en varios consultorios necesita varias cuentas; cambiarlo luego requiere una entidad de membresía.
**Cómo validar**: PA-06.

### SU-03 — Profesional separado del usuario
**Supuesto**: el profesional de la agenda puede existir sin usuario y vincularse luego a un usuario odontólogo.
**Origen**: inferido de CU1 (el administrador configura profesionales) y CU3 (el odontólogo consulta su agenda).
**Riesgo si es falso**: duplicación o confusión entre profesional y usuario.
**Cómo validar**: PA-17.

### SU-04 — Una prestación por turno
**Supuesto**: cada turno tiene una sola prestación.
**Origen**: R1 habla de "la prestación" del turno.
**Riesgo si es falso**: turnos de varias prestaciones requerirían sumar duraciones.
**Cómo validar**: consulta con consultorios (pregunta 2).

### SU-05 — La duración se fija al crear el turno
**Supuesto**: el turno toma la duración vigente de la prestación al crearse; los cambios posteriores en la prestación no lo modifican.
**Origen**: inferido de R1 y de la necesidad de no generar superposiciones retroactivas.
**Riesgo si es falso**: turnos existentes con duración desactualizada.
**Cómo validar**: confirmar con el autor junto con PA-09.

### SU-06 — Un turno cancelado libera el horario
**Supuesto**: solo los turnos no cancelados ocupan agenda para R2.
**Origen**: inferido de CU2 (cancelar) y R2.
**Riesgo si es falso**: horarios bloqueados por turnos cancelados.
**Cómo validar**: PA-07.

### SU-07 — Sin cuenta única de paciente entre consultorios
**Supuesto**: los pacientes no esperan una cuenta única entre consultorios.
**Origen**: Discovery §7, R6 ("Supuesto a validar").
**Riesgo si es falso**: fricción para pacientes de varios consultorios si se aprueba D4.
**Cómo validar**: preguntas 3 y 14.

### SU-08 — Feriados cargados manualmente
**Supuesto**: los feriados se cargan como bloqueos de consultorio, sin integración con un calendario oficial.
**Origen**: R4 y "sin integraciones externas" (Discovery §8).
**Riesgo si es falso**: olvido de feriados y turnos en días no laborables.
**Cómo validar**: confirmar con el autor; posible mejora futura.

### SU-09 — Los datos ficticios alcanzan para el MVP académico
**Supuesto**: la validación funcional con datos ficticios es suficiente para la entrega.
**Origen**: DD-13 y alcance académico.
**Riesgo si es falso**: la cátedra podría pedir validación con usuarios.
**Cómo validar**: pregunta 1 y requisitos de la entrega.

### SU-10 — Un solo local por consultorio
**Supuesto**: cada consultorio opera en una sola sede en la v0.1.
**Origen**: Discovery no menciona multisede para el producto. [MERCADO] Multisede aparece en Dentalink (plan Pro) y Dentidesk.
**Riesgo si es falso**: un consultorio con varias sedes no podría separar agendas por sede.
**Cómo validar**: consulta con consultorios (pregunta 2).

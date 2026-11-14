# Reglas de Negocio

> Fuentes: `discovery/discovery.md` §5, §7 (R1–R6), §8, §9 y §10 (RG1–RG7); D1–D9; `docs/discovery/informe-discovery.md` §5 y §6.3; respuestas del autor del 2026-10-13. Etiquetas: ver [README](README.md#convenciones).

Cada regla tiene un código `RN-{DOMINIO}-{NN}`, su **origen** y su **estado**.

- **R1–R6** son *propuestas del autor, pendientes de validar con consultorios* (Discovery §7). La KB las toma como base de la v0.1 sin cambiar ese estado: su validación sigue pendiente (RG2).
- Las reglas **derivadas** son consecuencias necesarias de una R# o de una D#, y se identifican como tales.
- Las reglas **propuestas** por esta KB llevan la etiqueta [PROP]. Los **requisitos técnicos propuestos** (buenas prácticas de seguridad incorporadas en la Etapa 3) también son [PROP]: se mantienen como recomendación y se aprueban en el Change correspondiente.

## Dominio: Multi-consultorio (RN-MT)

| Código | Regla | Origen | Estado |
|---|---|---|---|
| RN-MT-01 | Cada consultorio tiene sus propios registros de pacientes, profesionales, prestaciones, horarios, bloqueos y turnos, aislados del resto. | R6, D2 | [REQ] (D2 decidida; R6 propuesta del autor) |
| RN-MT-02 | El consultorio de una operación se **deriva de la identidad autenticada** en el servidor. Nunca se toma de un parámetro, encabezado o cuerpo enviado por el cliente. | Derivada de R6 y RG3 | [REQ] (derivada) |
| RN-MT-03 | Toda referencia entre entidades (turno → paciente, profesional o prestación; bloqueo → profesional) debe apuntar a registros **del mismo consultorio**. | Derivada de R6 | [REQ] (derivada) |
| RN-MT-04 | Una misma persona puede tener registros de paciente independientes en distintos consultorios. No hay cuenta única entre consultorios. | R6 (implicancia 2) | [REQ]. SU-07: los pacientes no esperarían una cuenta única (supuesto a validar, Discovery §7) |
| RN-MT-05 | El acceso a un recurso de otro consultorio responde igual que un recurso inexistente, sin revelar que existe. | Derivada de RG3 | [REQ] |
| RN-MT-06 | **Un filtro por consultorio en cada consulta no se considera protección suficiente por sí solo.** Se requiere defensa en profundidad: validación de RN-MT-02 y RN-MT-03, pruebas automatizadas de acceso cruzado por endpoint y, al menos, una barrera adicional en la base de datos. | RG3; respuesta del autor del 2026-10-13 | [REQ] el principio; el mecanismo concreto es [ABIERTA] PA-04 |

Riesgos que estas reglas buscan cubrir, documentados sin elegir todavía la implementación:

- Consultas o *joins* que omiten el filtro de consultorio (RG3).
- Identificadores de otro consultorio enviados por el cliente: acceso directo a objetos ajenos o asignación masiva de `consultorio_id` en el cuerpo de la petición.
- Referencias cruzadas válidas en la base pero entre consultorios distintos, por ejemplo un turno de A con un paciente de B.
- Exportaciones, listados o mensajes de error que filtran datos de otro consultorio.
- Tokens o sesiones manipulados para cambiar de consultorio.

## Dominio: Autenticación y autorización (RN-AU)

El mecanismo es [ABIERTA] PA-03. Es un dominio **crítico**: la implementación requiere aprobación explícita del autor antes de escribir código.

Origen de este dominio: los roles de Discovery §2, el riesgo RG3 y **buenas prácticas propuestas por esta KB en la Etapa 3**. La Ley 25.326 (arts. 9 y 10) establece un deber general de adoptar medidas de seguridad y confidencialidad, pero **no prescribe** algoritmos, vencimientos de sesión ni límites de intentos. La relación entre estas prácticas y ese deber general es una interpretación, no asesoramiento legal.

| Código | Regla | Origen | Estado |
|---|---|---|---|
| RN-AU-01 | Toda ruta no pública requiere un usuario autenticado y activo. | Derivada de Discovery §2 (roles por consultorio) y de D2 | [REQ] (derivada) |
| RN-AU-02 | Las credenciales se almacenan con un algoritmo de derivación de contraseñas resistente; nunca en texto plano ni con cifrado reversible. | Buena práctica propuesta por la KB (Etapa 3) | [PROP] requisito técnico propuesto; el algoritmo es PA-03 |
| RN-AU-03 | La autorización por rol se verifica en el servidor en cada operación, según la matriz de `03_actores_y_roles.md`. | Derivada de Discovery §2 | [REQ] (derivada); la matriz de permisos es [PROP] |
| RN-AU-04 | Las sesiones o tokens tienen vencimiento y pueden cerrarse. | Buena práctica propuesta por la KB (Etapa 3) | [PROP] requisito técnico propuesto; el mecanismo es PA-03 |
| RN-AU-05 | Se limitan los intentos fallidos de inicio de sesión. | Buena práctica propuesta por la KB (Etapa 3) | [PROP] requisito técnico propuesto |
| RN-AU-06 | Un usuario desactivado pierde el acceso de inmediato. | Derivada de RN-AU-01 | [REQ] (derivada) |
| RN-AU-07 | Los secretos (claves de firma, contraseñas de la base) se configuran por variables de entorno y nunca se versionan. | Buena práctica propuesta por la KB (Etapa 3); `08_arquitectura_propuesta.md` | [PROP] requisito técnico propuesto |
| RN-AU-08 | La recuperación de contraseña sin integraciones de email en el MVP queda sin definir. | IN-06 | [ABIERTA] PA-11 |

## Dominio: Agenda (RN-AG)

| Código | Regla | Origen | Estado |
|---|---|---|---|
| RN-AG-01 | **La duración de un turno depende de la prestación odontológica**: `fin = inicio + duración de la prestación`. | R1 | [REQ] (propuesta del autor) |
| RN-AG-02 | **Un profesional no puede tener dos turnos superpuestos.** | R2, D1; confirmado por el autor el 2026-10-13 | [REQ] (regla firme) |
| RN-AG-02b | **Qué estados ocupan agenda** a efectos de RN-AG-02. Propuesta inicial en RN-TU-05. La definición está pendiente y no cambia la regla firme, solo su alcance; su impacto en PostgreSQL está descrito en `04_modelo_de_datos.md` (entidad Turno). | Derivada de R2 y de la "gestión de turnos con estados" (Discovery §5) | [ABIERTA] PA-07 |
| RN-AG-03 | RN-AG-02 se garantiza también ante operaciones **concurrentes**: si dos usuarios reservan el mismo horario al mismo tiempo, solo una operación tiene éxito. La garantía final está en la base de datos, no solo en una verificación previa del código. | Derivada de R2 y RG1 | [REQ] (derivada) el comportamiento; el mecanismo es [PROP] (restricción de exclusión, `04_modelo_de_datos.md`). Esa garantía cubre solo turno contra turno: la concurrencia entre la creación de un turno y la de un bloqueo o un cambio de horario es [ABIERTA] PA-20 |
| RN-AG-04 | Los intervalos son semiabiertos `[inicio, fin)`: turnos consecutivos (uno termina 10:30 y el siguiente empieza 10:30) no se superponen. | Derivada de R2 | [PROP] |
| RN-AG-05 | Cada profesional tiene horarios de atención configurables por día de la semana, con una o más franjas. | R3 | [REQ] (propuesta del autor); varias franjas por día es [PROP] |
| RN-AG-06 | Un turno debe quedar **completo** dentro de una franja de atención del profesional: si la duración de la prestación excede el final de la franja, el turno se rechaza. | Derivada de R1 y R3 | [REQ] (derivada). Qué pasa con los turnos existentes si cambia una franja es [ABIERTA] PA-18 |
| RN-AG-07 | Se pueden bloquear vacaciones, ausencias, feriados y otros períodos sin atención. | R4 | [REQ] (propuesta del autor) |
| RN-AG-08 | Un turno no puede intersecar ningún bloqueo aplicable: los del profesional y los de todo el consultorio. | Derivada de R4 | [REQ] (derivada); el bloqueo de todo el consultorio es [PROP] (PA-10) |
| RN-AG-09 | Qué ocurre con los turnos ya existentes cuando se crea un bloqueo que los cubre (rechazar el bloqueo, avisar o cancelar) queda sin definir. | R4 | [ABIERTA] PA-10 |
| RN-AG-10 | No se admiten turnos nuevos con profesionales o prestaciones inactivos. | Derivada de CU1 | [PROP] |
| RN-AG-11 | La disponibilidad (horarios libres) que se ofrece a la secretaría o al paciente se calcula aplicando RN-AG-01 a RN-AG-08 para una prestación y un profesional dados. | Derivada de R1–R4 | [REQ] (derivada); qué turnos descuenta depende de RN-AG-02b |
| RN-AG-12 | La granularidad de los horarios ofrecidos (por ejemplo, cada 5, 10 o 15 minutos) y el uso de tiempos de preparación entre turnos están sin definir. | No surge de Discovery | [ABIERTA] PA-08 |
| RN-AG-13 | Si la secretaría puede modificar la duración de un turno respecto de la prestación, o si hay duraciones distintas por profesional, está sin definir. | R1 | [ABIERTA] PA-09 |

**Sillones o boxes: no hay regla aprobada.** RN-AG-02 impide la superposición del **mismo profesional**, pero no impide que dos profesionales distintos usen el mismo sillón al mismo tiempo. Ese riesgo queda documentado y la política de asignación de sillones o boxes es [ABIERTA] PA-01, por decisión del autor del 2026-10-13. [MERCADO] Órbita: "Agenda por sillón. Dos pacientes no pueden caer en el mismo sillón." (informe §5.2). Cómo impide Órbita la superposición entre profesionales, y no solo por sillón, quedó como punto a verificar en demo (informe §6.1).

[MERCADO] Solo 2 de 18 sistemas documentan públicamente la duración por prestación o los bloqueos: Odonto.ar ("Cada motivo ocupa los minutos que ocupa de verdad.") y Órbita ("Respeta la duración de cada práctica"; bloqueo de vacaciones y feriados de una vez). En el resto figura como "No evidenciado", que no equivale a "no existe" (informe §5.3).

## Dominio: Turnos (RN-TU)

| Código | Regla | Origen | Estado |
|---|---|---|---|
| RN-TU-01 | Un turno se crea con consultorio, profesional, paciente, prestación e inicio; el fin se calcula (RN-AG-01). | CU2, R1 | [REQ] (derivada) |
| RN-TU-02 | Toda modificación o reprogramación de inicio, profesional o prestación vuelve a validar RN-AG-01 a RN-AG-08. | Derivada de CU2 | [REQ] (derivada) |
| RN-TU-03 | **La anticipación mínima para cancelar o reprogramar es configurable por consultorio, con 24 horas como valor inicial.** No hay evidencia de que sea una regla universal del mercado. | R5 | [PROP] (propuesta del autor). Si alcanza a la secretaría o solo al paciente es [ABIERTA] PA-12 |
| RN-TU-04 | Conjunto inicial de estados: `reservado` → `confirmado` → `atendido`; `ausente` (no asistió); `cancelado`. La reprogramación modifica el mismo turno; el estado resultante tras reprogramar es PA-07. | Discovery §5 ("gestión de turnos con estados"); [MERCADO] en Dentally y Bilog el estado cambia según la respuesta del paciente (informe §6.3); Órbita como referencia para diseñar confirmado, cancelado y reprogramado (informe §6.2) | [PROP]; transiciones definitivas en [ABIERTA] PA-07 |
| RN-TU-05 | Propuesta inicial para RN-AG-02b: ocupan agenda los turnos `reservado` y `confirmado` (y `atendido` y `ausente`, por ser hechos pasados). Un turno `cancelado` libera el horario. Casos sin política: reutilizar el horario de un `ausente` y reactivar un `cancelado` (que debería revalidar RN-AG-01 a RN-AG-08). | Derivada de R2 | [PROP] SU-06; decisión en PA-07 |
| RN-TU-06 | No se crean turnos nuevos con inicio en el pasado. | No surge de Discovery | [PROP] |
| RN-TU-07 | El odontólogo consulta sus turnos y no los crea ni los cancela en la v0.1. | CU3 | [REQ] la consulta de la agenda; si marca `atendido` o `ausente` es [ABIERTA] PA-07 |
| RN-TU-08 | Registrar `ausente` permite medir el ausentismo propio en el futuro, sin prometer reducirlo. | H2 (pregunta 13), RG6 | [PROP] |
| RN-TU-09 | Cada turno registra quién hizo **el último cambio** y cuándo. Un historial completo de cambios es [ABIERTA] PA-19; la auditoría de accesos y cambios es candidata (E8) y no forma parte del núcleo. | Derivada de CU2 | [PROP] |

## Dominio: Pacientes y privacidad (RN-PA)

Ninguna de estas reglas es asesoramiento legal. Las preguntas 6 a 11 quedan para asesoría.

| Código | Regla | Origen | Estado |
|---|---|---|---|
| RN-PA-01 | La ficha del paciente es **básica y sin datos clínicos**: sin historia clínica, odontograma ni diagnóstico. | CU4, D3 | [REQ] (D3 decidida) |
| RN-PA-02 | Solo se piden datos adecuados, pertinentes y no excesivos para gestionar turnos. Qué datos identificatorios se piden (por ejemplo, DNI) queda abierto. | Principio de la Ley 25.326, art. 4 (Discovery §9) | [REQ] el principio; los campos concretos son PA-14 |
| RN-PA-03 | **La prestación o el motivo del turno se trata como dato sensible** hasta tener opinión legal: acceso restringido a los roles del consultorio que la necesitan; no se incluye en registros técnicos (logs) ni en mensajes enviados al paciente por canales externos (email, wa.me). | D9 (propuesta de criterio prudente); RG4; Ley 25.326, art. 2 (los datos de salud son sensibles) | [PROP]; las medidas concretas (acceso, logs y mensajes) son propuestas de esta KB, no mecanismos que la ley establezca |
| RN-PA-04 | El consultorio muestra un aviso de privacidad y se registra su aceptación con versión y fecha. | Discovery §5 (núcleo); Ley 25.326, arts. 5 y 7 | [REQ] el aviso; la forma de registro es [PROP]; si hace falta consentimiento expreso depende de las preguntas 6, 9 y 11 |
| RN-PA-05 | Los campos de la ficha que no son necesarios para gestionar el turno son opcionales. | Propuesta de la KB (Etapa 3), inspirada en la Ley 25.326, art. 7 ("nadie puede ser obligado a proporcionar datos sensibles"); la ley no prescribe este mecanismo | [PROP] |
| RN-PA-06 | No hay borrado físico de pacientes ni turnos en la v0.1; se desactivan. La política de conservación, supresión y acceso del titular es una pregunta abierta. | Propuesta de la KB (Etapa 3); la política de acceso y supresión se relaciona con la Ley 25.326, art. 14 (interpretación) | [PROP] la desactivación; la política es [ABIERTA] PA-16 |
| RN-PA-07 | El paciente puede tener un **contacto preferido** (teléfono, WhatsApp o email), útil para los pacientes sin email. | Discovery §8 (propuesta sin eficacia demostrada) | [PROP] |
| RN-PA-08 | En desarrollo y pruebas se usan **solo datos ficticios**. | Autor, 2026-10-13 | [REQ] |
| RN-PA-09 | La obra social o prepaga **no se registra** en la v0.1 mientras la pregunta 4 siga abierta. | D8 (parcialmente decidida), pregunta 4 | [ABIERTA] |

## Dominio: Comunicación con el paciente (RN-CO)

Todas son propuestas o segunda etapa; ninguna es parte comprometida del núcleo.

| Código | Regla | Origen | Estado |
|---|---|---|---|
| RN-CO-01 | Email de confirmación o aviso de turno, **sin afirmar que reduce el ausentismo**. | D5; RG6; CAIS 2016 (el email solo no mostró diferencia significativa) | [PROP] |
| RN-CO-02 | Lista diaria para secretaría con enlaces wa.me (mensaje prearmado, sin API). | D6 | [PROP] por validar; formato oficial del enlace [PEND] |
| RN-CO-03 | Recordatorios automáticos por WhatsApp API o SMS. | D7 | Segunda etapa |
| RN-CO-04 | Los recordatorios podrían requerir consentimiento específico u opción de baja. | Pregunta 11; [MERCADO] Dentally solo envía recordatorios a pacientes con consentimiento (informe §6.2) | [ABIERTA] |
| RN-CO-05 | Los enlaces de confirmación o cancelación sin inicio de sesión deben ser no adivinables, de uso acotado y con vencimiento. | Derivada de D5 y D6; [MERCADO] Dentally (recall con enlace sin login) | [PROP] |

## Dominio: Reserva online del paciente (RN-RE) — candidata

Aplica solo si el roadmap incorpora D4 al MVP (pregunta 5).

| Código | Regla | Origen | Estado |
|---|---|---|---|
| RN-RE-01 | El paciente solo ve y reserva horarios libres calculados con RN-AG-11; la reserva pasa por las mismas validaciones y por la garantía de concurrencia RN-AG-03. | D4, CU5; Discovery §5 ("concurrencia sobre horarios libres") | [PROP] |
| RN-RE-02 | El paciente reserva con cuenta propia o como invitado. | Pregunta 3 | [ABIERTA] |
| RN-RE-03 | La vista pública no expone datos de otros pacientes ni de turnos ajenos. | Derivada de D9 y RG3 | [PROP] |
| RN-RE-04 | El paciente cancela sus turnos respetando RN-TU-03. | CU5, R5 | [PROP] |

[MERCADO] Reserva online por el paciente: 10 de 18 sistemas (6 de 7 de nivel 1) según el informe §5.1. En la muestra inicial de Discovery eran 4 de 7 (IN-02). Es evidencia de mercado, no una decisión: D4 sigue como propuesta.

## Dominio: Excepciones globales

| Código | Regla | Origen | Estado |
|---|---|---|---|
| RN-GL-01 | Los instantes se almacenan con zona horaria y se muestran en la zona del consultorio. | SU-01 | [PROP] |
| RN-GL-02 | Toda operación que crea o modifica un turno es atómica: o se aplica completa o no se aplica. | Derivada de RN-AG-03 | [REQ] |
| RN-GL-03 | Los rechazos por reglas de agenda informan el motivo (superposición, fuera de horario, bloqueo, prestación inactiva) sin revelar datos de otros pacientes. | Derivada de RN-AG y RN-PA-03 | [PROP] |
| RN-GL-04 | Nada de lo marcado como [ABIERTA] se implementa como regla definitiva sin decisión del autor. | Consigna del autor | [REQ] |

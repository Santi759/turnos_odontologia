# Preguntas Abiertas

> Fuentes: punto 11 de `discovery/discovery.md` (19 preguntas, H1 y H2); §5.3, §6.1, §6.3 y §7 de `docs/discovery/informe-discovery.md`; preguntas nuevas detectadas al armar esta KB (2026-10-13). Etiquetas: ver [README](README.md#convenciones).

Códigos:

- **P-01 a P-19**: preguntas originales de Discovery, con su numeración y texto.
- **M-01 a M-07**: preguntas que aporta o refuerza el estudio de mercado (informe §7).
- **T-01 a T-04**: tensiones entre decisiones y evidencia de mercado (informe §6.3).
- **PA-01 a PA-20**: preguntas nuevas de esta KB (PA-18 a PA-20 agregadas en la auditoría del 2026-10-13).
- **IN-01 a IN-06**: inconsistencias detectadas entre fuentes.
- **NE-01 a NE-12**: ítems "No evidenciado" del estudio de mercado que afectan decisiones de producto.

## Inconsistencias detectadas

### IN-01 — Obra social en la muestra inicial frente al estudio ampliado
**Documento A dice**: `discovery/discovery.md` §5: "en las páginas leídas ninguno de los 7 competidores muestra un campo verificable" de obra social.
**Documento B dice**: informe §5.2: "Obras sociales — solo los 4 sistemas odontológicos argentinos" (Órbita, Bilog, DentalTec, Odonto.ar).
**Impacto**: no es una contradicción de hecho (son muestras distintas: los 4 sistemas argentinos se sumaron en el estudio ampliado), pero cambia el peso de la pregunta P-04.
**Resolución propuesta**: citar ambos datos con su muestra; la decisión sigue en P-04 y T-04.

### IN-02 — Proporción de reserva online según la muestra
**Documento A dice**: Discovery §5: "4 de 7 competidores la ofrecen según fuente oficial".
**Documento B dice**: informe §5.1: 10 de 18 (6 de 7 en nivel 1).
**Impacto**: distinta lectura del peso de mercado de D4.
**Resolución propuesta**: usar las cifras del informe como evidencia de mercado, aclarando la muestra; D4 no cambia de estado.

### IN-03 — Superposición por profesional frente a superposición por sillón
**Documento A dice**: R2: "Un profesional no puede tener dos turnos superpuestos."
**Documento B dice**: referencia de mercado Órbita: "Dos pacientes no pueden caer en el mismo sillón" (informe §5.2); el informe §6.1 pregunta cómo impide Órbita la superposición "entre profesionales y no solo por sillón".
**Impacto**: R2 no cubre conflictos de sillón entre profesionales distintos.
**Resolución propuesta**: resuelta en alcance por DD-12 (R2 aprobado; sillones abiertos). La pregunta sigue en PA-01.

### IN-04 — "Gestión de turnos con estados" sin estados definidos
**Documento A dice**: Discovery §5, núcleo: "gestión de turnos con estados".
**Documento B dice**: ninguna fuente define los estados; el informe §6.2 sugiere diseñar confirmado, cancelado y reprogramado tomando a Órbita como referencia.
**Impacto**: sin estados definidos no se puede cerrar R2 (qué turnos ocupan agenda) ni las transiciones.
**Resolución propuesta**: conjunto inicial [PROP] en RN-TU-04; decisión en PA-07.

### IN-05 — Fecha de entrega relativa
**Documento A dice**: Discovery §9: "Entrega del martes sin definir (avance o trabajo completo)".
**Documento B dice**: no hay fecha absoluta en ninguna fuente.
**Impacto**: el roadmap no puede dimensionar el alcance (RG1).
**Resolución propuesta**: el autor fija la fecha y el tipo de entrega (P-01) antes del roadmap.

### IN-06 — "Sin integraciones externas" frente a funciones que necesitan email
**Documento A dice**: Discovery §8: "No hay integraciones externas obligatorias en el MVP núcleo"; DD-11: no se contratan servicios externos todavía.
**Documento B dice**: D5 (email) y la recuperación de contraseña requieren enviar emails.
**Impacto**: sin email no hay recuperación de contraseña autoservicio ni avisos por email.
**Resolución propuesta**: [PROP] en la v0.1 local, recuperación de contraseña por el administrador del consultorio, y email fuera de la v0.1 o con un servidor de correo de prueba local. A decidir en PA-11 y en el roadmap (D5).

## Preguntas abiertas (priorizadas)

**Prioridad**: Alta = bloquea el roadmap o un Change del núcleo · Media = bloquea un Change específico o una candidata · Baja = no bloquea la v0.1.
**Decisor**: Autor = Santiago Chepilla · Asesoría = consulta legal · Consultorios = validación con consultorios reales · Verificación = comprobación de fuentes.

### Preguntas originales de Discovery (P-01 a P-19)

| Código | Prioridad | Pregunta | Bloquea | Decisor |
|---|---|---|---|---|
| P-01 | Alta | ¿Qué se presenta el martes: un avance o el trabajo completo? *Aclaración (2026-10-13): el texto original se conserva por trazabilidad; todavía no hay una fecha absoluta ni una confirmación del tipo de entrega (ver IN-05).* | Roadmap (alcance y orden); despliegue (PA-02) | Autor y cátedra |
| P-02 | Media | ¿Es posible entrevistar consultorios reales? Si no, las hipótesis de mercado se documentan como no validadas. | Validación de R1–R6 y de D1 (RG2) | Autor |
| P-03 | Media | ¿El paciente reserva con cuenta propia o como invitado? | E6 (D4) | Autor |
| P-04 | Media | ¿La obra social o prepaga se incluye como dato opcional o queda fuera del MVP? ¿Se necesita algún tratamiento de la cobertura? | Modelo de Paciente (RN-PA-09) | Autor |
| P-05 | Alta | ¿La reserva online entra al MVP o pasa a la segunda etapa? Se decide con el roadmap. | Roadmap; E6 | Autor |
| P-06 | Media | ¿La prestación o el motivo del turno es un dato sensible? | Alcance de D9 y RN-PA-03 | Asesoría |
| P-07 | Baja | ¿El SaaS actúa como encargado del tratamiento, como responsable o como ambos? | Despliegue real; contratos | Asesoría |
| P-08 | Baja | ¿Quién debe inscribir la base ante la AAIP, y una agenda de pacientes encuadra en bases "destinadas a proporcionar informes"? | Despliegue real | Asesoría |
| P-09 | Media | ¿La excepción del art. 5, inciso 2 d) de la Ley 25.326 alcanza a datos sensibles? | Forma del consentimiento (RN-PA-04) | Asesoría |
| P-10 | Baja | ¿Alojar los datos fuera de Argentina constituye transferencia internacional, y con qué requisitos? | Despliegue en la nube (PA-02) | Asesoría |
| P-11 | Media | ¿Los recordatorios requieren consentimiento específico u opción de baja? | E7 (D5, D6); segunda etapa (D7) | Asesoría |
| P-12 | Baja | H1: ¿cómo coordinan hoy los consultorios los turnos (WhatsApp, teléfono, papel, planillas)? Solo hay afirmaciones de vendedores y blogs [3°], por ejemplo https://developargentina.com/blog/software-para-clinicas-argentina-turnos-ausencias-2026 | Validación de D1 | Consultorios |
| P-13 | Baja | H2: ¿cuál es la tasa de ausentismo odontológico en Argentina? Sin dato local verificado. Referencias de otros contextos: odontopediatría académica en EE.UU., 14,3% (https://pmc.ncbi.nlm.nih.gov/articles/PMC12274092/); Finlandia, de 9,9% a 5,8% (https://pmc.ncbi.nlm.nih.gov/articles/PMC12535098/); CAIS 2016 presenta rangos generales no consistentes dentro del mismo trabajo. | Métricas de negocio futuras | Consultorios o literatura |
| P-14 | Baja | ¿Los pacientes prefieren reservar solos o a través de la secretaría? | Valor de D4 | Consultorios |
| P-15 | Baja | ¿Qué proporción de pacientes no tiene email o prefiere WhatsApp? | Valor de D5 y D6 | Consultorios |
| P-16 | Baja | ¿Cuánto estaría dispuesto a pagar un consultorio? | Modelo comercial (fuera de la v0.1) | Consultorios |
| P-17 | Baja | Tarifa de WhatsApp para Argentina, verificación de negocio y condiciones de consentimiento. | Segunda etapa (D7) | Verificación |
| P-18 | Baja | Tarifa de SMS en Argentina. | Segunda etapa (D7) | Verificación |
| P-19 | Baja | ¿XIAgenda sigue operativo? ¿Dentalink, Dentidesk y Doctocliq operan en Argentina? | Análisis competitivo | Verificación |

### Preguntas del estudio de mercado (M-01 a M-07; informe §7)

| Código | Prioridad | Pregunta | Bloquea | Decisor |
|---|---|---|---|---|
| M-01 | Baja | XIAgenda sigue sin sitio oficial accesible (ENOTFOUND el 2026-10-10 y el 2026-10-12); toda su ficha proviene de un comparador. | Análisis competitivo (amplía P-19) | Verificación |
| M-02 | Baja | Sistemas mencionados fuera de los 18 (por ejemplo, Reservo) no tienen ficha ni fuente; su inclusión queda pendiente. | Análisis competitivo | Verificación |
| M-03 | Media | ¿Se revisa D3 a la luz del mercado? Historia clínica y odontograma son estándar en los sistemas odontológicos de la muestra. | Posicionamiento (T-01) | Autor |
| M-04 | Media | ¿El dato de obra social entra como campo opcional? El mercado odontológico argentino lo gestiona en los 4 casos relevados. | Modelo de Paciente (P-04) | Autor |
| M-05 | Media | ¿Qué valor tiene la confirmación sin WhatsApp API? Falta evidencia de eficacia del email con enlace o del wa.me manual. | E7 (D5, D6) | Autor y Consultorios |
| M-06 | Baja | ¿Operan Odeen, Dentalink, Doctocliq y Dentidesk en Argentina? | Análisis competitivo (amplía P-19) | Verificación |
| M-07 | Baja | ¿Doctoralia atiende a odontología con funciones específicas? El segmento odontológico quedó No evidenciado. | Análisis competitivo | Verificación |

Pendientes de verificación personal de fuentes del informe (§8.1): filas 4, 5, 8, 9 y 10, y el contraste con InfoLEG de la fila 3. No se aportaron capturas de pantalla.

### Tensiones entre decisiones y mercado (T-01 a T-04; informe §6.3)

| Código | Prioridad | Tensión | Decisión afectada | Decisor |
|---|---|---|---|---|
| T-01 | Media | 15 de 18 sistemas con historia clínica y 12 de 18 con odontograma; sin ellos, el producto compite más cerca de una agenda genérica. | D3 (decidida) | Autor |
| T-02 | Alta | La reserva online es mayoritaria en la muestra (6 de 7 en nivel 1), pero es la primera candidata a salir del MVP por alcance (RG1). | D4 (propuesta) | Autor, en el roadmap |
| T-03 | Media | Recordatorios automáticos en 15 de 18 y WhatsApp en 13 de 18 (los 7 de nivel 1); postergarlos deja al MVP por debajo del estándar de la muestra. | D7 (propuesta) | Autor, en el roadmap |
| T-04 | Media | Los 4 sistemas odontológicos argentinos gestionan obras sociales; ARCA en 1 de 18. | D8 (parcialmente decidida) | Autor |

### Preguntas nuevas de esta KB (PA-01 a PA-20)

| Código | Prioridad | Pregunta | Bloquea | Decisor |
|---|---|---|---|---|
| PA-01 | Media | **Sillones o boxes**: ¿el sillón es un recurso que no puede superponerse entre profesionales? ¿Cómo se asigna (fijo por profesional, por turno, por prestación)? Mientras no se decida, R2 cubre solo al mismo profesional y el conflicto de sillón queda sin control. [MERCADO] Órbita: "Dos pacientes no pueden caer en el mismo sillón." | Extensión del modelo de turnos | Autor (y Consultorios) |
| PA-02 | Media | ¿La entrega exige un despliegue accesible para la cátedra? Si es así, ¿con qué proveedor y en qué región (P-07, P-08, P-10)? | Change de despliegue | Autor y cátedra |
| PA-03 | Alta | Mecanismo de autenticación: sesión con cookie, tokens de acceso y renovación, o librería; algoritmo de contraseñas. Dominio crítico. | Change de acceso (E1) | Autor |
| PA-04 | Alta | Capas concretas de aislamiento además del filtro por consultorio: claves foráneas compuestas, RLS de PostgreSQL, identificadores no secuenciales. | Change de acceso y modelo base | Autor |
| PA-05 | Alta | ¿Quién da de alta un consultorio nuevo: registro autoservicio, un administrador de la plataforma o solo el seed data en la v0.1 local? | E1 (US-004); actores | Autor |
| PA-06 | Media | ¿Un odontólogo puede pertenecer a varios consultorios con una sola cuenta? (SU-02). Relacionado: si el email de inicio de sesión es único en todo el sistema, el alta podría revelar que una persona ya está registrada en otro consultorio. | Modelo de Usuario | Autor |
| PA-07 | Alta | Estados definitivos del turno y sus transiciones; si el odontólogo puede marcar atendido o ausente; **qué estados ocupan agenda** (RN-AG-02b); estado tras reprogramar; si se puede reactivar un turno cancelado (con revalidación) y reutilizar el horario de un `ausente`. Propuesta inicial en RN-TU-04 y RN-TU-05. **Impacto en PostgreSQL**: el conjunto de estados define la condición de la restricción de exclusión; cambiarlo luego requiere una migración. | Change de turnos (E3) | Autor |
| PA-08 | Media | Granularidad de los horarios ofrecidos (por ejemplo, cada 5, 10 o 15 minutos) y tiempos de preparación entre turnos. | Disponibilidad (US-010) | Autor |
| PA-09 | Media | ¿Puede la secretaría cambiar la duración de un turno? ¿Hay duraciones distintas por profesional? ¿Todos los profesionales realizan todas las prestaciones? | Modelo de Prestacion y Turno | Autor (y Consultorios) |
| PA-10 | Media | Bloqueos: ¿se admiten bloqueos de todo el consultorio? ¿Qué pasa con los turnos existentes al crear un bloqueo que los cubre (rechazar, avisar o cancelar)? ¿Hacen falta excepciones de horario por fecha? | US-008, F7 | Autor |
| PA-11 | Media | ¿Cómo se recupera una contraseña sin integración de email en la v0.1 (IN-06)? | Change de acceso | Autor |
| PA-12 | Media | La anticipación mínima de R5, ¿aplica solo al paciente o también a la secretaría? ¿Se rechaza o solo se avisa? | US-009, US-013, F6 | Autor |
| PA-13 | Baja | ¿Se cargan los feriados nacionales manualmente cada año (SU-08) o se ofrece una lista precargada? | US-008 | Autor |
| PA-14 | Media | Datos mínimos de la ficha del paciente: ¿DNI, fecha de nacimiento, ambos o ninguno? (Ley 25.326, art. 4) | Modelo de Paciente | Autor (Asesoría si hay dudas) |
| PA-15 | Media | ¿Se permite un texto libre de observaciones en el turno? Riesgo de que se carguen datos clínicos (D3, D9). | Modelo de Turno | Autor |
| PA-16 | Baja | Política de conservación, supresión y acceso del titular a sus datos (Ley 25.326, art. 14); relación con la exportación candidata (US-025). | Despliegue real; E8 | Autor y Asesoría |
| PA-17 | Baja | ¿Puede haber profesionales sin cuenta de usuario? (SU-03) | Modelo de Profesional | Autor |
| PA-18 | Media | Si se modifica o elimina una franja de atención y quedan turnos existentes fuera del nuevo horario: ¿se rechaza el cambio, se avisa o se listan para reprogramar? | US-007; RN-AG-06 | Autor |
| PA-19 | Media | Registro de modificaciones del turno: ¿alcanza con el último cambio (quién y cuándo, RN-TU-09) o hace falta un historial completo? La auditoría avanzada es candidata (E8) y no entra al núcleo sin aprobación. | US-012; modelo de Turno | Autor |
| PA-20 | Media | Concurrencia entre la creación de un turno y la creación de un bloqueo o un cambio de horario: la restricción de PostgreSQL solo cubre turno contra turno. ¿Qué mecanismo evita que ambos queden registrados en conflicto? | RN-AG-03; Changes de agenda y turnos | Autor |

Los seis campos de `kb.discovery` del estado fueron confirmados por el autor (DD-14); no hay campos con confianza baja.

## Funciones "No evidenciado" que afectan decisiones de producto

"No evidenciado" significa que **no hay respaldo público en las páginas leídas**, no que el producto no tenga la función (convención del informe). Estos vacíos limitan lo que se puede tomar del mercado como referencia.

| Código | Ítem (rúbrica) | Situación en la muestra | Decisión o regla afectada | Qué falta saber |
|---|---|---|---|---|
| NE-01 | Duración por prestación o bloqueos (C1.2) | Evidenciado solo en 2 de 18 (Órbita, Odonto.ar); No evidenciado en los otros 16, incluidos Bilog, DentalTec y Odeen | R1, R4 (núcleo) | Cómo lo resuelven los demás; se recomienda verificar en demo (informe §6.1) |
| NE-02 | Prevención de superposición entre profesionales | Solo Órbita la formula, y por sillón; cómo la aplica entre profesionales no está evidenciado | R2, PA-01 | Verificar en la demo de Órbita (informe §6.1) |
| NE-03 | Confirmación por respuesta del paciente (C1.4) | 6 de 18; degradada a No evidenciado en Odeen, MR Dental Cloud y DentalSoft+ por citas que no describen la respuesta del paciente | D5, D6, D7; RN-TU-04 | Eficacia y diseño del flujo de confirmación |
| NE-04 | Lista de espera o recall (C1.5) | 5 de 18; No evidenciado en Bilog, DentalTec, Odonto.ar y Odeen | Segunda etapa | — |
| NE-05 | Cancelación o reprogramación por el paciente (C5.2) | 3 de 7 en nivel 1; degradada en Odonto.ar | D4, R5 | Cómo aplican la anticipación mínima |
| NE-06 | Mercado Pago (C3.2) | 1 de 18 (Turnito); No evidenciado en los 4 odontológicos argentinos | Segunda etapa (seña) | — |
| NE-07 | Facturación ARCA (C3.3) | 1 de 18 (DentalTec); degradada en Bilog | D8 | Qué cubre la integración de DentalTec (informe §6.1) |
| NE-08 | Cumplimiento de la Ley 25.326 declarado (C6.5) | 1 de 18 (Odonto.ar) | D9, RN-PA | Práctica habitual del mercado en privacidad |
| NE-09 | Registro de auditoría (C6.2) y exportación (C6.3) | 2 de 7 en nivel 1 (DentalTec, Órbita); auditoría degradada en Bilog; ambas No evidenciado en Odonto.ar | Candidatas E8 | Prioridad en el roadmap |
| NE-10 | Medidas de seguridad declaradas (C6.4) | 3 de 7 en nivel 1 | RN-AU, RN-MT | — |
| NE-11 | Reserva online del paciente (C5.1) en DentalTec | No evidenciado | D4 | Verificar en demo |
| NE-12 | Recordatorio de WhatsApp de Odonto.ar: ¿automático o envío manual "en un clic"? | No determinado | D6 (referencia cercana al wa.me manual) | Verificar en demo (informe §6.1) |

# Auditoría consolidada de Discovery

- **Fecha de consulta**: 2026-10-10
- **Método**: WebFetch de cada URL citada y de páginas oficiales de planes/funciones; los resúmenes de WebFetch son generados automáticamente (no es lectura de HTML crudo). Detalle por afirmación en la sección "Estado de verificación" de cada nota.
- **Notas relacionadas**: `_normativa.md`, `_recordatorios.md`, `_obras-sociales.md`, `_hipotesis-mercado.md`.

## Índice por competidor

| Competidor | Datos oficiales confirmados | Datos de terceros | Pendientes | Precio verificado (URL, fecha) | Limitaciones |
|---|---|---|---|---|---|
| Dentalink | Tres planes; ficha clínica, inventario, multisede, ortodoncia; recordatorios WhatsApp/email; sin precio publicado; países: CL, CO, MX, ES | "USD 29/mes" del blog de Turnito (competidor, promocional) | Presencia en Argentina; link de reserva online; odontograma/presupuestos por plan | No publicado ("solicita tu cotización"), https://www.softwaredentalink.com/planes, 2026-10-10 | `dentalink.com` no resuelve; el sitio es softwaredentalink.com |
| Doctoralia Pro AR | Starter/Plus/VIP; reserva online; recordatorios email/push/SMS/WhatsApp; HC desde Plus; versión gratuita | - | Alcance del plan por canal; odontología | ARS 25.000 / 35.000 / 55.000 por mes, facturación anual, https://pro.doctoralia.com/ar/precio, 2026-10-10 | Cuotas SMS descritas como campañas; "65%" es claim del vendor |
| AgendaPro | Landing dental; recordatorios WhatsApp/SMS/email; planes con precio; add-on WhatsApp | Ninguno | Qué incluye cada plan; si el precio es por profesional | ARS Individual 13.900 / Básico 33.900 / Premium 44.900 / Pro 314.900 por mes, https://agendapro.com/ar/planes, 2026-10-10 | Corrige "precio no publicado"; "98%" y "135.000" son claims del vendor |
| Turnito | Planes, comisiones, cupos de WhatsApp, canales, cobros, foco Argentina | - | HC/odontograma ausentes (no auditado) | ARS 0 / 9.900 / 20.300 / 34.800 por mes (+ IVA), https://turnito.app, 2026-10-10 | Blog propio promocional y contradictorio ("100% gratis") |
| XIAgenda | Ninguno (dominios no resuelven) | Descripción y USD 15/mes Esencial (comparasoftware) | Todo lo oficial; obra social | NO verificado oficialmente (USD 15, tercero: https://www.comparasoftware.com/xiagenda, 2026-10-10) | El artículo de Ámbito es sobre "Órbita", no XIAgenda |
| Dentidesk | Funciones, prueba 15 días, base en Chile, SII/DGII | - | Cabo Verde; Argentina; agendamiento online | No publicado, https://www.dentidesk.com, 2026-10-10 | Producto chileno |
| Doctocliq | Planes, precios USD, cupos de recordatorios WhatsApp, 20+ países, canales | - | Operación en Argentina; precio para Argentina | USD 0 / 19 / 29 / 49 por mes, https://www.doctocliq.com/planes, 2026-10-10 | Discrepancia 11 vs 20+ países (prevalece oficial) |

## Evidencia verificada
- Todos los competidores revisados con sitio accesible declaran recordatorios automáticos; los canales varían (WhatsApp es el común: Dentalink, Doctoralia, AgendaPro, Turnito, Doctocliq).
- WhatsApp suele estar limitado o cobrado aparte: AgendaPro add-on desde ARS 7.900/mes (50 mensajes); Turnito 30/100/250 mensajes por plan; Doctocliq 50/100/150 recordatorios por plan.
- Rango de precios públicos en Argentina para software de agenda: desde ARS 0 (Turnito, con comisión del 5% sobre señas) hasta ARS 55.000 (Doctoralia VIP) para planes de un solo profesional; Doctocliq cotiza en USD.
- Cochrane: recordatorios por mensajes de texto mejoran la asistencia (67,8% vs 78,6%, RR 1,14). Texto leído el 2026-10-10.
- El CAIS 2016 (RCT argentino): SMS y llamadas reducen el ausentismo; el email solo no mostró diferencia significativa.
- Ley 25.326: datos de salud son sensibles (art. 2); el art. 8 habilita a establecimientos y profesionales de la salud a tratar datos de salud con secreto profesional; la prestación de servicios de tratamiento por cuenta de terceros es el art. 25 (no 26). Ver `_normativa.md`.
- Costos de email: Resend gratis 3.000/mes (100/día); SES USD 0,10-0,16 por 1.000.

## Hipótesis pendientes de validar con consultorios reales
- H1: cómo coordinan hoy los turnos (WhatsApp, teléfono, papel, planillas). No hay encuesta independiente.
- Tasa real de ausentismo en odontología en Argentina (no hay dato local verificado; solo rangos genéricos y estudios de EE.UU./Finlandia).
- Si el email solo alcanza o los pacientes exigen WhatsApp.
- Qué porcentaje de pacientes no tiene email.
- Si los consultorios atienden por obra social/prepaga y si necesitan registrarlo en el turno.
- Disposición a pagar y rango de precio aceptable (los precios de competidores son una referencia, no una validación).
- Si el motivo/prestación del turno se percibe como dato sensible.
- Interés en autoagendamiento del paciente frente a agenda manejada por secretaría.

## Implicancias para decisiones de producto (como evidencia, no como decisión)
- Hay oferta consolidada con funciones clínicas profundas (Dentalink, Doctocliq, Dentidesk); un MVP solo de turnos competiría más cerca de Turnito (agenda genérica con plan gratuito) que de los sistemas clínicos.
- El costo del WhatsApp oficial parece ser relevante para los vendors (cupos de 30-250 mensajes); un MVP podría empezar con alternativas de bajo costo (email, lista manual, wa.me) y medir antes de integrar la API.
- El email solo tiene evidencia más débil que SMS/llamada; conviene un fallback para recepción.
- Evitar guardar datos clínicos en el turno reduce el alcance legal (Ley 26.529 aplica a HC), pero el campo "motivo" podría ser dato de salud (hipótesis).
- Aislamiento por consultorio y contrato de encargo de tratamiento aparecen como requisitos de diseño derivados del art. 9 y art. 25 y del Decreto 1558/2001 (a validar con asesoría legal).
- Ningún competidor expone obra social de forma verificable: es un posible diferencial o una falta de necesidad; falta validación.

## Preguntas abiertas
1. ¿Cuál es la tarifa de Meta por mensaje de utilidad en Argentina (archivo CSV de tarifas)?
2. ¿Qué exige Meta para la verificación de negocio y el opt-in?
3. ¿Es el SaaS "encargado del tratamiento" o "responsable"? ¿Quién inscribe la base ante la AAIP?
4. ¿Aplica el art. 21 ("destinado a proporcionar informes") a una agenda de pacientes, o el art. 24 de forma general?
5. ¿XIAgenda sigue operativo (dominios no resuelven)? ¿Cuál es su precio oficial?
6. ¿Dentalink opera comercialmente en Argentina?
7. ¿Qué incluye cada plan de AgendaPro y Doctoralia en canales de recordatorio?
8. ¿Hosting en el exterior implica transferencia internacional de datos?
9. ¿Cuántos consultorios usan hoy un sistema pago y cuánto están dispuestos a pagar?

## Limitaciones generales de esta auditoría
- Los resúmenes de WebFetch son generados por un modelo; las citas literales deberían contrastarse con el texto completo antes de decisiones legales.
- PubMed, la ayuda de Meta (verificación de negocio) y la ayuda de WhatsApp (wa.me) no devolvieron contenido útil.
- Brevo: solo fragmentos de búsqueda dentro de brevo.com.
- infoleg.gob.ar no se consultó; se usó argentina.gob.ar.

# Discovery — turnos_odontologia

**Fecha**: 2026-10-10
**Estado**: aprobado por el autor el 2026-10-10
**Fuentes investigadas**: 7 competidores + hipótesis de mercado, normativa, recordatorios y obras sociales (ver `discovery/sources/`; índice consolidado en `discovery/sources/_auditoria.md`)
**Informe ampliado (2026-10-12)**: estudio de mercado de 18 sistemas con matriz ponderada en `docs/discovery/informe-discovery.md` (versión PDF: `docs/discovery/informe-discovery.pdf`); checklist estructurado en `docs/discovery/checklist-discovery.md` y `.json`; trazabilidad de fuentes en `docs/discovery/fuentes.md`.

Convenciones: [OF] fuente oficial · [3°] fuente de terceros · [AUT] planteo o hipótesis del autor · [PEND] pendiente de verificación. Fecha de todas las consultas: 2026-10-10. Las páginas se leyeron mediante resúmenes automáticos; citas literales y precios deben contrastarse con la página original antes de usarlos en una entrega. Detalle por afirmación: sección "Estado de verificación (2026-10-10)" de cada nota en discovery/sources/.

## 1. Problema que resuelve

- Planteo del autor [AUT]: errores y superposición de turnos en consultorios odontológicos. Problema secundario: tiempo perdido coordinando citas.
- Evidencia externa: ninguna; el problema no está cuantificado para Argentina.
- Validación con consultorios: no se realizaron entrevistas. Pendiente (ver pregunta 2 del punto 11).

## 2. Usuarios y roles [AUT]

- Administrador del consultorio: configura el consultorio, los profesionales, las prestaciones y los horarios.
- Secretaría o recepción: crea, modifica, cancela y consulta turnos; administra datos básicos de pacientes.
- Odontólogo: consulta su agenda y la información necesaria para atender sus turnos.
- Paciente: reserva y consulta sus propios turnos. Su inclusión en el MVP depende del punto 5.

## 3. Casos de uso

- CU1. Como administrador, configuro el consultorio, los profesionales, las prestaciones con su duración y los horarios de atención, para que la agenda refleje la realidad del consultorio.
- CU2. Como secretaría, creo, modifico, cancelo y consulto turnos, y el sistema impide superposiciones, para evitar errores de agenda (núcleo del problema).
- CU3. Como odontólogo, consulto mi agenda diaria y semanal, para organizar la atención.
- CU4. Como secretaría, registro y edito los datos básicos de un paciente, para asociarlo a sus turnos.
- CU5. Como paciente, reservo un turno en un horario libre y consulto o cancelo mis reservas, para no depender de llamar (con riesgo de alcance, ver punto 5).

## 4. Competidores (muestra de 7 productos; no es un relevamiento exhaustivo)

### 4.1 Dentalink
- Público: odontología [OF].
- Datos oficiales [OF]: planes Esencial, Pro y Titanium; ficha clínica digital en todos los planes; inventario y multisede (Pro); ortodoncia y campañas de email (Titanium); países mencionados: Chile, Colombia, México y España. Fuente: https://www.softwaredentalink.com/planes
- Recordatorios [OF]: por WhatsApp y/o email; el paciente puede confirmar, reprogramar o cancelar. Fuentes: https://www.softwaredentalink.com/experiencia-de-pacientes/agenda y https://www.softwaredentalink.com/experiencia-de-pacientes/confirmaciones-automaticas-de-citas
- Precio [OF]: no publicado ("Solicita tu cotización"). Fuente: https://www.softwaredentalink.com/planes
- Datos de terceros [3°]: "desde USD 29/mes", tomado del blog de Turnito (competidor, contenido promocional). No se usa como precio. Fuente: https://turnito.app/blog/las-mejores-apps-de-turnos-para-odontologos-en-argentina-2026/
- Pendiente [PEND]: link de reserva online del paciente; presencia en Argentina; odontograma y presupuestos por plan.
- Limitación: el dominio dentalink.com no resolvió; el sitio verificado es softwaredentalink.com.

### 4.2 Doctoralia Pro AR
- Público: profesionales de la salud de múltiples especialidades, según la nota de la primera pasada; no re-verificado en la auditoría [PEND].
- Datos oficiales [OF]: planes Starter, Plus y VIP; reserva online en todos los planes; recordatorios email y push (Starter), SMS (Plus); historia clínica desde Plus; versión gratuita. Fuente: https://pro.doctoralia.com/ar/precio
- Recordatorios por WhatsApp [OF]. Fuente: https://pro.doctoralia.com/ar/agenda-doctoralia-para-especialistas
- Precio [OF]: Starter ARS 25.000, Plus ARS 35.000, VIP ARS 55.000 por mes, con facturación anual. Fuente: https://pro.doctoralia.com/ar/precio
- Afirmación del vendedor (no es evidencia): "reducción del ausentismo hasta en un 65%". Fuente: https://pro.doctoralia.com/ar/agenda-doctoralia-para-especialistas
- Pendiente [PEND]: qué canales de recordatorio incluye cada plan; pertenencia al grupo Docplanner.

### 4.3 AgendaPro
- Público: odontología y otros rubros [OF].
- Datos oficiales [OF]: página específica para odontología; agenda 24/7; recordatorios por WhatsApp, SMS o email; historia clínica odontológica, pagos y señas. Fuente: https://agendapro.com/ar/dental/software-odontologico
- Precio [OF]: Individual ARS 13.900, Básico ARS 33.900, Premium ARS 44.900, Pro ARS 314.900 por mes; WhatsApp como agregado desde ARS 7.900 por mes (50 mensajes). Fuente: https://agendapro.com/ar/planes
- Afirmación del vendedor (no es evidencia): "98% de quienes confirman asisten". Fuente: https://agendapro.com/ar/dental/software-odontologico
- Pendiente [PEND]: si el precio es por profesional; qué canal de recordatorio incluye cada plan.
- IVA [OF, verificado personalmente]: Santiago Chepilla comprobó el 2026-10-13 en https://agendapro.com/ar/planes la indicación «IVA incluido».
- Corrección registrada: la primera nota decía "precio no publicado"; era incorrecto.

### 4.4 Turnito
- Público: foco en Argentina, con versiones regionales [OF]. Multirrubro (no específico de odontología) según la descripción de la nota; no figura como afirmación separada en la tabla de verificación [PEND].
- Datos oficiales [OF]: landing de autoagendamiento; recordatorios por WhatsApp, email y Telegram; Google Calendar; cobros con Mercado Pago, PayPal y transferencia; WhatsApp con tope de 30, 100 o 250 mensajes por mes según plan. Fuente: https://turnito.app
  - Respaldo del autoagendamiento: la tabla de verificación de H3 en `discovery/sources/_hipotesis-mercado.md` (fila "H3: autoagendamiento como feature estándar") incluye a Turnito entre los 4 competidores con fuente oficial leída el 2026-10-10; la tabla de verificación de `discovery/sources/turnito.md` no lo lista como afirmación separada.
- Precio [OF]: Gratuito ARS 0 (100 reservas por mes, 5% de comisión), Plus ARS 9.900, Advance ARS 20.300, Pro ARS 34.800 por mes, más IVA. Fuente: https://turnito.app
- Limitación: su blog dice "100% gratis", lo que contradice sus planes pagos; se trata como contenido promocional. Fuente: https://turnito.app/blog/las-mejores-apps-de-turnos-para-odontologos-en-argentina-2026/
- Pendiente [PEND]: ausencia de odontograma o historia clínica (no se auditó la lista completa de funciones).

### 4.5 XIAgenda
- Datos oficiales: ninguno. Los dominios oficiales (https://xiagenda.com.ar) no resolvieron.
- Datos de terceros [3°]: descripción del producto (consultorios de Argentina, agente IA por WhatsApp y web, recordatorios, lista de espera, señas) y precio "Esencial USD 15 por mes por profesional". Fuente: https://www.comparasoftware.com/xiagenda
- Precio: no verificado oficialmente.
- Corrección registrada: el artículo de Ámbito citado en la primera pasada trata sobre otro producto ("Órbita") y se descartó como fuente.
- Pendiente [PEND]: si el producto sigue operativo; precio oficial; manejo de "planes de salud".

### 4.6 Dentidesk
- Público: odontología; base en Santiago de Chile [OF].
- Datos oficiales [OF]: agenda avanzada, historial, fichas especializadas, inventario, reportes y multisede; facturación electrónica con SII (Chile) y DGII (República Dominicana); dictado por voz; prueba gratuita de 15 días. Fuente: https://www.dentidesk.com
- Corrección registrada (2026-10-12): el consentimiento informado automatizado figura en la home como "próxima funcionalidad", no disponible [OF]. Fuente: https://www.dentidesk.com
- Precio [OF]: no publicado. Fuente: https://www.dentidesk.com
- Pendiente [PEND]: agendamiento online del paciente; presencia en Argentina.

### 4.7 Doctocliq
- Público: odontología (odontograma confirmado) y presencia declarada en más de 20 países [OF]. El público "estético" proviene de la nota de la primera pasada y no se re-verificó [PEND].
- Datos oficiales [OF]: reserva online; recordatorios por WhatsApp, email y SMS; odontograma e historia clínica; links de pago. Fuente: https://www.doctocliq.com
- Precio [OF]: Free USD 0, Individual USD 19, Basic USD 29, Advanced USD 49 por mes; recordatorios WhatsApp incluidos 50, 100 o 150 por mes según plan. Fuente: https://www.doctocliq.com/planes
- Pendiente [PEND]: operación comercial en Argentina; precio específico para Argentina.
- Corrección registrada: la primera nota decía "11 países"; la fuente oficial dice "20+ países".

### 4.8 Lectura de la muestra (interpretación, no hecho)
- Los productos con precio público en ARS (Doctoralia, AgendaPro, Turnito) no parecen ser exclusivamente odontológicos: AgendaPro lo confirma en fuente oficial (odontología y otros rubros); para Doctoralia y Turnito surge de las notas sin re-verificación [PEND].
- Los productos odontológicos (Dentalink, Dentidesk, Doctocliq) no confirman operación en Argentina en las páginas leídas.

## 5. Alcance: visión, candidatos al MVP y segunda etapa

La priorización definitiva se revisará en la Knowledge Base y el roadmap.

- Visión del producto [AUT]: SaaS en el que múltiples consultorios gestionan su agenda, profesionales y pacientes, y los pacientes pueden reservar online.
- MVP núcleo (propuesta): multi-consultorio con datos aislados; roles por consultorio; profesionales con horarios; prestaciones con duración; bloqueos de agenda; validación que impide superposiciones; gestión de turnos con estados; ficha básica del paciente; aviso de privacidad o consentimiento.
- Candidato al MVP con riesgo: reserva online por el paciente.
  - A favor: 4 de 7 competidores la ofrecen según fuente oficial (Doctoralia, AgendaPro, Turnito, Doctocliq); XIAgenda solo según terceros; Dentalink y Dentidesk pendientes.
  - Riesgo de alcance: suma autenticación del paciente o reserva como invitado, una vista pública por consultorio y concurrencia sobre horarios libres. Para una sola persona con plazo incierto, es la primera candidata a pasar a la segunda etapa.
- Segunda etapa: recordatorios automáticos por WhatsApp o SMS; lista de espera; seña con Mercado Pago; sincronización con Google Calendar.
- Fuera de alcance (decisión del autor): historia clínica y odontograma; verificación de cobertura, facturación e integraciones con obras sociales o prepagas.
- Obra social o prepaga como dato: en las páginas leídas ninguno de los 7 competidores muestra un campo verificable (detalle en discovery/sources/_obras-sociales.md). La ausencia no prueba que no exista ni que el mercado no lo necesite. Indicio sin fuente sobre "planes de salud" en XIAgenda [PEND]. La investigación no justifica ni descarta incluirlo; queda como pregunta abierta (punto 11, pregunta 4).

## 6. Funcionalidades opcionales

- Las de la segunda etapa del punto 5.
- Email como posible función de comunicación (confirmación o aviso de turno), sin afirmar que reduce el ausentismo. Su prioridad se define en el roadmap.

## 7. Reglas de negocio (propuestas del autor, pendientes de validar con consultorios)

- R1. La duración de un turno depende de la prestación odontológica.
- R2. Un profesional no puede tener dos turnos superpuestos.
- R3. Cada profesional tiene horarios de atención configurables.
- R4. Se pueden bloquear vacaciones, ausencias, feriados y otros períodos sin atención.
- R5. La anticipación mínima para cancelar o reprogramar es configurable; 24 horas como valor inicial, sin evidencia de que sea una regla universal del mercado.
- R6. Cada consultorio tiene sus propios registros de pacientes, aislados del resto (opción A, decisión del autor).
  - Implicancia: toda entidad del consultorio lleva su identificador y toda consulta filtra por él.
  - Implicancia: una misma persona puede tener registros independientes en distintos consultorios.
  - Implicancia: una consulta que no filtre por consultorio expone datos de otro (ver RG3).
  - Supuesto a validar: que los pacientes no esperan una cuenta única entre consultorios.

## 8. Integraciones y comunicación

- No hay integraciones externas obligatorias en el MVP núcleo.

Evidencia sobre recordatorios:
- SMS [OF]: revisión Cochrane CD007458 (8 ensayos, 6.615 participantes): asistencia 67,8% sin recordatorio frente a 78,6% con SMS; calidad de evidencia baja a moderada; estudios fuera de Argentina. Fuente: https://www.cochrane.org/evidence/CD007458_mobile-phone-messaging-reminders-attendance-healthcare-appointments
- Ensayo argentino CAIS 2016 (SADIO) [OF]: SMS y llamada mostraron efecto; el email solo no mostró diferencia significativa; muestra pequeña, 2016. Fuente: https://45jaiio.sadio.org.ar/sites/default/files/CAIS-19.pdf
- WhatsApp: sin resultados verificados. El IECS evalúa recordatorios en CABA sin resultados publicados. Fuente: https://iecs.org.ar/en/portfolio/evaluacion-del-impacto-de-una-estrategia-de-recordatorios-sobre-el-ausentismo-a-citas-de-atencion-ambulatoria-en-ciudad-de-buenos-aires/

Costos y dependencias:
- Email, Resend [OF]: 3.000 emails por mes gratis, máximo 100 por día. Fuente: https://resend.com/pricing
- Email, Amazon SES [OF]: USD 0,10 a 0,16 por cada 1.000 emails. Fuente: https://aws.amazon.com/ses/pricing/
- Email, Brevo [PEND]: dato parcial obtenido de un fragmento de búsqueda; página de precios no leída en detalle. Fuente: https://www.brevo.com/pricing
- Email, entregabilidad y configuración de dominio [PEND].
- WhatsApp Cloud API [OF]: cobro por mensaje entregado desde el 1/7/2025; aprobación de plantillas en hasta 24 horas. Fuentes: https://developers.facebook.com/docs/whatsapp/pricing y https://developers.facebook.com/docs/whatsapp/message-templates/guidelines
- WhatsApp [PEND]: tarifa para Argentina (archivos de tarifas no legibles en https://developers.facebook.com/docs/whatsapp/pricing/updates-to-pricing/), requisitos de verificación del negocio y condiciones de consentimiento.
- SMS [PEND]: tarifa en Argentina.

Pacientes sin email (propuestas, sin eficacia demostrada):
- Lista diaria para secretaría con enlace wa.me (abre WhatsApp con un mensaje prearmado, sin API). Propuesta por validar; formato oficial del enlace [PEND].
- Llamada telefónica.
- Campo de "contacto preferido" en la ficha del paciente.

## 9. Restricciones

Del proyecto [AUT]:
- Trabajo individual.
- La cátedra no impone stack; la elección se justificará en la Knowledge Base.
- Entrega del martes sin definir (avance o trabajo completo).
- Prioridades: investigación rigurosa, documentación sólida y MVP realista.

Normativas (solo lo respaldado por el texto oficial consultado; no es asesoramiento legal; no se consultó infoleg.gob.ar):
- Ley 25.326, fuente: https://www.argentina.gob.ar/normativa/nacional/ley-25326-64790/texto
  - Art. 2: los datos referentes a la salud son datos sensibles.
  - Art. 4: los datos deben ser adecuados, pertinentes y no excesivos respecto de su finalidad.
  - Art. 5: el tratamiento requiere consentimiento libre, expreso e informado, salvo las excepciones del inciso 2.
  - Art. 7: nadie puede ser obligado a proporcionar datos sensibles.
  - Art. 8: establecimientos y profesionales de la salud pueden tratar datos de salud de sus pacientes respetando el secreto profesional; el texto no menciona a proveedores de software.
  - Arts. 9 y 10: medidas de seguridad y confidencialidad; deber de secreto.
  - Art. 14: derecho de acceso, con respuesta dentro de los 10 días corridos.
  - Art. 25: quien presta servicios de tratamiento por cuenta de terceros no puede usar los datos con un fin distinto al del contrato.
  - Arts. 21 y 24: regulan la inscripción de bases de datos con redacciones distintas.
- Decreto 1558/2001, reglamentación del art. 25: el tratamiento por encargo debe regularse por contrato; numeral exacto [PEND]. Fuente: https://www.argentina.gob.ar/normativa/nacional/decreto-1558-2001-70368/texto
- AAIP: sus páginas hablan de bases "destinadas a dar informes". Fuentes: https://www.argentina.gob.ar/node/53779 y https://www.argentina.gob.ar/servicio/inscribir-un-responsable-de-bases-de-datos-personales-privadas
- Ley 26.529 (historia clínica): copia en 48 horas (art. 14) y conservación mínima de 10 años (art. 18). Fuente: https://www.argentina.gob.ar/normativa/nacional/ley-26529-160432/texto
- Excluir la historia clínica del MVP no elimina las obligaciones de protección de datos personales ni las relativas a datos de salud.

## 10. Riesgos

- RG1. Alcance frente a plazo: multi-consultorio más reserva online para una sola persona con fecha incierta (riesgo principal).
- RG2. El problema planteado no está validado en el mercado.
- RG3. Fuga de datos entre consultorios por consultas que no filtran por consultorio.
- RG4. La prestación o el motivo del turno podría constituir un dato de salud (cuestión legal abierta, ver pregunta 6).
- RG5. Distribución de responsabilidades legales entre consultorio y proveedor SaaS sin definir (ver preguntas 7, 8 y 10).
- RG6. Las comunicaciones por email pueden no tener impacto en la asistencia.
- RG7. Los datos de competidores provienen de resúmenes automáticos y pueden cambiar.

## 11. Preguntas abiertas

Proyecto:
1. ¿Qué se presenta el martes: un avance o el trabajo completo?
2. ¿Es posible entrevistar consultorios reales? Si no, las hipótesis de mercado se documentan como no validadas.

Producto:
3. ¿El paciente reserva con cuenta propia o como invitado?
4. ¿La obra social o prepaga se incluye como dato opcional o queda fuera del MVP? ¿Se necesita algún tratamiento de la cobertura?
5. ¿La reserva online entra al MVP o pasa a la segunda etapa? Se decide con el roadmap.

Legal (para asesoría; sin conclusiones):
6. ¿La prestación o el motivo del turno es un dato sensible?
7. ¿El SaaS actúa como encargado del tratamiento, como responsable o como ambos?
8. ¿Quién debe inscribir la base ante la AAIP, y una agenda de pacientes encuadra en bases "destinadas a proporcionar informes"?
9. ¿La excepción del art. 5, inciso 2 d) de la Ley 25.326 alcanza a datos sensibles?
10. ¿Alojar los datos fuera de Argentina constituye transferencia internacional, y con qué requisitos?
11. ¿Los recordatorios requieren consentimiento específico u opción de baja?

Hipótesis de mercado (sin evidencia local):
12. H1: ¿cómo coordinan hoy los consultorios los turnos (WhatsApp, teléfono, papel, planillas)? Solo hay afirmaciones de vendedores y blogs [3°], por ejemplo https://developargentina.com/blog/software-para-clinicas-argentina-turnos-ausencias-2026
13. H2: ¿cuál es la tasa de ausentismo odontológico en Argentina? Sin dato local verificado. Referencias de otros contextos: odontopediatría académica en EE.UU., 14,3% (https://pmc.ncbi.nlm.nih.gov/articles/PMC12274092/); Finlandia, de 9,9% a 5,8% (https://pmc.ncbi.nlm.nih.gov/articles/PMC12535098/); CAIS 2016 presenta rangos generales no consistentes dentro del mismo trabajo.
14. ¿Los pacientes prefieren reservar solos o a través de la secretaría?
15. ¿Qué proporción de pacientes no tiene email o prefiere WhatsApp?
16. ¿Cuánto estaría dispuesto a pagar un consultorio?

Datos por verificar:
17. Tarifa de WhatsApp para Argentina, verificación de negocio y condiciones de consentimiento.
18. Tarifa de SMS en Argentina.
19. ¿XIAgenda sigue operativo? ¿Dentalink, Dentidesk y Doctocliq operan en Argentina?

## Decisiones provisionales de producto

- D1. Problema central: superposición y errores de agenda. Estado: planteo del autor; mercado sin validar.
- D2. SaaS multi-consultorio con registros de pacientes aislados (opción A). Estado: decidida por el autor.
- D3. Historia clínica y odontograma fuera de alcance. Estado: decidida por el autor.
- D4. Reserva online como candidata al MVP, con riesgo de alcance explícito. Estado: propuesta; se revisa en el roadmap.
- D5. Email como posible función de comunicación, sin promesa sobre el ausentismo. Estado: propuesta.
- D6. Lista diaria para secretaría con enlaces wa.me. Estado: propuesta por validar.
- D7. WhatsApp API y SMS en la segunda etapa. Estado: propuesta.
- D8. Facturación, cobertura e integraciones con obras sociales fuera del MVP; inclusión del dato de obra social abierta. Estado: parcialmente decidida.
- D9. Tratar la prestación del turno como dato sensible hasta tener opinión legal. Estado: propuesta de criterio prudente, no conclusión jurídica.

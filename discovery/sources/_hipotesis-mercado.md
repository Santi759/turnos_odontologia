# Hipótesis de mercado y notas regulatorias (2026-10-10)

Leyenda: VERIFICADO (fuente independiente/primaria), PARCIAL, NO ENCONTRADO.

## H1 - Clínicas dentales argentinas coordinan turnos por WhatsApp/teléfono/papel/planillas
- Veredicto: PARCIAL. No se encontró encuesta ni porcentaje independiente para Argentina.
- Evidencia débil: AgendaPro describe el problema ("planillas, cuadernos de turnos y doble registro") y un blog de DevelopArgentina afirma, sin citar fuentes, que muchas clínicas usan WhatsApp y planillas. Ambas son fuentes comerciales. Varias clínicas argentinas publican WhatsApp/teléfono como canal de turnos (observación cualitativa en resultados de búsqueda).
- Fuentes: https://agendapro.com/ar/dental/software-odontologico ; https://developargentina.com/blog/software-para-clinicas-argentina-turnos-ausencias-2026
- Sugerencia: validar con 5-10 entrevistas a odontólogos.

## H2 - Ausentismo y efecto de recordatorios
- Tasa de ausentismo: PARCIAL (rangos, no específicos de odontología argentina). Consultorios externos: 15-30% en muchas instituciones (paper CAIS/SADIO, https://45jaiio.sadio.org.ar/sites/default/files/CAIS-19.pdf; cifra tomada de snippet, PDF no leído completo). Odontología pediátrica académica: 14,3% (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12274092/); Finlandia, niños/adolescentes: 9,9% a 5,8% entre 2006 y 2020 (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12535098/). Cifras de snippets de búsqueda.
- Recordatorios reducen ausentismo: VERIFICADO (global, SMS). Revisión Cochrane (8 RCT, 6.615 participantes): asistencia 67,8% sin recordatorio vs 78,6% con SMS (evidencia de calidad baja a moderada). https://www.cochrane.org/CD007458 ; https://pubmed.ncbi.nlm.nih.gov/24310741/
- WhatsApp en Argentina: PARCIAL. IECS evalúa recordatorios por WhatsApp (~72h y ~24h) en el sistema público de CABA (2023-2024, inferencia causal, financiado por BID), pero la página no publica resultados. Un resultado de búsqueda menciona reducción absoluta cercana a 3% sobre ~272.000 turnos; no se pudo verificar en la fuente, no atribuir. https://iecs.org.ar/en/portfolio/evaluacion-del-impacto-de-una-estrategia-de-recordatorios-sobre-el-ausentismo-a-citas-de-atencion-ambulatoria-en-ciudad-de-buenos-aires/
- Afirmaciones tipo "40-60% menos no-shows con WhatsApp" o "98% de asistencia" aparecen en blogs/sitios de vendors sin fuente: NO usar como evidencia.
- Un resultado de búsqueda indica un estudio dental pediátrico donde SMS fue menos efectivo que recordatorio por voz (no verificado).

## H3 - Autoagendamiento online como feature estándar
- Veredicto: VERIFICADO entre los competidores revisados (7 de 7 lo declaran en sitio oficial o fuente de terceros): Dentalink (link de reserva por redes/web), Doctoralia (todos los planes), AgendaPro (agenda online 24/7), Turnito (landing de reserva), XIAgenda (agente IA por WhatsApp/web), Doctocliq (citas online) y Dentidesk (integración de agendamiento online). Es una muestra de vendors, no una medición de expectativa de pacientes.

## Marco regulatorio (impacto en un sistema de turnos; no es asesoramiento legal)
- Ley 25.326 (Protección de Datos Personales; https://www.argentina.gob.ar/normativa/nacional/ley-25326-64790/texto): datos de salud son "sensibles" (art. 2 y 7); consentimiento libre, expreso e informado (art. 5); calidad y proporcionalidad de datos (art. 4); medidas de seguridad (art. 9); confidencialidad (art. 10); derecho de acceso (art. 14); prestadores de servicios de tratamiento no pueden usar los datos para otros fines (art. 25/26, numeración a confirmar en el texto); registro de bases ante la AAIP. Impacto: consentimiento en el alta del paciente, minimizar datos clínicos en el turno, aislamiento estricto por clínica (multi-tenant), registro de bases a cargo de cada clínica.
- Ley 26.529 (Derechos del Paciente; https://www.argentina.gob.ar/normativa/nacional/ley-26529-160432/texto): confidencialidad (art. 2), historia clínica (art. 12-18), formato digital permitido si hay integridad y accesos restringidos (art. 13), paciente titular con copia en 48 h (art. 14), conservación mínima 10 años (art. 18). Impacto: si el MVP solo agenda turnos y no incluye historia clínica, la carga de cumplimiento es menor; si se agrega HC, aplican estos requisitos. Interpretación a validar con asesoría legal.


## Estado de verificación (2026-10-10)

Leyenda: TEXTO = se abrió el texto/resumen de la fuente hoy; ABSTRACT = solo resumen; SNIPPET = solo fragmento de búsqueda; PENDIENTE = no verificable hoy.

| Afirmación | Clasificación | URL | Limitación / corrección |
|---|---|---|---|
| Cochrane CD007458: 8 RCT, 6.615 participantes; asistencia 67,8% sin recordatorio vs 78,6% con mensajes de texto (80,3% con llamada); RR 1,14 (IC95% 1,03-1,26); evidencia de calidad "baja a moderada" | TEXTO (página de síntesis de cochrane.org) | https://www.cochrane.org/evidence/CD007458_mobile-phone-messaging-reminders-attendance-healthcare-appointments | Cifras confirmadas. Es SMS/MMS, no WhatsApp, y publicado 2013 (estudios hasta agosto 2012). Páginas de PubMed no cargaron (bloqueo por cookies): https://pubmed.ncbi.nlm.nih.gov/24310741/ PENDIENTE |
| Odontología pediátrica académica: 14,3% de no-shows | TEXTO | https://pmc.ncbi.nlm.nih.gov/articles/PMC12274092/ | Precisión: es un servicio académico en Buffalo (EE.UU.), 7.379 visitas de 0-19 años, 2018-2023, población con alta privación social; adolescentes 12-17 años 24%. No extrapolable a Argentina. La URL antigua `www.ncbi.nlm.nih.gov/pmc/...` redirige (301) |
| Finlandia, niños/adolescentes: 9,9% a 5,8% (2006-2020) | TEXTO | https://pmc.ncbi.nlm.nih.gov/articles/PMC12535098/ | Servicio público de salud oral de Helsinki; global 7,4% (186.498 de 2.513.376); 5% de los jóvenes concentra 21,8% de las faltas. Contexto distinto a Argentina |
| "Ausentismo en consultorios externos 15-30%" (paper SADIO/CAIS) | TEXTO (PDF leído localmente con pdftotext) | https://45jaiio.sadio.org.ar/sites/default/files/CAIS-19.pdf | Corrección: es el CAIS 2016 (7º Congreso Argentino de Informática y Salud; Mandirola Brieux et al.), no un estudio reciente. El resumen dice "15 y 30 %" pero la introducción dice "20 y 30 %" y otro pasaje "25 %": inconsistencia interna. Es una afirmación introductoria "en muchas instituciones", no una medición dental |
| Mismo paper: RCT con email, llamada, SMS y SMS+email vs control; SMS y llamadas reducen el ausentismo (p<0,001) y el email solo no dio diferencia significativa | TEXTO | idem | Hallazgo nuevo y relevante para el diseño: en ese ensayo el recordatorio por email solo no fue significativo. Muestra pequeña (grupos de ~200); no se verificó el detalle de resultados por brazo |
| IECS evalúa recordatorios por WhatsApp (~72 h y ~24 h) en CABA | TEXTO | https://iecs.org.ar/en/portfolio/evaluacion-del-impacto-de-una-estrategia-de-recordatorios-sobre-el-ausentismo-a-citas-de-atencion-ambulatoria-en-ciudad-de-buenos-aires/ | Diseño "target trial" con datos observacionales, BID; intervención abr-2023 a mar-2024, evaluación jul-2024 a abr-2025. La página no publica resultados numéricos |
| "Reducción absoluta ~3% sobre ~272.000 turnos" (IECS) | PENDIENTE (SNIPPET sin verificar) | - | No hallado en la fuente; no usar |
| SMS menos efectivo que recordatorio por voz en odontología pediátrica | PENDIENTE | - | No verificado |
| H1: sin encuesta independiente sobre cómo coordinan turnos las clínicas argentinas | TEXTO | https://developargentina.com/blog/software-para-clinicas-argentina-turnos-ausencias-2026 | El blog es contenido comercial (leads de desarrollo a medida), sin estadísticas ni fuentes; no sirve como evidencia. Confirmado: H1 queda como hipótesis |
| "98% de asistencia" (AgendaPro) / "hasta 65%" menos ausentismo (Doctoralia) | TEXTO (como afirmaciones del vendor) | https://agendapro.com/ar/dental/software-odontologico ; https://pro.doctoralia.com/ar/agenda-doctoralia-para-especialistas | Marketing sin fuente; no usar como evidencia |
| H3: autoagendamiento como feature estándar (7/7) | CORREGIDO | ver notas por competidor | Con fuente oficial leída hoy: Doctoralia, AgendaPro, Turnito, Doctocliq (4/7). XIAgenda solo terceros (comparasoftware). Dentalink (link de reserva) y Dentidesk quedan PENDIENTE: el texto de la página de agenda de Dentalink leída hoy no lo mencionó. La afirmación "7 de 7" no se sostiene tal cual |
| Marco regulatorio de esta nota | CORREGIDO | ver `_normativa.md` | Art. 25/26 de 25.326 corregido a art. 25; registro AAIP matizado |

# Recordatorios de turnos: email vs WhatsApp vs SMS

- **Fecha de consulta**: 2026-10-10
- **Regla**: solo se citan precios efectivamente leídos hoy, con URL. El resto es PENDIENTE DE VERIFICACIÓN.
- No es asesoramiento legal.

## 1. Utilidad (qué dice la evidencia)
- SMS: Cochrane CD007458 (8 RCT, 6.615 participantes) halló asistencia de 67,8% sin recordatorio vs 78,6% con mensaje de texto; evidencia de calidad baja a moderada. https://www.cochrane.org/evidence/CD007458_mobile-phone-messaging-reminders-attendance-healthcare-appointments (leído 2026-10-10).
- Email: en el RCT argentino del CAIS 2016 (Mandirola Brieux et al.), el recordatorio solo por email no mostró diferencia significativa frente al control, mientras que SMS y llamada sí. https://45jaiio.sadio.org.ar/sites/default/files/CAIS-19.pdf (leído localmente; muestra pequeña, 2016).
- WhatsApp: no hay evidencia verificada con resultados numéricos. El IECS evalúa el tema en CABA pero la página no publica resultados. Las cifras de vendors (65% Doctoralia, 98% AgendaPro) no son evidencia.
- Conclusión provisoria: el email solo parece el canal más débil para asistencia; WhatsApp es el canal esperado por competidores y por costumbre local (hipótesis a validar con consultorios).

## 2. WhatsApp Business Platform (Cloud API de Meta)

| Tema | Hallazgo | URL (leída 2026-10-10) | Limitación |
|---|---|---|---|
| Modelo de precios | Cobro por mensaje entregado (no enviado), desde el 1 de julio de 2025 (antes por conversación). Varía por categoría de plantilla y país del destinatario | https://developers.facebook.com/docs/whatsapp/pricing ; https://whatsappbusiness.com/es-la/products/platform-pricing/ | Resumen automático de las páginas |
| Categorías | Marketing, Utilidad, Autenticación, Servicio. Servicio gratis; utilidad gratis dentro de la ventana de atención al cliente de 24 h; marketing siempre se cobra | idem | Un recordatorio de turno normalmente se enviaría iniciado por el negocio (fuera de la ventana de 24 h), así que sería plantilla de utilidad cobrada. Es una inferencia, no confirmada con un caso específico |
| Ventana gratis por anuncio | 72 h gratis tras contacto por anuncio Click-to-WhatsApp | idem | - |
| Tarifa para Argentina | PENDIENTE DE VERIFICACIÓN | https://developers.facebook.com/docs/whatsapp/pricing/updates-to-pricing/ | La documentación indica tarifas vigentes desde el 1/7/2026 en archivos CSV/PDF por moneda (USD, ARS entre otras) y calculadora interactiva, pero no se pudo leer un valor numérico para Argentina ni "Resto de Latinoamérica" |
| Aprobación de plantillas | Revisión automática, "puede tardar hasta 24 horas"; categorías authentication/marketing/utility; plantillas rechazadas no se pueden enviar; calidad puede pausarlas | https://developers.facebook.com/docs/whatsapp/message-templates/guidelines | Detalle de motivos de rechazo no leído |
| Verificación de negocio | Los límites de plantillas varían entre 250 y 6.000 según el estado de verificación. Requisitos de verificación PENDIENTE (la página de ayuda de Meta no devolvió contenido) | https://developers.facebook.com/docs/whatsapp/message-templates/guidelines | Requisitos de documentación para Argentina no verificados |
| Proveedor / BSP | No verificado hoy qué obligaciones tiene un integrador (Tech Provider/BSP) ni costos de intermediarios. Los competidores cobran WhatsApp con cupo: AgendaPro add-on desde ARS 7.900/mes (50 mensajes); Turnito 30/100/250 mensajes por plan; Doctocliq 50/100/150 recordatorios | https://agendapro.com/ar/planes ; https://turnito.app ; https://www.doctocliq.com/planes | Los cupos sugieren que el costo por mensaje es relevante para el vendor |
| Opt-in | La sección de plantillas leída no detalla el opt-in; la política de mensajería de WhatsApp no se leyó | - | PENDIENTE |

Dependencias y riesgos (hipótesis): cuenta de Meta Business, número dedicado, aprobación de plantillas, límites de calidad, cambios de política y precios unilaterales de Meta, y posiblemente un BSP.

## 3. Email transaccional

| Proveedor | Plan gratuito / precio leído | URL | Limitación |
|---|---|---|---|
| Resend | Gratis: 3.000 emails/mes, límite diario de 100, 3 dominios. Pago desde USD 20/mes por 50.000 emails | https://resend.com/pricing | 100/día alcanza para un consultorio chico pero se agota con muchos consultorios en un único plan |
| Amazon SES | USD 0,16 por 1.000 emails (plan Essentials, hasta 10M/mes) o USD 0,10 por 1.000 a la carta; créditos de hasta USD 200 por 12 meses para cuentas nuevas; IP dedicada administrada USD 15/mes por cuenta | https://aws.amazon.com/ses/pricing/ | Sandbox no confirmado en la página leída |
| Brevo | Plan gratis de 300 emails/día y pagos desde USD 9 por 5.000 emails/mes según resultados de búsqueda dentro de brevo.com; la página de precios no se pudo leer con detalle | https://www.brevo.com/pricing (no confirmada) ; https://www.brevo.com/bulk-email-service/ | Dato de fragmento de búsqueda oficial: parcialmente verificado. La versión gratis incluiría el branding de Brevo (no confirmado) |

Entregabilidad y dominio (sin fuente leída hoy, conocimiento general a verificar): requiere dominio propio con registros SPF/DKIM/DMARC; los recordatorios pueden caer en spam o en promociones; el paciente puede no mirar el email. PENDIENTE de verificación con la documentación del proveedor elegido.

## 4. SMS (breve)
- Efectivo según Cochrane y el CAIS 2016. Precio por SMS en Argentina: PENDIENTE (no se consultó un proveedor). Doctoralia incluye cupos de SMS por plan (300/1.000/5.000 mensuales, https://pro.doctoralia.com/ar/precio); Dentalink solo lista WhatsApp y email.

## 5. Paciente sin email
Opciones para el MVP (todas son propuestas, no decisiones):
1. Lista de recordatorios del día para secretaría, con teléfono y turno, para llamar o escribir a mano. Costo cero y sin dependencia externa.
2. Llamada telefónica: el CAIS 2016 la encontró efectiva (p<0,001 vs control) y Cochrane la ubica similar a SMS (80,3% de asistencia).
3. Enlace de click-to-chat `https://wa.me/<número>?text=<mensaje>` que abre WhatsApp con un mensaje prearmado y lo envía una persona, sin API. La documentación oficial de formato no se pudo leer hoy (la página de ayuda de WhatsApp no devolvió contenido): PENDIENTE de verificación del formato exacto.
4. Campo de contacto preferido (email, teléfono, WhatsApp) en el alta del paciente para elegir el fallback.

## 6. Veredicto provisorio (para decidir, no decidido)
- Para un MVP académico con un solo desarrollador, el costo y las dependencias de la Cloud API de Meta (verificación, plantillas, tarifas aún sin conocer para Argentina) son altos. Email gratuito más lista manual para secretaría y enlace wa.me son los caminos de menor dependencia.
- Riesgo: la evidencia hallada sugiere que el email solo es más débil; hay que medirlo con consultorios reales antes de afirmar que sirve.
- Pendientes para cerrar: tarifa de Argentina (archivo CSV de Meta), requisitos de verificación de negocio, opt-in, precio SMS, formato wa.me, entregabilidad.

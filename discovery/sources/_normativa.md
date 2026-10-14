# Normativa aplicable a un SaaS de turnos odontológicos (Argentina)

- **Fecha de consulta**: 2026-10-10
- **Aviso**: este documento resume textos legales para orientar el producto. No es asesoramiento legal. Las implicancias son hipótesis a validar con un profesional del derecho.
- **Método**: se leyeron los textos publicados en argentina.gob.ar (resumen automático de WebFetch con citas literales). infoleg.gob.ar no se consultó. Las citas literales son fragmentos; la lectura completa del artículo queda como tarea pendiente cuando se contrate asesoría.

## Ley 25.326 (Protección de los Datos Personales)

Fuente: https://www.argentina.gob.ar/normativa/nacional/ley-25326-64790/texto

| Artículo | Resumen literal corto | Estado de la cita previa | Implicancia para un SaaS solo de turnos (hipótesis) |
|---|---|---|---|
| Art. 2 | "Datos sensibles: Datos personales que revelan [...] información referente a la salud o a la vida sexual." También define "Responsable de archivo [...]: titular de un archivo, registro, base o banco de datos" y "Usuario de datos: toda persona [...] que realice a su arbitrio el tratamiento de datos". | CONFIRMADO | Cualquier dato "referente a la salud" es sensible. Un turno que diga "ortodoncia" o "dolor" podría caer ahí (ver preguntas abiertas). |
| Art. 3 | "La formación de archivos de datos será lícita cuando se encuentren debidamente inscriptos, observando en su operación los principios que establece la presente ley." | Nuevo (no estaba en la nota previa) | Vincula licitud con inscripción; ver sección de registro. |
| Art. 4 | Datos "ciertos, adecuados, pertinentes y no excesivos en relación al ámbito y finalidad". | CONFIRMADO | Minimizar: pedir al paciente solo lo necesario para el turno. |
| Art. 5 | Tratamiento ilícito si el titular no prestó "consentimiento libre, expreso e informado". El inc. 2 enumera excepciones, entre ellas d) datos que "deriven de una relación contractual, científica o profesional del titular de los datos, y resulten necesarios para su desarrollo o cumplimiento". | CONFIRMADO (se agrega la excepción d) | La excepción d) podría alcanzar datos necesarios para la relación profesional, pero que aplique a un dato sensible es una cuestión abierta. Prever igual un texto de consentimiento/aviso. |
| Art. 7 | Inc. 1: "Ninguna persona puede ser obligada a proporcionar datos sensibles." Inc. 2: los sensibles "sólo pueden ser recolectados y objeto de tratamiento cuando medien razones de interés general autorizadas por ley" (o fines estadísticos/científicos sin identificar). | CONFIRMADO | Hacer opcional cualquier campo que revele salud. |
| Art. 8 | "Los establecimientos sanitarios públicos o privados y los profesionales vinculados a las ciencias de la salud pueden recolectar y tratar los datos personales relativos a la salud física o mental de los pacientes [...] respetando los principios del secreto profesional." | NUEVO, no estaba citado y es clave | Habilita a consultorios y profesionales; no dice nada explícito sobre un proveedor de software. |
| Art. 9 | El responsable o usuario del archivo "debe adoptar las medidas técnicas y organizativas [...] para garantizar la seguridad y confidencialidad de los datos personales". | CONFIRMADO | Cifrado, control de acceso, backups, aislamiento por consultorio. |
| Art. 10 | Responsable y quienes intervengan en el tratamiento "están obligados al secreto profesional"; subsiste tras terminar la relación (según resumen). | CONFIRMADO | Acuerdos de confidencialidad para personal y proveedor. |
| Art. 14 | Derecho de acceso previa acreditación de identidad; respuesta "dentro de los diez días corridos de haber sido intimado fehacientemente". | CONFIRMADO (plazo agregado) | Prever exportación/consulta de datos de un paciente. |
| Art. 21 inc. 1 | "Todo archivo, registro, base o banco de datos público, y privado destinado a proporcionar informes debe inscribirse en el Registro que al efecto habilite el organismo de control." | Nuevo | Ver registro. |
| Art. 24 | "Los particulares que formen archivos, registros o bancos de datos que no sean para un uso exclusivamente personal deberán registrarse conforme lo previsto en el artículo 21." | Nuevo | Ver registro. |
| **Art. 25** | Título: "Prestación de servicios informatizados de datos personales". "Cuando por cuenta de terceros se presten servicios de tratamiento de datos personales, éstos no podrán aplicarse o utilizarse con un fin distinto al que figure en el contrato [...]". | **CORREGIDO**: la nota previa decía "art. 25/26". El art. 25 es el correcto; el **art. 26** trata de "Prestación de servicios de información crediticia" y no aplica. | Si el SaaS trata datos por cuenta de los consultorios, el art. 25 limita usar esos datos para fines distintos a los del contrato (p. ej., marketing propio, entrenamiento de modelos, venta de datos). |

### Decreto 1558/2001 (reglamentario de la Ley 25.326)
Fuente: https://www.argentina.gob.ar/normativa/nacional/decreto-1558-2001-70368/texto
- Reglamentación del art. 24: el texto dice "Sin reglamentar".
- Reglamentación del art. 25 (literal parcial): "Los contratos de prestación de servicios de tratamiento de datos personales deberán contener los niveles de seguridad previstos en la Ley Nº 25.326" y obligaciones de confidencialidad; el tratamiento "por encargo deberá estar regulada por un contrato" en el que el encargado actúa solo según instrucciones del responsable y asume las obligaciones del art. 9.
- Implicancia (hipótesis): conviene un contrato/términos de encargo de tratamiento entre el SaaS y cada consultorio, con niveles de seguridad y uso limitado a instrucciones.
- Limitación: el resumen no mostró el numeral exacto del anexo para cada párrafo; verificar en el texto completo.

## Registro de bases de datos ante la AAIP (ex DNPDP)

- Ley (art. 21 inc. 1): la obligación se enuncia para bases "destinadas a proporcionar informes". Art. 24 extiende a "particulares que formen archivos [...] que no sean para un uso exclusivamente personal". Art. 3 ata la licitud a la inscripción.
- AAIP (TERCEROS respecto de la ley, oficial del organismo): https://www.argentina.gob.ar/node/53779 dice que las bases "públicos y privados destinados a dar informes deben estar inscriptos en el Registro Nacional de Bases de Datos Personales"; exceptúa los archivos de uso exclusivamente personal. https://www.argentina.gob.ar/servicio/inscribir-un-responsable-de-bases-de-datos-personales-privadas lo limita a "responsables de archivos y bases de datos privadas destinadas a dar informes", y exige credenciales AFIP nivel 2 o autorización en TAD.
- Observación: la redacción del art. 21 ("destinado a proporcionar informes") y la del art. 24 ("no para uso exclusivamente personal") no coinciden entre sí; la lectura práctica de a quién alcanza el registro **es una pregunta abierta** para asesoría legal. No se pudo verificar a qué sujeto exacto (consultorio, SaaS o ambos) corresponde la inscripción.
- Transferencias internacionales: la página de la AAIP indica que a países sin protección adecuada se requiere autorización de la AAIP salvo cláusulas contractuales conformes. Relevante si el hosting está fuera de Argentina (cuestión abierta).

## Ley 26.529 (Derechos del Paciente)

Fuente: https://www.argentina.gob.ar/normativa/nacional/ley-26529-160432/texto

| Artículo | Resumen literal corto | Estado de la cita previa | Implicancia (hipótesis) |
|---|---|---|---|
| Art. 2 inc. d) | El paciente tiene derecho a que toda persona que "participe en la elaboración o manipulación de la documentación clínica, o bien tenga acceso al contenido de la misma, guarde la debida reserva". (La nota previa citaba el "art. 2" como confidencialidad: confirmado, es el inc. d.) | CONFIRMADO | Aplica a documentación clínica; un turno no es necesariamente historia clínica. |
| Art. 12 | Historia clínica: "documento obligatorio cronológico, foliado y completo en el que conste toda actuación" | CONFIRMADO | Si el MVP no guarda actuaciones clínicas, no sería historia clínica. |
| Art. 13 | Permite soporte magnético "siempre que" se garanticen integridad, autenticidad y recuperabilidad con acceso restringido y control de modificaciones (según resumen). | CONFIRMADO | Solo relevante si se agrega HC. |
| Art. 14 | "El paciente es el titular de la historia clínica. A su simple requerimiento debe suministrársele copia" dentro de "cuarenta y ocho (48) horas de solicitada, salvo caso de emergencia". | CONFIRMADO | Solo si hay HC. |
| Art. 18 | Inviolabilidad; guarda y custodia mínima de "DIEZ (10) años" desde la última actuación (según resumen). El título literal es "Inviolabilidad. Depositarios". | CONFIRMADO | Solo si hay HC. |
| Art. 19 | Legitimados para solicitar la HC. | Nuevo | Solo si hay HC. |

## Preguntas legales abiertas (no resueltas)
1. ¿El SaaS es "prestador de servicios informatizados" (art. 25) / encargado del tratamiento, o también "responsable" de la base? Depende del contrato y de quién decide fines y medios.
2. ¿El campo "motivo / prestación" de un turno (p. ej. "extracción", "ortodoncia") es dato de salud (sensible, art. 2 y 7)? Hipótesis prudente: puede serlo; tratarlo como sensible hasta tener opinión legal.
3. ¿Aplica la excepción del art. 5 inc. 2 d) al dato sensible, o se necesita consentimiento expreso igualmente?
4. ¿Quién debe inscribir la base ante la AAIP (consultorio, SaaS o ambos) y si el uso de agenda de pacientes encuadra en "destinado a proporcionar informes"?
5. Hosting en el exterior: ¿se configuran transferencias internacionales y qué cláusulas se requieren?
6. Recordatorios por WhatsApp/email: consentimiento del paciente para comunicaciones y opt-out (la AAIP menciona derecho de retiro/bloqueo para publicidad; confirmar si aplica a recordatorios transaccionales).
7. Un modelo multi-tenant con aislamiento por consultorio: ¿qué nivel de medidas de seguridad espera el art. 9 y el Decreto 1558/2001 (anexo de medidas)?

## Resumen de correcciones sobre la nota previa
- Art. 25/26: se corrige a **solo art. 25** (el 26 es información crediticia).
- Se agrega el art. 8 (datos de salud en establecimientos y profesionales de la salud), omitido antes.
- Registro: la ley lo ata a bases "destinadas a proporcionar informes" (art. 21) y particulares no personales (art. 24); en la nota previa se afirmaba "registro de bases a cargo de cada clínica", afirmación NO verificada.
- Ley 26.529: art. 2, 13, 14 (48 h) y 18 (10 años) confirmados.

# Informe de Discovery: SaaS de turnos odontológicos para Argentina

- **Proyecto**: turnos_odontologia (Metodología I)
- **Fecha**: 2026-10-12
- **Autor**: Santiago Chepilla
- **Estado**: Versión final — Discovery aprobado por el autor
- **Documento base aprobado**: `discovery/discovery.md` (checklist de 11 puntos, decisiones D1 a D9 y 19 preguntas abiertas, aprobado el 2026-10-10)

Convenciones de evidencia usadas en todo el informe:

- **Comprobado-oficial** (✔): la función está descripta en una página oficial del fabricante, con URL y fecha.
- **Terceros** (3°): solo la menciona una fuente que no es el fabricante (comparador, prensa, reseña).
- **Afirmación comercial**: cifra o promesa de marketing del propio fabricante; nunca se usa como evidencia.
- **No evidenciado**: no hay respaldo público en las páginas leídas. No significa que el producto no tenga la función.
- **Interpretación**: lectura del investigador sobre la evidencia; se rotula como tal.

---

## 1. Resumen ejecutivo

**Problema.** El autor plantea que los consultorios odontológicos sufren errores y superposición de turnos, y pierden tiempo coordinando citas (D1). El problema no está cuantificado para Argentina ni validado con consultorios: no se hicieron entrevistas (preguntas 2 y 12 de `discovery/discovery.md`).

**Alcance del estudio.** Se relevaron 18 sistemas de gestión de turnos o de gestión odontológica: 7 con presencia comercial comprobada en Argentina (nivel 1), 8 de Latinoamérica en español sin presencia argentina comprobada (nivel 2) y 3 internacionales usados como referencia funcional (nivel 3). Cada sistema se evaluó con una rúbrica de 7 criterios ponderados y 35 ítems observables, definida antes de la investigación ampliada. Los cuatro sistemas odontológicos argentinos (Órbita, Bilog, DentalTec, Odonto.ar) se revisaron con la misma profundidad; el resto, con menor profundidad.

**Hallazgos principales.**

- Los recordatorios automáticos son la función más extendida: 15 de 18 sistemas los evidencian en fuente oficial (16 contando terceros) y los 7 de nivel 1 los ofrecen. WhatsApp es el canal más frecuente (13 de 18 en fuente oficial y los 7 de nivel 1), pero los fabricantes lo limitan con cupos o lo cobran aparte.
- La reserva online por el paciente aparece en 10 de 18 sistemas (oficial) y en 6 de los 7 de nivel 1.
- En la muestra investigada, la historia clínica (15 de 18) y el odontograma (12 de 18) son estándar en el software odontológico; el MVP los deja fuera por decisión del autor (D3), lo que lo acerca más a una agenda genérica que a un sistema clínico. Excluirlos reduce el alcance funcional, pero no elimina las obligaciones de protección de datos personales (Ley 25.326) sobre los datos de pacientes y turnos.
- Los vacíos más marcados de la muestra relevada (18 sistemas; 7 con presencia en Argentina) son las integraciones locales y la trazabilidad: Mercado Pago y ARCA se evidencian en un solo sistema cada uno; solo un sistema declara cumplimiento de la Ley 25.326 (Odonto.ar); auditoría y exportación de datos aparecen en 2 de 7 sistemas de nivel 1.
- Las obras sociales aparecen en los 4 sistemas odontológicos argentinos y en ningún otro, lo que tensiona la decisión parcial D8.
- La configuración de duración por prestación o de bloqueos de agenda, núcleo del problema planteado, solo está documentada públicamente en 2 de 18 sistemas (Órbita y Odonto.ar).
- Mejores puntajes: Órbita 74/100 (mejor de nivel 1 y de los 18), Dentally 72 (nivel 3) y Odeen 70 (mejor de nivel 2). Un puntaje bajo con cobertura baja indica falta de información pública, no necesariamente falta de función.

**Recomendaciones.**

1. Evaluar mediante demo a Órbita, Bilog, DentalTec, Odonto.ar y Odeen, verificando los ítems no evidenciados listados en la sección 6.1.
2. Tomar como referencias de experiencia de usuario a Dentally (confirmación por respuesta SMS y portal del paciente), Odeen (página pública de reserva y precios transparentes) y Órbita (confirmación y reprogramación dentro del chat de WhatsApp).
3. Mantener el MVP sugerido en el núcleo de agenda sin superposiciones, multi-consultorio aislado y privacidad desde el diseño, conforme a D1 a D9; resolver con el roadmap las tensiones detectadas (reserva online, WhatsApp, obras sociales, historia clínica). El MVP de la sección 6.3 es una sugerencia sujeta a la aprobación del autor.
4. Completar la verificación personal de las fuentes pendientes (sección 8.1: filas 4, 5, 8, 9 y 10; de la fila 2, las condiciones comerciales no comprobadas) antes de usar esas citas o precios en una entrega.

---

## 2. Metodología

### 2.1 Fuentes y clasificación

Para cada sistema se leyeron páginas oficiales (sitio, funcionalidades, precios, documentación o centro de ayuda, términos y privacidad, repositorio público), fichas en tiendas de apps y, cuando no había fuente oficial, comparadores o prensa. Para los temas transversales se consultaron textos legales oficiales (argentina.gob.ar), revisiones científicas y documentación de proveedores (Meta, Resend, Amazon SES). Cada dato se registró con URL exacta y fecha de consulta y se clasificó como comprobado-oficial, terceros, afirmación comercial o no evidenciado (`docs/discovery/metodologia/plantilla-ficha.md`). El índice completo de URL está en `docs/discovery/fuentes.md`.

### 2.2 Rúbrica

Los pesos son los de la consigna de la cátedra y se fijaron el 2026-10-12, antes de la investigación ampliada (`docs/discovery/metodologia/criterios-puntuacion.md`).

| Código | Criterio | Peso |
|---|---|---|
| C1 | Gestión de turnos y automatización | 25 % |
| C2 | Funcionalidad odontológica clínica | 20 % |
| C3 | Integraciones locales y WhatsApp | 15 % |
| C4 | Administración, cobros y facturación | 15 % |
| C5 | Experiencia del paciente | 10 % |
| C6 | Seguridad, exportación y trazabilidad | 10 % |
| C7 | Precio y facilidad de adopción | 5 % |
| | **Total** | **100 %** |

Cada criterio tiene 5 ítems observables:

- **C1**: agenda multiprofesional o por sillón; duración por prestación o bloqueos de agenda; recordatorios automáticos; confirmación por respuesta del paciente; lista de espera, reasignación de huecos o recall.
- **C2**: odontograma; historia o ficha clínica; plan de tratamiento o presupuestos; periodontograma o imágenes; consentimiento informado digital o recetas.
- **C3**: WhatsApp; Mercado Pago; facturación electrónica de Argentina (ARCA, ex AFIP); obras sociales o prepagas argentinas; otras integraciones (calendario externo, SMS, API pública).
- **C4**: registro de pagos, caja o cuenta corriente; cobro online o seña al reservar; facturación electrónica de cualquier país; reportes; multisede, inventario o liquidación de honorarios.
- **C5**: reserva online por el paciente; cancelación o reprogramación autogestionada; canal móvil (WhatsApp, SMS, push o app); página pública de reserva o marketplace; portal o app del paciente, o encuestas.
- **C6**: roles y permisos; registro de auditoría; exportación de datos; medidas de seguridad declaradas; cumplimiento normativo declarado (Ley 25.326, GDPR, HIPAA u otra).
- **C7**: precio publicado; plan gratuito o prueba; precio en ARS u oferta explícita para Argentina; onboarding, migración o soporte en español; adopción verificable de fuente independiente.

### 2.3 Reglas de evidencia

- Ningún ítem se asigna sin URL; un ítem sin URL solo puede ser no evidenciado.
- Las cifras del fabricante (clientes, porcentajes de reducción del ausentismo, calificaciones mostradas en su propio sitio) son afirmación comercial y valen 0.
- Reglas agregadas durante la revisión (2026-10-12, decisiones del autor), aplicadas a todos los sistemas:
  - La cita debe describir la función; una palabra suelta, un cupo de plan, un medio de pago listado o una frase vaga no alcanzan.
  - Lo anunciado como "próximamente" no está disponible y queda no evidenciado.
  - Solo dos lecturas contradictorias de la misma página justifican degradar un ítem; que una cita no aparezca en otra página del mismo fabricante no es contradicción.
  - Profundidad pareja para los cuatro sistemas odontológicos de nivel 1 que se recomiendan para demo.

### 2.4 Orden por relevancia para Argentina

1. **Nivel 1**: presencia comercial en Argentina comprobada (precio en ARS, sitio `/ar`, integración local o clientes argentinos verificables).
2. **Nivel 2**: Latinoamérica, en español, sin presencia argentina comprobada.
3. **Nivel 3**: internacional, como referencia de funciones o de experiencia de usuario.

Dentro de cada nivel se ordena por puntaje total descendente y, ante empate, por cobertura de evidencia.

### 2.5 Proceso

1. **Investigación inicial (2026-10-10)**: 7 competidores, hipótesis de mercado, normativa, recordatorios y obras sociales; checklist aprobado en `discovery/discovery.md`.
2. **Re-auditoría (2026-10-10)**: relectura de cada URL citada con tabla "Estado de verificación" por nota; índice en `discovery/sources/_auditoria.md`. Se corrigieron varias afirmaciones (sección 8.2).
3. **Ampliación a 18 sistemas (2026-10-12)**: fichas con 12 grupos de campos (`discovery/sources/<slug>.md`) y 35 ítems puntuables (`discovery/sources/fichas/<slug>.json`).
4. **Reconfirmación con citas literales (2026-10-12)**: nivel 1 (`discovery/sources/_reconfirmacion-nivel1.md`) y Latinoamérica (`discovery/sources/_reconfirmacion-latam.md`).
5. **Pasada de profundidad de nivel 1 (2026-10-12)**: Bilog, DentalTec y Odonto.ar con varias páginas oficiales y citas por ítem; Órbita ya había sido reconfirmada ítem por ítem.
6. **Degradaciones y restitución (2026-10-12)**: aplicación de las reglas de la sección 2.3; registro en `discovery/sources/_degradaciones-evidencia-debil.md`.
7. **Cálculo reproducible**: `node docs/discovery/metodologia/puntuar.js discovery/sources/fichas` genera la matriz congelada en `docs/discovery/metodologia/matriz-resultado.md`.

### 2.6 Limitaciones

- Las páginas se leyeron mediante resúmenes automáticos (WebFetch), no como HTML crudo; las citas literales deben contrastarse con la página original.
- Las lecturas automáticas fueron inconsistentes entre intentos: por ejemplo, una primera lectura de Dentidesk listó funciones que una segunda lectura con citas no encontró, y la exportación de Órbita apareció en una página y no en otra.
- La profundidad fue despareja: los cuatro sistemas odontológicos de nivel 1 tuvieron revisión completa con citas; el resto, una revisión de menor profundidad.
- La rúbrica mide presencia declarada de una función, no su calidad ni su facilidad de uso.
- Las funciones que un producto tiene pero no publica quedan como no evidenciadas; por eso se recomiendan demos antes de cualquier conclusión comparativa fuerte.
- Solo 5 de las 10 fuentes de la sección 8.1 fueron verificadas personalmente (el 2026-10-12, con una ampliación de la fila 2 el 2026-10-13); el resto de la evidencia proviene de lecturas automáticas (sección 8). De AgendaPro siguen sin verificar personalmente las condiciones comerciales distintas de los precios, el IVA y el estado de la facturación electrónica.
- No se entrevistó a consultorios ni a pacientes; ninguna hipótesis de mercado está validada.
- Algunas páginas devolvieron error (403 en comparadores como Capterra y GetApp, 404 en algunas páginas de precios, ENOTFOUND en los dominios de XIAgenda).

---

## 3. A. Tabla comparativa

Orden idéntico al de la matriz de puntuación (nivel de relevancia y, dentro de cada nivel, puntaje total).

### A1. Identificación

| # | Sistema | Empresa | País de origen | URL oficial | Nivel | Segmento / modalidad |
|---|---|---|---|---|---|---|
| 1 | Órbita (Hi Órbita) | Órbita Global (La Plata) | Argentina | https://hiorbita.com/ | 1 | Clínicas odontológicas y centros médicos; gestión con asistente de WhatsApp con IA |
| 2 | Bilog | Bilog (razón social No evidenciado) | Argentina | https://bilog.com.ar/ | 1 | Clínicas, consultorios, obras sociales y auditoría odontológica; web y apps |
| 3 | DentalTec | DentalTec (razón social No evidenciado) | Argentina | https://web.dentaltec.com.ar/ | 1 | Odontólogos, círculos, federaciones y obras sociales; 100 % web |
| 4 | Odonto.ar | Odonto.ar (razón social No evidenciado; sede en Córdoba) | Argentina | https://odonto.ar/ | 1 | Clínicas y profesionales odontológicos; app web sin instalación |
| 5 | AgendaPro | AgendaPro SpA | Chile (indicio por términos) | https://agendapro.com/ar/dental/software-odontologico | 1 | Horizontal (belleza, bienestar, salud) con línea dental; SaaS |
| 6 | Doctoralia Pro (Argentina) | Docplanner Health (desarrollador de la app) | No evidenciado | https://pro.doctoralia.com/ar/precio | 1 | Multiespecialidad; agenda con marketplace de pacientes |
| 7 | Turnito | No evidenciado | Argentina (3°, iProUP) | https://turnito.app | 1 | Turnos multirrubro; no es software clínico |
| 8 | Odeen | Odeen SpA | Chile | https://www.odeen.cl | 2 | Consultorios y clínicas dentales de Chile; nube |
| 9 | Dentalink | Engenis SpA | Chile | https://www.softwaredentalink.com | 2 | Consultorios y clínicas dentales; nube |
| 10 | MR Dental Cloud | MR Desarrollos Inteligentes | México | https://www.mrdentalcloud.com | 2 | Clínicas odontológicas; nube multidispositivo |
| 11 | Doctocliq | Zolupro S.A.C. (desarrollador de la app) | Perú (indicio) | https://www.doctocliq.com | 2 | Clínicas dentales y estéticas; web y app del profesional |
| 12 | Clinicorp | Clinicorp | Brasil | https://www.clinicorp.com | 2 | Clínicas odontológicas de Brasil; nube, en portugués |
| 13 | DentalSoft+ | SEVEN GLOBAL COMPANY SAS | No evidenciado | https://dentalsoftplus.com | 2 | Clínicas de salud bucal; nube |
| 14 | Dentidesk | No evidenciado (marca DENTIDESK) | Chile | https://www.dentidesk.com | 2 | Clínicas y consultorios dentales; versión académica |
| 15 | XIAgenda | No evidenciado | No evidenciado | https://xiagenda.com.ar (no resuelve) | 2 | 3°: consultorios de Argentina, multiespecialidad, agente de IA |
| 16 | Dentally | Dentally (razón social No evidenciado) | Reino Unido | https://www.dentally.com/en-gb | 3 | Software dental en la nube; foco NHS |
| 17 | NexHealth | NexHealth (razón social No evidenciado) | Estados Unidos | https://www.nexhealth.com | 3 | Capa de experiencia del paciente sobre el sistema de gestión |
| 18 | DentalPin | Dentaltix (respaldo declarado) | No evidenciado | https://dentalpin.com | 3 | Gestión dental de código disponible, autoalojada |

### A2. Capacidades clave

Columnas según los ítems de la rúbrica: reserva online (C5.1), WhatsApp (C3.1), Mercado Pago (C3.2), ARCA (C3.3), obras sociales (C3.4) y precio (C7.1). ✔ = comprobado-oficial; 3° = solo terceros.

| # | Sistema | Reserva online paciente | Recordatorios WhatsApp | Mercado Pago | ARCA | Obras sociales | Precio publicado |
|---|---|---|---|---|---|---|---|
| 1 | Órbita | ✔ (por chat de WhatsApp) | ✔ | No evidenciado | No evidenciado | ✔ | ✔ USD 25 (Consultorio) y USD 113 (Clínica) por mes; abonable en dólares, pesos o USDT |
| 2 | Bilog | ✔ | ✔ | No evidenciado | No evidenciado | ✔ | No publicado (Lite y Premium "se cotizan por usuario"; Freemium sin costo) |
| 3 | DentalTec | No evidenciado | ✔ | No evidenciado | ✔ | ✔ | No publicado ("costo por odontólogo") |
| 4 | Odonto.ar | ✔ | ✔ | No evidenciado | No evidenciado | ✔ | ✔ USD 29 / 49 / 99 por mes (~ARS 44.950 / 75.950 / 153.450) |
| 5 | AgendaPro | ✔ | ✔ | No evidenciado | No evidenciado (facturación "Próximamente", verificado personalmente el 2026-10-13) | No evidenciado | ✔ ARS 13.900 / 33.900 / 44.900 / 314.900 por mes, IVA incluido (montos verificados personalmente el 2026-10-12; IVA, el 2026-10-13) |
| 6 | Doctoralia Pro | ✔ | ✔ | No evidenciado | No evidenciado | No evidenciado | ✔ ARS 25.000 / 35.000 / 55.000 por mes, facturación anual |
| 7 | Turnito | ✔ | ✔ | ✔ | No evidenciado | No evidenciado | ✔ ARS 0 / 9.900 / 20.300 / 34.800 por mes, más IVA |
| 8 | Odeen | ✔ | ✔ | No evidenciado | No evidenciado | No evidenciado | ✔ CLP 19.990 / 29.990 / 49.990 por mes, IVA incluido |
| 9 | Dentalink | No evidenciado | ✔ | No evidenciado | No evidenciado | No evidenciado | No publicado (cotización) |
| 10 | MR Dental Cloud | No evidenciado | ✔ | No evidenciado | No evidenciado | No evidenciado | ✔ MXN 350 / 750 por mes |
| 11 | Doctocliq | ✔ | ✔ | No evidenciado | No evidenciado | No evidenciado | ✔ USD 0 / 19 / 29 / 49 por mes |
| 12 | Clinicorp | No evidenciado | ✔ | No evidenciado | No evidenciado | No evidenciado | ✔ R$ 149,90 / 369,90 por mes |
| 13 | DentalSoft+ | No evidenciado | ✔ | No evidenciado | No evidenciado | No evidenciado | ✔ USD 0 (Gratis), USD 349 (anual + 2 meses), USD 799 (vitalicio) |
| 14 | Dentidesk | No evidenciado | No evidenciado (anunciado como próximo) | No evidenciado | No evidenciado | No evidenciado | No publicado |
| 15 | XIAgenda | 3° | 3° | 3° | No evidenciado | No evidenciado | 3° USD 15 por mes por profesional (plan Esencial) |
| 16 | Dentally | ✔ | No evidenciado | No evidenciado | No evidenciado | No evidenciado | ✔ GBP 125 / 220 / 320 por mes (3 gabinetes, sin IVA) |
| 17 | NexHealth | ✔ | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No publicado (cotización por formulario) |
| 18 | DentalPin | No evidenciado | No evidenciado | No evidenciado | No evidenciado | No evidenciado | ✔ Núcleo gratuito, sin cargos por puesto |

Notas:

1. Precios en moneda local tal como figuran en la fuente, vistos el 2026-10-10 o el 2026-10-12; los precios en ARS cambian con la inflación y deben reverificarse antes de citarlos.
2. Los cupos de WhatsApp también son parte del precio: AgendaPro lo vende como agregado desde ARS 7.900 por mes (50 mensajes); Turnito incluye 30, 100 o 250 mensajes por plan; Doctocliq 50, 100 o 150 recordatorios; Odeen 80, 120 o 200; DentalTec vende paquetes en USD (50 mensajes por USD 9).

---

## 4. B. Matriz de puntuación 0–5

### 4.1 Pesos

| Criterio | Peso |
|---|---|
| C1. Gestión de turnos y automatización | 25 |
| C2. Funcionalidad odontológica clínica | 20 |
| C3. Integraciones locales y WhatsApp | 15 |
| C4. Administración, cobros y facturación | 15 |
| C5. Experiencia del paciente | 10 |
| C6. Seguridad, exportación y trazabilidad | 10 |
| C7. Precio y facilidad de adopción | 5 |
| **Total** | **100** |

### 4.2 Cómo se calcula

- Cada ítem vale **1** si está comprobado en fuente oficial, **0,5** si solo lo respalda un tercero, **0** si es afirmación comercial y **0** si no está evidenciado.
- El puntaje de un criterio (0 a 5) es la suma de sus 5 ítems.
- **Total (0–100)** = Σ (puntaje del criterio / 5 × peso del criterio). Ejemplo, Órbita: 5/5 × 25 + 4/5 × 20 + 3/5 × 15 + 3/5 × 15 + 3/5 × 10 + 3/5 × 10 + 3/5 × 5 = 25 + 16 + 9 + 9 + 6 + 6 + 3 = 74.
- **Cobertura de evidencia** = ítems con estado distinto de no evidenciado / 35. Las afirmaciones comerciales cuentan para la cobertura pero no para el puntaje.

### 4.3 Matriz

Valores copiados de `docs/discovery/metodologia/matriz-resultado.md` y verificados con `puntuar.js` sobre las 18 fichas. Por ancho de página la matriz se presenta en dos partes con la misma numeración.

**Parte 1: criterios C1 a C4**

| # | Sistema | Nivel | C1 (25) | C2 (20) | C3 (15) | C4 (15) |
|---|---|---|---|---|---|---|
| 1 | Órbita (Hi Órbita) | 1 | 5 | 4 | 3 | 3 |
| 2 | Bilog | 1 | 3 | 5 | 2 | 4 |
| 3 | DentalTec | 1 | 3 | 3 | 3 | 3 |
| 4 | Odonto.ar | 1 | 3 | 4 | 2 | 1 |
| 5 | AgendaPro | 1 | 2 | 2 | 2 | 4 |
| 6 | Doctoralia Pro (Argentina) | 1 | 3 | 1 | 1 | 1 |
| 7 | Turnito | 1 | 2 | 0 | 3 | 2 |
| 8 | Odeen | 2 | 2 | 5 | 2 | 5 |
| 9 | Dentalink | 2 | 3 | 5 | 1 | 5 |
| 10 | MR Dental Cloud | 2 | 2 | 4 | 2 | 5 |
| 11 | Doctocliq | 2 | 2 | 5 | 2 | 4 |
| 12 | Clinicorp | 2 | 2 | 4 | 2 | 3 |
| 13 | DentalSoft+ | 2 | 1 | 4 | 1 | 2 |
| 14 | Dentidesk | 2 | 0 | 2 | 1 | 4 |
| 15 | XIAgenda | 2 | 2 | 0 | 1 | 1 |
| 16 | Dentally | 3 | 4 | 5 | 1 | 4 |
| 17 | NexHealth | 3 | 2 | 0 | 1 | 2 |
| 18 | DentalPin | 3 | 0 | 3 | 0 | 2 |

**Parte 2: criterios C5 a C7, total y cobertura**

| # | Sistema | C5 (10) | C6 (10) | C7 (5) | Total (0-100) | Cobertura |
|---|---|---|---|---|---|---|
| 1 | Órbita (Hi Órbita) | 3 | 3 | 3 | 74 | 71 % |
| 2 | Bilog | 4 | 1 | 3 | 66 | 63 % |
| 3 | DentalTec | 1 | 4 | 2 | 57 | 57 % |
| 4 | Odonto.ar | 3 | 3 | 4 | 56 | 57 % |
| 5 | AgendaPro | 4 | 0 | 4 | 48 | 51 % |
| 6 | Doctoralia Pro (Argentina) | 4 | 2 | 4,5 | 41,5 | 49 % |
| 7 | Turnito | 3 | 0 | 3,5 | 34,5 | 40 % |
| 8 | Odeen | 3 | 5 | 3 | 70 | 71 % |
| 9 | Dentalink | 3 | 3 | 1 | 66 | 60 % |
| 10 | MR Dental Cloud | 2 | 4 | 3 | 62 | 66 % |
| 11 | Doctocliq | 2 | 2 | 3 | 59 | 57 % |
| 12 | Clinicorp | 2 | 1 | 2 | 49 | 49 % |
| 13 | DentalSoft+ | 2 | 3 | 2 | 42 | 43 % |
| 14 | Dentidesk | 0 | 0 | 2 | 25 | 26 % |
| 15 | XIAgenda | 1,5 | 0 | 2 | 21 | 43 % |
| 16 | Dentally | 4 | 4 | 1 | 72 | 66 % |
| 17 | NexHealth | 2 | 2 | 1 | 28 | 31 % |
| 18 | DentalPin | 0 | 2 | 2 | 24 | 26 % |

### 4.4 Cómo leer la matriz

- **Puntaje bajo no es ausencia.** Con cobertura baja (Dentidesk 26 %, DentalPin 26 %, NexHealth 31 %, Turnito 40 %), el puntaje refleja sobre todo falta de información pública. Con cobertura alta, un puntaje bajo en un criterio sí sugiere que la función no se ofrece o no se promociona.
- **XIAgenda** tiene cobertura del 43 % con puntaje 21 porque toda su evidencia es de terceros (0,5 por ítem): su sitio oficial no resolvió.
- **Los niveles no se mezclan.** Dentally (72, nivel 3) supera a Odeen (70, nivel 2) y a todos los de nivel 1 salvo Órbita, pero figura al final por ser de nivel 3. El orden responde a la relevancia para Argentina, no al puntaje absoluto.
- **Profundidad despareja.** Los cuatro sistemas odontológicos de nivel 1 se revisaron con varias páginas y citas por ítem; para el resto, una diferencia de pocos puntos puede deberse a cuántas páginas se leyeron.
- **Presencia, no calidad.** Dos sistemas con ✔ en un ítem pueden resolverlo de forma muy distinta (por ejemplo, recordatorio manual "en un clic" frente a recordatorio automático por la API oficial).

### 4.5 Cambios notables producidos por las reglas

- **Órbita**: la reconfirmación con citas ascendió 11 ítems (C1.2, C1.4, C2.5, C4.2, C4.4, C5.2, C6.1, C6.2, C6.3, C7.1, C7.3). Luego se degradaron C2.3 (la cita era solo la palabra "presupuestos"), C4.2 ("Link de pago" no indica seña al reservar) y C6.3; C6.3 se restituyó al adoptarse la regla de contradicción dentro de la misma página.
- **Bilog**: la pasada de profundidad ascendió C3.1, C3.3, C4.3, C5.2, C5.3, C5.4, C6.2 y C7.2, y pasó C7.5 de afirmación comercial a comprobado (reseñas en App Store). La segunda ronda de degradaciones bajó C3.3 (la cita de facturación electrónica no menciona ARCA) y C6.2 ("queda trazabilidad de los movimientos" no describe un registro de auditoría).
- **Odonto.ar**: la pasada de profundidad ascendió C1.2, C5.2 y C5.4; C5.2 se degradó porque la cita no indica que el paciente cancele o reprograme.
- **DentalTec**: la pasada de profundidad ascendió C4.3 (facturación integrada con ARCA).
- **Turnito**: C3.1 degradado (la cita elegida era un cupo de mensajes) y luego restituido con la evidencia descriptiva "Recordatorios por WhatsApp, email y Telegram" (https://turnito.app): 31,5 → 34,5.
- **Uniformidad en C1.4 (tercera ronda)**: Odeen, MR Dental Cloud y DentalSoft+ perdieron C1.4 porque "confirmaciones automáticas" no describe que el paciente confirme o rechace respondiendo, el mismo criterio aplicado antes a Clinicorp. Odeen 75 → 70, MR Dental Cloud 67 → 62 y DentalSoft+ 47 → 42; en nivel 2, Dentalink pasó al segundo lugar.
- **Doctoralia**: C3.5 degradado (la ficha de Google My Business no es calendario externo, SMS ni API).
- **Clinicorp**: C1.4, C4.2 y C4.3 degradados en la reconfirmación; C1.1 ascendido y luego degradado por evidencia débil; C2.5 y C5.5 ascendidos con cita literal.
- **MR Dental Cloud**: C6.3 ascendido y luego degradado ("exportable a PDF" se refiere a la historia clínica, no a exportación de datos).

---

## 5. C. Análisis competitivo

Los conteos se calcularon con un script sobre las 18 fichas JSON (`discovery/sources/fichas/`). "Oficial" cuenta solo ítems comprobado-oficial; entre paréntesis se suman los de terceros. El nivel 1 tiene 7 sistemas.

**Alcance de estas conclusiones.** Las proporciones (por ejemplo, "13 de 18") y la calificación de una funcionalidad como "estándar", "mayoritaria" o "vacío" se refieren a la muestra de 18 sistemas investigados o, cuando se indica, al subconjunto de 7 con presencia comercial en Argentina (nivel 1). No son una medición de todo el mercado, y una función no evidenciada puede existir sin estar publicada.

### 5.1 Funcionalidades estándar en la muestra

| Función (ítem) | Sistemas con evidencia oficial (de 18) | Nivel 1 (de 7) |
|---|---|---|
| Recordatorios automáticos (C1.3) | 15 (16 con terceros) | 7 |
| Historia o ficha clínica (C2.2) | 15 | 6 |
| Canal móvil hacia el paciente (C5.3) | 15 (16) | 7 |
| Reportes o estadísticas (C4.4) | 15 (16) | 6 |
| Onboarding, migración o soporte en español (C7.4) | 13 (14) | 6 |
| WhatsApp (C3.1) | 13 (14) | 7 |
| Odontograma (C2.1) | 12 | 4 |
| Agenda multiprofesional o por sillón (C1.1) | 11 (12) | 6 |
| Registro de pagos o caja (C4.1) | 12 | 4 |
| Roles y permisos (C6.1) | 12 | 4 |
| Precio publicado (C7.1) | 12 (13) | 5 |
| Plan gratuito o prueba (C7.2) | 12 (13) | 6 |
| Reserva online por el paciente (C5.1) | 10 (11) | 6 |
| Confirmación por respuesta del paciente (C1.4) | 6 (7) | 4 |

Lectura: en la muestra investigada, recordatorios, canal móvil (sobre todo WhatsApp) y reportes son la base común. En los sistemas específicamente odontológicos de la muestra, historia clínica y odontograma también son estándar: los 4 sistemas odontológicos argentinos los evidencian.

### 5.2 Diferenciadores reales

Funciones evidenciadas en fuente oficial que pocos sistemas tienen:

- **Agenda por sillón que impide superposiciones** — Órbita: "Agenda por sillón. Dos pacientes no pueden caer en el mismo sillón." (https://hiorbita.com/). Es la única formulación pública del problema central de este proyecto (D1).
- **Confirmación y reprogramación dentro del chat** — Órbita: "El paciente confirma o avisa desde el mismo chat, sin llamar" y "Reprograma turnos en el mismo chat" (https://hiorbita.com/erp/funcionalidades/llena-la-agenda). Bilog: "El mensaje incluye opciones para que confirmen o cancelen su turno. Si responden, la agenda se actualiza automáticamente." (https://bilog.com.ar/reminders-whatsapp/).
- **Confirmación por respuesta SMS** — Dentally: responder "YES" confirma y "NO" cancela (https://help.dentally.com/en/articles/3566498-how-to-set-up-automated-reminders-and-confirmations-in-patient-communications).
- **Integración con ARCA** — solo DentalTec: "Facturación automática y ágil integrada con ARCA" (https://web.dentaltec.com.ar/).
- **Mercado Pago** — solo Turnito en fuente oficial: "Cobros con MercadoPago, PayPal y transferencia bancaria" (https://turnito.app); XIAgenda solo según un comparador.
- **Obras sociales** — solo los 4 sistemas odontológicos argentinos: Órbita (https://hiorbita.com/erp/funcionalidades/el-dinero), Bilog (https://bilog.com.ar/), DentalTec, con "más de 15 obras sociales" (https://web.dentaltec.com.ar/software-odontologos-argentina), y Odonto.ar, con cálculo automático de cobertura (https://odonto.ar/).
- **Cumplimiento de la Ley 25.326 declarado** — solo Odonto.ar, con derechos de acceso, rectificación y supresión y remisión a la AAIP (https://odonto.ar/privacidad).
- **Auditoría de accesos y exportación sin barreras** — Odeen: "registra los accesos a información clínica sensible" (https://www.odeen.cl/ficha-clinica) y "Exporta la información cuando quieras, sin trámites ni peajes para salir." (https://www.odeen.cl/funcionalidades). DentalTec: "Auditoría completa: quién hizo qué, cuándo y dónde" (https://web.dentaltec.com.ar/funcionalidades).
- **Duración por prestación** — Odonto.ar: "Cada motivo ocupa los minutos que ocupa de verdad." (https://odonto.ar/); Órbita: "Respeta la duración de cada práctica" y bloqueo de vacaciones y feriados de una vez (https://hiorbita.com/erp/funcionalidades/llena-la-agenda).
- **Recall con reserva sin login** — Dentally: enlace personalizado en el recordatorio que lleva a reservar sin iniciar sesión (https://help.dentally.com/en/articles/6791631-how-to-use-online-booking-for-recall-appointments).
- **Cadencia de recordatorios escalonada** — MR Dental Cloud: WhatsApp a las 24, 12, 4 y 1 hora (https://www.mrdentalcloud.com).
- **Marketplace de pacientes** — Doctoralia: reserva desde el perfil Doctoralia, Google y redes en todos los planes (https://pro.doctoralia.com/ar/precio).

### 5.3 Vacíos frecuentes en los sistemas con presencia en Argentina (nivel 1, 7 sistemas de la muestra)

| Capacidad | Nivel 1 con evidencia oficial (de 7) | Cuáles | Total (de 18) |
|---|---|---|---|
| Mercado Pago (C3.2) | 1 | Turnito (no odontológico) | 1 (2 con terceros) |
| Facturación ARCA (C3.3) | 1 | DentalTec | 1 |
| Cumplimiento Ley 25.326 declarado (C6.5) | 1 | Odonto.ar | 1 (7 declaran alguna norma) |
| Registro de auditoría (C6.2) | 2 | DentalTec, Órbita | 6 |
| Exportación de datos (C6.3) | 2 | DentalTec, Órbita | 4 |
| Duración por prestación o bloqueos (C1.2) | 2 | Odonto.ar, Órbita | 2 |
| Lista de espera o recall (C1.5) | 2 | Doctoralia, Órbita | 5 (6) |
| Cobro online o seña al reservar (C4.2) | 2 | AgendaPro, Turnito (no odontológicos) | 7 (8) |
| Cancelación o reprogramación por el paciente (C5.2) | 3 | Bilog, Doctoralia, Órbita | 5 (6) |
| Medidas de seguridad declaradas (C6.4) | 3 | DentalTec, Doctoralia, Odonto.ar | 10 |
| Adopción verificable independiente (C7.5) | 1 oficial (+2 terceros) | Bilog (App Store); Doctoralia y Turnito (terceros) | 1 (3) |
| Portal o app del paciente, o encuestas (C5.5) | 1 | AgendaPro (encuestas) | 6 |

Lectura: ningún sistema odontológico argentino evidencia Mercado Pago; solo uno evidencia ARCA; la trazabilidad (auditoría y exportación) y el cumplimiento normativo declarado son minoritarios. Dos de los siete no publican precio (Bilog y DentalTec).

### 5.4 Oportunidades de innovación (interpretación)

Las siguientes son interpretaciones del investigador sobre la evidencia; no son decisiones de producto.

1. **El núcleo del problema está poco documentado por el mercado.** Solo 2 de 18 sistemas describen públicamente duración por prestación o bloqueos, y solo Órbita formula explícitamente la imposibilidad de superponer turnos. Un MVP centrado en reglas de agenda claras (R1 a R4 y D1 de `discovery/discovery.md`) atacaría un aspecto que el mercado da por supuesto pero no explica. Requiere validar con consultorios que la superposición es un problema real (RG2).
2. **Privacidad y trazabilidad visibles como atributo.** Con 1 de 18 sistemas declarando la Ley 25.326 y 2 de 7 en nivel 1 con auditoría y exportación, hacer visibles el aislamiento entre consultorios (D2), el trato prudente de la prestación como dato sensible (D9) y la posibilidad de exportar los datos de un paciente (relacionada con el derecho de acceso del art. 14 de la Ley 25.326) podría diferenciar. No es asesoramiento legal; el alcance exacto de las obligaciones queda en las preguntas 6 a 11.
3. **Confirmación de bajo costo sin depender de la API de WhatsApp.** Solo 6 de 18 sistemas describen que el paciente confirma respondiendo (4 de 7 en nivel 1), y los fabricantes limitan o cobran el WhatsApp. Un enlace de confirmación o cancelación en el email (D5) o en el mensaje prearmado wa.me (D6) podría aproximar esa experiencia antes de la segunda etapa (D7). La eficacia no está demostrada: en el ensayo CAIS 2016 el email solo no mostró diferencia significativa.
4. **Integraciones locales como espacio libre a mediano plazo.** Mercado Pago y ARCA aparecen en un solo sistema cada uno. Esto es coherente con dejarlas para etapas posteriores (D7, D8), pero sugiere que serían diferenciales reales si el producto continúa.
5. **Obra social como dato.** Los cuatro sistemas odontológicos argentinos gestionan obras sociales y ningún otro lo hace. Esto refuerza la pregunta abierta 4 (registrar la obra social como dato opcional) sin resolverla: la gestión completa (padrones, liquidación, cobertura) sigue fuera del MVP por D8.
6. **Precio transparente en ARS.** Cinco de siete sistemas de nivel 1 publican precio en ARS o permiten pagar en pesos; los dos odontológicos más antiguos no publican montos. La transparencia de precio parece valorada como señal comercial, aunque la disposición a pagar no está validada (pregunta 16).

---

## 6. D. Recomendación final

### 6.1 Cinco competidores para evaluar mediante demo

**1. Órbita (Hi Órbita)** — nivel 1, 74/100, cobertura 71 %.
- Por qué: mejor puntaje de nivel 1; único que formula la prevención de superposición por sillón; confirmación y reprogramación por WhatsApp con la API oficial de Meta; obras sociales; roles, auditoría y exportación.
- Qué verificar en la demo: Mercado Pago (C3.2), facturación ARCA o de cualquier tipo (C3.3, C4.3), presupuestos con detalle (C2.3, degradado), cobro online o seña al reservar (C4.2, degradado), página pública de reserva fuera de WhatsApp (C5.4), portal del paciente (C5.5), medidas de seguridad más allá del alojamiento en AWS (C6.4), cumplimiento de la Ley 25.326 (C6.5), prueba gratuita (C7.2); cómo se impide la superposición entre profesionales y no solo por sillón; cómo la confirmación en el chat actualiza la agenda.

**2. Bilog** — nivel 1, 66/100, cobertura 63 %.
- Por qué: segundo de nivel 1; clínica completa (C2 = 5); reserva online con QR o enlace; confirmación y cancelación por WhatsApp que actualizan la agenda; obras sociales y liquidaciones; única evidencia de adopción independiente en nivel 1 (App Store Argentina, 3,5/5 con 15 reseñas).
- Qué verificar: duración por prestación y bloqueos (C1.2; solo se vio la etiqueta "ausencias por profesional"), lista de espera (C1.5), Mercado Pago (C3.2), si la facturación electrónica emite ante ARCA (C3.3, degradado), API o SMS (C3.5; el sitio dice "Hoy Bilog no ofrece una API pública documentada"), cobro online (C4.2), registro de auditoría (C6.2, degradado), exportación (C6.3), seguridad y Ley 25.326 (C6.4, C6.5), precio (C7.1), soporte multisede (no reconfirmado).

**3. DentalTec** — nivel 1, 57/100, cobertura 57 %.
- Por qué: único sistema con ARCA evidenciado; más de 15 obras sociales con validación; 10 roles, auditoría y exportación de reportes; modelo institucional (círculos y federaciones).
- Qué verificar: reserva online del paciente (C5.1) y autogestión (C5.2), página pública o portal (C5.4, C5.5), duración por prestación y bloqueos (C1.2), lista de espera (C1.5), presupuestos (C2.3), consentimiento o recetas (C2.5), Mercado Pago (C3.2), caja o cuenta corriente del paciente (C4.1; solo se vio la del prestador), cobro online (C4.2), Ley 25.326 (C6.5), precio (C7.1); qué cubre exactamente la integración con ARCA (planillas a obras sociales o factura al paciente).

**4. Odonto.ar** — nivel 1, 56/100, cobertura 57 %.
- Por qué: producto liviano y de precio publicado; duración por motivo; enlace público de reserva; único que declara la Ley 25.326 y detalla cifrado y RLS; prueba de 30 días.
- Qué verificar: si el recordatorio de WhatsApp es automático o un envío manual "en un clic" (C1.3); confirmación por respuesta (C1.4); bloqueos y feriados (C1.2, parcial); lista de espera (C1.5); cancelación o reprogramación por el paciente (C5.2, degradado); consentimiento o recetas (C2.5); Mercado Pago, ARCA y facturación (C3.2, C3.3, C4.3); reportes (C4.4); multisede (C4.5); auditoría y exportación (C6.2, C6.3); política de copias de seguridad.

**5. Odeen** — nivel 2, 70/100, cobertura 71 %.
- Por qué: sigue siendo el mejor puntaje de nivel 2 (70, frente a 66 de Dentalink) tras la ronda de uniformidad en C1.4; página pública de reserva; auditoría de accesos a datos clínicos; exportación total; cifrado por campo; precio por clínica con IVA incluido.
- Qué verificar: si opera o planea operar en Argentina (C7.3, sin ARS); si el paciente confirma o rechaza respondiendo (C1.4, degradado: la página solo dice "Confirmaciones automáticas"); duración por prestación y bloqueos (C1.2); lista de espera (C1.5); cancelación o reprogramación por el paciente (C5.2); portal del paciente (C5.5); Mercado Pago, ARCA y obras sociales (C3.2 a C3.4).

### 6.2 Tres referencias de experiencia de usuario

1. **Dentally — confirmación por respuesta y portal del paciente.** Los recordatorios por SMS o email se envían a pacientes que dieron consentimiento; responder "YES" pasa el turno a "Confirmed" y "NO" a "Cancelled" (https://help.dentally.com/en/articles/3566498-how-to-set-up-automated-reminders-and-confirmations-in-patient-communications). Desde el Portal, el paciente reserva, cancela y vuelve a reservar (https://help.dentally.com/en/collections/2414893-online-booking), y el recall incluye un enlace para reservar sin login (https://help.dentally.com/en/articles/6791631-how-to-use-online-booking-for-recall-appointments). Referencia para un flujo de confirmación simple y para condicionar los recordatorios al consentimiento.
2. **Odeen — página pública de reserva y precios transparentes.** "El paciente elige un horario en tu página pública y la cita entra directamente en la agenda" (https://www.odeen.cl/funcionalidades). Precios publicados por tamaño de clínica, con IVA incluido y recepción y asistentes sin costo (https://www.odeen.cl/precios). Referencia para la vista pública por consultorio (CU5) y para comunicar el precio.
3. **Órbita — confirmar y reprogramar dentro del chat de WhatsApp.** "Primer aviso por WhatsApp 48 horas antes", "El paciente confirma o avisa desde el mismo chat, sin llamar" y "Reprograma turnos en el mismo chat" (https://hiorbita.com/erp/funcionalidades/llena-la-agenda). Referencia para la segunda etapa (D7) y para diseñar los estados del turno (confirmado, cancelado, reprogramado) desde el MVP.

### 6.3 MVP sugerido (sujeto a aprobación del autor)

Esta sección es una sugerencia derivada del análisis. No agrega decisiones: respeta D1 a D9 y el punto 5 de `discovery/discovery.md`. Donde el mercado apunta en otra dirección se señala como tensión a resolver en el roadmap.

**Esenciales (núcleo del MVP, ya propuesto en `discovery/discovery.md`)**

| Elemento | Justificación |
|---|---|
| Multi-consultorio con datos aislados | D2 (decidida). RG3: una consulta sin filtro por consultorio expone datos de otro. |
| Roles por consultorio (administrador, secretaría, odontólogo) | Punto 2 del checklist. Mercado: 12 de 18 sistemas evidencian roles y permisos. |
| Profesionales con horarios y prestaciones con duración | R1 y R3. Mercado: solo 2 de 18 documentan duración por prestación (Órbita, Odonto.ar). |
| Bloqueos de agenda (vacaciones, ausencias, feriados) | R4. Mercado: Órbita bloquea vacaciones y feriados "de una vez, no turno por turno". |
| Validación que impide superposiciones | D1 y R2. Mercado: Órbita lo promociona como función ("Dos pacientes no pueden caer en el mismo sillón"). |
| Gestión de turnos con estados | CU2. Mercado: en Dentally y Bilog el estado del turno cambia según la respuesta del paciente. |
| Ficha básica del paciente | CU4; sin datos clínicos por D3. |
| Aviso de privacidad o consentimiento | Ley 25.326, arts. 2, 5 y 7 (sección 9 de `discovery/discovery.md`). Mercado: solo Odonto.ar declara la Ley 25.326. No es asesoramiento legal. |

**Diferenciadores candidatos (a decidir por el autor)**

| Elemento | Justificación | Tensión o riesgo |
|---|---|---|
| Reserva online por el paciente | D4 (candidata con riesgo). Mercado: 10 de 18 y 6 de 7 en nivel 1. | En la muestra es mayoritaria (6 de 7 en nivel 1); el autor la identificó como primera candidata a pasar a la segunda etapa por alcance (RG1). Se decide en el roadmap (pregunta 5). |
| Email de confirmación o aviso de turno | D5 (propuesta). Mercado: 6 de 18 describen confirmación por respuesta del paciente. | Evidencia débil del email solo (CAIS 2016); no prometer reducción del ausentismo. |
| Lista diaria para secretaría con enlaces wa.me | D6 (propuesta por validar). | El formato oficial del enlace wa.me está pendiente de verificación. |
| Exportación avanzada de datos y registro de auditoría | Muestra: 2 de 7 sistemas de nivel 1 evidencian auditoría y exportación. Relación con arts. 9 y 14 de la Ley 25.326 (interpretación, no asesoramiento legal). | Funcionalidad candidata sujeta al roadmap: no es una obligación del MVP sin una decisión explícita del autor. Sugerencia nueva del análisis; no figura en D1 a D9. Suma alcance. |

**Etapas posteriores**

| Elemento | Justificación | Tensión |
|---|---|---|
| Recordatorios automáticos por WhatsApp API o SMS | D7. Costo y dependencias de la Cloud API de Meta (tarifa para Argentina pendiente). | 15 de 18 sistemas tienen recordatorios automáticos y 13 de 18 WhatsApp (los 7 de nivel 1): es la función más extendida en la muestra. Postergarla es razonable por costo y plazo, pero el MVP quedaría por debajo del estándar en este punto. |
| Lista de espera | Punto 5 de `discovery/discovery.md`. Mercado: 5 de 18. | Ninguna. |
| Seña con Mercado Pago | Punto 5. Mercado: Mercado Pago en 1 de 18. | Ninguna; sería diferencial a futuro. |
| Sincronización con Google Calendar | Punto 5. Mercado: Turnito y MR Dental Cloud. | Ninguna. |
| Historia clínica y odontograma | Fuera de alcance por D3. | Tensión: 15 de 18 con historia clínica, 12 de 18 con odontograma y los 4 odontológicos argentinos tienen ambos. Sin ellos, el producto compite más cerca de Turnito (agenda genérica) que de los sistemas clínicos. Excluirlos reduce el alcance funcional y evita las obligaciones propias de la historia clínica (Ley 26.529), pero no elimina las obligaciones de protección de datos personales (Ley 25.326) sobre los datos de pacientes y turnos. No es asesoramiento legal. |
| Obras sociales y facturación ARCA | Fuera del MVP por D8; el dato de obra social sigue abierto (pregunta 4). | Tensión: los 4 sistemas odontológicos argentinos gestionan obras sociales; ARCA solo en 1 de 18. |

---

## 7. Hipótesis y preguntas abiertas

Las 19 preguntas abiertas y las hipótesis H1 y H2 están en el punto 11 de `discovery/discovery.md` y siguen vigentes; no se repiten aquí. En resumen: no hay validación con consultorios (preguntas 2 y 12 a 16), las cuestiones legales requieren asesoría (6 a 11) y quedan datos por verificar (17 a 19).

El estudio de mercado del 2026-10-12 aporta o refuerza las siguientes:

1. **XIAgenda sigue sin sitio oficial accesible.** `https://xiagenda.com.ar` y `https://www.xiagenda.com` dieron ENOTFOUND el 2026-10-10 y el 2026-10-12; toda su ficha proviene de un comparador. La pregunta 19 sigue abierta.
2. **Otros sistemas no documentados.** Cualquier sistema mencionado fuera de los 18 (por ejemplo, Reservo) no tiene ficha ni fuente en `discovery/sources/`; su inclusión queda Pendiente.
3. **¿Se revisa D3 a la luz del mercado?** Historia clínica y odontograma son estándar en los sistemas odontológicos de la muestra. La decisión sigue siendo del autor; aquí solo se registra la tensión.
4. **¿El dato de obra social entra como campo opcional?** El mercado argentino odontológico lo gestiona en los 4 casos relevados (pregunta 4).
5. **¿Qué valor tiene la confirmación sin WhatsApp API?** Falta evidencia de eficacia del email con enlace o del wa.me manual (preguntas 11, 15 y 17).
6. **¿Operan Odeen, Dentalink, Doctocliq y Dentidesk en Argentina?** Ninguna página leída lo menciona (amplía la pregunta 19).
7. **¿Doctoralia atiende a odontología con funciones específicas?** El segmento odontológico quedó No evidenciado.

Las inconsistencias de la rúbrica detectadas durante la redacción (aplicación despareja de C1.4 y la cita mal elegida para Turnito C3.1) ya fueron resueltas por el autor; ver sección 8.2.

---

## 8. Verificación de fuentes

Todas las fuentes se consultaron primero mediante lectura automática. **Cinco de las diez fuentes de la tabla fueron verificadas personalmente por Santiago Chepilla** (filas 1, 2, 3, 6 y 7, todas confirmadas; el 2026-10-12, con una ampliación de la fila 2 el 2026-10-13). Las filas 4, 5, 8, 9 y 10 siguen pendientes de revisión humana. Todavía no se aportaron capturas de pantalla como evidencia de la verificación personal.

### 8.1 Fuentes a verificar

| # | Tipo de fuente | URL | Afirmación a verificar | Cómo verificar |
|---|---|---|---|---|
| 1 | Sitio oficial de funcionalidades | https://hiorbita.com/erp/funcionalidades/llena-la-agenda | "El paciente confirma o avisa desde el mismo chat, sin llamar" y "Primer aviso por WhatsApp 48 horas antes" | Abrir la página en un navegador y buscar las frases literales |
| 2 | Página de precios | https://agendapro.com/ar/planes | Individual ARS 13.900, Básico 33.900, Premium 44.900, Pro 314.900 por mes, IVA incluido; facturación electrónica "Próximamente" | Abrir la página, anotar montos, moneda, período e indicación de IVA; captura con fecha |
| 3 | Texto legal oficial | https://www.argentina.gob.ar/normativa/nacional/ley-25326-64790/texto | El art. 25 regula la prestación de servicios informatizados por cuenta de terceros; el art. 26 trata información crediticia | Leer los arts. 25 y 26 completos; contrastar con infoleg.gob.ar |
| 4 | Revisión científica | https://www.cochrane.org/evidence/CD007458_mobile-phone-messaging-reminders-attendance-healthcare-appointments | 8 ensayos, 6.615 participantes; asistencia 67,8 % sin recordatorio frente a 78,6 % con SMS; calidad baja a moderada | Leer la síntesis y, si es posible, el texto completo de la revisión |
| 5 | Comparador de terceros | https://www.comparasoftware.com/xiagenda | XIAgenda: plan Esencial USD 15 por mes por profesional; agente de IA por WhatsApp, web y email | Abrir la ficha, verificar el precio y si declara la fuente o fecha de los datos |
| 6 | Tienda de apps | https://apps.apple.com/ar/app/bilog-gesti%C3%B3n-odontol%C3%B3gica/id1554140449 | Bilog: calificación 3,5 de 5 con 15 reseñas en la App Store de Argentina | Abrir la ficha y anotar calificación y cantidad de reseñas del día |
| 7 | Página de ayuda o documentación | https://help.dentally.com/en/articles/3566498-how-to-set-up-automated-reminders-and-confirmations-in-patient-communications | Responder "YES" confirma y "NO" cancela; recordatorios solo a pacientes con consentimiento | Leer el artículo completo y citar el párrafo |
| 8 | Política de privacidad oficial | https://odonto.ar/privacidad | Odonto.ar declara derechos según la Ley 25.326, reclamo ante la AAIP, cifrado y RLS | Leer la política y buscar las menciones literales |
| 9 | Ensayo científico argentino | https://45jaiio.sadio.org.ar/sites/default/files/CAIS-19.pdf | CAIS 2016: SMS y llamada reducen el ausentismo; el email solo no mostró diferencia significativa | Leer resultados por brazo en el PDF |
| 10 | Prensa | https://www.iproup.com/startups/63662-argentinos-crean-app-gratuita-para-que-pymes-y-comercios-no-pierdan-clientes | Turnito presentada como startup argentina con más de 40.000 usuarios activos | Abrir la nota completa y anotar su fecha de publicación |

| # | Consulta automatizada (fecha) | Verificación personal | Resultado | Fecha | Verificado por |
|---|---|---|---|---|---|
| 1 | 2026-10-12 | CONFIRMADA | Comprobados en el sitio oficial el recordatorio por WhatsApp 48 horas antes y la posibilidad de que el paciente confirme desde el chat. | 2026-10-12 | Santiago Chepilla |
| 2 | 2026-10-10 y 2026-10-12 | CONFIRMADA | Comprobados los precios publicados (2026-10-12): Individual ARS 13.900, Básico ARS 33.900, Premium ARS 44.900 y Pro ARS 314.900 por mes. Ampliación (2026-10-13): comprobadas la indicación «IVA incluido» y la facturación electrónica como «Próximamente». Sin verificación personal: las demás condiciones comerciales. | 2026-10-12; ampliada el 2026-10-13 | Santiago Chepilla |
| 3 | 2026-10-10 | CONFIRMADA | Leídos los arts. 25 y 26: el art. 25 regula la prestación de servicios informatizados de datos personales por cuenta de terceros; el art. 26 trata sobre información crediticia. Contraste con InfoLEG: no realizado. | 2026-10-12 | Santiago Chepilla |
| 4 | 2026-10-10 | PENDIENTE — revisión humana | — | — | — |
| 5 | 2026-10-10 y 2026-10-12 | PENDIENTE — revisión humana | — | — | — |
| 6 | 2026-10-12 | CONFIRMADA | Comprobados en la App Store de Argentina la aplicación Bilog Gestión Odontológica, su desarrollador y la calificación 3,5/5 con 15 reseñas. | 2026-10-12 | Santiago Chepilla |
| 7 | 2026-10-12 | CONFIRMADA | Comprobado en el centro de ayuda que el paciente puede responder YES para confirmar y NO para cancelar, y la información sobre consentimiento para los recordatorios. | 2026-10-12 | Santiago Chepilla |
| 8 | 2026-10-12 | PENDIENTE — revisión humana | — | — | — |
| 9 | 2026-10-10 | PENDIENTE — revisión humana | — | — | — |
| 10 | 2026-10-12 | PENDIENTE — revisión humana | — | — | — |

### 8.2 Afirmaciones incorrectas o sin respaldo y correcciones

Compilado de los registros de auditoría, reconfirmación, degradaciones y fichas. Fechas: 2026-10-10 (auditoría) y 2026-10-12 (ampliación y revisión).

| # | Afirmación original | Origen | Corrección | Evidencia / URL |
|---|---|---|---|---|
| 1 | AgendaPro: "precio no publicado" | Nota inicial `agendapro.md` | Publica precios en ARS en /ar/planes (la URL /ar/precios da 404) | https://agendapro.com/ar/planes |
| 2 | AgendaPro: no se sabía si el precio incluye IVA | `discovery/discovery.md`, punto 4.3 | La página indica IVA incluido (lectura automática del 2026-10-12; verificado personalmente el 2026-10-13, sección 8.1, fila 2) | https://agendapro.com/ar/planes |
| 3 | AgendaPro: "98 % de asistencia" | Sitio del fabricante | Afirmación comercial; además refiere a quienes confirman (sesgo de selección), no a reducción del ausentismo | https://agendapro.com/ar/dental/software-odontologico |
| 4 | Dentalink: "desde USD 29/mes" | Nota inicial (agregador) | Proviene del blog de Turnito, un competidor; no se usa como precio. Precio oficial no publicado | https://turnito.app/blog/las-mejores-apps-de-turnos-para-odontologos-en-argentina-2026/ ; https://www.softwaredentalink.com/planes |
| 5 | Dentalink: link de reserva online del paciente | Nota inicial | No reconfirmado en la página de agenda; C5.1 No evidenciado | https://www.softwaredentalink.com/experiencia-de-pacientes/agenda |
| 6 | Artículo de Ámbito como fuente de XIAgenda | Primera pasada de `xiagenda.md` | El artículo trata sobre Órbita (La Plata); se descartó como fuente de XIAgenda | https://www.ambito.com/tecnologia/desarrollo-nacional-crearon-una-ia-argentina-que-organiza-turnos-medicos-whatsapp-y-ya-se-prueba-consultorios-n6304027 |
| 7 | Ley 25.326 "art. 25/26" para prestadores de servicios | `_hipotesis-mercado.md` | Es el art. 25; el art. 26 trata información crediticia | https://www.argentina.gob.ar/normativa/nacional/ley-25326-64790/texto |
| 8 | Registro ante la AAIP "a cargo de cada clínica" | Nota previa de normativa | No verificado; a quién alcanza la inscripción es una pregunta abierta (preguntas 7 y 8) | https://www.argentina.gob.ar/node/53779 |
| 9 | H3: autoagendamiento "7 de 7" competidores | `_hipotesis-mercado.md` | 4 de 7 con fuente oficial en ese momento (Doctoralia, AgendaPro, Turnito, Doctocliq); XIAgenda solo terceros; Dentalink y Dentidesk pendientes | `discovery/sources/_hipotesis-mercado.md` |
| 10 | Doctocliq: presencia en "11 países" | Nota inicial (agregador) | El sitio oficial dice "20+ países"; luego clasificado como afirmación comercial | https://www.doctocliq.com |
| 11 | Doctocliq: "sitio oficial no fetcheado" y "precios no encontrados" | Nota inicial | Se leyeron el sitio y la página de planes: USD 0 / 19 / 29 / 49 por mes | https://www.doctocliq.com/planes |
| 12 | Doctoralia: público multiespecialidad y pertenencia a Docplanner | Nota inicial | No re-verificado el 2026-10-10; el 2026-10-12 se confirmó Docplanner Health como desarrollador de la app; segmento odontológico No evidenciado | https://apps.apple.com/es/app/doctoralia-para-especialistas/id1237598188 |
| 13 | Doctoralia: la nota omitía WhatsApp | Nota inicial | Recordatorios por WhatsApp confirmados en fuente oficial (plan no identificado) | https://pro.doctoralia.com/ar/agenda-doctoralia-para-especialistas |
| 14 | Doctoralia: C3.5 comprobado (otras integraciones) | Ficha 2026-10-12 | Degradado: la cita sobre Google My Business no es calendario externo, SMS ni API; SMS no se pudo citar en la relectura | `discovery/sources/_reconfirmacion-nivel1.md` |
| 15 | Doctoralia: "reducción del ausentismo hasta 65 %" | Sitio del fabricante | Afirmación comercial sin fuente; no se usa | https://pro.doctoralia.com/ar/agenda-doctoralia-para-especialistas |
| 16 | Dentidesk: consentimiento informado automatizado disponible | Auditoría 2026-10-10 y punto 4.6 de `discovery/discovery.md` | Figura como "una de las próximas funcionalidades"; No evidenciado. El autor ya corrigió el punto 4.6 de `discovery/discovery.md` ("próxima funcionalidad", no disponible) | https://www.dentidesk.com |
| 17 | Dentidesk: WhatsApp automático | Primera lectura del 2026-10-12 | "una de las próximas alternativas"; No evidenciado | https://www.dentidesk.com |
| 18 | Dentidesk: Mercado Pago, roles, auditoría, backups, GDPR y lista de espera | Primera lectura automática del 2026-10-12 | Descartada: una segunda lectura con citas no los encontró | https://www.dentidesk.com |
| 19 | Dentidesk: facturación con SII y DGII | Auditoría 2026-10-10 | La ficha ampliada del 2026-10-12 cita SII (Chile) y Alegra (República Dominicana); DGII no se reconfirmó | https://www.dentidesk.com |
| 20 | Turnito: precios sin indicación de impuestos | Nota inicial | Los precios son "más IVA" | https://turnito.app |
| 21 | Turnito: "100% gratis de por vida" | Blog propio | Contradice su tabla de precios (planes pagos y comisión del 5 %); se trata como marketing | https://turnito.app/blog/las-mejores-apps-de-turnos-para-odontologos-en-argentina-2026/ |
| 22 | Clinicorp: confirmación por respuesta, cobro online y facturación (C1.4, C4.2, C4.3) | Ficha 2026-10-12 | Degradados: las citas no describen la respuesta del paciente ni la seña, y la facturación devolvió NOT FOUND | `discovery/sources/_reconfirmacion-latam.md` |
| 23 | Degradaciones por evidencia débil (9 ítems) | Fichas 2026-10-12 | MR Dental Cloud C6.3; Clinicorp C1.1; Turnito C3.1; Órbita C2.3, C4.2 y C6.3; Odonto.ar C5.2; Bilog C3.3 y C6.2 pasaron a No evidenciado (Órbita C6.3 y Turnito C3.1 se restituyeron después) | `discovery/sources/_degradaciones-evidencia-debil.md` |
| 24 | Turnito C3.1 degradado por evidencia débil | Primera ronda de degradaciones | Restituido: la cita elegida era un cupo de mensajes, pero existía evidencia descriptiva oficial, "Recordatorios por WhatsApp, email y Telegram" (31,5 → 34,5) | https://turnito.app |
| 25 | Odeen, MR Dental Cloud y DentalSoft+: C1.4 comprobado con "confirmaciones automáticas" | Fichas 2026-10-12 | Degradados a No evidenciado por uniformidad con Clinicorp C1.4: la frase no describe que el paciente confirme o rechace respondiendo (Odeen 75 → 70, MR Dental Cloud 67 → 62, DentalSoft+ 47 → 42) | `discovery/sources/_degradaciones-evidencia-debil.md` |
| 26 | Órbita C6.3 degradado por no figurar en /la-operacion | Primera ronda de degradaciones | Restituido: la ausencia en otra página no es contradicción | https://hiorbita.com/erp/funcionalidades |
| 27 | Órbita: precios No evidenciado (página de precios ilegible) | Ficha inicial `orbita.md` | La relectura de /precios mostró USD 25 (Consultorio) y USD 113 (Clínica) por mes, abonables en pesos | https://hiorbita.com/precios |
| 28 | Órbita: "6 meses gratis" como prueba gratuita | Lectura de /precios | Corresponde a otro producto (Turnero); C7.2 No evidenciado | https://hiorbita.com/precios |
| 29 | Bilog: soporte multisede | Ficha inicial `bilog.md` | No reconfirmado en la pasada de profundidad; C4.5 se apoya en la liquidación de honorarios | https://bilog.com.ar/soluciones/clinicas |
| 30 | Bilog: recordatorios por SMS | llms.txt del sitio | Contradice la página de recordatorios y la documentación (solo WhatsApp y email); C3.5 No evidenciado | https://bilog.com.ar/reminders-whatsapp/ |
| 31 | Bilog: encuestas de satisfacción | Documentación | Marcadas "Muy pronto"; C5.5 No evidenciado | `discovery/sources/bilog.md` |
| 32 | DentalTec: cuenta corriente | Pasada de profundidad | Es del prestador u obra social, no del paciente; C4.1 No evidenciado | https://web.dentaltec.com.ar/funcionalidades |
| 33 | DentalTec: paquetes de WhatsApp en USD como precio | Pasada de profundidad | No son el precio del software; C7.1 No evidenciado | https://web.dentaltec.com.ar/preguntas-frecuentes |
| 34 | Odonto.ar: reportes (C4.4) | Pasada de profundidad | El "Panel de finanzas" con totales no describe reportes; no se infiere | https://odonto.ar/ |
| 35 | XIAgenda: precio USD 20 del plan Profesional | Extracto de búsqueda | No confirmado en la página abierta; no se usa | https://www.comparasoftware.com/xiagenda |
| 36 | Paper CAIS/SADIO como estudio reciente con ausentismo "15-30 %" | `_hipotesis-mercado.md` | Es el CAIS 2016; el mismo trabajo da 15-30 %, 20-30 % y 25 % en distintos pasajes | https://45jaiio.sadio.org.ar/sites/default/files/CAIS-19.pdf |
| 37 | IECS: "reducción absoluta ~3 % sobre ~272.000 turnos" | Extracto de búsqueda | No hallado en la fuente; no se usa | https://iecs.org.ar/en/portfolio/evaluacion-del-impacto-de-una-estrategia-de-recordatorios-sobre-el-ausentismo-a-citas-de-atencion-ambulatoria-en-ciudad-de-buenos-aires/ |
| 38 | Odontopediatría, 14,3 % de inasistencias, como dato general | `_hipotesis-mercado.md` | Servicio académico de Buffalo (EE. UU.), población con alta privación social; no extrapolable | https://pmc.ncbi.nlm.nih.gov/articles/PMC12274092/ |

---

## 9. Anexos

### 9.1 Resumen por sistema

Doce grupos de campos por sistema, en una línea cada uno. Estado más reciente según la ficha JSON y las secciones de reconfirmación o profundidad. "No evidenciado" indica falta de respaldo público.

#### 1. Órbita (Hi Órbita) — nivel 1 — ficha: `discovery/sources/orbita.md`
1. Segmento: clínicas odontológicas y centros médicos argentinos; Órbita Chat (WhatsApp con IA) y Órbita Gestión.
2. Agenda: por sillón sin superposición; duración por práctica; bloqueo de vacaciones y feriados.
3. Reserva y autogestión: turno por WhatsApp con el asistente; confirma y reprograma en el chat; página pública No evidenciado.
4. Automatizaciones: primer aviso por WhatsApp 48 h antes; recontacto al que no responde; lista de espera.
5. Clínica: odontograma, periodontograma, historia clínica, consentimientos con plantillas; presupuestos No evidenciado (degradado).
6. Administración: caja por sede, liquidación de honorarios, diez vistas de reportes; facturación y seña No evidenciado.
7. Integraciones: WhatsApp por API oficial; Dentalink y Benty; obras sociales; Mercado Pago y ARCA No evidenciado.
8. Roles y trazabilidad: cinco roles; registro de cambios; exportación completa; multisede por caja.
9. Seguridad y cumplimiento: alojamiento en AWS; medidas declaradas y Ley 25.326 No evidenciado.
10. Precio: USD 25 (Consultorio) y USD 113 (Clínica) por mes; pago en dólares, pesos o USDT; prueba gratuita No evidenciado.
11. Interpretación: fuerte en agenda y WhatsApp conversacional; débil en evidencia de facturación y seguridad.
12. Adopción: cifras y clínicas citadas por el fabricante (afirmación comercial); independiente No evidenciado.

#### 2. Bilog — nivel 1 — ficha: `discovery/sources/bilog.md`
1. Segmento: clínicas y consultorios odontológicos, obras sociales y auditoría; web y apps iOS y Android.
2. Agenda: turnos, profesionales y consultorios; duración por prestación y bloqueos No evidenciado.
3. Reserva y autogestión: reserva por QR o enlace; el paciente reserva, cancela y consulta online.
4. Automatizaciones: recordatorio de WhatsApp por día de agenda con confirmar o cancelar; lista de espera No evidenciado.
5. Clínica: ficha, odontograma, historia clínica y anamnesis, presupuestos, asistencia radiográfica con IA, recetas.
6. Administración: pagos imputados al tratamiento, facturas y notas de crédito, reportes, liquidación de honorarios.
7. Integraciones: WhatsApp; obras sociales; ARCA no nombrada (degradado); sin API pública documentada; Mercado Pago No evidenciado.
8. Roles y trazabilidad: perfiles con permisos; auditoría (degradada), exportación y multisede No evidenciado.
9. Seguridad y cumplimiento: No evidenciado.
10. Precio: Freemium sin costo; Lite y Premium se cotizan por usuario; migración sin costo.
11. Interpretación: el más completo en clínica y obras sociales; sin precio ni seguridad publicados.
12. Adopción: App Store Argentina 3,5 de 5 con 15 reseñas; cifras propias son afirmación comercial.

#### 3. DentalTec — nivel 1 — ficha: `discovery/sources/dentaltec.md`
1. Segmento: odontólogos, círculos, federaciones y obras sociales; 100 % web.
2. Agenda: turnos configurables por odontólogo, día, horario e intervalos; duración por prestación y bloqueos No evidenciado.
3. Reserva y autogestión: confirmación por respuesta en WhatsApp; reserva online del paciente No evidenciado.
4. Automatizaciones: recordatorios automáticos por WhatsApp vinculados a la agenda; lista de espera No evidenciado.
5. Clínica: odontograma interactivo, historia clínica, imágenes; presupuestos, consentimiento y recetas No evidenciado.
6. Administración: planillas, liquidaciones, facturación integrada con ARCA, dashboard; caja del paciente No evidenciado.
7. Integraciones: WhatsApp oficial; ARCA; más de 15 obras sociales; Mercado Pago No evidenciado.
8. Roles y trazabilidad: 10 tipos de roles; auditoría; exportación de reportes a PDF y Excel.
9. Seguridad y cumplimiento: JWT y bcrypt, respaldo automático; Ley 25.326 No evidenciado.
10. Precio: no publicado ("costo por odontólogo"); paquetes de WhatsApp en USD; demo gratuita.
11. Interpretación: fuerte en obras sociales, ARCA y trazabilidad; débil en experiencia del paciente.
12. Adopción: cifras y reseñas del propio sitio (afirmación comercial); independiente No evidenciado.

#### 4. Odonto.ar — nivel 1 — ficha: `discovery/sources/odonto-ar.md`
1. Segmento: clínicas y profesionales odontológicos; app web en PC, tablet y celular.
2. Agenda: vista día, semana o mes con arrastre; duración por motivo; bloqueos No evidenciado.
3. Reserva y autogestión: enlace público donde el paciente elige motivo, día y hora; cancelación por el paciente No evidenciado (degradado).
4. Automatizaciones: recordatorio de WhatsApp armado desde la agenda "en un clic"; confirmación por respuesta y lista de espera No evidenciado.
5. Clínica: odontograma interactivo, historial clínico, presupuestos, radiografías; consentimiento y recetas No evidenciado.
6. Administración: panel de finanzas con saldos; reportes, facturación y seña No evidenciado.
7. Integraciones: WhatsApp; cálculo de cobertura de obras sociales; importación desde Excel; Mercado Pago y ARCA No evidenciado.
8. Roles y trazabilidad: permisos por rol y módulo; auditoría, exportación y multisede No evidenciado.
9. Seguridad y cumplimiento: cifrado en reposo y tránsito, RLS; derechos según Ley 25.326 y AAIP; backups No evidenciado.
10. Precio: USD 29 / 49 / 99 por mes con equivalente en ARS; prueba de 30 días sin tarjeta.
11. Interpretación: liviano, transparente en precio y privacidad; poca automatización evidenciada.
12. Adopción: No evidenciado.

#### 5. AgendaPro — nivel 1 — ficha: `discovery/sources/agendapro.md`
1. Segmento: horizontal (belleza, bienestar, salud) con landing odontológica; SaaS.
2. Agenda: hasta 20 profesionales según plan; duración por prestación y bloqueos No evidenciado.
3. Reserva y autogestión: reserva online 24/7; cancelación por el paciente No evidenciado.
4. Automatizaciones: recordatorios por WhatsApp, SMS o email; WhatsApp como agregado pago.
5. Clínica: historia clínica odontológica editable e imágenes; odontograma y presupuestos No evidenciado.
6. Administración: caja, señas y links de pago, comisiones, inventario; facturación electrónica "Próximamente" (verificado personalmente el 2026-10-13).
7. Integraciones: WhatsApp; API en plan Pro; Mercado Pago, ARCA y obras sociales No evidenciado.
8. Roles y trazabilidad: multi-ubicación; roles, auditoría y exportación No evidenciado.
9. Seguridad y cumplimiento: No evidenciado.
10. Precio: ARS 13.900 / 33.900 / 44.900 / 314.900 por mes, IVA incluido (montos verificados personalmente el 2026-10-12; IVA, el 2026-10-13); prueba gratis.
11. Interpretación: fuerte en cobros y precio local; débil en clínica y seguridad documentada.
12. Adopción: cifras del fabricante (afirmación comercial); independiente No evidenciado.

#### 6. Doctoralia Pro (Argentina) — nivel 1 — ficha: `discovery/sources/doctoralia-argentina.md`
1. Segmento: profesionales de la salud multiespecialidad; segmento odontológico No evidenciado.
2. Agenda: agenda online y app móvil; multiprofesional y bloqueos No evidenciado.
3. Reserva y autogestión: reserva online en todos los planes desde perfil, Google y redes; reprogramación por mensaje.
4. Automatizaciones: email y push (Starter), SMS (Plus y VIP), WhatsApp para confirmaciones; lista de espera en VIP.
5. Clínica: historia clínica desde Plus; resto No evidenciado.
6. Administración: estadísticas en VIP; cobros y facturación No evidenciado.
7. Integraciones: WhatsApp; Mercado Pago, ARCA y obras sociales No evidenciado.
8. Roles y trazabilidad: No evidenciado.
9. Seguridad y cumplimiento: AWS y protocolos RGPD declarados; Ley 25.326 No evidenciado.
10. Precio: ARS 25.000 / 35.000 / 55.000 por mes con facturación anual; versión gratuita.
11. Interpretación: fuerte en captación de pacientes (marketplace); sin funciones odontológicas evidenciadas.
12. Adopción: App Store España 4,7 de 5 (terceros, no específico de Argentina).

#### 7. Turnito — nivel 1 — ficha: `discovery/sources/turnito.md`
1. Segmento: turnos multirrubro; no es software clínico; versiones regionales.
2. Agenda: multi-agenda; Google Calendar bidireccional; duración y bloqueos No evidenciado.
3. Reserva y autogestión: reserva online sin registro y landing de autoagendamiento; cancelación por el paciente No evidenciado.
4. Automatizaciones: recordatorios por WhatsApp, email y Telegram con cupo de WhatsApp por plan.
5. Clínica: No evidenciado.
6. Administración: seña online con comisión de 5 % a 0 %; reportes; facturación No evidenciado.
7. Integraciones: Mercado Pago, PayPal, Talo, Google Calendar y Meet; ARCA y obras sociales No evidenciado.
8. Roles y trazabilidad: No evidenciado.
9. Seguridad y cumplimiento: No evidenciado; los términos advierten transmisión sin cifrar.
10. Precio: ARS 0 / 9.900 / 20.300 / 34.800 por mes, más IVA.
11. Interpretación: referencia de agenda genérica de bajo costo con Mercado Pago.
12. Adopción: nota de iProUP (terceros); cifras propias son afirmación comercial.

#### 8. Odeen — nivel 2 — ficha: `discovery/sources/odeen.md`
1. Segmento: consultorios y clínicas dentales de Chile; web en la nube.
2. Agenda: citas, sedes y profesionales en una vista; duración y bloqueos No evidenciado.
3. Reserva y autogestión: página pública de reserva; cancelación por el paciente No evidenciado.
4. Automatizaciones: recordatorios por WhatsApp (80/120/200 por mes) y email; confirmación por respuesta del paciente No evidenciado ("confirmaciones automáticas" sin detalle).
5. Clínica: odontograma por pieza y superficie, periodontograma, ficha, imágenes, consentimientos y recetas.
6. Administración: caja por sede, cobro en línea, facturación digital, reportes, laboratorio.
7. Integraciones: WhatsApp y SMS; Mercado Pago, ARCA y obras sociales No evidenciado.
8. Roles y trazabilidad: roles; registro de accesos a fichas; exportación total; sedes según plan.
9. Seguridad y cumplimiento: cifrado en tránsito, reposo y por campo; Ley 21.719 (Chile).
10. Precio: CLP 19.990 / 29.990 / 49.990 por mes, IVA incluido; prueba de 14 días.
11. Interpretación: de los más completos y transparentes del estudio (mejor puntaje de nivel 2); sin adaptación argentina.
12. Adopción: No evidenciado.

#### 9. Dentalink — nivel 2 — ficha: `discovery/sources/dentalink.md`
1. Segmento: consultorios y clínicas dentales; nube en AWS; Argentina No evidenciado.
2. Agenda: vista por sillón y profesional; tiempos por odontólogo; duración por prestación No evidenciado.
3. Reserva y autogestión: el paciente confirma, reprograma o cancela; reserva online No evidenciado.
4. Automatizaciones: recordatorios por WhatsApp y email configurables por sucursal.
5. Clínica: historia clínica, odontograma, presupuestos, periodontograma, RX, consentimientos, recetas.
6. Administración: pagos presenciales y online, caja, comisiones, inventario, facturación (Colombia).
7. Integraciones: WhatsApp; Mercado Pago, ARCA y obras sociales No evidenciado.
8. Roles y trazabilidad: roles con permisos editables; multisede en Pro; auditoría y exportación No evidenciado.
9. Seguridad y cumplimiento: backups diarios y tráfico cifrado; ISO 27001, HIPAA y GDPR declarados.
10. Precio: no publicado (cotización); el "USD 29" de terceros no se usa.
11. Interpretación: profundidad clínica y de gestión; precio opaco y sin adaptación argentina.
12. Adopción: cifras del fabricante (afirmación comercial).

#### 10. MR Dental Cloud — nivel 2 — ficha: `discovery/sources/mr-dentalcloud.md`
1. Segmento: clínicas odontológicas de México y Latinoamérica; nube multidispositivo.
2. Agenda: multi-doctor; duración y bloqueos No evidenciado.
3. Reserva y autogestión: confirmaciones automáticas por WhatsApp sin detalle del mecanismo (C1.4 No evidenciado); reserva online No evidenciado.
4. Automatizaciones: recordatorios por WhatsApp a las 24, 12, 4 y 1 hora.
5. Clínica: odontograma, expediente NOM-004, presupuestos, recetas electrónicas.
6. Administración: pagos en línea, facturación CFDI, dashboards, inventario.
7. Integraciones: WhatsApp API, Google Calendar, PayPal; Mercado Pago y ARCA No evidenciado.
8. Roles y trazabilidad: roles; auditoría inmutable; exportación No evidenciado (degradado).
9. Seguridad y cumplimiento: AES-256, respaldos diarios; NOM-004, COFEPRIS, HIPAA/GDPR "ready".
10. Precio: MXN 350 / 750 por mes; prueba de 30 días.
11. Interpretación: precio bajo y cadencia de recordatorios; cumplimiento centrado en México.
12. Adopción: cifras del fabricante (afirmación comercial).

#### 11. Doctocliq — nivel 2 — ficha: `discovery/sources/doctocliq.md`
1. Segmento: clínicas dentales y estéticas; web y app del profesional; Argentina no listada.
2. Agenda: múltiples doctores en plan Avanzado; duración y bloqueos No evidenciado.
3. Reserva y autogestión: link de agendamiento; cancelación por el paciente No evidenciado.
4. Automatizaciones: recordatorios por WhatsApp (50/100/150 por mes), email y SMS.
5. Clínica: odontograma, periodontograma, historia clínica, presupuestos, imágenes, consentimientos.
6. Administración: link de pago, reportes, facturación en Perú, México, Ecuador y Colombia.
7. Integraciones: WhatsApp, API para citas; Mercado Pago, ARCA y obras sociales No evidenciado.
8. Roles y trazabilidad: niveles de acceso por rol; sedes adicionales; "descargar toda tu información".
9. Seguridad y cumplimiento: No evidenciado.
10. Precio: USD 0 / 19 / 29 / 49 por mes; prueba de 7 días.
11. Interpretación: clínica completa a bajo precio; sin adaptación argentina.
12. Adopción: cifras del fabricante (afirmación comercial); App Store sin calificaciones suficientes.

#### 12. Clinicorp — nivel 2 — ficha: `discovery/sources/clinicorp.md`
1. Segmento: clínicas odontológicas de Brasil; nube, en portugués.
2. Agenda: agenda digital con check-in por QR; multiprofesional No evidenciado (degradado).
3. Reserva y autogestión: el paciente confirma presencia por QR; reserva online No evidenciado.
4. Automatizaciones: confirmaciones y recordatorios por WhatsApp; alerta de retorno (recall).
5. Clínica: prontuario, planes de tratamiento, imágenes y radiología con IA, recetas firmadas.
6. Administración: conciliación, dashboard, inventario, comisiones; facturación y seña No evidenciado (degradados).
7. Integraciones: WhatsApp, centros de radiología; Mercado Pago, ARCA y obras sociales No evidenciado.
8. Roles y trazabilidad: niveles de acceso personalizados; auditoría y exportación No evidenciado.
9. Seguridad y cumplimiento: No evidenciado.
10. Precio: R$ 149,90 / 369,90 por mes; migración y capacitación gratuitas.
11. Interpretación: referente brasileño con finanzas e IA; ecosistema fiscal ajeno a Argentina.
12. Adopción: cifras del fabricante (afirmación comercial).

#### 13. DentalSoft+ — nivel 2 — ficha: `discovery/sources/dentalsoft-plus.md`
1. Segmento: clínicas de salud bucal; nube.
2. Agenda: calendario virtual; multiprofesional y bloqueos No evidenciado.
3. Reserva y autogestión: "confirmaciones automáticas" sin detalle del mecanismo (C1.4 No evidenciado); reserva online No evidenciado.
4. Automatizaciones: recordatorios automáticos y WhatsApp para notificaciones.
5. Clínica: odontograma, periodontograma, registro electrónico, firma electrónica, receta con código de barras.
6. Administración: reportes financieros e inventario; facturación No evidenciado.
7. Integraciones: WhatsApp; Mercado Pago, ARCA, obras sociales y API No evidenciado.
8. Roles y trazabilidad: roles y auditoría; exportación y multisede No evidenciado.
9. Seguridad y cumplimiento: respaldos; norma concreta No evidenciado.
10. Precio: USD 0, USD 349 (anual + 2 meses) y USD 799 (vitalicio).
11. Interpretación: plan gratuito y licencia vitalicia; empresa y país poco verificables.
12. Adopción: No evidenciado.

#### 14. Dentidesk — nivel 2 — ficha: `discovery/sources/dentidesk.md`
1. Segmento: clínicas y consultorios dentales; Chile, República Dominicana y Cabo Verde declarados.
2. Agenda: "agenda de citas avanzada"; multiprofesional y bloqueos No evidenciado.
3. Reserva y autogestión: "agendamiento online" nombrado sin descripción; No evidenciado.
4. Automatizaciones: recordatorios No evidenciado; WhatsApp automático anunciado como próximo.
5. Clínica: odontograma y fichas de especialidad, historial médico, dictado por voz; consentimiento anunciado como próximo.
6. Administración: registro de pagos, más de 20 reportes, multisucursal, facturación con SII y Alegra.
7. Integraciones: SII, Alegra; Mercado Pago, ARCA y obras sociales No evidenciado.
8. Roles y trazabilidad: multisucursal; roles, auditoría y exportación No evidenciado.
9. Seguridad y cumplimiento: No evidenciado.
10. Precio: no publicado; prueba de 15 días; migración incluida.
11. Interpretación: profundidad clínica; poco relevante para Argentina.
12. Adopción: No evidenciado.

#### 15. XIAgenda — nivel 2 — ficha: `discovery/sources/xiagenda.md`
1. Segmento (3°): consultorios de Argentina multiespecialidad; nube; sitio oficial no resuelve.
2. Agenda (3°): múltiples profesionales por consultorio.
3. Reserva y autogestión (3°): agente de IA que agenda, reprograma y cancela por WhatsApp, web y email.
4. Automatizaciones (3°): recordatorios con pedido de confirmación; lista de espera automática.
5. Clínica: No evidenciado.
6. Administración (3°): señas por Mercado Pago; reportes en plan superior.
7. Integraciones (3°): WhatsApp y Mercado Pago; obras sociales solo "interpreta obras sociales" al pedir turno.
8. Roles y trazabilidad: No evidenciado.
9. Seguridad y cumplimiento: No evidenciado.
10. Precio (3°): Esencial USD 15 por mes por profesional; prueba gratuita.
11. Interpretación: posible entrante de IA conversacional; operatividad sin confirmar.
12. Adopción: comparador "Aún sin calificación"; No evidenciado.

#### 16. Dentally — nivel 3 — ficha: `discovery/sources/dentally.md`
1. Segmento: software dental en la nube del Reino Unido; planes por gabinetes.
2. Agenda: multiprofesional, tipos de turno, lista de espera y relleno de huecos.
3. Reserva y autogestión: portal con reserva, cancelación y nueva reserva; depósitos; recall sin login.
4. Automatizaciones: recordatorios SMS y email con consentimiento; confirmación respondiendo YES o NO.
5. Clínica: odontograma, notas, plan y presupuestos, periodontograma, imágenes con IA, consentimientos y recetas.
6. Administración: pagos, facturación y reportes en tiempo real; multisede.
7. Integraciones: hub de desarrolladores; WhatsApp, Mercado Pago, ARCA y obras sociales No evidenciado.
8. Roles y trazabilidad: 5 niveles de permiso, 2FA, auditoría; exportación No evidenciado.
9. Seguridad y cumplimiento: TLS, BCrypt, AWS en la UE, backups; ICO y NHS DSP Toolkit.
10. Precio: GBP 125 / 220 / 320 por mes para 3 gabinetes, sin IVA.
11. Interpretación: mejor referencia de ciclo completo del paciente.
12. Adopción: No evidenciado.

#### 17. NexHealth — nivel 3 — ficha: `discovery/sources/nexhealth.md`
1. Segmento: capa de experiencia del paciente sobre más de 70 sistemas de gestión (EE. UU.).
2. Agenda: No evidenciado.
3. Reserva y autogestión: reserva online sincronizada; cancelación por el paciente No evidenciado.
4. Automatizaciones: recordatorios SMS y email; lista de espera; recall en un clic.
5. Clínica: No evidenciado.
6. Administración: cobros, cuentas por cobrar, verificación de seguro, analítica.
7. Integraciones: API, SDKs y más de 70 integraciones.
8. Roles y trazabilidad: No evidenciado.
9. Seguridad y cumplimiento: HIPAA y SOC 2 declarados.
10. Precio: modular sin importes publicados.
11. Interpretación: referencia de arquitectura "capa sobre el sistema de gestión".
12. Adopción: cifra del fabricante (afirmación comercial).

#### 18. DentalPin — nivel 3 — ficha: `discovery/sources/dentalpin.md`
1. Segmento: gestión dental de código disponible (BSL 1.1), autoalojada; interfaz en español.
2. Agenda: vistas semanal, diaria y kanban; multiprofesional No evidenciado.
3. Reserva y autogestión: No evidenciado.
4. Automatizaciones: recordatorios No evidenciado; asistente de IA con confirmación del usuario.
5. Clínica: odontograma, historia clínica, presupuestos con aprobación.
6. Administración: facturas y pagos; Verifactu (España) y GST (India).
7. Integraciones: No evidenciado.
8. Roles y trazabilidad: cinco tipos de usuario; exportación No evidenciado.
9. Seguridad y cumplimiento: tokenización de identificadores ante el modelo de IA; norma No evidenciado.
10. Precio: núcleo gratuito sin cargos por puesto.
11. Interpretación: referencia de modelo de datos abierto.
12. Adopción: No evidenciado.

### 9.2 Archivos de metodología y evidencia

| Archivo | Contenido |
|---|---|
| `docs/discovery/metodologia/criterios-puntuacion.md` | Pesos, ítems, valores y reglas de evidencia |
| `docs/discovery/metodologia/plantilla-ficha.md` | Plantilla de ficha y reglas de clasificación |
| `docs/discovery/metodologia/puntuar.js` | Cálculo reproducible de la matriz |
| `docs/discovery/metodologia/puntuar.test.js` | Pruebas del cálculo |
| `docs/discovery/metodologia/matriz-resultado.md` | Matriz final congelada |
| `discovery/sources/fichas/*.json` | 18 fichas con 35 ítems cada una |
| `discovery/sources/<slug>.md` | Fichas legibles con 12 grupos de campos |
| `discovery/sources/_auditoria.md` | Auditoría consolidada del 2026-10-10 |
| `discovery/sources/_reconfirmacion-nivel1.md` | Reconfirmación de nivel 1 con citas |
| `discovery/sources/_reconfirmacion-latam.md` | Reconfirmación de Latinoamérica con citas |
| `discovery/sources/_degradaciones-evidencia-debil.md` | Degradaciones y restitución |
| `discovery/sources/_hipotesis-mercado.md` | Hipótesis H1 a H3 |
| `discovery/sources/_normativa.md` | Normativa argentina (no es asesoramiento legal) |
| `discovery/sources/_recordatorios.md` | Canales y costos de recordatorios |
| `discovery/sources/_obras-sociales.md` | Obras sociales en la muestra inicial |
| `discovery/discovery.md` | Checklist aprobado, D1 a D9 y 19 preguntas |
| `docs/discovery/checklist-discovery.md` y `.json` | Resultado estructurado del checklist |
| `docs/discovery/fuentes.md` | Índice de trazabilidad de todas las URL |

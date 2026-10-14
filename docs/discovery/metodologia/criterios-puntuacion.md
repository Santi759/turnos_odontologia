# Criterios de puntuación de la matriz comparativa

Definidos el 2026-10-12, **antes** de la investigación ampliada, para que la puntuación no se ajuste a los resultados.

## Pesos (consigna de Metodología I)

| Código | Criterio | Peso |
|---|---|---|
| C1 | Gestión de turnos y automatización | 25 % |
| C2 | Funcionalidad odontológica clínica | 20 % |
| C3 | Integraciones locales y WhatsApp | 15 % |
| C4 | Administración, cobros y facturación | 15 % |
| C5 | Experiencia del paciente | 10 % |
| C6 | Seguridad, exportación y trazabilidad | 10 % |
| C7 | Precio y facilidad de adopción | 5 % |

## Método

Cada criterio tiene **5 ítems observables**. El puntaje del criterio (0 a 5) es la suma de los ítems según su estado de evidencia:

| Estado del ítem | Valor | Cuándo se usa |
|---|---|---|
| `comprobado-oficial` | 1 | La función está descripta en una página oficial del producto (sitio, documentación, tienda de apps del propio fabricante), con URL y fecha de consulta. |
| `terceros` | 0,5 | Solo la menciona una fuente que no es el fabricante (comparador, nota de prensa, reseña). |
| `afirmacion-comercial` | 0 | Solo existe como afirmación de marketing sin descripción funcional verificable (porcentajes, "el mejor", cifras de clientes sin respaldo). Cuenta para la cobertura, no para el puntaje. |
| `no-evidenciado` | 0 | No hay respaldo público. **No significa que el producto no lo tenga.** |

- **Puntaje total (0–100)** = Σ (puntaje del criterio / 5 × peso).
- **Cobertura de evidencia** = ítems con estado distinto de `no-evidenciado` / 35. Permite distinguir un puntaje bajo por falta de función de uno bajo por falta de información pública.
- Ninguna capacidad se asigna sin evidencia: un ítem sin URL solo puede ser `no-evidenciado`.
- El cálculo es reproducible con `docs/discovery/metodologia/puntuar.js` sobre las fichas JSON de `discovery/sources/fichas/`.

### Reglas de evidencia agregadas durante la revisión (2026-10-12, decisiones del autor)

Estas reglas se fijaron al revisar la matriz provisoria y se aplicaron de forma pareja a todos los sistemas. Los cambios que produjeron están registrados en `discovery/sources/_degradaciones-evidencia-debil.md`.

- **La cita debe describir la función.** Una palabra suelta, un cupo de plan, un medio de pago listado o una frase vaga no alcanzan; el ítem queda `no-evidenciado`.
- **Lo anunciado como "próximamente" no está disponible** y queda `no-evidenciado`.
- **Contradicción solo dentro de la misma página.** Se degrada un ítem cuando dos lecturas de la misma página oficial se contradicen; que la cita no aparezca en otra página del mismo fabricante no es contradicción.
- **Profundidad pareja para la recomendación de demos.** Los sistemas de nivel 1 con foco odontológico (Órbita, Bilog, Odonto.ar, DentalTec) se revisaron con la misma profundidad (35 ítems, varias páginas oficiales, citas textuales). El resto tuvo una revisión de menor profundidad; esa diferencia se declara como limitación.

## Ítems por criterio

### C1. Gestión de turnos y automatización (25 %)
1. `C1.1` Agenda para múltiples profesionales o por sillón/consultorio.
2. `C1.2` Configuración de duración por prestación/tipo de turno, o bloqueos de agenda (ausencias, feriados).
3. `C1.3` Recordatorios automáticos de turno (cualquier canal).
4. `C1.4` Confirmación automática: el paciente confirma o rechaza respondiendo un mensaje o enlace.
5. `C1.5` Lista de espera u otra automatización de agenda (reasignación de huecos, recall periódico).

### C2. Funcionalidad odontológica clínica (20 %)
1. `C2.1` Odontograma.
2. `C2.2` Historia o ficha clínica.
3. `C2.3` Plan de tratamiento o presupuestos odontológicos.
4. `C2.4` Periodontograma, o gestión de imágenes/radiografías.
5. `C2.5` Consentimiento informado digital o recetas.

### C3. Integraciones locales y WhatsApp (15 %)
1. `C3.1` WhatsApp (recordatorio, confirmación o canal de reserva).
2. `C3.2` Mercado Pago.
3. `C3.3` Facturación electrónica de Argentina (ARCA, ex AFIP).
4. `C3.4` Obras sociales o prepagas argentinas (padrones, autorizaciones, liquidación o registro).
5. `C3.5` Otras integraciones (calendario externo, SMS, API pública).

### C4. Administración, cobros y facturación (15 %)
1. `C4.1` Registro de pagos, caja o cuenta corriente del paciente.
2. `C4.2` Cobro online o seña al reservar.
3. `C4.3` Facturación electrónica (cualquier país).
4. `C4.4` Reportes o estadísticas de gestión.
5. `C4.5` Multisede/sucursales, inventario o liquidación de honorarios a profesionales.

### C5. Experiencia del paciente (10 %)
1. `C5.1` Reserva online por el paciente.
2. `C5.2` Cancelación o reprogramación autogestionada por el paciente.
3. `C5.3` Comunicación por canal móvil (WhatsApp, SMS, push o app).
4. `C5.4` Perfil o página pública de reserva, o presencia en marketplace.
5. `C5.5` Portal o app del paciente, o encuestas de satisfacción.

### C6. Seguridad, exportación y trazabilidad (10 %)
1. `C6.1` Roles y permisos por usuario.
2. `C6.2` Registro de auditoría o trazabilidad de cambios.
3. `C6.3` Exportación de datos (pacientes, agenda o historia clínica).
4. `C6.4` Medidas de seguridad declaradas (cifrado, copias de seguridad, certificaciones).
5. `C6.5` Cumplimiento normativo declarado (Ley 25.326, GDPR, HIPAA u otra).

### C7. Precio y facilidad de adopción (5 %)
1. `C7.1` Precio publicado.
2. `C7.2` Plan gratuito o prueba gratuita.
3. `C7.3` Precio en ARS u oferta comercial explícita para Argentina.
4. `C7.4` Onboarding, migración de datos o soporte en español.
5. `C7.5` Evidencia verificable de adopción **de fuente independiente** (reseñas en tiendas o comparadores, casos con nombre). Las cifras del propio fabricante son `afirmacion-comercial`.

## Orden por relevancia para Argentina

1. **Nivel 1**: presencia comercial en Argentina comprobada (precio en ARS, sitio `/ar`, integración local o clientes argentinos verificables).
2. **Nivel 2**: Latinoamérica, en español, sin presencia argentina comprobada.
3. **Nivel 3**: internacional (referencia de funciones o de experiencia de usuario).

Dentro de cada nivel se ordena por puntaje total descendente y, ante empate, por cobertura de evidencia.

## Limitaciones

- La evidencia proviene de páginas públicas leídas mediante resúmenes automáticos; las funciones que un producto tiene pero no publica quedan como `no-evidenciado`.
- Los ítems miden **presencia declarada** de una función, no su calidad.
- Los puntajes no reemplazan las demos recomendadas en el informe.

# Flujos Principales

> Fuentes: CU1–CU5 de `discovery/discovery.md`; reglas de `05_reglas_de_negocio.md`; arquitectura de `02_descripcion_general.md`. Etiquetas: ver [README](README.md#convenciones).
>
> Componentes: **Front** (React + Vite) · **API** (FastAPI) · **Dominio** (servicios de reglas) · **DB** (PostgreSQL). Los pasos describen el comportamiento esperado; la implementación concreta se define en los Changes.

| Flujo | Estado |
|---|---|
| F1. Inicio de sesión y contexto de consultorio | Núcleo; mecanismo [ABIERTA] PA-03 |
| F2. Configuración inicial de la agenda | Núcleo |
| F3. Consulta de disponibilidad | Núcleo |
| F4. Creación de un turno sin superposiciones | Núcleo (flujo central de D1) |
| F5. Reprogramación de un turno | Núcleo |
| F6. Cancelación de un turno | Núcleo; alcance de R5 [ABIERTA] PA-12 |
| F7. Creación de un bloqueo con turnos existentes | Núcleo; efecto [ABIERTA] PA-10 |
| F8. Alta de paciente y aviso de privacidad | Núcleo |
| F9. Agenda del odontólogo | Núcleo |
| F10. Reserva online del paciente | Candidato (D4) |
| F11. Lista diaria con enlaces wa.me | Candidato (D6) |

---

## Flujo 1: Inicio de sesión y contexto de consultorio

**Disparador**: un usuario abre la aplicación.
**Actor**: administrador, secretaría u odontólogo.

**Pasos**:
1. **Front** envía las credenciales a la **API**.
2. **API** verifica las credenciales y que el usuario esté activo (RN-AU-01, RN-AU-02, RN-AU-06).
3. **API** emite la sesión o el token, con el mecanismo que se decida en PA-03.
4. En cada petición posterior, la **API** obtiene el usuario autenticado y, **a partir de él**, el consultorio y el rol (RN-MT-02). Ese contexto se inyecta en los servicios de dominio.
5. **Dominio** y repositorios operan siempre dentro de ese consultorio; la **DB** aplica la barrera adicional que se decida en PA-04 (RN-MT-06).

```
Usuario → Front → API: credenciales
               API → DB: buscar usuario activo
               API ← DB
         Front ← API: sesión o token
Petición → API: identidad → (consultorio, rol) → Dominio → DB (acotado al consultorio)
```

**Casos de error**:
- Credenciales inválidas o usuario inactivo → rechazo genérico, sin indicar qué falló (US-001).
- Demasiados intentos fallidos → bloqueo temporal ([PROP] RN-AU-05).
- Sesión vencida → nuevo inicio de sesión.
- Petición con un identificador de otro consultorio → respuesta igual a "no encontrado" (RN-MT-05).

## Flujo 2: Configuración inicial de la agenda (CU1)

**Disparador**: un consultorio empieza a usar el sistema.
**Actor**: administrador.

**Pasos**:
1. El administrador revisa los datos del consultorio y la anticipación de cancelación (24 horas por defecto, R5).
2. Da de alta las **prestaciones** con su duración en minutos (R1).
3. Da de alta los **profesionales** y, si corresponde, los vincula a usuarios odontólogos.
4. Define los **horarios de atención** de cada profesional por día de la semana (R3). Si más adelante modifica una franja que ya tiene turnos, el comportamiento es [ABIERTA] PA-18.
5. Carga los **bloqueos** conocidos: feriados del consultorio, vacaciones y ausencias (R4).
6. A partir de aquí, la disponibilidad (F3) refleja la realidad del consultorio.

**Casos de error**:
- Duración menor o igual a cero → rechazo.
- Franja con inicio igual o posterior al fin, o solapada con otra del mismo día → rechazo.
- Vincular un usuario de otro consultorio o sin rol odontólogo → rechazo (RN-MT-03).

## Flujo 3: Consulta de disponibilidad

**Disparador**: la secretaría (o el paciente, si se aprueba D4) busca un horario.
**Actor**: secretaría.

**Pasos**:
1. **Front** pide los horarios libres para una prestación, un profesional y un rango de fechas.
2. **Dominio** obtiene la duración de la prestación (R1).
3. **Dominio** toma las franjas de atención del profesional para cada día (R3).
4. **Dominio** descuenta los bloqueos del profesional y los de todo el consultorio (R4).
5. **Dominio** descuenta los turnos que ocupan agenda del profesional (R2). Qué estados ocupan agenda es RN-AG-02b (propuesta inicial en RN-TU-05; PA-07).
6. **Dominio** genera los inicios posibles en los que la prestación entra **completa** en el tiempo libre, con la granularidad que se decida en PA-08 (RN-AG-06, RN-AG-12).
7. **Front** muestra los horarios en la zona horaria del consultorio.

**Casos de error**:
- Prestación o profesional inactivos → sin disponibilidad, con motivo.
- Un horario que se muestra libre puede ocuparse antes de confirmar: F4 vuelve a validar.

## Flujo 4: Creación de un turno sin superposiciones (CU2, núcleo de D1)

**Disparador**: la secretaría confirma un horario para un paciente.
**Actor**: secretaría.

**Pasos**:
1. **Front** envía paciente, profesional, prestación e inicio. **No envía el consultorio** (RN-MT-02).
2. **API** valida el formato con Pydantic y verifica el rol (RN-AU-03).
3. **Dominio** comprueba que paciente, profesional y prestación pertenezcan al consultorio del usuario y estén activos (RN-MT-03, RN-AG-10).
4. **Dominio** calcula `fin = inicio + duración de la prestación` (RN-AG-01).
5. **Dominio** verifica que el inicio no esté en el pasado ([PROP] RN-TU-06), que el turno quede completo dentro de una franja de atención (RN-AG-06) y que no interseque bloqueos (RN-AG-08).
6. **Dominio** verifica que no haya superposición con otros turnos que ocupan agenda del profesional (RN-AG-02 y RN-AG-02b) para dar un mensaje claro.
7. **DB** inserta el turno en una transacción. La **restricción de exclusión** por profesional y rango horario ([PROP]) es la garantía final ante concurrencia (RN-AG-03, RN-GL-02).
8. **API** responde con el turno creado en estado `reservado` ([PROP] RN-TU-04).

```
Secretaría → Front → API: crear turno
                     API → Dominio: validar consultorio, activos, horario, bloqueos, superposición
                     Dominio → DB: INSERT en transacción
                               DB: restricción de exclusión (profesional, [inicio, fin))
                     API ← ok | conflicto
            Front ← turno creado | motivo del rechazo
```

**Casos de error**:
- Superposición detectada en el paso 6 → rechazo con motivo "el profesional ya tiene un turno en ese horario", sin datos del otro paciente (RN-GL-03).
- Dos peticiones simultáneas pasan el paso 6 → la **DB** rechaza la segunda en el paso 7; la **API** la traduce al mismo rechazo por superposición.
- Fuera de franja o dentro de un bloqueo → rechazo con el motivo correspondiente.
- Paciente, profesional o prestación de otro consultorio → "no encontrado" (RN-MT-05).

**Fuera de este flujo**: la superposición de **sillones o boxes** entre profesionales distintos **no se valida**, porque no hay regla aprobada (PA-01).

## Flujo 5: Reprogramación de un turno

**Disparador**: el paciente pide cambiar el turno.
**Actor**: secretaría.

**Pasos**:
1. **Front** envía el nuevo inicio y, si cambian, el profesional o la prestación.
2. **Dominio** verifica la anticipación mínima si corresponde (RN-TU-03, PA-12).
3. **Dominio** repite los pasos 3 a 6 del F4, **excluyendo al propio turno** de la comparación de superposición.
4. **DB** actualiza en una transacción; la restricción de exclusión vuelve a aplicar.
5. Se registra quién hizo el último cambio y cuándo ([PROP] RN-TU-09). El historial completo es PA-19 y el estado resultante tras reprogramar es PA-07.

**Casos de error**: los mismos del F4. Si falla, el turno original queda intacto (RN-GL-02).

## Flujo 6: Cancelación de un turno

**Disparador**: el paciente avisa que no asistirá.
**Actor**: secretaría (o paciente, si se aprueba D4).

**Pasos**:
1. **Dominio** verifica la anticipación mínima configurada (R5). Su aplicación a la secretaría depende de PA-12.
2. El turno pasa a `cancelado` y registra `cancelado_en`.
3. El horario vuelve a estar disponible (RN-TU-05).

**Casos de error**:
- Cancelación dentro del plazo mínimo → rechazo o aviso, según PA-12.
- Turno ya cancelado o atendido → rechazo por transición inválida (PA-07).

## Flujo 7: Creación de un bloqueo con turnos existentes

**Disparador**: el administrador carga vacaciones, una ausencia o un feriado.
**Actor**: administrador.

**Pasos**:
1. **Front** envía el período y, opcionalmente, el profesional; sin profesional, aplica a todo el consultorio ([PROP] PA-10).
2. **Dominio** valida `inicio < fin`.
3. **Dominio** busca turnos que ocupan agenda dentro del período (RN-AG-02b).
4. Si no hay turnos afectados, se crea el bloqueo. Si en el mismo momento se está creando un turno dentro del período, la restricción de la base no lo detecta: [ABIERTA] PA-20.
5. Si hay turnos afectados: **[ABIERTA] PA-10**, con tres alternativas (rechazar el bloqueo, crearlo y listar los turnos para reprogramar, o cancelarlos). Hasta la decisión, el comportamiento mínimo es **informar los turnos afectados** sin cancelarlos automáticamente.

**Casos de error**: un período inválido se rechaza.

## Flujo 8: Alta de paciente y aviso de privacidad (CU4)

**Disparador**: llega un paciente nuevo.
**Actor**: secretaría.

**Pasos**:
1. La secretaría busca al paciente en **su** consultorio. No hay búsqueda entre consultorios (RN-MT-04).
2. Si no existe, carga la ficha básica sin datos clínicos (RN-PA-01, RN-PA-02) y, si corresponde, el contacto preferido (RN-PA-07).
3. Informa el aviso de privacidad vigente y registra la aceptación con versión, fecha y medio ([PROP] RN-PA-04).
4. El paciente queda disponible para F4.

**Casos de error**:
- Datos obligatorios faltantes → rechazo.
- Si el paciente no acepta el aviso: [ABIERTA], depende de las preguntas 6, 9 y 11.

## Flujo 9: Agenda del odontólogo (CU3)

**Disparador**: el odontólogo abre su agenda.
**Actor**: odontólogo.

**Pasos**:
1. **API** identifica al profesional vinculado al usuario (SU-03).
2. **Dominio** devuelve solo los turnos de ese profesional, para el día o la semana.
3. **Front** muestra paciente, prestación y horario. Es una vista de solo lectura en la v0.1 (RN-TU-07).

**Casos de error**: un usuario odontólogo sin profesional vinculado ve una agenda vacía con un aviso.

## Flujo 10: Reserva online del paciente — Candidato (D4)

Aplica solo si el roadmap lo incorpora (pregunta 5).

**Disparador**: un paciente entra a la página pública del consultorio.
**Actor**: paciente.

**Pasos**:
1. **Front** muestra las prestaciones y los profesionales que el consultorio ofrece.
2. El paciente elige y ve horarios libres (F3).
3. El paciente se identifica con cuenta o como invitado, según la pregunta 3.
4. La reserva sigue el F4 con las mismas validaciones y la misma garantía de concurrencia (RN-RE-01).

**Casos de error**:
- Horario tomado por otra persona durante la reserva → rechazo y nueva disponibilidad.
- Intentos de enumerar consultorios o turnos → sin datos de otros pacientes (RN-RE-03).

## Flujo 11: Lista diaria con enlaces wa.me — Candidato (D6)

**Disparador**: la secretaría prepara los avisos del día siguiente.
**Actor**: secretaría.

**Pasos**:
1. **Dominio** lista los turnos que ocupan agenda del día siguiente en el consultorio.
2. Para cada uno arma un enlace wa.me con un mensaje prearmado: fecha, hora y consultorio, **sin la prestación** (RN-PA-03).
3. La secretaría abre cada enlace y envía el mensaje desde su WhatsApp. No hay API ni envío automático (D6, D7).
4. Si el paciente responde, la secretaría actualiza el estado manualmente (F5, F6 o RN-TU-04).

**Casos de error**:
- Paciente sin teléfono válido → se marca para contacto por otro medio.
- El formato oficial del enlace wa.me está [PEND].

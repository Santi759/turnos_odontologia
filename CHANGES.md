# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **turnos_odontologia** (SaaS multi-consultorio de turnos odontológicos, Argentina; MVP académico v0.1).
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes" y resolver las "Decisiones previas al propose" listadas en el Scope (son preguntas abiertas PA-xx de `knowledge-base/10_preguntas_abiertas.md`: las decide el autor, no el agente).
3. Ejecutar `/opsx:propose <nombre-del-change>`. El nombre del change es el que figura entre comillas invertidas en su encabezado (por ejemplo, `foundation-setup`); el prefijo `C-NN` es solo el número de orden en este documento y **no** forma parte del nombre en OpenSpec.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

> Reglas de gobernanza: en changes **CRITICO** solo se hace análisis y no se escribe código sin aprobación explícita del autor; en **ALTO** se propone y se espera revisión antes de escribir; en **MEDIO** se implementa por pasos con checkpoints; en **BAJO** hay autonomía si los tests pasan. El proyecto usa TDD estricto (DD-10).
> Los changes **candidatos** (FASE 6 a 8) y los **posteriores** (FASE 9) están solo **planificados**: no se proponen ni implementan sin decisión explícita del autor. Ver "Niveles de alcance".
> Datos: todos los datos de desarrollo y pruebas son **ficticios** (RN-PA-08, DD-13).
> **Decisión técnica nueva de la Etapa 4 (autor, 2026-10-13):** el frontend React + Vite se escribe en **TypeScript**. No proviene de Discovery ni de la Knowledge Base aprobada: DD-10 (`knowledge-base/09_decisiones_y_supuestos.md`) elige React con Vite sin fijar el lenguaje. El backend se mantiene en FastAPI con Python y la base de datos en PostgreSQL. Su registro en la Knowledge Base queda pendiente de autorización del autor.

---

## Árbol de dependencias

```
C-01 foundation-setup                                     ← sin historias; ALTERNATIVA condicionada (ver Niveles de alcance)
  └── C-02 modelo-base-consultorios-seed                  ← CRITICO: Consultorio, Usuario, seed ficticio, repos acotados
        └── C-03 autenticacion-sesion                     ← CRITICO (US-001)
              │
              ├── C-06 frontend-base-sesion               ← login/layout/rutas por rol
              │
              └── C-04 aislamiento-roles-rbac             ← CRITICO (US-002)   desbloquea TODO recurso protegido
                    │
                    ├── C-05 gestion-usuarios             (US-003) — fuera de la línea de corte
                    │
                    ├── C-07 profesionales                (US-005)
                    │     ├── C-09 horarios-atencion      (US-007)
                    │     └── C-10 bloqueos-agenda        (US-008)
                    │
                    ├── C-08 prestaciones-duracion        (US-006)
                    │
                    └── C-12 pacientes                    (US-017, US-019)
                          └── C-13 aviso-privacidad       (US-018)

C-06 + C-07 + C-08 + C-09 + C-10 ──► C-11 frontend-configuracion-agenda
C-06 + C-13 (+ C-12) ───────────────► C-14 frontend-pacientes

C-08 + C-09 + C-10 + C-12 ──► C-15 turnos-crear-sin-superposicion   ← ALTO (US-011) — NUCLEO DEL PROBLEMA (D1)
                                    │
                                    ├── C-16 disponibilidad                 (US-010)
                                    ├── C-17 turnos-reprogramar             (US-012)
                                    ├── C-18 turnos-cancelar-estados        (US-013, US-014)
                                    │     └── C-22 anticipacion-minima-cancelacion   (US-009, CONDICIONADA: R5 es propuesta)
                                    └── C-19 agenda-consulta-api            (US-015, US-016)

C-06 + C-16 + C-19 ─────────────────► C-20 frontend-agenda-disponibilidad
C-14 + C-17 + C-18 + C-20 ──────────► C-21 frontend-gestion-turnos      ← fin del núcleo funcional demostrable
C-21 ───────────────────────────────► C-23 seed-demo-y-cierre-nucleo     (opcional, fuera de la línea de corte)

── Candidatos (FUERA del camino crítico y de la línea de corte; solo planificados) ──
C-16 + C-13 ──► C-24 reserva-online-api-publica        (D4, US-020)  ← CRITICO
                  └── C-25 reserva-online-consulta-cancelacion (US-021, US-022)   [+ C-18, C-22]
                        └── C-26 reserva-online-frontend-publico
C-19 ─────────► C-27 lista-diaria-wa-me                (D6, US-023)
C-18 ─────────► C-28 email-aviso-turno                 (D5, US-024)
C-15 ─────────► C-29 exportacion-datos-paciente        (E8, US-025)
C-18 ─────────► C-30 auditoria-accesos-cambios         (E8, US-026)  ← CRITICO
```

### Paralelismo por fase

> Cada "gate" es un punto de sincronización. Los changes de un gate pueden *proponerse* en paralelo desde el punto de vista del grafo; **en este proyecto hay una sola persona desarrolladora y la ejecución real es secuencial** (ver "Plan óptimo con 3 agentes"). Las marcas `[Agente A/B/C]` son perfiles técnicos, no personas.

```
GATE 0: ninguna
  → C-01 foundation-setup                           [Agente A]

GATE 1: C-01 ✓
  → C-02 modelo-base-consultorios-seed              [Agente A]

GATE 2: C-02 ✓
  → C-03 autenticacion-sesion                       [Agente A]

GATE 3: C-03 ✓
  → C-04 aislamiento-roles-rbac                     [Agente A]
  → C-06 frontend-base-sesion                       [Agente C]

GATE 4: C-04 ✓                                       ← PRIMER FORK (4 ramas)
  → C-07 profesionales                              [Agente A]
  → C-08 prestaciones-duracion                      [Agente A]
  → C-12 pacientes                                  [Agente B]
  → C-05 gestion-usuarios                           [Agente B]   (fuera de la línea de corte)

GATE 5: C-07 ✓
  → C-09 horarios-atencion                          [Agente A]
  → C-10 bloqueos-agenda                            [Agente A]

GATE 6: C-12 ✓
  → C-13 aviso-privacidad                           [Agente B]

GATE 7: C-06 + C-07 + C-08 + C-09 + C-10 ✓          (UI de configuración)
  → C-11 frontend-configuracion-agenda              [Agente C]
GATE 7b: C-06 + C-12 + C-13 ✓
  → C-14 frontend-pacientes                         [Agente C]

GATE 8: C-08 + C-09 + C-10 + C-12 ✓                  ← DECISION PA-07 obligatoria antes del propose
  → C-15 turnos-crear-sin-superposicion             [Agente A]

GATE 9: C-15 ✓                                       ← SEGUNDO FORK (4 ramas)
  → C-16 disponibilidad                             [Agente A]
  → C-19 agenda-consulta-api                        [Agente A]
  → C-17 turnos-reprogramar                         [Agente B]
  → C-18 turnos-cancelar-estados                    [Agente B]

GATE 10: C-06 + C-16 + C-19 ✓
  → C-20 frontend-agenda-disponibilidad             [Agente C]

GATE 11: C-14 + C-17 + C-18 + C-20 ✓                 ← cierre de la línea de corte
  → C-21 frontend-gestion-turnos                    [Agente C]

GATE 12: C-18 ✓ (y PA-12 resuelta)
  → C-22 anticipacion-minima-cancelacion            [Agente B]   (condicionada)
GATE 12b: C-21 ✓
  → C-23 seed-demo-y-cierre-nucleo                  [Agente B]   (opcional)

── Gates de candidatos (requieren decisión explícita del autor; fuera del camino crítico) ──
GATE C1: C-16 + C-13 ✓ y D4/P-05 aprobada            → C-24 reserva-online-api-publica
GATE C2: C-24 + C-18 + C-22 ✓                        → C-25 reserva-online-consulta-cancelacion
GATE C3: C-24 + C-25 ✓                               → C-26 reserva-online-frontend-publico
GATE C4: C-19 ✓                                      → C-27 lista-diaria-wa-me
GATE C5: C-18 ✓                                      → C-28 email-aviso-turno, C-30 auditoria-accesos-cambios
GATE C6: C-15 ✓                                      → C-29 exportacion-datos-paciente
```

### Camino crítico (10 changes — mínimo irreducible hasta el cierre de la línea de corte)

```
C-01 → C-02 → C-03 → C-04 → C-07 → C-09 → C-15 → C-16 → C-20 → C-21
```

> Notas: (a) C-08, C-10, C-12 deben estar archivados antes de C-15 aunque no estén en la cadena lineal. (b) C-11\* es el otro extremo de la línea de corte (rama de configuración, más corta). (c) Ningún candidato (C-24 a C-30) ni posterior integra el camino crítico. (d) C-05, C-22 y C-23 cuelgan del grafo pero no lo extienden.

### Plan óptimo con 3 agentes

> **Aclaración obligatoria:** "Agente A / B / C" son **perfiles técnicos o responsabilidades** (A = backend core y dominio; B = backend auxiliar y datos; C = frontend). **No son tres personas reales**: el proyecto tiene **un solo desarrollador** (Santiago Chepilla) y la ejecución es **secuencial**, siguiendo el camino crítico. La tabla indica qué perfil correspondería a cada change y qué changes serían paralelizables si hubiera más capacidad; en la práctica se avanza un change por vez, en el orden de los pasos.

```
Paso │ Agente A (Backend Core)            │ Agente B (Backend Aux)             │ Agente C (Frontend)
─────┼────────────────────────────────────┼────────────────────────────────────┼─────────────────────────────────
  1  │ C-01 foundation-setup              │ —                                  │ —
  2  │ C-02 modelo-base-consultorios-seed │ —                                  │ —
  3  │ C-03 autenticacion-sesion          │ —                                  │ —
  4  │ C-04 aislamiento-roles-rbac        │ —                                  │ C-06 frontend-base-sesion
  5  │ C-07 profesionales                 │ C-12 pacientes                     │ —
  6  │ C-08 prestaciones-duracion         │ C-13 aviso-privacidad              │ —
  7  │ C-09 horarios-atencion             │ C-05 gestion-usuarios (fuera corte)│ C-14 frontend-pacientes
  8  │ C-10 bloqueos-agenda               │ —                                  │ —
  9  │ C-15 turnos-crear-sin-superposicion│ —                                  │ C-11 frontend-configuracion-agenda
 10  │ C-16 disponibilidad                │ C-17 turnos-reprogramar            │ —
 11  │ C-19 agenda-consulta-api           │ C-18 turnos-cancelar-estados       │ —
 12  │ —                                  │ —                                  │ C-20 frontend-agenda-disponibilidad
 13  │ —                                  │ C-22 anticipacion-minima (condic.) │ C-21 frontend-gestion-turnos
 14  │ —                                  │ C-23 seed-demo-y-cierre (opcional) │ —
```

> Los pasos 15 en adelante (candidatos C-24 a C-30) no se asignan: dependen de decisiones del autor.

### Niveles de alcance

> Sin fechas ni estimaciones obligatorias de tiempo: la entrega del martes está sin definir (Discovery, pregunta 1; IN-05) y no se inventa un plazo. Las horas por change (~4-6 h) son una referencia de tamaño, no un compromiso.

**Nivel 1 — Alcance total del MVP académico (v0.1)**
Todo lo que la KB considera perímetro de la v0.1: los 8 esenciales del informe §6.3 (núcleo, US-001 a US-019) más los candidatos que el autor decida incorporar (D4, D5, D6, E8). "Núcleo" es un *perímetro funcional propuesto*, **no** obligación de construirlo todo (KB 06). Dentro de este nivel, todo lo que no esté en la línea de corte es **planificado, no comprometido**.

**Nivel 2 — Primer Change que se desarrollará y entregará: C-01, nombre en OpenSpec `foundation-setup`**
- C-01 es una base técnica pequeña, independiente, verificable y de bajo riesgo: React + Vite con TypeScript (decisión de la Etapa 4), FastAPI con Python, PostgreSQL con `btree_gist` disponible, Docker Compose, pytest + Vitest cableados, README de arranque y health check. **No contiene historias de usuario ni reglas de negocio.** Sirve para ejercitar el ciclo OpenSpec completo (propose → apply → archive).
- **Condición pendiente de verificación:** *su elección definitiva como primer change entregado está condicionada a verificar si la consigna de la cátedra para el primer change exige funcionalidad observable por el usuario.* Hasta verificarlo, C-01 se desarrolla como cimiento sin promesa de que sea lo que se presente como "primer change".
- **Alternativa documentada (no se elige entre ambas todavía):** *C-01 + un corte de dominio mínimo que NO dependa de autenticación ni de aislamiento por consultorio*. Ejemplo: funciones puras de dominio para **R1** (`fin = inicio + duración de la prestación`, RN-AG-01) y **R2** (detección de superposición con intervalos semiabiertos `[inicio, fin)`, RN-AG-02/04) con pruebas unitarias, expuestas solo como tests y/o documentación OpenAPI. Esa porción nace luego como parte de C-08 y C-15 (que la reutilizan), de modo que no se descarta trabajo. **No** se agregan a C-01 reglas que necesiten garantías de autenticación o aislamiento (RN-MT, RN-AU), ni la restricción de exclusión (depende de PA-07).

**Nivel 3 — Changes restantes: SOLO planificados**
C-02 a C-30 (y los posteriores de la FASE 9) quedan como plan. **No se implementan automáticamente**: cada uno requiere `/opsx:propose` explícito, dependencias archivadas y las decisiones previas resueltas. Los candidatos (C-24 a C-30) además requieren decisión explícita del autor sobre su inclusión.

**Línea de corte para la entrega académica**
Conjunto mínimo para *demostrar el núcleo* (login → aislamiento entre dos consultorios → configuración de agenda → paciente con aviso → turno sin superposición → estados/cancelación → agenda), sin construir todo el producto:

```
C-01, C-02, C-03, C-04, C-06,                     (cimiento, acceso y aislamiento, base de UI)
C-07, C-08, C-09, C-10, C-11,                     (configuración de la agenda)
C-12, C-13, C-14,                                 (pacientes y aviso de privacidad)
C-15, C-16, C-17, C-18, C-19, C-20, C-21          (turnos, disponibilidad y agenda)
```

Quedan **fuera de la línea de corte**: C-05 (la demo usa usuarios del seed; US-003 puede esperar), C-22 (R5 es propuesta condicionada), C-23 (pulido de demo), todos los candidatos (C-24 a C-30, incluida la **reserva online D4**) y los posteriores. La línea de corte es un mínimo *sugerido para decisión del autor*: si el plazo aprieta (RG1), el orden de recorte recomendado es C-17 → C-14/C-11 reducidos a lo esencial, nunca C-04 ni C-15.

**Próxima entrega académica:** se centra en el **primer Change** (Nivel 2). Los 20 Changes de la línea de corte son una **propuesta de corte para demostrar el MVP**; **no** son obligatorios para la próxima entrega ni fijan un plazo. Se conserva la granularidad actual (30 Changes) para que cada uno tenga alcance pequeño, verificable, dependencias claras y contexto suficiente.

**Alta de consultorios (PA-05):** en la v0.1 los consultorios existen **solo como seed data ficticio** (C-02: dos consultorios demo para probar aislamiento real). No hay autoservicio ni administrador de plataforma. El procedimiento definitivo de alta queda **pendiente para una etapa posterior** (US-004 bloqueada/postergada). El aislamiento (RN-MT-01 a 06) se implementa y se prueba igual.

### Alineación con el MVP del informe §6.3

Fuente: `docs/discovery/informe-discovery.md` §6.3 (sugerencia sujeta a aprobación del autor).

| # | Esencial (núcleo) | Changes que lo cubren |
|---|---|---|
| 1 | Multi-consultorio con datos aislados | C-02 (modelo base, seed, repos acotados), C-03 (identidad → consultorio), **C-04** (barreras de aislamiento + pruebas de acceso cruzado) |
| 2 | Roles por consultorio | C-02 (rol en Usuario), C-04 (autorización por rol, matriz de `03_actores_y_roles.md`), C-05 (gestión de usuarios, fuera de la línea de corte), C-06 (rutas por rol en UI) |
| 3 | Profesionales con horarios y prestaciones con duración | C-07 (profesionales), C-08 (prestaciones y R1), C-09 (horarios R3), C-11 (UI) |
| 4 | Bloqueos de agenda | C-10 (R4), C-11 (UI) |
| 5 | Validación que impide superposiciones | **C-15** (servicio de dominio + restricción de exclusión), C-16 (disponibilidad solo con horarios válidos), C-17 (revalidación al reprogramar) |
| 6 | Gestión de turnos con estados | C-15 (estado inicial), C-18 (transiciones, cancelación), C-17, C-21 (UI) |
| 7 | Ficha básica del paciente | C-12 (ficha, búsqueda, desactivación), C-14 (UI) |
| 8 | Aviso de privacidad o consentimiento | C-13 (registro de aceptación versionado), C-14 (UI) |

| Diferenciador candidato (informe §6.3) | Dónde quedó |
|---|---|
| Reserva online por el paciente (D4) | C-24, C-25, C-26 (FASE 6, candidata; fuera del camino crítico y de la línea de corte) |
| Email de confirmación o aviso (D5) | C-28 (FASE 7, candidata) |
| Lista diaria con enlaces wa.me (D6) | C-27 (FASE 7, candidata) |
| Exportación avanzada y registro de auditoría (E8) | C-29 y C-30 (FASE 8, candidata) |

| Etapa posterior (informe §6.3) | Dónde quedó |
|---|---|
| Recordatorios automáticos WhatsApp API / SMS (D7) | FASE 9, posterior, sin C-NN |
| Lista de espera | FASE 9, posterior |
| Seña con Mercado Pago | FASE 9, posterior |
| Sincronización con Google Calendar | FASE 9, posterior |
| Historia clínica y odontograma (D3) | Fuera de alcance, no se planifica |
| Obras sociales / ARCA / facturación (D8) | Fuera de alcance, no se planifica (dato de obra social sigue abierto, pregunta 4) |

Tensiones del informe sin resolver aquí: T-01 (sin historia clínica), T-02 (reserva online mayoritaria en el mercado pero candidata a recorte), T-03 (sin recordatorios automáticos), T-04 (obras sociales). No se convierten en decisiones.

### Riesgos

| ID | Riesgo | Changes afectados | Mitigación |
|---|---|---|---|
| RG1 | Alcance frente a plazo, con un solo desarrollador (principal) | Todos; especialmente C-24 a C-30 | Línea de corte explícita; candidatos y posteriores fuera del camino crítico; reserva online (D4) separada en FASE 6 y primera en recortarse (T-02, P-05); orden de recorte definido |
| RG2 | Problema no validado con consultorios reales | C-15, C-16, C-18 | Las reglas R1-R6 siguen siendo propuestas del autor; no se presentan como estándar de mercado; priorizar entrevistas (P-02) fuera del roadmap técnico |
| RG3 | Fuga de datos entre consultorios | C-02, C-04 y **todo endpoint con datos de consultorio** (C-05, C-07 a C-19, C-24+) | Defensa en profundidad (RN-MT-06): contexto derivado de la identidad, repos acotados, barrera en DB (PA-04), pruebas de acceso cruzado por endpoint como parte de la definición de terminado de cada change; seed con dos consultorios |
| RG4 | La prestación/motivo del turno podría ser dato de salud | C-08, C-15, C-19, C-27, C-28 | Tratarla como sensible (D9, RN-PA-03): fuera de logs y mensajes externos; solo roles que la necesitan; sin texto libre en el turno hasta decidir PA-15 |
| RG5 | Responsabilidades legales consultorio/SaaS sin definir | C-12, C-13, C-29 | Datos mínimos (PA-14), aviso versionado, datos ficticios; consultar asesoría (P-07 a P-11); no es asesoramiento legal |
| RG6 | El email puede no reducir el ausentismo | C-28 | Candidato; sin promesa de eficacia (D5); no entra al núcleo |
| RG7 | Datos de competidores provienen de resúmenes automáticos | Ninguno técnico | Solo afecta priorización de candidatos; no condiciona el núcleo |
| RT1 | **PA-07** define la condición de la restricción de exclusión (qué estados ocupan agenda); cambiarla después exige migración y revisar datos | C-15, C-17, C-18 | Resolver PA-07 **antes** de crear la migración de C-15; checkpoint del autor; test de migración con datos existentes |
| RT2 | **PA-20**: la restricción de PostgreSQL solo cubre turno contra turno; concurrencia turno vs bloqueo/horario sin mecanismo | C-09, C-10, C-15, C-17 | Decidir mecanismo (p. ej. bloqueo de fila/advisory lock) antes de C-15; prueba de concurrencia dedicada; documentar la limitación si se acepta |
| RT3 | Autenticación y aislamiento son gobernanza **CRITICA**: errores aquí invalidan todo lo demás | C-02, C-03, C-04, C-05, C-24, C-30 | Solo análisis hasta aprobación explícita; PA-03, PA-04, PA-06, PA-11 resueltas antes; revisión de seguridad al archivar |
| RT4 | `btree_gist` no disponible en la imagen de PostgreSQL elegida | C-01, C-15 | C-01 verifica la extensión disponible; C-15 la habilita por migración |
| RT5 | R5 (US-009) es propuesta, no decisión; PA-12 abierta | C-18, C-22, C-25 | C-22 marcado condicionada; C-18 no depende de R5; no se implementa como definitiva (RN-GL-04) |
| RT6 | Sillones/boxes (PA-01) abierto: conflicto de sillón entre profesionales no se controla | C-15 | Ningún change lo implementa; documentado como limitación; el diseño por profesional permite agregar una segunda restricción después |
| RT7 | C-01 podría no cumplir la consigna del primer change (funcionalidad observable) | C-01 | Verificar consigna; alternativa documentada en "Niveles de alcance" |
| RT8 | Un solo desarrollador: sin paralelismo real, sin revisión cruzada | Todos | Ejecución secuencial; TDD estricto; checkpoints por governance |

### Índice historias → Changes

| Historia | Título | Change | Condición / nota |
|---|---|---|---|
| US-001 | Iniciar y cerrar sesión | C-03 | Condicionada (PA-03, PA-11); UI en C-06 |
| US-002 | Aislamiento entre consultorios | C-04 | Condicionada (PA-04); base en C-02 |
| US-003 | Gestionar usuarios del consultorio | C-05 | Fuera de la línea de corte |
| US-004 | Alta de un consultorio | **posterior** | Bloqueada (PA-05); v0.1 usa seed ficticio de C-02 |
| US-005 | Gestionar profesionales | C-07 | UI en C-11 |
| US-006 | Gestionar prestaciones con duración | C-08 | Condicionada (PA-09); UI en C-11 |
| US-007 | Definir horarios de atención | C-09 | PA-18; UI en C-11 |
| US-008 | Bloquear períodos sin atención | C-10 | Condicionada (PA-10); UI en C-11 |
| US-009 | Configurar anticipación de cancelación | C-22 | **Condicionada: R5 es propuesta** (PA-12) |
| US-010 | Consultar disponibilidad | C-16 | PA-08; UI en C-20 |
| US-011 | Crear un turno sin superposiciones | C-15 | Condicionada (PA-07); UI en C-21 |
| US-012 | Modificar o reprogramar un turno | C-17 | UI en C-21 |
| US-013 | Cancelar un turno | C-18 | PA-12; UI en C-21 |
| US-014 | Cambiar el estado de un turno | C-18 | PA-07; UI en C-21 |
| US-015 | Consultar la agenda del consultorio | C-19 | UI en C-20 |
| US-016 | Ver mi agenda (odontólogo) | C-19 | UI en C-20 |
| US-017 | Registrar y editar pacientes | C-12 | PA-14; UI en C-14 |
| US-018 | Registrar aceptación del aviso de privacidad | C-13 | UI en C-14 |
| US-019 | Desactivar un paciente | C-12 | PA-16; UI en C-14 |
| US-020 | Reservar un turno online | C-24 | **Candidata** (D4) |
| US-021 | Consultar mis turnos (paciente) | C-25 | **Candidata** (D4) |
| US-022 | Cancelar mi turno (paciente) | C-25 | **Candidata** (D4) |
| US-023 | Lista diaria con enlaces wa.me | C-27 | **Candidata** (D6) |
| US-024 | Email de confirmación o aviso | C-28 | **Candidata** (D5) |
| US-025 | Exportar datos de un paciente | C-29 | **Candidata** (E8) |
| US-026 | Registro de auditoría | C-30 | **Candidata** (E8) |

Cobertura: 26 de 26 historias, cada una en exactamente un change principal o fase (US-004: posterior). Changes sin historias: C-01, C-06, C-11, C-14, C-20, C-21, C-23, C-26 (cimiento o interfaz; las UI se enlazan en la columna "nota" sin duplicar la historia).

### Resumen por fase

| Fase | Changes | Núcleo / línea de corte | Governance máxima |
|---|---|---|---|
| FASE 0 — Cimientos | C-01 | Sí (condicionado a la consigna) | BAJO |
| FASE 1 — Acceso y aislamiento | C-02 a C-06 | Sí (salvo C-05) | CRITICO |
| FASE 2 — Configuración de la agenda | C-07 a C-11 | Sí | MEDIO |
| FASE 3 — Pacientes y privacidad | C-12 a C-14 | Sí | ALTO |
| FASE 4 — Núcleo de turnos | C-15 a C-21 | Sí | ALTO |
| FASE 5 — Cierre de la v0.1 | C-22, C-23 | No | MEDIO |
| FASE 6 — Reserva online (D4) | C-24 a C-26 | No (candidata) | CRITICO |
| FASE 7 — Comunicación (D5, D6) | C-27, C-28 | No (candidata) | ALTO |
| FASE 8 — Trazabilidad (E8) | C-29, C-30 | No (candidata) | CRITICO |
| FASE 9 — Posteriores | sin C-NN | No planificado | — |

**Total**: 30 changes en 9 fases con changes (más FASE 9 informativa) · 15 gates principales (GATE 0 a 12b) + 6 de candidatos (GATE C1 a C6) · camino crítico de 10 changes · línea de corte de 20 changes (C-01 a C-04, C-06 a C-21), propuesta para demostrar el MVP y no obligatoria para la próxima entrega.

**Primer change recomendado**: C-01, nombre en OpenSpec `foundation-setup`, sujeto a la verificación de la consigna del primer change (ver "Niveles de alcance").
Para arrancar, solo con autorización del autor: `/opsx:propose foundation-setup`.

---

## FASE 0 — Cimientos

### [C-01] `foundation-setup`
- **Estado**: `[ ]` pendiente
- **Scope**: Base técnica mínima, sin historias de usuario ni reglas de negocio. **Su elección definitiva como primer change entregado está condicionada a verificar si la consigna de la cátedra para el primer change exige funcionalidad observable por el usuario.** Alternativa (no decidida): C-01 + funciones puras de dominio R1/R2 con tests unitarios y OpenAPI, sin auth ni aislamiento.
  - Estructura: `backend/` (`app/main.py`, `core/`, `api/`, `domain/`, `repositories/`, `models/`, `alembic/`, `tests/{unit,integration,isolation}`), `frontend/` (Vite + React + TypeScript; TypeScript es decisión del autor en la Etapa 4, 2026-10-13, no de la KB; `src/{features,shared,pages}`) según `08_arquitectura_propuesta.md`
  - Backend: FastAPI mínimo con `GET /api/health` (liveness; opcionalmente chequea la DB), configuración por variables de entorno (`DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, `APP_ENV`), Alembic inicializado (sin migraciones de dominio), SQLAlchemy 2 + Pydantic instalados
  - `docker-compose.yml`: servicios `db` (PostgreSQL con extensión `btree_gist` verificada, p. ej. `CREATE EXTENSION IF NOT EXISTS btree_gist` comprobado en un test de integración), `api`, `frontend`; volumen local; `.env.example` sin valores reales
  - Pruebas cableadas: pytest (un test de health) y Vitest (un test de render mínimo); comando único para correr ambas suites
  - Documentación mínima: `README.md` de arranque (cómo levantar con Docker Compose, correr tests, estructura)
  - Fuera de C-01: modelos de dominio, migraciones de negocio, autenticación, CI en la nube, despliegue (PA-02)
  - Decisiones previas al propose: elegir el driver de PostgreSQL (`DATABASE_URL`, KB 08 §Variables de entorno); verificar la consigna del primer change (ver arriba). Sin PA-xx bloqueantes.
  - Tests: health 200; conexión a DB; `btree_gist` instalable; Vitest ejecuta
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Infraestructura, §Variables de entorno
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-10, DD-11
  - `knowledge-base/01_vision_y_objetivos.md` §Alcance v0.1

---

## FASE 1 — Acceso y aislamiento por consultorio

> Toda la fase es **CRITICA**: no se escribe código sin aprobación explícita del autor. Seguridad y aislamiento no se difieren: son prerrequisito de cualquier recurso protegido.

### [C-02] `modelo-base-consultorios-seed`
- **Estado**: `[ ]` pendiente
- **Scope**: Modelo base multi-consultorio, migración inicial y seed ficticio. Alta de consultorios (PA-05) = **solo seed** en la v0.1.
  - Modelos SQLAlchemy 2: `Consultorio` (`nombre`, `zona_horaria` default `America/Argentina/Buenos_Aires`, `anticipacion_cancelacion_horas` default 24, `activo`, `creado_en`), `Usuario` (`consultorio_id`, `email`, `nombre`, `credencial` como hash, `rol` enum administrador|secretaria|odontologo, `activo`)
  - Migración 001: tablas `consultorio` y `usuario`; constraint `anticipacion_cancelacion_horas >= 0`
  - Repositorio base acotado al consultorio (recibe el consultorio y lo aplica en todas las consultas; RN-MT-01/02)
  - Seed ficticio: 2 consultorios ("Consultorio Demo A/B"), 1 admin + 1 secretaría + 1 odontólogo por consultorio
  - Sin endpoints de alta de consultorio; sin administrador de plataforma
  - Decisiones previas al propose: PA-04 (capas de aislamiento: claves foráneas compuestas con `consultorio_id`, RLS, identificadores no secuenciales; define el tipo de `id` y la forma de los repos); PA-06 (¿email de usuario único global? ¿usuario en varios consultorios?); PA-05 confirmada como "solo seed"
  - Tests: unitarios del repositorio acotado; integración de migración contra PostgreSQL real; el seed es idempotente
- **Dependencias**: C-01
- **Governance**: CRITICO (cimiento de aislamiento y de identidad)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Consultorio, §Usuario, §Seed data inicial
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio Multi-consultorio (RN-MT)
  - `knowledge-base/08_arquitectura_propuesta.md` §Aislamiento multi-consultorio
  - `knowledge-base/10_preguntas_abiertas.md` PA-04, PA-05, PA-06

### [C-03] `autenticacion-sesion`
- **Estado**: `[ ]` pendiente
- **Scope**: US-001. Autenticación y contexto de consultorio derivado de la identidad (RN-MT-02).
  - Endpoints: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` (usuario, rol, consultorio)
  - Dependencia FastAPI `contexto_consultorio` (usuario → consultorio + rol) inyectada a servicios; el cliente nunca envía `consultorio_id`
  - Hash robusto de contraseñas (RN-AU-02), vencimiento y cierre de sesión/token (RN-AU-04), límite de intentos fallidos (RN-AU-05), rechazo genérico de credenciales inválidas o usuario inactivo (US-001), `AUTH_SECRET_KEY`/`AUTH_SESSION_MINUTES` por entorno (RN-AU-07)
  - Rutas no públicas rechazan peticiones sin autenticar (RN-AU-01)
  - Decisiones previas al propose: PA-03 (sesión con cookie vs tokens vs librería; algoritmo de contraseñas), PA-04 (si afecta la forma de inyectar el consultorio), PA-06 (unicidad del email), PA-11 (recuperación de contraseña sin email; puede quedar explícitamente fuera de la v0.1)
  - Tests: login válido/ inválido/ usuario inactivo (mismo mensaje), logout invalida, token/sesión vencida, límite de intentos, ruta protegida sin credencial → 401
- **Dependencias**: C-02
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC, §Rutas públicas
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio Autenticación y autorización (RN-AU)
  - `knowledge-base/07_flujos_principales.md` Flujo 1
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad / Autenticación
  - `knowledge-base/06_funcionalidades.md` US-001

### [C-04] `aislamiento-roles-rbac`
- **Estado**: `[ ]` pendiente
- **Scope**: US-002. Barreras de aislamiento y autorización por rol reutilizables por todos los changes siguientes.
  - Barrera adicional en base de datos según PA-04 (claves foráneas compuestas incluyendo `consultorio_id` y/o RLS con variable de sesión); migración 002 correspondiente
  - Dependencias `require_rol(...)` según la matriz de `03_actores_y_roles.md` (RN-AU-03), verificadas en servidor
  - Respuesta de recurso ajeno idéntica a "no encontrado" (RN-MT-05)
  - Arnés de pruebas de acceso cruzado (`tests/isolation/`): fixture con 2 consultorios, helper para ejecutar cada endpoint como usuario del otro consultorio; **regla de proceso: todo change posterior con endpoints de datos de consultorio agrega su prueba aquí**
  - Esquemas Pydantic de entrada que excluyen `consultorio_id` y campos de control
  - Decisiones previas al propose: PA-04 (capas definitivas), PA-06
  - Tests: acceso cruzado (lectura, modificación, referencia por ID), matriz de roles, intento de pasar `consultorio_id` en body/query/header es ignorado o rechazado
- **Dependencias**: C-03
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio Multi-consultorio (RN-MT-01 a 06)
  - `knowledge-base/08_arquitectura_propuesta.md` §Aislamiento multi-consultorio, §Estrategia de pruebas
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/10_preguntas_abiertas.md` PA-04

### [C-05] `gestion-usuarios`
- **Estado**: `[ ]` pendiente
- **Scope**: US-003 (fuera de la línea de corte; la demo usa usuarios del seed).
  - Endpoints admin: `POST/GET/PATCH /api/usuarios`, desactivación (`activo=false`), asignación de rol, siempre dentro del consultorio del administrador
  - Un usuario desactivado pierde el acceso de inmediato (RN-AU-06); roles distintos de administrador reciben 403
  - Esquemas sin `consultorio_id`; contraseña inicial/restablecimiento según lo decidido en PA-11
  - Decisiones previas al propose: PA-03 y PA-11 (ya resueltas en C-03; confirmar alcance de restablecimiento), PA-06 (¿usuario en varios consultorios?)
  - Tests: CRUD por rol, aislamiento cruzado, desactivación efectiva en la siguiente petición
- **Dependencias**: C-04
- **Governance**: ALTO (gestión de roles y acceso; no toca el mecanismo de autenticación)
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/05_reglas_de_negocio.md` RN-AU-03, RN-AU-06, RN-MT-02
  - `knowledge-base/06_funcionalidades.md` US-003
  - `knowledge-base/04_modelo_de_datos.md` §Usuario

### [C-06] `frontend-base-sesion`
- **Estado**: `[ ]` pendiente
- **Scope**: Base de interfaz (UI de US-001; la historia se cuenta en C-03).
  - `frontend/src/shared`: cliente HTTP con manejo de sesión según PA-03, utilidades de fecha/hora en zona del consultorio
  - `features/auth`: pantalla de login, cierre de sesión, guardas de ruta por rol (administrador / secretaría / odontólogo), layout con navegación por rol
  - Mensajes genéricos ante credenciales inválidas (sin indicar qué falló)
  - `VITE_API_BASE_URL`; sin lógica de autorización crítica en el cliente (la autorización real es del servidor, RN-AU-03)
  - Decisiones previas al propose: las de C-03 (mecanismo de sesión) ya resueltas
  - Tests (Vitest): render de login, redirección sin sesión, menú según rol, formato de fechas
- **Dependencias**: C-03
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones (organización por funcionalidad), §Estructura de directorios
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/07_flujos_principales.md` Flujo 1
  - `knowledge-base/06_funcionalidades.md` US-001

---

## FASE 2 — Configuración de la agenda

> Tras C-04, C-07 y C-08 son independientes entre sí. C-09 y C-10 requieren C-07.

### [C-07] `profesionales`
- **Estado**: `[ ]` pendiente
- **Scope**: US-005.
  - Modelo `Profesional` (`consultorio_id`, `nombre`, `usuario_id` opcional, `activo`); migración 003
  - Endpoints admin `POST/GET/PATCH /api/profesionales`; lectura para secretaría y odontólogo (propio)
  - Vínculo opcional con `Usuario` de rol odontólogo **del mismo consultorio** (RN-MT-03); inactivo no admite turnos nuevos y conserva los existentes
  - Decisiones previas al propose: PA-17 (¿profesionales sin cuenta?), PA-09 (¿todos hacen todas las prestaciones?; si cambia el modelo se decide aquí o en C-08), SU-03
  - Tests: CRUD, vínculo a usuario ajeno/rol incorrecto → rechazo, aislamiento cruzado, desactivación
- **Dependencias**: C-04
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Profesional
  - `knowledge-base/06_funcionalidades.md` US-005
  - `knowledge-base/07_flujos_principales.md` Flujo 2
  - `knowledge-base/10_preguntas_abiertas.md` PA-09, PA-17

### [C-08] `prestaciones-duracion`
- **Estado**: `[ ]` pendiente
- **Scope**: US-006 y regla R1.
  - Modelo `Prestacion` (`consultorio_id`, `nombre` único por consultorio, `duracion_minutos` > 0, `activa`); migración 004
  - Endpoints admin `POST/GET/PATCH /api/prestaciones`
  - Función pura de dominio `calcular_fin(inicio, prestacion)` (RN-AG-01) con tests unitarios (reutilizable por C-15; es la porción candidata a la alternativa de C-01)
  - Cambiar la duración **no** altera turnos existentes (SU-05); prestación inactiva no se ofrece
  - La prestación es dato posiblemente sensible (D9): no aparece en logs
  - Decisiones previas al propose: PA-09 (duración por profesional o por turno; ¿la secretaría puede cambiar la duración?)
  - Tests: duración entera > 0, nombre duplicado, aislamiento cruzado, `calcular_fin` con varios casos
- **Dependencias**: C-04
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Prestacion
  - `knowledge-base/05_reglas_de_negocio.md` RN-AG-01, RN-AG-13, RN-PA-03
  - `knowledge-base/06_funcionalidades.md` US-006
  - `knowledge-base/10_preguntas_abiertas.md` PA-09

### [C-09] `horarios-atencion`
- **Estado**: `[ ]` pendiente
- **Scope**: US-007 y regla R3.
  - Modelo `HorarioAtencion` (`consultorio_id`, `profesional_id`, `dia_semana` 0-6, `hora_inicio`, `hora_fin`); constraints `hora_inicio < hora_fin` y no solapamiento de franjas del mismo profesional y día; migración 005
  - Endpoints admin `PUT/GET /api/profesionales/{id}/horarios`
  - Varias franjas por día (mañana/tarde); referencias del mismo consultorio (RN-MT-03)
  - Cambio de franjas con turnos existentes: aún no existen turnos; dejar el gancho documentado para C-15/C-17
  - Decisiones previas al propose: PA-18 (qué hacer con turnos fuera de la nueva franja; puede resolverse ya como "solo avisar"), PA-10 (¿excepciones de horario por fecha?), PA-20 (mecanismo de concurrencia horario/turno, se confirma en C-15)
  - Tests: franjas válidas, inicio ≥ fin, solapadas, aislamiento cruzado
- **Dependencias**: C-07
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §HorarioAtencion
  - `knowledge-base/05_reglas_de_negocio.md` RN-AG-05, RN-AG-06
  - `knowledge-base/06_funcionalidades.md` US-007
  - `knowledge-base/10_preguntas_abiertas.md` PA-18, PA-20

### [C-10] `bloqueos-agenda`
- **Estado**: `[ ]` pendiente
- **Scope**: US-008 y regla R4.
  - Modelo `Bloqueo` (`consultorio_id`, `profesional_id` opcional, `inicio`, `fin`, `tipo` vacaciones|ausencia|feriado|otro, `descripcion` sin datos clínicos); constraint `inicio < fin`; migración 006
  - Endpoints admin `POST/GET/DELETE /api/bloqueos`; sin profesional = todo el consultorio (marcado [PROP] hasta cerrar PA-10)
  - Función de dominio `intersecta_bloqueo(turno, bloqueos)` con tests unitarios
  - Mínimo ante turnos existentes: **informar** los afectados sin cancelar (cuando existan turnos en C-15/C-18 se completa)
  - Feriados cargados manualmente (SU-08)
  - Decisiones previas al propose: PA-10 (bloqueo de consultorio; efecto sobre turnos: rechazar, avisar o cancelar), PA-13 (feriados precargados o manuales), PA-20
  - Tests: período inválido, bloqueo de consultorio vs de profesional, aislamiento cruzado, bordes semiabiertos
- **Dependencias**: C-07
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Bloqueo
  - `knowledge-base/05_reglas_de_negocio.md` RN-AG-07, RN-AG-08, RN-AG-09
  - `knowledge-base/07_flujos_principales.md` Flujo 7
  - `knowledge-base/10_preguntas_abiertas.md` PA-10, PA-13, PA-20

### [C-11] `frontend-configuracion-agenda`
- **Estado**: `[ ]` pendiente
- **Scope**: UI de US-005 a US-008 (las historias se cuentan en C-07 a C-10).
  - `features/configuracion`: ABM de profesionales, prestaciones (duración en minutos), editor de horarios por día con varias franjas, alta de bloqueos
  - Visible solo para administrador; validaciones de formulario duplicadas de las del servidor (el servidor manda)
  - Muestra el aviso de turnos afectados al crear un bloqueo (cuando exista)
  - Decisiones previas al propose: las de C-07 a C-10
  - Tests (Vitest): formularios, validación de franja, visibilidad por rol
- **Dependencias**: C-06, C-07, C-08, C-09, C-10
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujo 2
  - `knowledge-base/06_funcionalidades.md` Épica 2 (US-005 a US-008)
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones (organización por funcionalidad)

---

## FASE 3 — Pacientes y privacidad

> C-12 puede avanzar en paralelo con C-07/C-08 una vez archivado C-04.

### [C-12] `pacientes`
- **Estado**: `[ ]` pendiente
- **Scope**: US-017 y US-019. Manejo de datos personales (Ley 25.326): ficha básica, sin datos clínicos.
  - Modelo `Paciente` (`consultorio_id`, `nombre`, `apellido`, `telefono`, `email` opcional, `contacto_preferido` opcional, `activo`, `creado_en`); migración 007
  - Endpoints `POST/GET/PATCH /api/pacientes`, búsqueda por nombre/apellido/teléfono **solo dentro del consultorio** (RN-MT-04), desactivación (sin borrado físico, RN-PA-06)
  - Roles: administrador y secretaría C/L/M; odontólogo solo lectura de pacientes con turnos propios (se completa en C-19)
  - Sin campos clínicos ni obra social (D3, RN-PA-09); campos no necesarios opcionales (RN-PA-05)
  - Datos de pacientes fuera de logs técnicos; solo datos ficticios en pruebas
  - Decisiones previas al propose: PA-14 (datos mínimos: ¿DNI?, ¿fecha de nacimiento?), PA-15 (texto libre; afecta solo a Turno pero conviene cerrarla acá), PA-16 (supresión/acceso; la desactivación es [PROP])
  - Tests: alta/edición/búsqueda, desactivación conserva turnos, mismo teléfono en dos consultorios = registros independientes, aislamiento cruzado
- **Dependencias**: C-04
- **Governance**: ALTO (datos personales de pacientes; posible dato sensible D9)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Paciente
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio Pacientes y privacidad (RN-PA)
  - `knowledge-base/06_funcionalidades.md` US-017, US-019
  - `knowledge-base/10_preguntas_abiertas.md` PA-14, PA-15, PA-16

### [C-13] `aviso-privacidad`
- **Estado**: `[ ]` pendiente
- **Scope**: US-018. Esencial #8 del informe §6.3 (sin carácter de asesoramiento legal).
  - Modelo `AceptacionPrivacidad` (`consultorio_id`, `paciente_id`, `version_aviso`, `aceptado_en`, `medio` presencial|online); registro **inmutable**; migración 008
  - Endpoints `POST /api/pacientes/{id}/aceptaciones`, `GET .../aceptaciones`; nueva versión del aviso permite nueva aceptación
  - Texto de aviso de ejemplo versionado (seed), configurable por consultorio sin lógica legal propia
  - Comportamiento si el paciente no acepta: [ABIERTA]; no se bloquea la creación de turnos en la v0.1 salvo decisión
  - Decisiones previas al propose: P-06, P-09, P-11 (si hace falta consentimiento expreso o alcanza con informar); forma concreta [PROP]; qué hacer si no acepta
  - Tests: registro versionado, inmutabilidad (sin UPDATE/DELETE), consulta por paciente, aislamiento cruzado
- **Dependencias**: C-12
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §AceptacionPrivacidad
  - `knowledge-base/05_reglas_de_negocio.md` RN-PA-04, RN-PA-05
  - `knowledge-base/06_funcionalidades.md` US-018
  - `knowledge-base/07_flujos_principales.md` Flujo 8
  - `knowledge-base/10_preguntas_abiertas.md` P-06, P-09, P-11

### [C-14] `frontend-pacientes`
- **Estado**: `[ ]` pendiente
- **Scope**: UI de US-017, US-018, US-019 (las historias se cuentan en C-12 y C-13).
  - `features/pacientes`: buscador, alta/edición, desactivación, registro de aceptación del aviso con versión y medio
  - Para secretaría y administrador; no muestra la prestación ni datos clínicos
  - Decisiones previas al propose: las de C-12 y C-13
  - Tests (Vitest): formulario con campos opcionales, búsqueda, visibilidad por rol
- **Dependencias**: C-06, C-12, C-13
- **Governance**: ALTO (maneja datos personales en pantalla)
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujo 8
  - `knowledge-base/06_funcionalidades.md` Épica 5
  - `knowledge-base/05_reglas_de_negocio.md` RN-PA-03, RN-PA-07

---

## FASE 4 — Núcleo de turnos

> **Gate de decisión:** PA-07 debe estar resuelta *antes* del propose de C-15. C-16, C-17, C-18 y C-19 pueden proponerse en cualquier orden tras archivar C-15.

### [C-15] `turnos-crear-sin-superposicion`
- **Estado**: `[ ]` pendiente
- **Scope**: US-011. Núcleo del problema (D1): crear turnos sin superposiciones.
  - Modelo `Turno` (`consultorio_id`, `profesional_id`, `paciente_id`, `prestacion_id`, `inicio`, `fin` calculado con R1, `estado`, `creado_por`, `creado_en`, `actualizado_en`, `actualizado_por`); sin texto libre salvo decisión PA-15
  - Migración 009: tabla `turno`, extensión `btree_gist`, **restricción de exclusión** por `profesional_id` y rango `[inicio, fin)` aplicada solo a los estados que ocupan agenda (RN-AG-02b); referencias del mismo consultorio garantizadas en DB (claves compuestas o equivalente de PA-04)
  - Servicio de dominio `crear_turno`: valida activos y mismo consultorio (RN-MT-03), pasado (RN-TU-06), franja completa (RN-AG-06), bloqueos (RN-AG-08), superposición con mensaje claro; transacción atómica (RN-GL-02); traduce el rechazo de la restricción al mismo error de superposición; rechazos sin datos de otros pacientes (RN-GL-03)
  - `POST /api/turnos` (sin `consultorio_id` en el body); turno nace `reservado` [PROP]
  - Intervalos semiabiertos: consecutivos aceptados
  - Decisiones previas al propose: **PA-07 ANTES de crear la restricción** (estados que ocupan agenda, estado inicial, transiciones; cambiarla luego exige migración), PA-12, PA-19 (alcance de la trazabilidad del turno), PA-20 (mecanismo turno vs bloqueo/horario), PA-15, PA-09; PA-01 sigue abierta: **no se implementan sillones/boxes**
  - Tests: unitarios de dominio (bordes, fuera de franja, bloqueo, inactivos), integración de la restricción contra PostgreSQL real, **concurrencia (dos creaciones simultáneas → exactamente una gana)**, concurrencia turno vs bloqueo según PA-20, aislamiento cruzado, migración sobre datos existentes
- **Dependencias**: C-08, C-09, C-10, C-12
- **Governance**: ALTO. Justificación: núcleo del producto (D1) y garantía de integridad en DB; la migración con la condición de PA-07 es costosa de revertir y la concurrencia admite errores sutiles; no es CRITICO porque no toca autenticación ni la barrera de aislamiento (se apoya en C-04). Exige checkpoint del autor antes de la migración.
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Turno
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio Agenda (RN-AG-01 a 08), §Turnos (RN-TU), §Excepciones globales
  - `knowledge-base/07_flujos_principales.md` Flujo 4
  - `knowledge-base/08_arquitectura_propuesta.md` §Estrategia de pruebas
  - `knowledge-base/10_preguntas_abiertas.md` PA-07, PA-20, PA-19

### [C-16] `disponibilidad`
- **Estado**: `[ ]` pendiente
- **Scope**: US-010. Horarios libres para una prestación, un profesional y un rango de fechas.
  - `GET /api/disponibilidad?profesional_id&prestacion_id&desde&hasta` (el consultorio sale de la identidad)
  - Función de dominio: franjas (R3) − bloqueos (R4) − turnos que ocupan agenda (R2), generando inicios donde la prestación entra completa (RN-AG-11, RN-AG-12)
  - Zona horaria del consultorio (SU-01); prestación/profesional inactivos → sin disponibilidad con motivo
  - Un horario ofrecido puede ocuparse antes de confirmar: la creación (C-15) vuelve a validar
  - Decisiones previas al propose: PA-08 (granularidad: 5/10/15 min, tiempo de preparación), PA-07 (qué estados ocupan agenda; ya resuelta en C-15)
  - Tests: unitarios con varias franjas, bordes, bloqueos parciales; aislamiento cruzado; coherencia con `crear_turno` (todo horario ofrecido es creable)
- **Dependencias**: C-15
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujo 3
  - `knowledge-base/05_reglas_de_negocio.md` RN-AG-06, RN-AG-11, RN-AG-12
  - `knowledge-base/06_funcionalidades.md` US-010
  - `knowledge-base/10_preguntas_abiertas.md` PA-08

### [C-17] `turnos-reprogramar`
- **Estado**: `[ ]` pendiente
- **Scope**: US-012.
  - `PATCH /api/turnos/{id}` para cambiar inicio, profesional o prestación; revalida RN-AG-01 a RN-AG-08 **excluyendo al propio turno**; si falla el turno queda intacto (RN-GL-02)
  - Registra `actualizado_por`/`actualizado_en` (RN-TU-09); historial completo solo si PA-19 lo exige
  - Estado resultante tras reprogramar según PA-07; la restricción de exclusión sigue aplicando
  - Decisiones previas al propose: PA-07 (estado tras reprogramar), PA-12 (anticipación mínima al reprogramar), PA-19
  - Tests: reprogramar a horario libre/ocupado, mismo horario (excluirse a sí mismo), atomicidad ante fallo, concurrencia, aislamiento cruzado
- **Dependencias**: C-15
- **Governance**: ALTO (mantiene la invariante D1 en modificaciones)
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujo 5
  - `knowledge-base/05_reglas_de_negocio.md` RN-TU-02, RN-TU-03, RN-TU-09
  - `knowledge-base/06_funcionalidades.md` US-012
  - `knowledge-base/10_preguntas_abiertas.md` PA-07, PA-12, PA-19

### [C-18] `turnos-cancelar-estados`
- **Estado**: `[ ]` pendiente
- **Scope**: US-013 y US-014.
  - `POST /api/turnos/{id}/cancelar` (estado `cancelado`, `cancelado_en`, libera el horario) y `POST /api/turnos/{id}/estado` para confirmar/atendido/ausente
  - Máquina de estados con las transiciones aprobadas en PA-07; transición inválida → rechazo; reactivar un cancelado (si se aprueba) revalida todas las reglas
  - La anticipación mínima **no** se aplica en este change si PA-12 sigue abierta; se completa en C-22
  - `ausente` deja el dato para medir ausentismo propio, sin promesas (RN-TU-08)
  - Decisiones previas al propose: PA-07 (estados, transiciones, ¿odontólogo marca atendido/ausente?, ¿reutilizar horario de ausente?), PA-12
  - Tests: cada transición válida/ inválida, liberación de horario (nueva creación posible), reactivación con revalidación, roles, aislamiento cruzado
- **Dependencias**: C-15
- **Governance**: ALTO (cambia la condición de ocupación de agenda y afecta la restricción de C-15)
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` RN-TU-03 a RN-TU-08
  - `knowledge-base/07_flujos_principales.md` Flujo 6
  - `knowledge-base/06_funcionalidades.md` US-013, US-014
  - `knowledge-base/10_preguntas_abiertas.md` PA-07, PA-12

### [C-19] `agenda-consulta-api`
- **Estado**: `[ ]` pendiente
- **Scope**: US-015 y US-016 (lecturas de agenda).
  - `GET /api/agenda?fecha|semana&profesional_id` para secretaría y administrador (vista diaria y semanal; cancelados distinguibles u ocultables)
  - `GET /api/mi-agenda?fecha|semana` para odontólogo: solo turnos del profesional vinculado a su usuario (SU-03), solo lectura (RN-TU-07); sin vínculo → agenda vacía con aviso
  - El odontólogo no ve turnos de otros ni pacientes sin turnos suyos; la prestación solo para roles autorizados (RN-PA-03)
  - Completa el rol "odontólogo L pacientes con turnos propios" de C-12
  - Decisiones previas al propose: PA-07 (¿odontólogo marca atendido/ausente?: define si hay escritura), PA-17
  - Tests: filtros por día/semana/profesional, odontólogo solo ve lo suyo, usuario sin profesional, aislamiento cruzado
- **Dependencias**: C-15
- **Governance**: ALTO (alcance por rol sobre datos de pacientes y prestaciones sensibles)
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujo 9
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/06_funcionalidades.md` US-015, US-016
  - `knowledge-base/05_reglas_de_negocio.md` RN-TU-07, RN-PA-03

### [C-20] `frontend-agenda-disponibilidad`
- **Estado**: `[ ]` pendiente
- **Scope**: UI de US-010, US-015, US-016 (las historias se cuentan en C-16 y C-19).
  - `features/agenda`: vista diaria y semanal con filtro por profesional, distinción de cancelados, buscador de horarios libres por prestación/profesional/fecha
  - Vista de solo lectura para odontólogo (`/mi-agenda`)
  - Horarios en zona del consultorio; no se muestran datos de otros pacientes ni la prestación en vistas donde no corresponde
  - Decisiones previas al propose: PA-08 ya resuelta; PA-07 para presentar estados
  - Tests (Vitest): render de agenda, formato de horarios, visibilidad por rol
- **Dependencias**: C-06, C-16, C-19
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujos 3 y 9
  - `knowledge-base/06_funcionalidades.md` US-010, US-015, US-016
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones

### [C-21] `frontend-gestion-turnos`
- **Estado**: `[ ]` pendiente
- **Scope**: UI de US-011, US-012, US-013, US-014 (las historias se cuentan en C-15, C-17, C-18). Cierra la línea de corte.
  - Flujo de alta de turno: paciente (buscar/crear con C-14), prestación, profesional, horario libre (C-20); muestra el motivo de rechazo (superposición, fuera de horario, bloqueo)
  - Reprogramar, cancelar y cambiar estado desde la agenda
  - Maneja el conflicto de concurrencia (horario tomado) pidiendo nueva disponibilidad
  - Decisiones previas al propose: PA-07, PA-12 (mensajes de rechazo vs aviso en cancelación)
  - Tests (Vitest): flujo de creación con éxito y con conflicto, transiciones de estado en UI, ocultamiento por rol; una prueba end-to-end manual documentada de F4
- **Dependencias**: C-14, C-17, C-18, C-20
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujos 4, 5, 6
  - `knowledge-base/06_funcionalidades.md` Épica 3 (US-011 a US-014)
  - `knowledge-base/05_reglas_de_negocio.md` RN-GL-03

---

## FASE 5 — Cierre de la v0.1 (condicionado y demo)

> Ninguno de estos changes pertenece a la línea de corte.

### [C-22] `anticipacion-minima-cancelacion`
- **Estado**: `[ ]` pendiente — **CONDICIONADA: R5 es propuesta del autor, no decisión**
- **Scope**: US-009. No se implementa como definitiva hasta resolver PA-12 (RN-GL-04).
  - `PATCH /api/consultorio/configuracion` (solo administrador): `anticipacion_cancelacion_horas`, default 24, ≥ 0 (campo ya creado en C-02)
  - Aplicación de la anticipación en cancelación/reprogramación (C-17, C-18) según PA-12: ¿solo paciente o también secretaría?, ¿se rechaza o solo se avisa?
  - Decisiones previas al propose: **PA-12** (alcance y rechazo vs aviso). Si no se resuelve, el change no se propone.
  - Tests: valor por defecto, cambio por administrador, rechazo/aviso dentro del plazo, secretaría vs paciente según decisión, aislamiento cruzado
- **Dependencias**: C-18
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` RN-TU-03, RN-GL-04
  - `knowledge-base/06_funcionalidades.md` US-009, US-013
  - `knowledge-base/07_flujos_principales.md` Flujo 6
  - `knowledge-base/10_preguntas_abiertas.md` PA-12

### [C-23] `seed-demo-y-cierre-nucleo`
- **Estado**: `[ ]` pendiente (opcional)
- **Scope**: Pulido de demostración del núcleo; sin historias.
  - Ampliar el seed ficticio según KB 04 §Seed data: profesionales, prestaciones con duraciones distintas, franjas de mañana y tarde, un feriado de consultorio y una ausencia, pacientes (uno sin email), turnos en distintos estados incluidos dos consecutivos, una versión de aviso de privacidad
  - Comando documentado `make seed` o equivalente (idempotente) y guion de demo en el README (login en A y B, intento de acceso cruzado, superposición rechazada, consecutivos aceptados)
  - Prueba de humo end-to-end del flujo F4 sobre el seed
  - Sin datos reales (RN-PA-08)
  - Decisiones previas al propose: ninguna bloqueante
  - Tests: el seed corre dos veces sin duplicar; humo del flujo
- **Dependencias**: C-21
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Seed data inicial
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-13, SU-09
  - `knowledge-base/07_flujos_principales.md` Flujo 4

---

## FASE 6 — Reserva online del paciente (candidata, D4)

> **CANDIDATA, fuera del camino crítico y de la línea de corte.** D4 es propuesta, no decisión. Es la primera candidata a salir del MVP por alcance (RG1, T-02, P-05) aunque el mercado la ofrece (6 de 7 en nivel 1). Requiere decisión explícita del autor (P-05). Solo planificada.

### [C-24] `reserva-online-api-publica`
- **Estado**: `[ ]` candidata (no planificada para desarrollo)
- **Scope**: US-020 (D4, CU5).
  - Modelo: `identificador_publico` único en `Consultorio` (+ `creado_por` "reserva pública" en Turno); migración
  - Endpoints públicos sin autenticación de usuario: `GET /api/publico/{identificador}/catalogo` (solo prestaciones/profesionales ofrecidos), `GET .../disponibilidad`, `POST .../reservas` reutilizando `crear_turno` (mismas validaciones y garantía de concurrencia, RN-RE-01)
  - Anti-enumeración de consultorios y turnos (RN-RE-03), rate limiting, sin datos de otros pacientes, mínima superficie de datos
  - Registro de aceptación del aviso con medio `online` (C-13)
  - Decisiones previas al propose: P-05/T-02 (¿entra en el MVP?), P-03 (paciente con cuenta o invitado), PA-02, PA-14, RG4/D9 (qué se muestra de la prestación)
  - Tests: reserva con y sin conflicto, concurrencia contra reserva de secretaría, enumeración, aislamiento cruzado
- **Dependencias**: C-16, C-13
- **Governance**: CRITICO (superficie pública sin autenticación sobre datos de pacientes y multi-tenant)
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio Reserva online (RN-RE)
  - `knowledge-base/07_flujos_principales.md` Flujo 10
  - `knowledge-base/06_funcionalidades.md` Épica 6
  - `knowledge-base/10_preguntas_abiertas.md` P-03, P-05, T-02
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-04

### [C-25] `reserva-online-consulta-cancelacion`
- **Estado**: `[ ]` candidata
- **Scope**: US-021 y US-022.
  - Identificación del paciente según lo decidido en P-03 (cuenta propia o enlace/token de invitado)
  - `GET .../mis-turnos`, `POST .../turnos/{id}/cancelar` respetando RN-TU-03 (C-22)
  - Decisiones previas al propose: P-03, PA-12, PA-06
  - Tests: el paciente ve solo sus turnos, cancelación dentro/fuera del plazo, enumeración
- **Dependencias**: C-24, C-18, C-22
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` RN-RE-02, RN-RE-04, RN-TU-03
  - `knowledge-base/06_funcionalidades.md` US-021, US-022
  - `knowledge-base/10_preguntas_abiertas.md` P-03, PA-12

### [C-26] `reserva-online-frontend-publico`
- **Estado**: `[ ]` candidata
- **Scope**: UI pública de US-020 a US-022 (las historias se cuentan en C-24 y C-25).
  - Página pública por consultorio: elegir prestación, profesional y horario libre; confirmación; consulta/cancelación; aviso de privacidad
  - Tests (Vitest): flujo de reserva, conflicto de horario, accesibilidad básica
- **Dependencias**: C-24, C-25
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujo 10
  - `knowledge-base/06_funcionalidades.md` Épica 6
  - `knowledge-base/05_reglas_de_negocio.md` RN-RE-01, RN-RE-03

---

## FASE 7 — Comunicación con el paciente (candidata, D5 y D6)

> **CANDIDATA, fuera del camino crítico y de la línea de corte.** Eficacia no demostrada (RG6, CAIS 2016): sin promesas sobre el ausentismo.

### [C-27] `lista-diaria-wa-me`
- **Estado**: `[ ]` candidata
- **Scope**: US-023 (D6, propuesta por validar).
  - `GET /api/comunicacion/lista-diaria?fecha` con los turnos que ocupan agenda del día siguiente y un enlace `wa.me` con mensaje prearmado (fecha, hora, consultorio; **sin la prestación**, RN-PA-03); pacientes sin teléfono válido marcados
  - Sin API de WhatsApp ni envío automático (D7 es posterior); el formato oficial del enlace wa.me está [PEND]
  - Decisiones previas al propose: verificar formato wa.me; P-09/P-11 (consentimiento para recordatorios), RG4
  - Tests: el mensaje nunca incluye la prestación, teléfonos inválidos, aislamiento cruzado
- **Dependencias**: C-19
- **Governance**: ALTO (datos personales hacia un canal externo)
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` Flujo 11
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio Comunicación (RN-CO), RN-PA-03, RN-PA-07
  - `knowledge-base/06_funcionalidades.md` US-023
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-06

### [C-28] `email-aviso-turno`
- **Estado**: `[ ]` candidata
- **Scope**: US-024 (D5, propuesta). En tensión con "sin servicios externos" (IN-06).
  - Integración de proveedor de email transaccional (Resend o Amazon SES verificados; Brevo pendiente) detrás de una interfaz; variables `EMAIL_*`
  - Aviso de turno con enlace para confirmar o cancelar (token firmado de un solo uso); sin prestación en el cuerpo (RN-PA-03)
  - Decisiones previas al propose: IN-06 (aprobar un servicio externo), PA-02, P-07 a P-11 (responsabilidad legal y transferencia), PA-11 (si se reutiliza para recuperar contraseña)
  - Tests: proveedor simulado, token vencido/reutilizado, aislamiento cruzado
- **Dependencias**: C-18
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` RN-CO-01, RN-CO-04, RN-CO-05
  - `knowledge-base/06_funcionalidades.md` US-024
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-05
  - `knowledge-base/10_preguntas_abiertas.md` IN-06

---

## FASE 8 — Trazabilidad de datos (candidata, E8)

> **CANDIDATA, fuera del camino crítico y de la línea de corte.** Sugerencia nueva del informe §6.3, no incluida en D1-D9; no es obligación del MVP sin decisión explícita del autor.

### [C-29] `exportacion-datos-paciente`
- **Estado**: `[ ]` candidata
- **Scope**: US-025.
  - `GET /api/pacientes/{id}/exportacion` (solo administrador): datos de la ficha, aceptaciones y turnos, en JSON/CSV; solo del propio consultorio
  - Decisiones previas al propose: PA-16 (política de acceso/supresión, Ley 25.326 art. 14), PA-14
  - Tests: contenido, solo administrador, aislamiento cruzado
- **Dependencias**: C-15
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 8 (US-025)
  - `knowledge-base/10_preguntas_abiertas.md` PA-16
  - `knowledge-base/05_reglas_de_negocio.md` RN-PA-06

### [C-30] `auditoria-accesos-cambios`
- **Estado**: `[ ]` candidata
- **Scope**: US-026.
  - Modelo de log de auditoría append-only (quién, cuándo, acción, entidad) para turnos (crear/modificar/cancelar) y accesos a datos de pacientes; migración
  - `GET /api/auditoria` (solo administrador, acotado al consultorio); el log no guarda la prestación ni datos clínicos
  - Decisiones previas al propose: PA-19 (último cambio vs historial), PA-16, qué eventos se registran
  - Tests: append-only, eventos generados, aislamiento cruzado, sin datos sensibles en el log
- **Dependencias**: C-18
- **Governance**: CRITICO (audit trail)
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 8 (US-026)
  - `knowledge-base/05_reglas_de_negocio.md` RN-TU-09, RN-PA-03
  - `knowledge-base/10_preguntas_abiertas.md` PA-19, PA-16

---

## FASE 9 — Posteriores y fuera de alcance (no planificado para la v0.1)

> Sin C-NN: **no se planifican ni se proponen para la v0.1**. Se listan para no perderlos (KB 06 Épica 9; informe §6.3).

| Ítem | Origen | Estado |
|---|---|---|
| Recordatorios automáticos por WhatsApp API o SMS | D7 | Posterior; tarifas para Argentina pendientes (P-17, P-18); tensión T-03 |
| Confirmación por respuesta del paciente | Informe §5.4 (vinculada a D7) | Posterior |
| Lista de espera | Discovery §5 | Posterior |
| Seña con Mercado Pago | Discovery §5 | Posterior |
| Sincronización con Google Calendar | Discovery §5 | Posterior |
| Alta definitiva de consultorios (autoservicio o administrador de plataforma) | PA-05, US-004 | Posterior; bloqueada hasta decidir PA-05 |
| Despliegue en la nube | PA-02 | Condicionado a lo que exija la entrega; también abre P-07, P-08, P-10 |
| Sillones/boxes como recurso de agenda | PA-01 | Pregunta abierta; ningún change lo implementa |
| Historia clínica y odontograma | D3 | **Fuera de alcance** (decidido); no se planifica |
| Obras sociales, cobertura, ARCA y facturación | D8 | **Fuera de alcance**; dato de obra social sigue abierto (pregunta 4); no se planifica |


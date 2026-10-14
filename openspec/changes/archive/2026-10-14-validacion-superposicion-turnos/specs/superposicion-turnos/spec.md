# Spec Delta: superposicion-turnos

## Purpose

Impedir, en el dominio, que un turno candidato se superponga con los turnos que ocupan agenda del mismo profesional (RN-AG-02), usando intervalos semiabiertos `[inicio, fin)` (RN-AG-04) e instantes con zona horaria explícita.

Convenciones de los escenarios: datos ficticios (D1); profesionales `PROF-A` y `PROF-B`; fecha 2026-11-02; zona America/Argentina/Buenos_Aires (UTC-03:00); todos los instantes llevan zona horaria explícita salvo que el escenario diga lo contrario. Los "turnos existentes" son los turnos que ocupan agenda, ya seleccionados por quien invoca la validación.

## ADDED Requirements

### Requirement: Aceptación de un turno sin superposición
El sistema DEBE (MUST) aceptar un turno candidato cuando su intervalo `[inicio, fin)` no se interseca con el intervalo de ningún turno existente del mismo profesional. Aceptar significa que la validación termina sin error.

#### Scenario: Exitoso con un turno existente que no se cruza
- **DADO** que `PROF-A` tiene un turno existente de 10:00 a 10:30
- **CUANDO** se valida un candidato de `PROF-A` de 11:00 a 11:30
- **ENTONCES** el candidato se acepta sin error

#### Scenario: Exitoso sin turnos existentes
- **DADO** que `PROF-A` no tiene turnos existentes
- **CUANDO** se valida un candidato de `PROF-A` de 10:00 a 10:30
- **ENTONCES** el candidato se acepta sin error

### Requirement: Rechazo por superposición con el mismo profesional
El sistema DEBE (MUST) rechazar un turno candidato cuyo intervalo se interseca total o parcialmente con el de un turno existente del mismo profesional. El rechazo DEBE (MUST) ser un error de superposición (`SuperposicionError`) cuyo mensaje es exactamente el mensaje fijo "El horario se superpone con otro turno del mismo profesional.", sin identificadores, horarios ni datos del turno en conflicto ni de pacientes (RN-GL-03).

#### Scenario: Superposición parcial por izquierda
- **DADO** que `PROF-A` tiene un turno existente de 10:00 a 10:30
- **CUANDO** se valida un candidato de `PROF-A` de 09:45 a 10:15
- **ENTONCES** se rechaza con `SuperposicionError`
- **Y** el mensaje del error es exactamente el mensaje fijo

#### Scenario: Superposición parcial por derecha
- **DADO** que `PROF-A` tiene un turno existente de 10:00 a 10:30
- **CUANDO** se valida un candidato de `PROF-A` de 10:15 a 10:45
- **ENTONCES** se rechaza con `SuperposicionError`
- **Y** el mensaje del error es exactamente el mensaje fijo

#### Scenario: Candidato contenido en el turno existente
- **DADO** que `PROF-A` tiene un turno existente de 10:00 a 10:30
- **CUANDO** se valida un candidato de `PROF-A` de 10:10 a 10:20
- **ENTONCES** se rechaza con `SuperposicionError`
- **Y** el mensaje del error es exactamente el mensaje fijo

#### Scenario: Candidato que contiene al turno existente
- **DADO** que `PROF-A` tiene un turno existente de 10:00 a 10:30
- **CUANDO** se valida un candidato de `PROF-A` de 09:30 a 10:45
- **ENTONCES** se rechaza con `SuperposicionError`
- **Y** el mensaje del error es exactamente el mensaje fijo

#### Scenario: Candidato idéntico al turno existente
- **DADO** que `PROF-A` tiene un turno existente de 10:00 a 10:30
- **CUANDO** se valida un candidato de `PROF-A` de 10:00 a 10:30
- **ENTONCES** se rechaza con `SuperposicionError`
- **Y** el mensaje del error es exactamente el mensaje fijo

### Requirement: Turnos consecutivos con intervalos semiabiertos
El sistema DEBE (MUST) tratar los intervalos como semiabiertos `[inicio, fin)`: un candidato que empieza exactamente cuando termina un turno existente, o que termina exactamente cuando empieza, no se superpone y se acepta.

#### Scenario: Caso límite consecutivo posterior
- **DADO** que `PROF-A` tiene un turno existente de 10:00 a 10:30
- **CUANDO** se valida un candidato de `PROF-A` de 10:30 a 11:00
- **ENTONCES** el candidato se acepta sin error

#### Scenario: Caso límite consecutivo anterior
- **DADO** que `PROF-A` tiene un turno existente de 10:00 a 10:30
- **CUANDO** se valida un candidato de `PROF-A` de 09:30 a 10:00
- **ENTONCES** el candidato se acepta sin error

### Requirement: Independencia entre profesionales distintos
El sistema DEBE (MUST) considerar solo los turnos existentes del mismo profesional que el candidato; los turnos de otros profesionales recibidos en la entrada se ignoran a efectos de la superposición.

#### Scenario: Turnos simultáneos de profesionales distintos
- **DADO** que `PROF-B` tiene un turno existente de 10:00 a 10:30
- **CUANDO** se valida un candidato de `PROF-A` de 10:00 a 10:30
- **ENTONCES** el candidato se acepta sin error

### Requirement: Validación de los intervalos de entrada
El sistema DEBE (MUST) rechazar con `IntervaloInvalidoError`, distinto de `SuperposicionError`, todo intervalo con `inicio >= fin`, sin zona horaria o con mezcla de instantes con y sin zona. DEBE (MUST) validar el candidato y todos los turnos recibidos, incluidos los de otros profesionales, antes de evaluar la superposición, que solo compara turnos del mismo profesional.

#### Scenario: Intervalo de duración cero
- **DADO** que `PROF-A` no tiene turnos existentes
- **CUANDO** se valida un candidato de `PROF-A` de 10:00 a 10:00
- **ENTONCES** se rechaza con `IntervaloInvalidoError`
- **Y** el error no es `SuperposicionError`

#### Scenario: Fin anterior al inicio
- **DADO** que `PROF-A` no tiene turnos existentes
- **CUANDO** se valida un candidato de `PROF-A` de 10:30 a 10:00
- **ENTONCES** se rechaza con `IntervaloInvalidoError`
- **Y** el error no es `SuperposicionError`

#### Scenario: Instantes sin zona horaria
- **DADO** que `PROF-A` no tiene turnos existentes
- **CUANDO** se valida un candidato de `PROF-A` de 10:00 a 10:30 cuyos dos instantes no tienen zona horaria
- **ENTONCES** se rechaza con `IntervaloInvalidoError`

#### Scenario: Mezcla de instantes con y sin zona horaria en el candidato
- **DADO** que `PROF-A` no tiene turnos existentes
- **CUANDO** se valida un candidato de `PROF-A` cuyo inicio 10:00 tiene zona horaria y cuyo fin 10:30 no la tiene
- **ENTONCES** se rechaza con `IntervaloInvalidoError`

#### Scenario: Turno existente sin zona horaria frente a candidato con zona horaria
- **DADO** que `PROF-A` tiene un turno existente de 08:00 a 08:30 cuyos instantes no tienen zona horaria
- **CUANDO** se valida un candidato de `PROF-A` de 11:00 a 11:30 con zona horaria
- **ENTONCES** se rechaza con `IntervaloInvalidoError`

#### Scenario: Turno existente inválido de otro profesional
- **DADO** que `PROF-B` tiene un turno existente de 10:30 a 10:00
- **CUANDO** se valida un candidato de `PROF-A` de 11:00 a 11:30
- **ENTONCES** se rechaza con `IntervaloInvalidoError`
- **Y** el error no es `SuperposicionError`

#### Scenario: Turno existente con intervalo inválido
- **DADO** que `PROF-A` tiene un turno existente de 10:30 a 10:00
- **CUANDO** se valida un candidato de `PROF-A` de 11:00 a 11:30
- **ENTONCES** se rechaza con `IntervaloInvalidoError`

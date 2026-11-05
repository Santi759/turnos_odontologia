# frontend-base Specification

## Purpose
Disponer de una aplicación de frontend mínima, tipada de forma estricta, que renderiza una pantalla inicial verificable con pruebas automatizadas, como punto de partida de las funcionalidades del MVP.

## Requirements

### Requirement: Pantalla inicial mínima
La aplicación DEBE (MUST) renderizar una pantalla inicial con un encabezado de nivel 1 cuyo texto es exactamente `Turnos Odontología`. La pantalla NO DEBE (MUST NOT) mostrar datos de pacientes, profesionales ni turnos.

#### Scenario: Render del encabezado
- **CUANDO** se renderiza el componente raíz de la aplicación en un DOM de prueba
- **ENTONCES** existe un encabezado de nivel 1 con el texto exacto `Turnos Odontología`

#### Scenario: Un único encabezado principal
- **CUANDO** se renderiza el componente raíz de la aplicación en un DOM de prueba
- **ENTONCES** hay exactamente un encabezado de nivel 1

### Requirement: Tipado estricto
El código del frontend DEBE (MUST) compilar sin errores con el modo estricto de TypeScript activado (`strict: true`) y sin emitir archivos, como parte del comando único de pruebas.

#### Scenario: Verificación de tipos estricta
- **DADO** que la configuración de TypeScript del frontend tiene `strict: true`
- **CUANDO** se ejecuta la verificación de tipos del frontend
- **ENTONCES** termina con código 0

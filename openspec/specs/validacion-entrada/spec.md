# validacion-entrada Specification

## Purpose
Establecer la base común de los esquemas de entrada de la API para que todo esquema de entrada rechace campos no declarados, lo que además impide colar campos de control como `consultorio_id` (S1, D5).

## Requirements

### Requirement: Esquemas de entrada estrictos
Todo esquema de entrada de la API DEBE (MUST) derivar de una base común que rechaza campos no declarados. Un cuerpo con un campo extra DEBE (MUST) fallar la validación; un cuerpo con solo los campos declarados DEBE (MUST) validarse. En C-01 no existe ningún endpoint con cuerpo de entrada: la base se verifica con un esquema de prueba.

#### Scenario: Campo no declarado rechazado
- **DADO** un esquema de prueba derivado de la base común con un único campo `nombre` de tipo texto
- **CUANDO** se valida `{"nombre": "Consultorio Ficticio", "consultorio_id": 1}`
- **ENTONCES** la validación falla
- **Y** el error identifica `consultorio_id` como campo no permitido

#### Scenario: Solo campos declarados
- **DADO** el mismo esquema de prueba
- **CUANDO** se valida `{"nombre": "Consultorio Ficticio"}`
- **ENTONCES** la validación es exitosa y `nombre` vale `Consultorio Ficticio`

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

### Requirement: Consultorio en la query rechazado
Toda petición a la API con un parámetro de query cuyo nombre, sin distinguir mayúsculas, sea `consultorio_id` DEBE (MUST) rechazarse con 422, `Cache-Control: no-store` y un detalle con tipo, ubicación y mensaje, sin reflejar el valor, antes de cualquier otra validación de la ruta y sin ejecutarla. El valor NO DEBE (MUST NOT) usarse para derivar el contexto.

#### Scenario: Query con consultorio_id
- **DADO** una sesión válida de A
- **CUANDO** se hace `GET /api/auth/me?consultorio_id=<id de B>`
- **ENTONCES** la respuesta es 422 con `Cache-Control: no-store`
- **Y** el detalle identifica `consultorio_id` en la query y no contiene el valor enviado

#### Scenario: Variante de mayúsculas
- **CUANDO** se hace `GET /api/health?Consultorio_ID=1`
- **ENTONCES** la respuesta es 422

#### Scenario: Otros parámetros admitidos
- **CUANDO** se hace `GET /api/health?otro=1`
- **ENTONCES** la respuesta es 200

### Requirement: Cabecera X-Consultorio-Id rechazada
Toda petición a la API que incluya la cabecera `X-Consultorio-Id`, sin distinguir mayúsculas, DEBE (MUST) rechazarse con 422, `Cache-Control: no-store` y un detalle con tipo, ubicación y mensaje, sin el valor, antes de ejecutar la ruta. Es la única cabecera rechazada por este requisito: las demás NO DEBEN (MUST NOT) rechazarse por él.

#### Scenario: Cabecera de consultorio
- **DADO** una sesión válida de A
- **CUANDO** se hace `GET /api/auth/me` con `X-Consultorio-Id: <id de B>`
- **ENTONCES** la respuesta es 422 con `Cache-Control: no-store` y el detalle identifica la cabecera sin el valor

#### Scenario: Variantes de mayúsculas de la cabecera
- **CUANDO** se hace `GET /api/health` con `x-consultorio-id: 1` y con `X-CONSULTORIO-ID: 1`
- **ENTONCES** cada respuesta es 422

#### Scenario: Login con consultorio en cabecera
- **CUANDO** se hace un login con credenciales correctas y `X-Consultorio-Id`
- **ENTONCES** la respuesta es 422, no se crea sesión y no se registra intento

### Requirement: Identidad y consultorio solo desde la sesión
Ninguna cabecera, parámetro de query ni cookie distinta de la de sesión DEBE (MUST) usarse como fuente de identidad o de consultorio. Las lecturas de cabeceras, query y cookies del código de la aplicación DEBEN (MUST) limitarse a una lista blanca exacta verificada por una prueba estática, y ninguna fuera del rechazo DEBE (MUST) leer un nombre que contenga `consultorio` o `tenant`.

#### Scenario: Otras cabeceras ignoradas
- **DADO** una sesión válida de A
- **CUANDO** se hace `GET /api/auth/me` con `X-Consultorio`, `Consultorio-Id` o `X-Tenant-Id` con el `id` de B, o con `X-Request-Id: prueba`
- **ENTONCES** cada respuesta es 200 con la identidad y el consultorio de A

#### Scenario: Lecturas de la petición en lista blanca
- **CUANDO** se buscan en el código de la aplicación (excluidas las pruebas) los accesos a cabeceras, parámetros de query y cookies de la petición
- **ENTONCES** coinciden exactamente con la lista blanca y ninguno, salvo el rechazo, lee un nombre que contenga `consultorio` o `tenant`

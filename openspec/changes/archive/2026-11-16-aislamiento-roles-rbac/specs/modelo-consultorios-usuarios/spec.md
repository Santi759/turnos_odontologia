# Spec Delta: modelo-consultorios-usuarios

## MODIFIED Requirements

### Requirement: Usuario sin credencial utilizable
La base DEBE (MUST) permitir un usuario **sin credencial**, con `credencial` nula, y DEBE (MUST) rechazar una credencial vacía. Una credencial no nula DEBE (MUST) ser un hash de contraseña, nunca texto plano; solo la escribe el comando local de credenciales; ningún rol de la API la modifica (C-04). La base NO DEBE (MUST NOT) restringir el prefijo del hash con un `CHECK`: los formatos los valida la aplicación (DA-08). Un usuario sin credencial DEBE (MUST) tratarse como imposible de autenticar.

#### Scenario: Usuario sin credencial aceptado
- **DADO** un consultorio existente
- **CUANDO** se inserta un usuario sin `credencial`
- **ENTONCES** la inserción es exitosa y `credencial` es nula

#### Scenario: Credencial vacía rechazada
- **CUANDO** se inserta un usuario con `credencial = ''`
- **ENTONCES** la inserción falla por violación de una restricción `CHECK`

#### Scenario: Sin restricción de prefijo en la base
- **CUANDO** se listan las restricciones `CHECK` de `usuario` en el catálogo
- **ENTONCES** ninguna menciona `argon2`

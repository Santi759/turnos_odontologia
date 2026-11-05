# Spec Delta: salud-api

## Purpose

Exponer un endpoint de liveness que indique que el proceso de la API está vivo y atiende peticiones, sin depender de la base de datos ni revelar detalles internos.

## ADDED Requirements

### Requirement: Liveness de la API independiente de la base de datos
El sistema DEBE (MUST) responder `GET /api/health` con estado HTTP 200 y cuerpo JSON exactamente igual a `{"status": "ok"}`, sin abrir conexiones a la base de datos. La respuesta DEBE (MUST) ser la misma esté o no disponible PostgreSQL, y NO DEBE (MUST NOT) incluir versiones, entorno, variables de configuración ni datos personales.

#### Scenario: Health responde ok
- **DADO** que la API está configurada con una `DATABASE_URL` válida
- **CUANDO** se hace `GET /api/health`
- **ENTONCES** la respuesta tiene estado 200
- **Y** el cuerpo es exactamente `{"status": "ok"}`

#### Scenario: Health responde ok con la base inaccesible
- **DADO** que la API está configurada con una `DATABASE_URL` que apunta a un host inexistente (`host-inexistente.invalid`)
- **CUANDO** se hace `GET /api/health`
- **ENTONCES** la respuesta tiene estado 200
- **Y** el cuerpo es exactamente `{"status": "ok"}`
- **Y** no se intentó ninguna conexión a la base de datos

### Requirement: Rutas inexistentes bajo el prefijo de la API
El sistema DEBE (MUST) responder con estado 404 a una ruta no declarada bajo `/api/`, de modo que el health no actúe como comodín de otras rutas.

#### Scenario: Ruta no declarada
- **CUANDO** se hace `GET /api/no-existe`
- **ENTONCES** la respuesta tiene estado 404

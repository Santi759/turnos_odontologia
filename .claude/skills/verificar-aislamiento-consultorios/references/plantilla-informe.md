# Plantilla del informe

Copia esta estructura sin agregar ni quitar secciones. Reemplaza lo que esta entre `<...>`. Escribi en espanol, con rutas relativas al repositorio y sin secretos (ver "Limites" en `SKILL.md`).

```markdown
# Verificacion de aislamiento entre consultorios: <alcance>

> Revision generada con la skill `verificar-aislamiento-consultorios`. <Si el alcance es un Change archivado:> Es una revision nueva, posterior al Archive; no forma parte del Change archivado ni modifica su evidencia.

## Identificacion

| Campo | Valor |
|---|---|
| Fecha | <AAAA-MM-DD> |
| Commit revisado | <hash completo de `git rev-parse HEAD`> |
| Rama | <rama> |
| Cambios sin confirmar | <ninguno / lista de rutas> |
| Alcance | <repositorio / ruta del Change> |
| Modo | <estatico / pruebas / catalogo> |
| Autorizaciones | <ninguna adicional / quien autorizo que y cuando> |

## Resultado por control

| ID | Control | Estado | Origen | Evidencia |
|---|---|---|---|---|
| V-01 | Cobertura de escenarios | <Cumple / No cumple / No evidenciado / No evaluado> | <Verificado ahora / Citado del historial> | <comando y resultado resumido, o `ruta:linea`> |
| V-02 | Referencias de la matriz existen | | | |
| V-03 | RLS habilitada y forzada | | | |
| V-04 | Politicas cerradas y contexto transaccional | | | |
| V-05 | Funciones SECURITY DEFINER | | | |
| V-06 | Atributos y pertenencia de roles | | | |
| V-07 | Privilegios minimos | | | |
| V-08 | El consultorio no viene del cliente | | | |
| V-09 | Credenciales e identidad de la conexion | | | |
| V-10 | Acceso cruzado por endpoint privado | | | |

## Hallazgos

<Por cada `No cumple`: ID, severidad (Alta / Media / Baja), descripcion, escenario concreto de falla y evidencia. Si no hay: "Sin hallazgos".>

## Comandos ejecutados

<Lista numerada de los comandos de solo lectura, en el orden en que se ejecutaron, para que otra persona los repita.>

## Limitaciones

<Que no se verifico y por que: modo usado, ejecuciones no autorizadas, decisiones abiertas, diferencias con el historial.>

## Veredicto

**<GO / NO-GO>.** <Dos o tres oraciones que lo justifican.>
```

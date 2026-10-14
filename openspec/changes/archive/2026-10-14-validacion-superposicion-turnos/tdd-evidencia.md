# Evidencia TDD (RED / GREEN) — `validacion-superposicion-turnos`

> Resumen de la evidencia de Apply. Se basa **solo** en las salidas reales del registro de trabajo `tdd-evidencia.log`, escrito durante Apply el 2026-10-13 y conservado fuera del repositorio.
>
> - Los extractos son textuales. Se omitieron las líneas de traza intermedias, y la ruta local del repositorio se reemplazó por `<repo>`.
> - El registro no tiene marca de hora por corrida; la última escritura del archivo fue el 2026-10-13 a las 23:22 (UTC-03:00).
> - Todas las corridas se ejecutaron desde `backend/` con `.venv/Scripts/python -m pytest -q`, salvo que se indique `-v`.
> - Datos ficticios únicamente (D1).

## 1. Resumen por tarea

| Tarea | Tipo | Resultado registrado | Código de salida |
|---|---|---|---|
| 1.5 | Configuración (sin pruebas) | `no tests ran in 0.01s` | 5 (esperado) |
| 2.1 | RED | `ModuleNotFoundError: No module named 'app.domain.superposicion_turnos'`, `1 error in 0.18s` | 2 |
| 2.2 | GREEN | `1 passed in 0.01s` | 0 |
| 3.1 | Triangulación (pasó sin fallar antes) | `2 passed in 0.02s` | 0 |
| 4.1 | RED | `DID NOT RAISE SuperposicionError` en los 5 casos, `5 failed, 2 passed in 0.11s` | 1 |
| 4.2 | GREEN | `7 passed in 0.03s` | 0 |
| 4.3 | Triangulación (literal del mensaje) | `9 passed in 0.04s` | 0 |
| 5.1 | Triangulación (pasó sin fallar antes) | `9 passed in 0.02s` | 0 |
| 6.1 | RED | `SuperposicionError` falsa entre PROF-A y PROF-B, `1 failed, 9 passed in 0.09s` | 1 |
| 6.2 | GREEN | `10 passed in 0.03s` | 0 |
| 6.3 | Triangulación (pasó sin fallar antes) | `11 passed in 0.03s` | 0 |
| 7.1 | RED | `DID NOT RAISE IntervaloInvalidoError` (2 casos), `2 failed, 11 passed in 0.11s` | 1 |
| 7.2 | GREEN | `13 passed in 0.03s` | 0 |
| 7.3 | RED | `DID NOT RAISE IntervaloInvalidoError` y `TypeError: can't compare offset-naive and offset-aware datetimes`, `2 failed, 13 passed in 0.10s` | 1 |
| 7.4 | GREEN | `15 passed in 0.04s` | 0 |
| 7.5 | RED | `TypeError` (naive/aware) y `DID NOT RAISE IntervaloInvalidoError`, `2 failed, 15 passed in 0.10s` | 1 |
| 7.6 | GREEN | `17 passed in 0.04s` | 0 |
| 7.7 + 7.8 | Primera corrida: pasaron sin fallar antes | `19 passed in 0.04s` (`-v`) | 0 |
| 7.7 | RED por mutación temporal | `DID NOT RAISE IntervaloInvalidoError`, `1 failed, 18 passed in 0.09s` | 1 |
| 7.7 | GREEN (código restaurado) | `19 passed in 0.03s` | 0 |
| 8.1 | REFACTOR | `19 passed in 0.03s` (`-q` y `-v`) | 0 |

**Pruebas que fallaron antes de implementar (RED genuino):** 2.1, 4.1, 6.1, 7.1, 7.3 y 7.5, que suman 13 pruebas (1 + 5 + 1 + 2 + 2 + 2). Cada una pasó en su GREEN siguiente (2.2, 4.2, 6.2, 7.2, 7.4 y 7.6).

## 2. Ejemplos de falla antes de implementar y prueba pasando después

### 2.1 → 2.2: el módulo todavía no existía

```
=== 2.1 RED ===
tests\unit\test_superposicion_turnos.py:10: in <module>
    from app.domain.superposicion_turnos import (
E   ModuleNotFoundError: No module named 'app.domain.superposicion_turnos'
ERROR tests/unit/test_superposicion_turnos.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.18s
exit code: 2

=== 2.2 GREEN ===
.                                                                        [100%]
1 passed in 0.01s
exit code: 0
```

### 4.1 → 4.2: el rechazo por superposición todavía no existía

```
=== 4.1 RED ===
..FFFFF                                                                  [100%]
>       with pytest.raises(SuperposicionError) as info:
E       Failed: DID NOT RAISE SuperposicionError
FAILED tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[parcial_izquierda]
FAILED tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[parcial_derecha]
FAILED tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[contenido]
FAILED tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[contenedor]
FAILED tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[identico]
5 failed, 2 passed in 0.11s
exit code: 1

=== 4.2 GREEN ===
.......                                                                  [100%]
7 passed in 0.03s
exit code: 0
```

### 6.1 → 6.2: el código todavía no filtraba por profesional

En el RED, la implementación de ese momento rechazaba un turno simultáneo de otro profesional:

```
=== 6.1 RED ===
.........F                                                               [100%]
        for existente in turnos_que_ocupan_agenda:
            if candidato.inicio < existente.fin and existente.inicio < candidato.fin:
>               raise SuperposicionError(MENSAJE_SUPERPOSICION)
E               app.domain.superposicion_turnos.SuperposicionError: El horario se superpone con otro turno del mismo profesional.
FAILED tests/unit/test_superposicion_turnos.py::test_turnos_simultaneos_de_profesionales_distintos_se_aceptan
1 failed, 9 passed in 0.09s
exit code: 1

=== 6.2 GREEN ===
..........                                                               [100%]
10 passed in 0.03s
exit code: 0
```

### 7.1 → 7.2: no se validaba `inicio >= fin`

```
=== 7.1 RED ===
...........FF                                                            [100%]
E       Failed: DID NOT RAISE IntervaloInvalidoError
FAILED tests/unit/test_superposicion_turnos.py::test_candidato_con_intervalo_no_positivo_es_invalido[duracion_cero]
FAILED tests/unit/test_superposicion_turnos.py::test_candidato_con_intervalo_no_positivo_es_invalido[fin_anterior_al_inicio]
2 failed, 11 passed in 0.11s
exit code: 1

=== 7.2 GREEN ===
.............                                                            [100%]
13 passed in 0.03s
exit code: 0
```

### 7.3 → 7.4: no se validaba la zona horaria del candidato

Con ambos instantes sin zona horaria no se lanzaba el error. Con la mezcla, Python lanzaba un `TypeError` en lugar del error de dominio:

```
=== 7.3 RED ===
.............FF                                                          [100%]
E       Failed: DID NOT RAISE IntervaloInvalidoError
>       if candidato.inicio >= candidato.fin:
E       TypeError: can't compare offset-naive and offset-aware datetimes
FAILED tests/unit/test_superposicion_turnos.py::test_candidato_sin_zona_horaria_es_invalido[instantes_sin_zona_horaria]
FAILED tests/unit/test_superposicion_turnos.py::test_candidato_sin_zona_horaria_es_invalido[mezcla_con_y_sin_zona_horaria]
2 failed, 13 passed in 0.10s
exit code: 1

=== 7.4 GREEN ===
...............                                                          [100%]
15 passed in 0.04s
exit code: 0
```

### 7.5 → 7.6: no se validaban los turnos existentes

```
=== 7.5 RED ===
...............FF                                                        [100%]
>           if candidato.inicio < existente.fin and existente.inicio < candidato.fin:
E           TypeError: can't compare offset-naive and offset-aware datetimes
E       Failed: DID NOT RAISE IntervaloInvalidoError
FAILED tests/unit/test_superposicion_turnos.py::test_turno_existente_sin_zona_horaria_es_invalido
FAILED tests/unit/test_superposicion_turnos.py::test_turno_existente_con_intervalo_invalido_es_invalido
2 failed, 15 passed in 0.10s
exit code: 1

=== 7.6 GREEN ===
.................                                                        [100%]
17 passed in 0.04s
exit code: 0
```

## 3. Pruebas de triangulación (pasaron sin fallar antes)

Agregan un segundo caso con datos distintos sobre un comportamiento ya implementado. El registro muestra que pasaron en su primera corrida. **No tuvieron un RED propio.**

| Tarea | Prueba | Por qué pasó de entrada (según la etiqueta del registro y el código) |
|---|---|---|
| 3.1 | `test_exitoso_con_un_turno_existente_que_no_se_cruza` | La implementación mínima de 2.2 ya aceptaba el caso ("pasa con implementacion minima") |
| 4.3 | Comparación con el texto literal del mensaje, dentro de la prueba de 4.1 | El mensaje fijo ya existía desde 4.2 |
| 5.1 | `test_turnos_consecutivos_se_aceptan[consecutivo_posterior]` y `[consecutivo_anterior]` | El predicado de 4.2 ya usaba `<` estricto ("pasan: predicado estricto '<'") |
| 6.3 | `test_rechazo_con_turno_de_otro_profesional_en_la_entrada` | El filtro por profesional de 6.2 ya no descartaba los turnos del mismo profesional |
| 7.8 | `test_candidato_invalido_tiene_precedencia_sobre_la_superposicion` | La validación previa de todos los intervalos ya estaba implementada en 7.6 |

Las corridas de 4.3 y 5.1 terminan las dos con `9 passed`. El registro no permite separarlas: el paso de 7 a 9 pruebas corresponde a los dos casos consecutivos de 5.1, que ya estaban presentes en la corrida etiquetada 4.3.

## 4. Prueba que requirió una mutación temporal del código (7.7)

La prueba del escenario "Turno existente inválido de otro profesional" pasó en su primera corrida, porque la validación de todos los turnos ya estaba implementada desde 7.6:

```
=== 7.7 RED/GREEN + 7.8 TRIANGULATE (pasan: validacion previa a todos los turnos ya implementada en 7.6) ===
tests/unit/test_superposicion_turnos.py::test_turno_existente_invalido_de_otro_profesional_es_invalido PASSED [ 94%]
tests/unit/test_superposicion_turnos.py::test_candidato_invalido_tiene_precedencia_sobre_la_superposicion PASSED [100%]
============================= 19 passed in 0.04s ==============================
exit code: 0
```

Para demostrar que la prueba detecta el defecto que protege, se cambió el código temporalmente para que validara solo los turnos del mismo profesional. La prueba falló y las otras 18 siguieron pasando. Después se restauró el código:

```
=== 7.7 RED (mutacion temporal: validar solo turnos del mismo profesional) + 7.8 ===
.................F.                                                      [100%]
>       with pytest.raises(IntervaloInvalidoError) as info:
E       Failed: DID NOT RAISE IntervaloInvalidoError
FAILED tests/unit/test_superposicion_turnos.py::test_turno_existente_invalido_de_otro_profesional_es_invalido
1 failed, 18 passed in 0.09s
exit code: 1

=== 7.7 GREEN (codigo restaurado) ===
...................                                                      [100%]
19 passed in 0.03s
exit code: 0
```

El registro describe la mutación, pero **no guarda el código mutado**, así que no se reproduce aquí. Es la única prueba que se verificó con una mutación.

## 5. Refactorización (8.1)

El paso consistió en extraer funciones auxiliares privadas y materializar la lista de turnos una sola vez, sin cambiar el comportamiento:

```
=== 8.1 REFACTOR (helpers privados, lista materializada una vez) ===
...................                                                      [100%]
19 passed in 0.03s
exit code: 0
```

La corrida de Verify del 2026-10-14 confirma el mismo resultado: `19 passed in 0.03s` (ver `verify.md`).

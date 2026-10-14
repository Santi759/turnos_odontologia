# Verify — `validacion-superposicion-turnos`

> Evidencia de Verify según la regla O2 de `AGENTS.md` y la estructura de DIS-13 (`design.md`).
> Ejecutado el 2026-10-14 (01:02, UTC-03:00), con autorización del autor. Datos ficticios únicamente (D1).
> En las salidas, la ruta local del repositorio se reemplazó por `<repo>`; el resto es textual.

## 1. Entorno

| Elemento | Valor | Evidencia |
|---|---|---|
| Sistema operativo | Windows 11 Home Single Language 10.0.26200 (`platform win32`) | Encabezado de pytest |
| Python | 3.14.5 | `backend/.venv/Scripts/python --version` → `Python 3.14.5` |
| pip | 26.1.1 | `python -m pip --version` → `pip 26.1.1 from <repo>\backend\.venv\Lib\site-packages\pip (python 3.14)` |
| pytest | 9.1.1 (fijado en `backend/requirements-dev.txt`) | `python -m pytest --version` → `pytest 9.1.1` |
| Compatibilidad pytest / Python 3.14 | Declarada y comprobada | `pip show -v pytest` incluye el clasificador `Programming Language :: Python :: 3.14`; las 19 pruebas corren con Python 3.14.5 |
| OpenSpec CLI | 1.14.1 | `openspec --version` → `1.14.1` |
| Entorno virtual | `backend/.venv`, ignorado por Git | `git check-ignore -v backend/.venv` → `.gitignore:11:.venv/` |

Paquetes del venv (`pip freeze`): `colorama==0.4.6`, `iniconfig==2.3.1`, `packaging==26.3`, `pluggy==1.6.0`, `Pygments==2.21.0`, `pytest==9.1.1`. Son pytest y sus dependencias; no se instaló nada más.

No se usan Docker ni PostgreSQL: el módulo es dominio puro sin I/O (X2).

## 2. Comandos ejecutados y resultados

### 2.1 Validación estricta de OpenSpec (tarea 9.1)

Desde la raíz del repositorio:

```
$ openspec validate validacion-superposicion-turnos --strict
Change 'validacion-superposicion-turnos' is valid
```

Código de salida: **0**.

### 2.2 Pruebas automatizadas (tarea 9.2)

Desde `backend/`, con el intérprete del venv:

```
$ .venv/Scripts/python -m pytest -v
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0 -- <repo>\backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: <repo>\backend
configfile: pyproject.toml
testpaths: tests
collecting ... collected 19 items

tests/unit/test_superposicion_turnos.py::test_exitoso_sin_turnos_existentes PASSED [  5%]
tests/unit/test_superposicion_turnos.py::test_exitoso_con_un_turno_existente_que_no_se_cruza PASSED [ 10%]
tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[parcial_izquierda] PASSED [ 15%]
tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[parcial_derecha] PASSED [ 21%]
tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[contenido] PASSED [ 26%]
tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[contenedor] PASSED [ 31%]
tests/unit/test_superposicion_turnos.py::test_rechazo_por_superposicion_con_el_mismo_profesional[identico] PASSED [ 36%]
tests/unit/test_superposicion_turnos.py::test_turnos_consecutivos_se_aceptan[consecutivo_posterior] PASSED [ 42%]
tests/unit/test_superposicion_turnos.py::test_turnos_consecutivos_se_aceptan[consecutivo_anterior] PASSED [ 47%]
tests/unit/test_superposicion_turnos.py::test_turnos_simultaneos_de_profesionales_distintos_se_aceptan PASSED [ 52%]
tests/unit/test_superposicion_turnos.py::test_rechazo_con_turno_de_otro_profesional_en_la_entrada PASSED [ 57%]
tests/unit/test_superposicion_turnos.py::test_candidato_con_intervalo_no_positivo_es_invalido[duracion_cero] PASSED [ 63%]
tests/unit/test_superposicion_turnos.py::test_candidato_con_intervalo_no_positivo_es_invalido[fin_anterior_al_inicio] PASSED [ 68%]
tests/unit/test_superposicion_turnos.py::test_candidato_sin_zona_horaria_es_invalido[instantes_sin_zona_horaria] PASSED [ 73%]
tests/unit/test_superposicion_turnos.py::test_candidato_sin_zona_horaria_es_invalido[mezcla_con_y_sin_zona_horaria] PASSED [ 78%]
tests/unit/test_superposicion_turnos.py::test_turno_existente_sin_zona_horaria_es_invalido PASSED [ 84%]
tests/unit/test_superposicion_turnos.py::test_turno_existente_con_intervalo_invalido_es_invalido PASSED [ 89%]
tests/unit/test_superposicion_turnos.py::test_turno_existente_invalido_de_otro_profesional_es_invalido PASSED [ 94%]
tests/unit/test_superposicion_turnos.py::test_candidato_invalido_tiene_precedencia_sobre_la_superposicion PASSED [100%]

============================= 19 passed in 0.03s ==============================
```

Código de salida: **0**. 19 aprobadas, 0 fallidas, 0 omitidas, 0 errores.

### 2.3 `CHANGES.md` sin modificar (tarea 9.5)

```
$ git diff --quiet -- CHANGES.md && echo "CHANGES.md sin cambios"
CHANGES.md sin cambios
```

`git status --short` no lista `CHANGES.md`. En `CHANGES.md`, C-01 `foundation-setup` y C-15 `turnos-crear-sin-superposicion` siguen con **Estado: `[ ]` pendiente**.

## 3. Trazabilidad escenario → prueba (tarea 9.3)

Archivo de pruebas: `backend/tests/unit/test_superposicion_turnos.py` (abreviado `T`). Se comparó el texto de cada escenario de `specs/superposicion-turnos/spec.md` con los datos de su prueba: profesional, horarios, error esperado y mensaje.

| # | Requisito | Escenario | Prueba (`T::prueba[id]`) | Resultado |
|---|---|---|---|---|
| 1 | Aceptación de un turno sin superposición | Exitoso con un turno existente que no se cruza | `test_exitoso_con_un_turno_existente_que_no_se_cruza` | PASSED |
| 2 | Aceptación de un turno sin superposición | Exitoso sin turnos existentes | `test_exitoso_sin_turnos_existentes` | PASSED |
| 3 | Rechazo por superposición con el mismo profesional | Superposición parcial por izquierda | `test_rechazo_por_superposicion_con_el_mismo_profesional[parcial_izquierda]` | PASSED |
| 4 | Rechazo por superposición con el mismo profesional | Superposición parcial por derecha | `test_rechazo_por_superposicion_con_el_mismo_profesional[parcial_derecha]` | PASSED |
| 5 | Rechazo por superposición con el mismo profesional | Candidato contenido en el turno existente | `test_rechazo_por_superposicion_con_el_mismo_profesional[contenido]` | PASSED |
| 6 | Rechazo por superposición con el mismo profesional | Candidato que contiene al turno existente | `test_rechazo_por_superposicion_con_el_mismo_profesional[contenedor]` | PASSED |
| 7 | Rechazo por superposición con el mismo profesional | Candidato idéntico al turno existente | `test_rechazo_por_superposicion_con_el_mismo_profesional[identico]` | PASSED |
| 8 | Turnos consecutivos con intervalos semiabiertos | Caso límite consecutivo posterior | `test_turnos_consecutivos_se_aceptan[consecutivo_posterior]` | PASSED |
| 9 | Turnos consecutivos con intervalos semiabiertos | Caso límite consecutivo anterior | `test_turnos_consecutivos_se_aceptan[consecutivo_anterior]` | PASSED |
| 10 | Independencia entre profesionales distintos | Turnos simultáneos de profesionales distintos | `test_turnos_simultaneos_de_profesionales_distintos_se_aceptan` | PASSED |
| 11 | Validación de los intervalos de entrada | Intervalo de duración cero | `test_candidato_con_intervalo_no_positivo_es_invalido[duracion_cero]` | PASSED |
| 12 | Validación de los intervalos de entrada | Fin anterior al inicio | `test_candidato_con_intervalo_no_positivo_es_invalido[fin_anterior_al_inicio]` | PASSED |
| 13 | Validación de los intervalos de entrada | Instantes sin zona horaria | `test_candidato_sin_zona_horaria_es_invalido[instantes_sin_zona_horaria]` | PASSED |
| 14 | Validación de los intervalos de entrada | Mezcla de instantes con y sin zona horaria en el candidato | `test_candidato_sin_zona_horaria_es_invalido[mezcla_con_y_sin_zona_horaria]` | PASSED |
| 15 | Validación de los intervalos de entrada | Turno existente sin zona horaria frente a candidato con zona horaria | `test_turno_existente_sin_zona_horaria_es_invalido` | PASSED |
| 16 | Validación de los intervalos de entrada | Turno existente inválido de otro profesional | `test_turno_existente_invalido_de_otro_profesional_es_invalido` | PASSED |
| 17 | Validación de los intervalos de entrada | Turno existente con intervalo inválido | `test_turno_existente_con_intervalo_invalido_es_invalido` | PASSED |

**Cobertura: 17 de 17 escenarios con prueba automatizada; ninguno sin cubrir.**

Pruebas adicionales, que no corresponden a un escenario propio y triangulan reglas de los requisitos:

| Prueba | Qué refuerza | Tarea |
|---|---|---|
| `test_rechazo_con_turno_de_otro_profesional_en_la_entrada` | Con turnos de PROF-A y PROF-B en la entrada, la superposición con PROF-A se rechaza igual (requisitos de rechazo e independencia) | 6.3 |
| `test_candidato_invalido_tiene_precedencia_sobre_la_superposicion` | La validación ocurre antes de evaluar la superposición: un candidato inválido que además se solaparía produce `IntervaloInvalidoError` (DIS-03) | 7.8 |

Total: 17 + 2 = 19 pruebas, igual a las recolectadas por pytest.

### Observaciones sobre las pruebas

- En los escenarios de aceptación se verifica `validar_sin_superposicion(...) is None`. Lo que realmente demuestra la aceptación es que no se lanza ningún error, porque la función siempre devuelve `None`.
- La comprobación "el error no es `SuperposicionError`" (escenarios 11, 12 y 16) no puede fallar con el código actual, porque las dos clases no están relacionadas por herencia. Se mantiene porque reproduce literalmente el escenario y protege ante un cambio futuro de jerarquía.
- La evidencia RED/GREEN de Apply está en [`tdd-evidencia.md`](tdd-evidencia.md). Es un resumen con extractos textuales del registro de trabajo de Apply (2026-10-13), que queda fuera del repositorio. En resumen:
  - 13 pruebas fallaron antes de implementar y pasaron después.
  - Las tareas 3.1, 4.3, 5.1, 6.3 y 7.8 son triangulaciones que pasaron sin fallar antes.
  - En la 7.7, el defecto se mostró con una mutación temporal del código que luego se revirtió.

## 4. Conclusión

| Condición de O2 | Estado |
|---|---|
| `openspec validate validacion-superposicion-turnos --strict` sin errores | Cumple (código 0, "is valid") |
| pytest exitoso | Cumple (19 aprobadas, código 0) |
| Todos los escenarios de la spec cubiertos por pruebas automatizadas | Cumple (17/17) |
| Comandos, resultados y evidencia registrados en el Change | Cumple (este archivo) |

**Verify: APROBADO.** El Change queda en condiciones de archivarse. Archive requiere la autorización del autor y **no** marca C-15 ni C-01 en `CHANGES.md`.

## 5. Limitaciones vigentes

Este Change académico demuestra la regla RN-AG-02 (R2) en el dominio. **No garantiza por sí solo la ausencia de superposiciones en el sistema (RT9).**

- **Sin persistencia ni restricción de base:** no hay modelo `Turno`, migración ni restricción de exclusión de PostgreSQL (`btree_gist`). Siguen pendientes en C-15.
- **Concurrencia (RN-AG-03, PA-20):** dos creaciones simultáneas podrían pasar ambas la validación previa. La garantía final será la restricción de base de C-15, con una prueba de concurrencia real contra PostgreSQL.
- **Estados que ocupan agenda (PA-07, abierta):** la función no conoce estados. Recibe los turnos ya seleccionados por quien la llama y no se inventan estados.
- **Sillones y boxes (PA-01, abierta):** el control es solo por profesional. Dos profesionales distintos en el mismo horario se aceptan (escenario 10), aunque compartan sillón.
- **Fuera de alcance:** endpoints, autenticación, aislamiento multi-consultorio, datos de pacientes, cálculo del fin por prestación (C-08) e interfaz gráfica.
- **C-15 `turnos-crear-sin-superposicion` sigue pendiente**: este recorte no lo completa.
- **C-01 `foundation-setup` sigue pendiente**: el venv con pytest y la estructura mínima de `backend/` son una preparación del recorte, no la base técnica de C-01 (Docker Compose, PostgreSQL, FastAPI, frontend, Vitest, README).

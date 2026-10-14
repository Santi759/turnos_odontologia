# Tareas: validacion-superposicion-turnos

> Referencias: requisitos y escenarios en `specs/superposicion-turnos/spec.md`; decisiones en `design.md` (DIS-01 a DIS-13).
> TDD estricto por comportamiento: RED (prueba que falla, ejecutada) → GREEN (código mínimo, ejecutado) → TRIANGULATE (segundo caso con datos distintos) → REFACTOR (pruebas en verde tras cada paso).
> Todos los comandos de pytest se ejecutan desde `backend/` con el venv activo: `python -m pytest -v`.
> Datos ficticios únicamente (D1): `PROF-A`, `PROF-B`, 2026-11-02, UTC-03:00.

## 1. Entorno mínimo (requiere autorización del autor en Apply)

- [x] 1.1 Pedir y obtener la autorización explícita del autor para crear el venv e instalar pytest; verificar: autorización registrada en la conversación de Apply antes de ejecutar 1.3. (autorizado por el autor el 2026-10-13)
- [x] 1.2 Crear solo `backend/app/__init__.py`, `backend/app/domain/__init__.py` y `backend/tests/unit/` (DIS-10), sin `main.py`, `api/`, `models/`, `alembic/`, Docker ni frontend; verificar con un listado de `backend/` que no hay otros archivos.
- [x] 1.3 Crear el venv con `python -m venv backend/.venv` e instalar pytest con `pip install pytest`; verificar que `git status --short` no muestra `backend/.venv` (ignorado por `.gitignore`).
- [x] 1.4 Confirmar que la versión de pytest instalada declara soporte para Python 3.14 (clasificadores con `pip show -v pytest` o notas de versión) y que `python -m pytest --version` funciona con Python 3.14.5; si no, detenerse y consultar al autor.
- [x] 1.5 Crear `backend/requirements-dev.txt` con `pytest==<versión instalada>` y `backend/pyproject.toml` solo con `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`) según DIS-11; verificar que `python -m pytest` desde `backend/` termina con "no tests ran" (código 5) sin errores de configuración.
- [x] 1.6 Anotar versiones de Python, pip y pytest y la evidencia de 1.4 para volcarlas luego en `verify.md` (sección Entorno).

## 2. Tipos públicos y errores

- [x] 2.1 RED: escribir en `backend/tests/unit/test_superposicion_turnos.py` el auxiliar de instantes (UTC-03:00 fijo, DIS-12) y la primera prueba del escenario "Exitoso sin turnos existentes" que importa `IntervaloDeTurno` y `validar_sin_superposicion` desde `app.domain.superposicion_turnos`; verificar que pytest falla por import inexistente.
- [x] 2.2 GREEN: crear `backend/app/domain/superposicion_turnos.py` con `IntervaloDeTurno` (dataclass frozen: `profesional_id`, `inicio`, `fin`), `SuperposicionError(Exception)`, `IntervaloInvalidoError(ValueError)`, `MENSAJE_SUPERPOSICION` y `validar_sin_superposicion(...) -> None` mínima; verificar que la prueba de 2.1 pasa.

## 3. Aceptación sin superposición (Requisito "Aceptación de un turno sin superposición")

- [x] 3.1 RED/TRIANGULATE: agregar la prueba del escenario "Exitoso con un turno existente que no se cruza" (existente PROF-A 10:00–10:30, candidato 11:00–11:30); verificar con pytest que ambas pruebas de aceptación pasan o, si la implementación mínima no alcanza, que la nueva falla antes de generalizar.

## 4. Rechazo por superposición (Requisito "Rechazo por superposición con el mismo profesional")

- [x] 4.1 RED: agregar una prueba parametrizada con ids `parcial_izquierda` (09:45–10:15), `parcial_derecha` (10:15–10:45), `contenido` (10:10–10:20), `contenedor` (09:30–10:45) e `identico` (10:00–10:30) contra el existente PROF-A 10:00–10:30, que espera `SuperposicionError` y `str(error) == MENSAJE_SUPERPOSICION` con el texto fijo de la spec; verificar que falla.
- [x] 4.2 GREEN: implementar el predicado `a.inicio < b.fin and b.inicio < a.fin` (DIS-01) y lanzar `SuperposicionError(MENSAJE_SUPERPOSICION)`; verificar que los 5 casos pasan y que las pruebas de los grupos 2 y 3 siguen en verde.
- [x] 4.3 TRIANGULATE: comprobar que el mensaje es exactamente el de la spec ("El horario se superpone con otro turno del mismo profesional.") comparando también contra el literal en una de las pruebas; verificar con pytest.

## 5. Turnos consecutivos (Requisito "Turnos consecutivos con intervalos semiabiertos")

- [x] 5.1 RED/TRIANGULATE: agregar una prueba parametrizada con ids `consecutivo_posterior` (10:30–11:00) y `consecutivo_anterior` (09:30–10:00) contra el existente PROF-A 10:00–10:30, que espera aceptación; verificar con pytest (si el predicado de 4.2 usara `<=`, estas pruebas deben fallar y se corrige a `<`).

## 6. Profesionales distintos (Requisito "Independencia entre profesionales distintos")

- [x] 6.1 RED: agregar la prueba "Turnos simultáneos de profesionales distintos" (existente PROF-B 10:00–10:30, candidato PROF-A 10:00–10:30) que espera aceptación; verificar que falla mientras no se filtre por profesional.
- [x] 6.2 GREEN: filtrar en la función los turnos con `profesional_id` distinto al del candidato (DIS-06); verificar que pasa y que el grupo 4 sigue rechazando.
- [x] 6.3 TRIANGULATE: agregar un caso con PROF-B 10:00–10:30 y PROF-A 10:00–10:30 ambos existentes y candidato PROF-A 10:15–10:45, que espera `SuperposicionError`; verificar con pytest.

## 7. Validación de intervalos (Requisito "Validación de los intervalos de entrada")

- [x] 7.1 RED: agregar prueba parametrizada del candidato con ids `duracion_cero` (10:00–10:00) y `fin_anterior_al_inicio` (10:30–10:00) que espera `IntervaloInvalidoError` y verifica que el error no es instancia de `SuperposicionError`; verificar que falla.
- [x] 7.2 GREEN: validar `inicio < fin` del candidato y lanzar `IntervaloInvalidoError`; verificar que pasa.
- [x] 7.3 RED: agregar pruebas `instantes_sin_zona_horaria` (ambos naive) y `mezcla_con_y_sin_zona_horaria` (inicio aware, fin naive) que esperan `IntervaloInvalidoError`; verificar que fallan (o que fallan con `TypeError` en la mezcla).
- [x] 7.4 GREEN: validar que `inicio` y `fin` son aware (`tzinfo` no nulo y `utcoffset()` no nulo) antes de comparar; verificar que pasan.
- [x] 7.5 RED: agregar las pruebas de turnos existentes inválidos: "Turno existente sin zona horaria frente a candidato con zona horaria" (PROF-A 08:00–08:30 naive; candidato 11:00–11:30) y "Turno existente con intervalo inválido" (PROF-A 10:30–10:00; candidato 11:00–11:30); verificar que fallan.
- [x] 7.6 GREEN: aplicar la misma validación a todos los turnos recibidos antes de filtrar y de evaluar la superposición (DIS-03); verificar que pasan y que todo el archivo sigue en verde.
- [x] 7.7 RED/GREEN: agregar la prueba del escenario "Turno existente inválido de otro profesional" (PROF-B 10:30–10:00; candidato PROF-A 11:00–11:30; espera `IntervaloInvalidoError` y no `SuperposicionError`), confirmado por el autor el 2026-10-13; verificar con pytest.
- [x] 7.8 TRIANGULATE: agregar un caso con candidato inválido que además se superpondría, esperando `IntervaloInvalidoError` (precedencia de la validación, DIS-03); verificar con pytest.

## 8. Refactor

- [x] 8.1 Extraer auxiliares privados (por ejemplo, `_validar_intervalo` y `_se_superponen`), materializar la colección una sola vez y revisar nombres en `snake_case` con anotaciones de tipo en las funciones públicas (S1); ejecutar pytest tras cada paso y verificar que sigue en verde.
- [x] 8.2 Revisar que el módulo no tenga I/O, logs, estados de turno ni datos de pacientes (DIS-07, X1) y que el error de superposición no transporte atributos del turno en conflicto (DIS-04); verificar por lectura del módulo y con pytest en verde.

## 9. Verify (integración; antes de cualquier Archive)

- [x] 9.1 Ejecutar `openspec validate validacion-superposicion-turnos --strict` desde la raíz; verificar código de salida 0 y "is valid".
- [x] 9.2 Ejecutar `python -m pytest -v` desde `backend/` con el venv activo; verificar que todas las pruebas pasan, sin errores ni omitidas.
- [x] 9.3 Construir la tabla de trazabilidad: cada uno de los 17 escenarios de la spec con su prueba (`archivo::prueba[id]`); verificar que no queda ningún escenario sin prueba.
- [x] 9.4 Crear `openspec/changes/validacion-superposicion-turnos/verify.md` con la estructura de DIS-13 (Entorno, Comandos y resultados, Trazabilidad, Conclusión, Limitaciones vigentes); verificar que incluye las salidas reales de 9.1 y 9.2 y las versiones de 1.6.
- [x] 9.5 Comprobar que `CHANGES.md` no fue modificado: C-15 y C-01 siguen `[ ]`; verificar con `git status --short` que `CHANGES.md` no aparece.

## Workflow follow-up

- NO archivar si falla `openspec validate --strict`, si falla alguna prueba, si algún escenario no tiene prueba o si falta la evidencia en `verify.md` (AGENTS.md O2).
- Archive (`/opsx:archive validacion-superposicion-turnos`) solo después de Verify exitoso y con indicación del autor.
- Archivar este recorte NO marca C-15 ni C-01 como completados en `CHANGES.md` (AGENTS.md O1).
- Commit solo con autorización explícita del autor (G1).

# Diseño: validacion-superposicion-turnos

## Contexto

Motivación y alcance: ver `proposal.md` (Why, What Changes, Fuera de alcance). Requisitos y escenarios: ver `specs/superposicion-turnos/spec.md`.

Estado actual del repositorio: no existe `backend/` ni código de aplicación; solo documentación (Discovery, KB, `CHANGES.md`) y OpenSpec. C-01 `foundation-setup` no está implementado. Localmente hay Python 3.14.5; pytest no está instalado. La KB (`08_arquitectura_propuesta.md` §Estructura de directorios) ubica las reglas en `backend/app/domain/` y las pruebas unitarias sin base de datos en `backend/tests/unit/`; §Estrategia de pruebas asigna la superposición y los bordes de intervalos semiabiertos al nivel "unitario de dominio" con pytest. La KB modela `Turno.inicio` como instante con zona horaria (KB 04 §Turno, RN-GL-01) con la invariante `inicio < fin`.

Restricciones vinculantes: reglas duras de `AGENTS.md` (D1 datos ficticios, D3, D4, D6, O1, O2, S1, X1, X2, X4) y gobernanza MEDIO.

## Objetivos / No objetivos

**Objetivos:**

- Una función pura, sin I/O ni estado, que valida un candidato contra una colección de turnos y termina sin error o lanza un error tipado.
- Dos tipos de error separados: superposición (regla de negocio) y validación de entrada (contrato de la función).
- Pruebas unitarias pytest que cubren 1:1 los 17 escenarios de la spec, ejecutables sin Docker ni PostgreSQL (X2).
- Una preparación de entorno mínima, reemplazable o ampliable por C-01 sin conflicto.

**No objetivos (de diseño):**

- No se modela la entidad `Turno` completa (paciente, prestación, estado, consultorio): solo el intervalo ocupado por un profesional.
- No se define orden de evaluación entre varios turnos en conflicto: basta con detectar uno.
- No se optimiza para grandes volúmenes (búsqueda lineal; la agenda diaria de un profesional es pequeña y C-15 delegará la garantía final en PostgreSQL).
- No se agrega `FastAPI`, `SQLAlchemy`, `Pydantic` ni otras dependencias: solo pytest como dependencia de desarrollo.

## Decisiones

Las decisiones de diseño se numeran `DIS-xx` para no confundirlas con las reglas duras de `AGENTS.md` (D1, D3, ...). Correspondencia con las 12 decisiones confirmadas por el autor el 2026-10-13 (Explore): 1 → DIS-01; 2 → DIS-02; 3 → DIS-03; 4 → DIS-04 y DIS-05; 5 → DIS-07; 6 → DIS-06; 7 → DIS-10; 8 → DIS-13; 9 (nombre del Change `validacion-superposicion-turnos`) y 10 (capacidad `superposicion-turnos`) → `proposal.md`; 11 → DIS-08; 12 → DIS-11. DIS-09 (firmas) y DIS-12 (estrategia de pruebas) son decisiones de este Propose que concretan las anteriores. Cada una se registra con su justificación y las alternativas consideradas.

### DIS-01. Intervalos semiabiertos `[inicio, fin)`

Predicado de superposición entre dos intervalos `a` y `b` del mismo profesional: `a.inicio < b.fin and b.inicio < a.fin`. Con desigualdades estrictas, los turnos consecutivos (10:00–10:30 y 10:30–11:00) no se superponen.

- Justificación: RN-AG-04 (confirmada para este Change), criterio de US-011 "turnos consecutivos se aceptan", y coherencia con el rango `[)` que usará la restricción de exclusión de PostgreSQL en C-15.
- Alternativas: intervalos cerrados `[inicio, fin]` (rechazaría consecutivos, contradice US-011); comparación con `<=` (mismo problema).

### DIS-02. Instantes con zona horaria obligatoria

`inicio` y `fin` deben ser `datetime` *aware* (con `tzinfo` que devuelve un `utcoffset()` no nulo). La comparación se hace entre instantes absolutos, por la semántica de Python para `datetime` aware.

- Justificación: KB 04 (instante con zona horaria), RN-GL-01; evita ambigüedades de horario local.
- Alternativas: aceptar naive y asumir la zona del consultorio (inventa un dato, D6); convertir todo a UTC internamente (innecesario: Python ya compara aware por instante).

### DIS-03. Errores de validación de entrada

Se lanza `IntervaloInvalidoError` cuando, en el candidato o en cualquier turno recibido: un instante es naive; se mezclan instantes naive y aware; o `inicio >= fin` (incluye duración cero). La validación de **todas** las entradas (candidato y todos los turnos recibidos, de cualquier profesional) ocurre **antes** de evaluar la superposición; por lo tanto, ante una entrada inválida el resultado es siempre `IntervaloInvalidoError`, aunque además hubiera superposición.

- Justificación: la invariante `inicio < fin` de KB 04 §Turno; un turno existente mal formado indica un error del llamador que no debe ocultarse; el orden fijo hace el resultado determinista.
- **Confirmado por el autor (2026-10-13):** se validan todos los intervalos recibidos, incluidos los de profesionales distintos; si alguno es inválido, se produce `IntervaloInvalidoError`. La comprobación de superposición solo se realiza entre turnos del mismo profesional (DIS-06). El mensaje fijo de DIS-04 también quedó confirmado por el autor.
- Alternativas: validar en `__post_init__` del dataclass (impediría construir intervalos inválidos, pero dispersa la regla y C-15 podría construir los objetos desde filas de base de datos; se prefiere un único punto de validación dentro de la función); validar solo el candidato (dejaría pasar datos corruptos silenciosamente).

### DIS-04. Rechazo por superposición con mensaje fijo

Se lanza `SuperposicionError` con el mensaje constante `"El horario se superpone con otro turno del mismo profesional."`, expuesto como constante del módulo (por ejemplo, `MENSAJE_SUPERPOSICION`). El error no transporta atributos con ids, horarios ni datos del turno en conflicto.

- Justificación: RN-GL-03 (informar el motivo sin revelar datos de otros pacientes) y X1 (nada sensible en mensajes técnicos). La prueba compara el mensaje con el texto fijo; no se escribe una prueba aislada de "no contiene datos del paciente", porque la función nunca recibe datos de pacientes y esa aserción sería trivial.
- Alternativas: incluir el intervalo en conflicto (útil para depurar, pero revela la agenda ajena); devolver un `bool` o un resultado (el rechazo como excepción es lo que C-15 traducirá también desde la restricción de PostgreSQL).

### DIS-05. Separación de tipos de error

`SuperposicionError` e `IntervaloInvalidoError` son clases independientes: ninguna hereda de la otra. `IntervaloInvalidoError` hereda de `ValueError` (entrada inválida); `SuperposicionError` hereda de `Exception` (regla de negocio). Así `pytest.raises(SuperposicionError)` nunca captura un error de validación y viceversa.

- Alternativas: una jerarquía común `ErrorDeDominio` (posible más adelante en C-15, no se necesita ahora); un único error con un código (mezcla dos contratos distintos).

### DIS-06. La función ignora a otros profesionales

La función filtra internamente los turnos cuyo `profesional_id` es distinto del del candidato. No exige que el llamador haya filtrado por profesional.

- Justificación: hace explícita la regla "mismo profesional" (D3) y la prueba de profesionales distintos ejerce comportamiento real.
- Alternativa: exigir que el llamador pase solo turnos del mismo profesional (la regla quedaría fuera del dominio).

### DIS-07. La función no conoce estados

Recibe los turnos que ocupan agenda **ya seleccionados** por el llamador. No existe campo `estado` ni se inventan estados. PA-07 sigue abierta; C-15 decidirá qué estados pasar.

### DIS-08. Sin identificador del turno existente

El intervalo no lleva `id`. Excluir al propio turno al reprogramar es alcance de C-17; si se necesita, el llamador lo excluirá de la colección o se ampliará el tipo en ese Change.

### DIS-09. API pública (bosquejo a nivel de firmas)

Módulo `backend/app/domain/superposicion_turnos.py` (nombres en español, `snake_case`, anotaciones de tipo; S1, X4):

```python
MENSAJE_SUPERPOSICION: Final[str]

class SuperposicionError(Exception): ...
class IntervaloInvalidoError(ValueError): ...

@dataclass(frozen=True)
class IntervaloDeTurno:
    profesional_id: str
    inicio: datetime
    fin: datetime

def validar_sin_superposicion(
    candidato: IntervaloDeTurno,
    turnos_que_ocupan_agenda: Iterable[IntervaloDeTurno],
) -> None: ...
```

Comportamiento: (1) materializa la colección una sola vez; (2) valida candidato y turnos (DIS-03); (3) filtra por `profesional_id` (DIS-06); (4) si algún turno cumple el predicado de DIS-01, lanza `SuperposicionError`; (5) si no, retorna `None`. Funciones auxiliares privadas (por ejemplo, `_validar_intervalo`, `_se_superponen`) pueden surgir en el refactor. El mismo tipo `IntervaloDeTurno` representa al candidato y a los turnos existentes.

- Alternativas: dataclasses distintas para candidato y existentes (duplicación sin beneficio); Pydantic (dependencia innecesaria para dominio puro; S1 aplica a esquemas de entrada de la API, que este Change no tiene).

### DIS-10. Ubicación del código y de las pruebas

Código en `backend/app/domain/` y pruebas en `backend/tests/unit/test_superposicion_turnos.py`, según KB 08 §Estructura de directorios. Se crean solo los paquetes necesarios (`backend/app/__init__.py`, `backend/app/domain/__init__.py`). No se crean `main.py`, `api/`, `models/`, `alembic/`, Docker ni frontend: eso es C-01. Esta preparación **no completa C-01** (O1).

### DIS-11. Entorno mínimo de Python y pytest

Se elige la opción mínima de dos archivos dentro de `backend/`:

- `backend/requirements-dev.txt`: una sola línea con pytest fijado a la versión instalada durante Apply (`pytest==<versión>`).
- `backend/pyproject.toml`: **solo** la sección `[tool.pytest.ini_options]` con `testpaths = ["tests"]` y `pythonpath = ["."]`, para que las pruebas importen `app.domain...` sin instalar el paquete. Sin `[project]` ni `[build-system]`.

Entorno virtual en `backend/.venv` (ya ignorado por `.gitignore`), creado con `python -m venv`. Instalación con `pip install -r requirements-dev.txt`. Crear el venv e instalar pytest **requiere autorización explícita del autor en Apply**.

- Justificación: es lo mínimo para ejecutar pytest con imports estables; `pyproject.toml` es el archivo que C-01 ampliará con la metadata completa del proyecto (FastAPI, SQLAlchemy, etc.), y `requirements-dev.txt` puede ser reemplazado por el gestor de dependencias que elija C-01, sin conflicto.
- Alternativas: `pyproject.toml` completo con `[project]` y dependencias opcionales (adelanta decisiones de empaquetado de C-01); `pytest.ini` (otro archivo de configuración que C-01 probablemente eliminaría); `conftest.py` manipulando `sys.path` (frágil); Poetry o uv (herramienta nueva sin decisión del autor).
- Compatibilidad: en Apply se confirma que la versión de pytest instalada declara soporte para Python 3.14 (clasificadores del paquete o notas de versión) y que la suite corre; si no, se detiene y se consulta al autor. Versiones de Python, pip y pytest se registran en `verify.md`.

### DIS-12. Estrategia de pruebas

- Pruebas unitarias puras en un único archivo, sin fixtures de base de datos, red ni archivos (X2).
- Instantes construidos con `datetime(2026, 11, 2, H, M, tzinfo=timezone(timedelta(hours=-3)))`, con un auxiliar de prueba; para los escenarios naive se omite `tzinfo`. Se usa un desplazamiento fijo UTC-03:00 (equivalente a America/Argentina/Buenos_Aires en esa fecha) para no depender de `tzdata`, que en Windows no viene incluido con Python.
- `pytest.mark.parametrize` con `ids` legibles para los cinco casos de superposición, para los dos consecutivos y para los casos de validación del candidato; cada id o prueba se nombra según el escenario de la spec para la trazabilidad.
- En los rechazos se verifica el tipo exacto y, para superposición, `str(error) == MENSAJE_SUPERPOSICION`. En validación se verifica además que el error no es `SuperposicionError`.
- Ciclo TDD estricto por comportamiento (RED → GREEN → TRIANGULATE → REFACTOR), como indica `tasks.md`.

### DIS-13. Procedimiento de Verify y estructura de `verify.md`

Verify ocurre después de Apply y antes de Archive (O2). No hay comando `/opsx:verify`. `verify.md` se crea **en Verify**, no en Propose, en `openspec/changes/validacion-superposicion-turnos/verify.md`, con esta estructura:

1. **Entorno**: fecha, sistema operativo, versiones de Python, pip y pytest (salida de `python --version` y `python -m pytest --version`), y la evidencia de compatibilidad de pytest con Python 3.14.
2. **Comandos ejecutados y resultados**: `openspec validate validacion-superposicion-turnos --strict` y `python -m pytest -v` (desde `backend/`, con el venv activo), con su salida textual y código de salida.
3. **Trazabilidad escenario → prueba**: tabla con cada uno de los 17 escenarios de la spec (requisito, escenario, archivo::prueba[id], resultado).
4. **Conclusión**: cumplimiento de las condiciones de O2 (validate sin errores, pytest exitoso, todos los escenarios cubiertos, evidencia registrada).
5. **Limitaciones vigentes**: RT9, PA-07, PA-20, PA-01; C-15 y C-01 siguen pendientes.

Si alguna condición falla, no se archiva.

### Reutilización en C-15 completo

C-15 llamará a `validar_sin_superposicion` dentro de `crear_turno`, después de calcular el fin con `calcular_fin` (C-08) y de seleccionar los turnos que ocupan agenda según PA-07, y traducirá el rechazo de la restricción de exclusión de PostgreSQL al mismo `SuperposicionError` con el mismo mensaje fijo. La función sigue siendo la validación previa; la garantía final ante concurrencia será de la base (RN-AG-03).

## Riesgos / Trade-offs

- [RT9: el recorte se presenta como garantía completa contra superposiciones] → `proposal.md` y `verify.md` declaran explícitamente que no hay persistencia, restricción de exclusión ni concurrencia.
- [PA-07 abierta: qué estados ocupan agenda] → la función no conoce estados; el llamador decide; no se inventan estados.
- [PA-20 / RN-AG-03: dos creaciones concurrentes pueden pasar la validación previa] → fuera de alcance; se resuelve en C-15 con la restricción de PostgreSQL y una prueba de concurrencia real.
- [PA-01: conflicto de sillón entre profesionales distintos no controlado] → documentado como limitación; el escenario de profesionales distintos acepta explícitamente ese caso.
- [Python 3.14 es reciente y una versión de pytest podría no declararlo soportado] → tarea explícita en Apply para confirmarlo antes de escribir pruebas; si no hay versión compatible, se detiene y se consulta al autor.
- [La preparación mínima de `backend/` se confunde con C-01] → archivos limitados a los de DIS-11; `proposal.md`, `tasks.md` y `verify.md` lo aclaran; `CHANGES.md` no se modifica.
- [Validar turnos de otros profesionales puede rechazar una entrada que, para la superposición, sería irrelevante] → trade-off aceptado por determinismo; registrado como supuesto en DIS-03 para revisión del autor.
- [Búsqueda lineal O(n)] → aceptable para la agenda de un profesional; no es una garantía de rendimiento.

## Plan de migración

No aplica: no hay datos, despliegue ni esquema de base. Revertir equivale a eliminar los archivos nuevos de `backend/`.

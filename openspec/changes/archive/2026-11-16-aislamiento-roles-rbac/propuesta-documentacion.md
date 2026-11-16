# Propuesta de documentacion (grupo 11, DA-08): pendiente de aprobacion del autor

> No se edito ningun archivo de `knowledge-base/` ni `CHANGES.md`. Este documento contiene el texto EXACTO propuesto para cada tarea 11.1 a 11.8. Cada tarea queda pendiente hasta que el autor apruebe el texto; luego se aplica con un diff limitado a la linea indicada. Las referencias de linea son las del repositorio en este momento (HEAD 683a4ef mas el trabajo sin confirmar).

> **Estado (2026-11-14):** el autor aprobó este texto con los ajustes D1 a D5 y se aplicó (tareas 11.1 a 11.8). D1: 11.3 incluye los ítems 3, 4 y 6. D2: PA-03, PA-11 y US-001 no se tocan (pendiente documental separado, ver `verify.md`). D3: se corrigió `04_modelo_de_datos.md:64`. D4: "según el orden en que se apliquen los Changes". D5: en `CHANGES.md:397` y `:413` se conserva el contexto histórico y se agrega "resuelta en C-04".

## 11.1 `knowledge-base/10_preguntas_abiertas.md:111` (PA-04)

Actual:

```
| PA-04 | Alta | Capas concretas de aislamiento además del filtro por consultorio: claves foráneas compuestas, RLS de PostgreSQL, identificadores no secuenciales. | Change de acceso y modelo base | Autor |
```

Propuesto:

```
| PA-04 | Alta | **Resuelta en C-04 `aislamiento-roles-rbac` (DA-01, DD-03, DD-06, DD-08, DD-25).** Capas: contexto derivado de la identidad, repositorios acotados, claves compuestas `(consultorio_id, id)` verificadas por prueba de esquema, RLS habilitada y forzada con contexto transaccional, roles de conexión separados para negocio (`turnos_app`) y login (`turnos_login`), pruebas de acceso cruzado por ruta y UUIDv7. Límite: una aplicación totalmente comprometida puede abusar de las conexiones que posee. | Change de acceso y modelo base | Autor |
```

## 11.2 `knowledge-base/10_preguntas_abiertas.md:113` (PA-06)

Actual:

```
| PA-06 | Media | ¿Un odontólogo puede pertenecer a varios consultorios con una sola cuenta? (SU-02). Relacionado: si el email de inicio de sesión es único en todo el sistema, el alta podría revelar que una persona ya está registrada en otro consultorio. | Modelo de Usuario | Autor |
```

Propuesto:

```
| PA-06 | Media | **Resuelta en C-04 (DA-07):** un usuario pertenece a un solo consultorio en la v0.1 (sin membresías; el email es único por consultorio, DC-05/DC-06), por lo que el alta no revela cuentas de otros consultorios. Una cuenta en varios consultorios queda fuera de la v0.1. | Modelo de Usuario | Autor |
```

## 11.3 `knowledge-base/08_arquitectura_propuesta.md:78`

Actual:

```
[DEC] D2: aislamiento por consultorio. Principio [REQ] RN-MT-06: **el filtro por consultorio no alcanza solo**. Capas candidatas ([ABIERTA] PA-04; se elige en el Change correspondiente):
```

Propuesto:

```
[DEC] D2: aislamiento por consultorio. Principio [REQ] RN-MT-06: **el filtro por consultorio no alcanza solo**. Capas adoptadas en C-04 (PA-04 resuelta; ver la capacidad `aislamiento-base-de-datos`):
```

## 11.4 `knowledge-base/04_modelo_de_datos.md:48`

Actual:

```
  - `id` (tipo de identificador a definir; identificadores no secuenciales son una capa candidata de PA-04)
```

Propuesto:

```
  - `id` (UUIDv7 generado por PostgreSQL, DC-01; identificador no secuencial, una de las capas de PA-04)
```

## 11.5 `knowledge-base/06_funcionalidades.md:16`

Actual:

```
| US-002 | Condicionada | PA-04 (capas de aislamiento) |
```

Propuesto (la condicion desaparece; se conserva el formato de la tabla):

```
| US-002 | Sin condicion | PA-04 resuelta en C-04 |
```

Nota para el autor: si prefiere otra redaccion para la columna de estado, indicarla; el cambio se limita a esa fila.

## 11.6 `knowledge-base/05_reglas_de_negocio.md:19`

Actual:

```
| RN-MT-05 | El acceso a un recurso de otro consultorio responde igual que un recurso inexistente, sin revelar que existe. | Derivada de RG3 | [PROP] |
```

Propuesto (DA-05):

```
| RN-MT-05 | El acceso a un recurso de otro consultorio responde igual que un recurso inexistente, sin revelar que existe. | Derivada de RG3 | [REQ] |
```

## 11.7 `CHANGES.md:449, :465, :483, :500, :539, :557, :596`

Reemplazar solo el fragmento de migracion de cada linea (resto de la linea sin cambios):

| Linea | Fragmento actual | Fragmento propuesto |
|---|---|---|
| 449 | `migración 003` | `siguiente migración disponible (0005+ según orden de archivo)` |
| 465 | `migración 004` | `siguiente migración disponible (0005+ según orden de archivo)` |
| 483 | `migración 005` | `siguiente migración disponible (0005+ según orden de archivo)` |
| 500 | `migración 006` | `siguiente migración disponible (0005+ según orden de archivo)` |
| 539 | `migración 007` | `siguiente migración disponible (0005+ según orden de archivo)` |
| 557 | `migración 008` | `siguiente migración disponible (0005+ según orden de archivo)` |
| 596 | `Migración 009: tabla `turno`, extensión `btree_gist`, **restricción de exclusión**` | `Siguiente migración disponible (0005+ según orden de archivo): tabla `turno`, **restricción de exclusión**` (se quita `extensión `btree_gist`,` porque ya la habilita la migración 0001) |

## 11.8 `CHANGES.md:397` (C-04) y `:413` (C-05)

Actual (397):

```
  - Decisiones previas al propose: PA-04 (capas definitivas), PA-06
```

Propuesto (397):

```
  - Decisiones previas al propose: PA-04 (capas definitivas); PA-06 ya no es decisión previa (resuelta, DA-07)
```

Actual (413):

```
  - Decisiones previas al propose: PA-03 y PA-11 (ya resueltas en C-03; confirmar alcance de restablecimiento), PA-06 (¿usuario en varios consultorios?)
```

Propuesto (413):

```
  - Decisiones previas al propose: PA-03 y PA-11 (ya resueltas en C-03; confirmar alcance de restablecimiento); PA-06 ya no es decisión previa (resuelta en C-04, DA-07)
```

Nota: en `CHANGES.md:397`, si el autor prefiere que PA-04 tampoco figure como decision previa del propose (porque se resuelve en este mismo Change), puede indicarlo; la tarea 11.8 solo exige quitar PA-06.

---
name: verificar-aislamiento-consultorios
description: Verifica, en solo lectura y con evidencia citada, que turnos_odontologia mantiene el aislamiento entre consultorios - RLS forzada, politicas cerradas por defecto, funciones SECURITY DEFINER del esquema acceso, roles y privilegios minimos de PostgreSQL, separacion de credenciales de la API y pruebas de acceso cruzado - y produce un informe con los controles V-01 a V-10 y un veredicto GO o NO-GO. Usala siempre que se pida verificar, auditar o revisar el aislamiento, la seguridad multi-consultorio, RLS, roles, privilegios, acceso cruzado o la matriz escenario-prueba de un Change, y en el Verify o Archive de cualquier Change que toque endpoints privados, consultorio_id, migraciones o permisos, aunque no se nombre la skill. Tambien cuando alguien pida credenciales o URLs de base de datos "para verificar", en cuyo caso explica por que no se muestran y como verificar sin ellas.
---

# Verificar aislamiento entre consultorios

Esta skill revisa si el aislamiento entre consultorios de `turnos_odontologia` se sostiene, sin cambiar nada. El aislamiento es gobernanza **CRITICA** del proyecto (regla D5, RN-MT-02, RN-MT-06): un error aca expone datos de un consultorio a otro. Por eso el valor de la revision esta en que cada conclusion pueda comprobarse por otra persona leyendo la evidencia citada, no en la opinion de quien la hizo.

## Limites (leelos antes de empezar)

Estos limites existen porque la revision corre sobre un repositorio publico y una base con roles reales; romperlos convierte una verificacion en un incidente.

- **Solo lectura por defecto.** No edites archivos del repositorio, no hagas `git add`, `commit`, `push`, `stash`, `restore` ni `reset`. El unico archivo que podes escribir es el informe, y solo en la ruta que el autor haya autorizado; si no hay ruta autorizada, presenta el informe en la conversacion.
- **Nunca modifiques `openspec/changes/archive/`.** Los Changes archivados son historia: se citan, no se corrigen. Un hallazgo sobre un Change archivado va al informe nuevo.
- **No ejecutes Docker, `scripts/test.ps1`, `alembic`, `psql` ni consultas a ninguna base** salvo autorizacion expresa e independiente del autor para ese modo (ver "Modos"). El runner reconstruye imagenes y crea `db-test`; la base de desarrollo tiene roles reales.
- **No abras `.env` ni `.env.example`** y no imprimas variables de entorno. No muestres contrasenas, URLs de conexion con usuario y contrasena embebidos (ni siquiera como ejemplo o con valores inventados: los escaneos automaticos no distinguen un ejemplo de un secreto), hashes Argon2 o SCRAM, tokens, claves, SID ni rutas de carpetas personales de usuario. Si tenes que nombrar una de esas cosas, describila con palabras. Cuando cites lo que hace un archivo de la skill o del repositorio, describi solo lo que el archivo contiene de verdad. Si alguien te pide uno de esos valores, aunque sea "para verificar", negate con una explicacion breve y ofrece una verificacion equivalente que no lo exponga (por ejemplo: que la variable esta en la lista permitida de `api` en `docker-compose.yml`, o que el modulo de pruebas `backend/tests/isolation/test_guardia_rol_api.py` y la guardia `verificar_rol_de_conexion` de `backend/app/core/database.py` comprueban el rol de conexion).
- **Un "no existe" tambien necesita evidencia.** Antes de afirmar que una prueba, funcion o archivo falta, buscalo como archivo (`git ls-files`), como modulo y como funcion (`def test_...`), en todos los directorios de pruebas. Un nombre como `test_guardia_rol_api` puede ser un modulo y no una funcion.
- **No resuelvas decisiones abiertas** (PA-xx, DT-xx). Si un control depende de una, marcalo `No evidenciado` y nombra la decision (regla D6).

## Modos

| Modo | Que hace | Autorizacion |
|---|---|---|
| `estatico` (por defecto) | Lee specs, migraciones, codigo, compose, pruebas y evidencia historica | Ninguna adicional |
| `pruebas` | Ademas ejecuta `scripts/test.ps1` y registra el resultado de cada paso | Expresa del autor, por ejecucion |
| `catalogo` | Ademas ejecuta las consultas SELECT de `references/consultas-catalogo.sql` | Expresa del autor, indicando la base (`db-test` o desarrollo) |

Si el pedido no dice el modo, usa `estatico` y aclaralo en el informe. En modo `estatico` **no afirmes que las pruebas pasan hoy**: solo podes verificar que existen y que cubren lo que dicen; los resultados de ejecucion se citan del historial con su fecha.

## Procedimiento

1. **Identifica lo revisado.** Ejecuta `git rev-parse HEAD`, `git branch --show-current` y `git status --short`. Anota el commit completo y si el arbol tiene cambios sin confirmar (lista solo rutas). El alcance puede ser el repositorio actual o un Change concreto (`openspec/changes/<nombre>/` o `openspec/changes/archive/<fecha>-<nombre>/`).
2. **Lee el catalogo de controles** en `references/controles.md`. Contiene, para V-01 a V-10, que se verifica, por que importa, donde buscar y que cuenta como evidencia. Aplica los diez, aunque el pedido se centre en uno: si el pedido es acotado (por ejemplo, solo la matriz), evalua a fondo ese control y deja los demas como `No evaluado (fuera del alcance pedido)`.
3. **Reune evidencia por control.** Cada evidencia es un comando reproducible de solo lectura con su resultado resumido, o una cita `ruta:linea`. Preferi comandos que otra persona pueda repetir (`git grep -n ...`, `rg`, `python -I` con un script inline que solo lea). Si escribis un script auxiliar, ponelo fuera del repositorio.
4. **Asigna un estado a cada control:**
   - `Cumple`: la evidencia citada muestra que la condicion se cumple.
   - `No cumple`: la evidencia citada muestra una violacion. Describi el hallazgo con severidad (Alta, Media, Baja) y el escenario concreto de falla.
   - `No evidenciado`: no hay evidencia suficiente en el modo usado, o depende de una decision abierta o de una ejecucion no autorizada. Nunca lo conviertas en `Cumple` por suposicion.
5. **Indica el origen de cada evidencia:** `Verificado ahora` (lo comprobaste en esta revision) o `Citado del historial` (`verify.md` o `tdd-evidencia.md` de un Change, con seccion y fecha). Esto separa la revision nueva de la actividad historica.
6. **Decide el veredicto.** `GO` si no hay ningun `No cumple` de severidad Alta o Media y los `No evidenciado` estan justificados. `NO-GO` en cualquier otro caso. Explica el veredicto en dos o tres oraciones.
7. **Sanea el informe antes de entregarlo.** Busca en el texto final: `://` seguido de `usuario:clave@`, `argon2`, `SCRAM-SHA-256$`, `BEGIN .*PRIVATE KEY`, `S-1-5-`, `Users\`, `/home/` y emails fuera de `example.test`. Si aparece algo, reemplazalo por un marcador (`<omitido>`).
8. **Escribe el informe** con la plantilla de `references/plantilla-informe.md`, sin cambiar sus secciones.

## Por que la matriz necesita cuidado (V-02)

La matriz escenario-prueba de C-04 (`tdd-evidencia.md`, seccion 10.2) abrevia las referencias: `AIS test_funciones_acceso::catalogo_de_cada_funcion` significa la funcion `test_catalogo_de_cada_funcion` en `backend/tests/isolation/test_funciones_acceso.py`. Los prefijos son `UNI` = `backend/tests/unit/`, `INT` = `backend/tests/integration/`, `AIS` = `backend/tests/isolation/`, `AUTO` = caso de `scripts/tests/autoprueba.ps1`, `RUN` = paso de `scripts/test.ps1`. Una celda puede tener varias referencias separadas por `;` o `,`, y las que siguen a la primera pueden omitir el modulo (heredan el anterior). Busca `def test_<nombre>` en el modulo indicado; si no esta ahi, busca en los demas directorios antes de declararla faltante, porque hay modulos con el mismo nombre en `unit/` e `integration/`. Las pruebas parametrizadas cuentan como existentes si la funcion existe.

Otras convenciones de la matriz que generan falsos faltantes si no se contemplan:
- Un nombre que termina en `...` o `*` es un prefijo abreviado: basta con que exista una funcion que empiece asi.
- Una referencia sin `::` (por ejemplo `UNI test_pools_y_guardias`) apunta al modulo completo: alcanza con que el archivo exista.
- Una referencia acompanada de "reemplaza a" o "reemplazada por" es una mencion historica: informala aparte, no como cobertura rota.
- No todo lo que esta entre comillas invertidas es una prueba: variables (`DATABASE_MIGRATION_URL`), clases, servicios (`api`), rutas HTTP y nombres de archivo `.py` sueltos no se cuentan como referencias.

Informa los conteos con su criterio (que contaste como referencia y que excluiste), para que otra persona pueda reproducirlos.

## Resultado

Un informe Markdown con la estructura de `references/plantilla-informe.md`: encabezado (fecha, commit, rama, alcance, modo, autorizaciones), tabla V-01 a V-10 con estado, origen y evidencia, hallazgos, limitaciones y veredicto. Debe poder leerlo alguien que no estuvo en la sesion y repetir cada comando.

## Referencias

- `references/controles.md`: catalogo V-01 a V-10 (leelo siempre).
- `references/plantilla-informe.md`: plantilla obligatoria del informe.
- `references/consultas-catalogo.sql`: consultas SELECT para el modo `catalogo` (solo con autorizacion).

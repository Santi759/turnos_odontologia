-- Consultas de solo lectura para el modo `catalogo` de verificar-aislamiento-consultorios.
--
-- Usalas SOLO con autorizacion expresa del autor, indicando la base (db-test o desarrollo).
-- Todas son SELECT: no crean, modifican ni borran nada. Devuelven booleanos, conteos o nombres
-- de objetos del esquema, nunca datos de usuarios, hashes ni credenciales.
-- Ejecutalas dentro de una transaccion de solo lectura:
--   BEGIN TRANSACTION READ ONLY; ... ; ROLLBACK;

-- V-03: RLS habilitada y forzada por tabla del esquema public.
SELECT c.relname AS tabla, c.relrowsecurity AS rls, c.relforcerowsecurity AS rls_forzada
  FROM pg_catalog.pg_class c
  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relkind = 'r'
 ORDER BY c.relname;

-- V-04: politicas por tabla (nombre, orden, roles y si tiene WITH CHECK).
SELECT tablename AS tabla, policyname AS politica, cmd AS orden, roles,
       with_check IS NOT NULL AS con_check
  FROM pg_catalog.pg_policies
 WHERE schemaname = 'public'
 ORDER BY tablename, policyname;

-- V-05: funciones del esquema acceso: SECURITY DEFINER, search_path fijo y EXECUTE publico.
SELECT p.proname AS funcion, p.prosecdef AS security_definer,
       p.proconfig AS configuracion,
       pg_catalog.has_function_privilege('public', p.oid, 'EXECUTE') AS execute_publico
  FROM pg_catalog.pg_proc p
  JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'acceso'
 ORDER BY p.proname;

-- V-06: atributos de los cuatro roles del proyecto (solo booleanos).
SELECT rolname AS rol, rolcanlogin AS login, rolsuper AS superusuario,
       rolbypassrls AS bypassrls, rolcreaterole AS createrole,
       rolcreatedb AS createdb, rolreplication AS replication
  FROM pg_catalog.pg_roles
 WHERE rolname IN ('turnos_app', 'turnos_login', 'turnos_acceso_previo', 'turnos_acceso_login')
 ORDER BY rolname;

-- V-06: membresias que involucran a esos roles (resultado esperado: cero filas).
SELECT COUNT(*) AS membresias
  FROM pg_catalog.pg_auth_members m
  JOIN pg_catalog.pg_roles a ON a.oid = m.member
  JOIN pg_catalog.pg_roles b ON b.oid = m.roleid
 WHERE a.rolname IN ('turnos_app', 'turnos_login', 'turnos_acceso_previo', 'turnos_acceso_login')
    OR b.rolname IN ('turnos_app', 'turnos_login', 'turnos_acceso_previo', 'turnos_acceso_login');

-- V-07: privilegios de turnos_app sobre la columna sensible y la tabla de intentos
-- (resultado esperado: false y false).
SELECT pg_catalog.has_column_privilege('turnos_app', 'public.usuario', 'credencial', 'SELECT')
           AS app_lee_credencial,
       pg_catalog.has_table_privilege('turnos_app', 'public.intento_login', 'SELECT')
           AS app_lee_intentos;

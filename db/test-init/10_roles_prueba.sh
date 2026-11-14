#!/bin/bash
# Roles de PostgreSQL de la base de pruebas efimera (db-test), DD-14, DD-21 (ASCII).
# Se ejecuta en cada arranque de db-test (usa tmpfs). Las contrasenas llegan por variables de
# entorno del contenedor efimero; nunca se imprimen ni se pasan como argumentos de procesos.
if [ -z "${TURNOS_APP_TEST_PASSWORD:-}" ] || [ -z "${TURNOS_LOGIN_TEST_PASSWORD:-}" ]; then
    echo "error: faltan las contrasenas de los roles de prueba (TURNOS_APP_TEST_PASSWORD, TURNOS_LOGIN_TEST_PASSWORD)" >&2
    exit 1
fi
if [ "${TURNOS_APP_TEST_PASSWORD}" = "${TURNOS_LOGIN_TEST_PASSWORD}" ]; then
    echo "error: las contrasenas de los roles de prueba deben ser distintas" >&2
    exit 1
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\getenv clave_app TURNOS_APP_TEST_PASSWORD
\getenv clave_login TURNOS_LOGIN_TEST_PASSWORD
CREATE ROLE turnos_app LOGIN PASSWORD :'clave_app' NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION;
CREATE ROLE turnos_login LOGIN PASSWORD :'clave_login' NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION;
CREATE ROLE turnos_acceso_previo NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION;
CREATE ROLE turnos_acceso_login NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION;
SQL

"""Convenciones de esquema por consultorio (3.4, DD-08, DD-19).

Toda tabla de `public` con `consultorio_id` declara `UNIQUE (consultorio_id, id)`, toda FK hacia
una tabla con `consultorio_id` lo incluye, y todas las tablas (salvo `alembic_version`) tienen RLS
habilitada y forzada, con la politica exacta de DD-03 en las tablas por consultorio. La propia
verificacion se prueba con tablas temporales no conformes (creadas y revertidas).
"""

import re

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import IntegrityError

from tests.integration.datos_auth import crear_consultorio, crear_usuario

TABLA_SIN_RLS = "alembic_version"


def _norm(expresion: str | None) -> str:
    """Sin espacios ni parentesis: PostgreSQL normaliza la forma de la expresion guardada."""
    return re.sub(r"[()\s]", "", expresion or "")


def _tablas_con_consultorio(conexion: Connection) -> set[str]:
    filas = conexion.execute(
        text(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = 'consultorio_id' "
            "AND NOT a.attisdropped WHERE n.nspname = 'public' AND c.relkind = 'r'"
        )
    )
    return {f[0] for f in filas}


def violaciones_de_convencion(conexion: Connection) -> list[str]:
    """Reglas de DD-08 y DD-19 incumplidas en el catalogo de `public` (vacia si conforme)."""
    violaciones: list[str] = []
    con_consultorio = _tablas_con_consultorio(conexion)

    for tabla in sorted(con_consultorio):
        claves = conexion.execute(
            text(
                "SELECT pg_get_constraintdef(co.oid) FROM pg_constraint co "
                "WHERE co.conrelid = ('public.' || quote_ident(:t))::regclass AND co.contype IN ('u', 'p')"
            ),
            {"t": tabla},
        ).scalars().all()
        if "UNIQUE (consultorio_id, id)" not in claves:
            violaciones.append(f"{tabla}: falta UNIQUE (consultorio_id, id)")

    for tabla, restriccion, columnas_origen, tabla_destino in conexion.execute(
        text(
            "SELECT c.relname, co.conname, "
            "(SELECT array_agg(a.attname::text ORDER BY k.ord) FROM unnest(co.conkey) "
            " WITH ORDINALITY AS k(num, ord) JOIN pg_attribute a ON a.attrelid = co.conrelid AND a.attnum = k.num), "
            "d.relname "
            "FROM pg_constraint co JOIN pg_class c ON c.oid = co.conrelid "
            "JOIN pg_class d ON d.oid = co.confrelid JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE co.contype = 'f' AND n.nspname = 'public'"
        )
    ):
        if tabla_destino in con_consultorio and tabla_destino != "consultorio":
            if "consultorio_id" not in columnas_origen:
                violaciones.append(f"{tabla}: la FK {restriccion} no incluye consultorio_id")

    for tabla, habilitada, forzada in conexion.execute(
        text(
            "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname <> :excluida"
        ),
        {"excluida": TABLA_SIN_RLS},
    ):
        if not (habilitada and forzada):
            violaciones.append(f"{tabla}: RLS no habilitada y forzada")

    for tabla in sorted(con_consultorio):
        columna = "id" if tabla == "consultorio" else "consultorio_id"
        politicas = conexion.execute(
            text(
                "SELECT qual, with_check FROM pg_policies WHERE schemaname = 'public' "
                "AND tablename = :t AND roles = '{public}' AND cmd = 'ALL'"
            ),
            {"t": tabla},
        ).all()
        esperado = (
            f"{columna} = (NULLIF(current_setting('app.consultorio_id'::text, true), ''::text))::uuid"
        )
        if not any(
            _norm(q) == _norm(esperado) and _norm(c) == _norm(esperado) for q, c in politicas
        ):
            violaciones.append(f"{tabla}: falta la politica de aislamiento exacta")
    return violaciones


def test_el_esquema_actual_cumple_las_convenciones(motor: Engine, base_migrada: Engine):
    with motor.connect() as conexion:
        assert violaciones_de_convencion(conexion) == []


def test_las_tablas_con_consultorio_son_las_esperadas(motor: Engine, base_migrada: Engine):
    with motor.connect() as conexion:
        assert _tablas_con_consultorio(conexion) == {"usuario", "sesion"}


def _con_tabla_temporal(motor: Engine, ddl: list[str]) -> list[str]:
    with motor.connect() as conexion:
        transaccion = conexion.begin()
        try:
            for sentencia in ddl:
                conexion.execute(text(sentencia))
            return violaciones_de_convencion(conexion)
        finally:
            transaccion.rollback()


def test_una_tabla_sin_clave_compuesta_ni_rls_se_detecta(motor: Engine, base_migrada: Engine):
    violaciones = _con_tabla_temporal(
        motor, ["CREATE TABLE public.paciente_x (id uuid PRIMARY KEY, consultorio_id uuid NOT NULL)"]
    )

    assert "paciente_x: falta UNIQUE (consultorio_id, id)" in violaciones
    assert "paciente_x: RLS no habilitada y forzada" in violaciones
    assert "paciente_x: falta la politica de aislamiento exacta" in violaciones


def test_una_fk_sin_consultorio_id_hacia_usuario_se_detecta(motor: Engine, base_migrada: Engine):
    violaciones = _con_tabla_temporal(
        motor,
        [
            "CREATE TABLE public.nota_x (id uuid PRIMARY KEY, consultorio_id uuid NOT NULL, "
            "usuario_id uuid NOT NULL REFERENCES public.usuario (id), UNIQUE (consultorio_id, id))",
            "ALTER TABLE public.nota_x ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE public.nota_x FORCE ROW LEVEL SECURITY",
        ],
    )

    assert any(v.startswith("nota_x: la FK") and "consultorio_id" in v for v in violaciones)
    assert "nota_x: RLS no habilitada y forzada" not in violaciones


def test_una_tabla_conforme_no_produce_violaciones(motor: Engine, base_migrada: Engine):
    expresion = "NULLIF(current_setting('app.consultorio_id', true), '')::uuid"
    violaciones = _con_tabla_temporal(
        motor,
        [
            "CREATE TABLE public.cita_x (id uuid PRIMARY KEY, consultorio_id uuid NOT NULL, "
            "usuario_id uuid NOT NULL, UNIQUE (consultorio_id, id), "
            "FOREIGN KEY (consultorio_id, usuario_id) REFERENCES public.usuario (consultorio_id, id))",
            "ALTER TABLE public.cita_x ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE public.cita_x FORCE ROW LEVEL SECURITY",
            f"CREATE POLICY pol_cita_x_aislamiento ON public.cita_x "
            f"USING (consultorio_id = {expresion}) WITH CHECK (consultorio_id = {expresion})",
        ],
    )

    assert violaciones == []


def test_una_politica_distinta_de_la_exacta_se_detecta(motor: Engine, base_migrada: Engine):
    violaciones = _con_tabla_temporal(
        motor,
        [
            "CREATE TABLE public.cita_y (id uuid PRIMARY KEY, consultorio_id uuid NOT NULL, "
            "UNIQUE (consultorio_id, id))",
            "ALTER TABLE public.cita_y ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE public.cita_y FORCE ROW LEVEL SECURITY",
            "CREATE POLICY pol_cita_y ON public.cita_y USING (true) WITH CHECK (true)",
        ],
    )

    assert violaciones == ["cita_y: falta la politica de aislamiento exacta"]


def test_una_referencia_cruzada_entre_consultorios_la_rechaza_la_fk_compuesta(sesion):
    a = crear_consultorio(sesion, "conv-a")
    b = crear_consultorio(sesion, "conv-b")
    usuario_de_b = crear_usuario(sesion, b, email="b@example.test")

    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.execute(
                text(
                    "INSERT INTO sesion (consultorio_id, usuario_id, token_hmac, creada_en, "
                    "ultimo_uso_en, vence_absoluto_en) VALUES (:c, :u, :h, now(), now(), now() + interval '1 hour')"
                ),
                {"c": a, "u": usuario_de_b, "h": b"x" * 32},
            )

"""autenticacion: codigo de consultorio, sesion e intento_login

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("consultorio", sa.Column("codigo", sa.Text(), nullable=True))
    # Backfill generico y determinista (DD-13): la regla de `app/models/codigo.py` en SQL
    # en linea, sin funciones ni disparadores. Ante colision del codigo corto, el de menor
    # `id` conserva el corto y los demas reciben el largo. Unico UPDATE de la migracion
    # y solo sobre la columna nueva.
    op.execute(
        """
        UPDATE consultorio AS c
           SET codigo = CASE WHEN o.orden = 1
                             THEN 'c-' || right(replace(c.id::text, '-', ''), 12)
                             ELSE 'c-' || replace(c.id::text, '-', '') END
          FROM (SELECT id,
                       row_number() OVER (
                           PARTITION BY right(replace(id::text, '-', ''), 12)
                           ORDER BY id) AS orden
                  FROM consultorio) AS o
         WHERE o.id = c.id
        """
    )
    # Obligatorio y SIN valor por defecto: toda insercion debe indicar el codigo.
    op.alter_column("consultorio", "codigo", nullable=False)
    op.create_unique_constraint(op.f("uq_consultorio_codigo"), "consultorio", ["codigo"])
    op.create_check_constraint(
        op.f("ck_consultorio_codigo_formato"),
        "consultorio",
        "codigo ~ '^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$'",
    )

    op.create_table(
        "sesion",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("consultorio_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("token_hmac", sa.LargeBinary(), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ultimo_uso_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vence_absoluto_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocada_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "creada_en < vence_absoluto_en AND ultimo_uso_en >= creada_en "
            "AND ultimo_uso_en <= vence_absoluto_en",
            name=op.f("ck_sesion_vencimientos_coherentes"),
        ),
        sa.CheckConstraint(
            "octet_length(token_hmac) = 32",
            name=op.f("ck_sesion_token_hmac_longitud"),
        ),
        sa.CheckConstraint(
            "revocada_en IS NULL OR revocada_en >= creada_en",
            name=op.f("ck_sesion_revocacion_posterior"),
        ),
        sa.ForeignKeyConstraint(
            ["consultorio_id", "usuario_id"],
            ["usuario.consultorio_id", "usuario.id"],
            name=op.f("fk_sesion_consultorio_id_usuario"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sesion")),
        sa.UniqueConstraint("token_hmac", name=op.f("uq_sesion_token_hmac")),
    )
    op.create_index(
        "ix_sesion_consultorio_id_usuario_id", "sesion", ["consultorio_id", "usuario_id"]
    )
    op.create_index("ix_sesion_vence_absoluto_en", "sesion", ["vence_absoluto_en"])
    op.create_index("ix_sesion_ultimo_uso_en", "sesion", ["ultimo_uso_en"])
    op.create_index("ix_sesion_revocada_en", "sesion", ["revocada_en"])

    op.create_table(
        "intento_login",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("clave_cuenta", sa.LargeBinary(), nullable=False),
        sa.Column("clave_ip", sa.LargeBinary(), nullable=False),
        sa.Column("ocurrido_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "descartado_para_cuenta",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "octet_length(clave_cuenta) = 32 AND octet_length(clave_ip) = 32",
            name=op.f("ck_intento_login_claves_longitud"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intento_login")),
    )
    op.create_index(
        "ix_intento_login_clave_cuenta_ocurrido_en",
        "intento_login",
        ["clave_cuenta", "ocurrido_en"],
    )
    op.create_index(
        "ix_intento_login_clave_ip_ocurrido_en",
        "intento_login",
        ["clave_ip", "ocurrido_en"],
    )
    op.create_index("ix_intento_login_ocurrido_en", "intento_login", ["ocurrido_en"])


def downgrade() -> None:
    # Solo se ejecuta contra la base de pruebas efimera (db-test); nunca contra la de
    # desarrollo ni con `down -v`. Elimina exactamente lo que agrega `upgrade`, en orden
    # inverso; no toca `usuario` ni `btree_gist`.
    op.drop_table("intento_login")
    op.drop_table("sesion")
    op.drop_constraint(op.f("ck_consultorio_codigo_formato"), "consultorio", type_="check")
    op.drop_constraint(op.f("uq_consultorio_codigo"), "consultorio", type_="unique")
    op.drop_column("consultorio", "codigo")

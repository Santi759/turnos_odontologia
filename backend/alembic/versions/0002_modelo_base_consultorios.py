"""modelo base: tablas consultorio y usuario (sin datos)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consultorio",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column(
            "zona_horaria",
            sa.Text(),
            server_default=sa.text("'America/Argentina/Buenos_Aires'"),
            nullable=False,
        ),
        sa.Column(
            "anticipacion_cancelacion_horas",
            sa.Integer(),
            server_default=sa.text("24"),
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "anticipacion_cancelacion_horas >= 0",
            name=op.f("ck_consultorio_anticipacion_no_negativa"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consultorio")),
    )
    op.create_table(
        "usuario",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("consultorio_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("credencial", sa.Text(), nullable=True),
        sa.Column("rol", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rol IN ('administrador', 'secretaria', 'odontologo')",
            name=op.f("ck_usuario_rol_valido"),
        ),
        sa.CheckConstraint(
            "email = lower(btrim(email)) AND email <> ''",
            name=op.f("ck_usuario_email_normalizado"),
        ),
        sa.CheckConstraint(
            "credencial IS NULL OR credencial <> ''",
            name=op.f("ck_usuario_credencial_no_vacia"),
        ),
        sa.ForeignKeyConstraint(
            ["consultorio_id"],
            ["consultorio.id"],
            name=op.f("fk_usuario_consultorio_id_consultorio"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuario")),
        sa.UniqueConstraint(
            "consultorio_id", "id", name=op.f("uq_usuario_consultorio_id_id")
        ),
        sa.UniqueConstraint(
            "consultorio_id", "email", name=op.f("uq_usuario_consultorio_id_email")
        ),
    )


def downgrade() -> None:
    # Solo se ejecuta contra la base de pruebas efimera (db-test); nunca contra la de
    # desarrollo. No toca btree_gist, que pertenece a 0001.
    op.drop_table("usuario")
    op.drop_table("consultorio")

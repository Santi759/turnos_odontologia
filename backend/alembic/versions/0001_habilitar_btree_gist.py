"""habilitar btree_gist (infraestructura, sin tablas de dominio)

Revision ID: 0001
Revises:
Create Date: 2026-11-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")


def downgrade() -> None:
    # Solo se ejecuta contra la base de pruebas efimera; nunca contra la de desarrollo.
    op.execute("DROP EXTENSION IF EXISTS btree_gist")

"""add registry details to trucks (model, year, VIN, color, body, traction)

Revision ID: a7c2e5f8b913
Revises: f3b9d1e7a254
Create Date: 2026-11-03 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c2e5f8b913'
down_revision: Union[str, None] = 'f3b9d1e7a254'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ('model', 'vin', 'color', 'body_type', 'traction')


def upgrade() -> None:
    # Datos de la ficha del Registro Nacional; como el código y la marca, solo los ve el admin.
    for name in COLUMNS:
        op.add_column('trucks', sa.Column(name, sa.String(), nullable=True))
    op.add_column('trucks', sa.Column('year', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('trucks', 'year')
    for name in reversed(COLUMNS):
        op.drop_column('trucks', name)

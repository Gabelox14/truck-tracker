"""add code brand to trucks

Revision ID: 85e05a018f2d
Revises: 0faf5cf127ac
Create Date: 2026-07-31 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85e05a018f2d'
down_revision: Union[str, None] = '0faf5cf127ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('trucks', sa.Column('code', sa.String(), nullable=True))
    op.add_column('trucks', sa.Column('brand', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('trucks', 'brand')
    op.drop_column('trucks', 'code')

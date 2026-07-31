"""add active to drivers

Revision ID: 0faf5cf127ac
Revises: a1b05037e3ac
Create Date: 2026-07-31 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0faf5cf127ac'
down_revision: Union[str, None] = 'a1b05037e3ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'drivers',
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column('drivers', 'active')

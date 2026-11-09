"""trips without a driver account and a free-text unit label

Revision ID: b5d8e2a4c719
Revises: a7c2e5f8b913
Create Date: 2026-11-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5d8e2a4c719'
down_revision: Union[str, None] = 'a7c2e5f8b913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Viajes del registro histórico hechos por terceros sin cuenta en la app
    # (por ejemplo "JP" o "MYR"): no tienen chofer ni camión, solo la unidad
    # tal como la escribe el registro. Los viajes de la app siguen exigiendo chofer.
    op.alter_column('trips', 'driver_id', existing_type=sa.UUID(), nullable=True)
    op.add_column('trips', sa.Column('unit_label', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('trips', 'unit_label')
    op.alter_column('trips', 'driver_id', existing_type=sa.UUID(), nullable=False)

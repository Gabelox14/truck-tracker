"""add trip_type to trips

Revision ID: e65cc466c119
Revises: 85e05a018f2d
Create Date: 2026-07-31 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e65cc466c119'
down_revision: Union[str, None] = '85e05a018f2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('trips', sa.Column('trip_type', sa.String(), nullable=True))
    op.create_check_constraint(
        'ck_trips_trip_type', 'trips', "trip_type IN ('directo', 'indirecto')"
    )


def downgrade() -> None:
    op.drop_constraint('ck_trips_trip_type', 'trips', type_='check')
    op.drop_column('trips', 'trip_type')

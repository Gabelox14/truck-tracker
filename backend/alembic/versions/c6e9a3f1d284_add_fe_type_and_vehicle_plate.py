"""add trips.fe_type and trip_cars.plate

Revision ID: c6e9a3f1d284
Revises: b5d8e2a4c719
Create Date: 2026-11-09 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6e9a3f1d284'
down_revision: Union[str, None] = 'b5d8e2a4c719'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tipo de FE: de qué registro sale el viaje (VINS DIRECTOS, VINS USADOS DIRECTOS
    # o VINS PROFORMAS). Los usados además llevan la placa del vehículo.
    op.add_column('trips', sa.Column('fe_type', sa.String(), nullable=True))
    op.create_check_constraint(
        'ck_trips_fe_type', 'trips', "fe_type IN ('directo', 'directo_usado', 'proforma')"
    )
    op.add_column('trip_cars', sa.Column('plate', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('trip_cars', 'plate')
    op.drop_constraint('ck_trips_fe_type', 'trips', type_='check')
    op.drop_column('trips', 'fe_type')

"""add assigned truck and driver type to drivers

Revision ID: e8a4c6b2d917
Revises: d2e7f3a91c40
Create Date: 2026-11-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8a4c6b2d917'
down_revision: Union[str, None] = 'd2e7f3a91c40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Camión fijo del chofer. Nullable porque los choferes que ya existían no lo
    # tienen; la API lo exige al crear y al reactivar.
    op.add_column('drivers', sa.Column('truck_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_drivers_truck_id', 'drivers', 'trucks', ['truck_id'], ['id'], ondelete='SET NULL'
    )
    # Un camión tiene un solo chofer activo; al desactivarlo el camión queda libre.
    op.create_index(
        'uq_drivers_active_truck',
        'drivers',
        ['truck_id'],
        unique=True,
        postgresql_where=sa.text('active AND truck_id IS NOT NULL'),
    )
    # Tipo de chofer, solo visible para el admin.
    op.add_column('drivers', sa.Column('driver_type', sa.String(), nullable=True))
    op.create_check_constraint(
        'ck_drivers_driver_type', 'drivers', "driver_type IN ('fijo', 'suplente', 'tercero')"
    )


def downgrade() -> None:
    op.drop_constraint('ck_drivers_driver_type', 'drivers', type_='check')
    op.drop_column('drivers', 'driver_type')
    op.drop_index('uq_drivers_active_truck', table_name='drivers')
    op.drop_constraint('fk_drivers_truck_id', 'drivers', type_='foreignkey')
    op.drop_column('drivers', 'truck_id')

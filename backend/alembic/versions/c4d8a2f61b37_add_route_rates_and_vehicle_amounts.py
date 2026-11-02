"""add route rates, per-vehicle amounts, requester and photo groups

Revision ID: c4d8a2f61b37
Revises: b7c3e1f05a92
Create Date: 2026-11-02 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d8a2f61b37'
down_revision: Union[str, None] = 'b7c3e1f05a92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tarifa por ruta: en los viajes directos el monto lo fija la ruta y la clase
    # del vehículo (los camiones JAC 1035/1042 pagan más que los livianos).
    op.create_table('route_rates',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('category', sa.String(), server_default='directo', nullable=False),
    sa.Column('origin_zone_id', sa.UUID(), nullable=False),
    sa.Column('destination_zone_id', sa.UUID(), nullable=False),
    sa.Column('vehicle_class', sa.String(), server_default='liviano', nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), server_default='CRC', nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("category IN ('directo', 'indirecto')", name='ck_route_rates_category'),
    sa.CheckConstraint("vehicle_class IN ('liviano', 'carga')", name='ck_route_rates_vehicle_class'),
    sa.CheckConstraint("currency IN ('CRC', 'USD')", name='ck_route_rates_currency'),
    sa.ForeignKeyConstraint(['destination_zone_id'], ['zones.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['origin_zone_id'], ['zones.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('category', 'origin_zone_id', 'destination_zone_id', 'vehicle_class', name='uq_route_rates_route')
    )
    op.execute("ALTER TABLE route_rates ENABLE ROW LEVEL SECURITY")

    # Monto y clase por vehículo: el total del viaje es la suma de sus vehículos.
    op.add_column('trip_cars', sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('trip_cars', sa.Column('vehicle_class', sa.String(), server_default='liviano', nullable=False))
    op.create_check_constraint('ck_trip_cars_vehicle_class', 'trip_cars', "vehicle_class IN ('liviano', 'carga')")

    # Quién pidió el traslado (la columna SOLICITADO del registro de directos).
    op.add_column('trips', sa.Column('requested_by', sa.String(), nullable=True))

    # Varias fotos del mismo vehículo (etiqueta del VIN y el carro) en una sola
    # lectura: las fotos extra apuntan a la principal.
    op.add_column('intake_files', sa.Column('parent_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_intake_files_parent_id', 'intake_files', 'intake_files', ['parent_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_intake_files_parent_id'), 'intake_files', ['parent_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_intake_files_parent_id'), table_name='intake_files')
    op.drop_constraint('fk_intake_files_parent_id', 'intake_files', type_='foreignkey')
    op.drop_column('intake_files', 'parent_id')
    op.drop_column('trips', 'requested_by')
    op.drop_constraint('ck_trip_cars_vehicle_class', 'trip_cars', type_='check')
    op.drop_column('trip_cars', 'vehicle_class')
    op.drop_column('trip_cars', 'amount')
    op.drop_table('route_rates')

"""add intake files, vehicle VIN fields and review status

Revision ID: b7c3e1f05a92
Revises: a1f4c9d2e8b3
Create Date: 2026-10-31 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7c3e1f05a92'
down_revision: Union[str, None] = 'a1f4c9d2e8b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REVIEW_STATUSES = "('ok', 'needs_review', 'confirmed')"


def upgrade() -> None:
    # Cada foto o audio recibido: deduplicación por hash, ruta en el bucket
    # privado, lo extraído, y modelo/tokens para controlar costos. Sin trip_id
    # es un borrador pendiente de asignar a un viaje.
    op.create_table('intake_files',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('file_sha256', sa.String(length=64), nullable=False),
    sa.Column('storage_path', sa.String(), nullable=False),
    sa.Column('mime_type', sa.String(), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('trip_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(), server_default='processed', nullable=False),
    sa.Column('error', sa.String(), nullable=True),
    sa.Column('extraction', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('transcript', sa.Text(), nullable=True),
    sa.Column('duration_seconds', sa.Numeric(precision=8, scale=2), nullable=True),
    sa.Column('ai_model', sa.String(), nullable=True),
    sa.Column('input_tokens', sa.Integer(), nullable=True),
    sa.Column('output_tokens', sa.Integer(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('vin_photo', 'audio')", name='ck_intake_files_kind'),
    sa.CheckConstraint("status IN ('processed', 'failed')", name='ck_intake_files_status'),
    sa.ForeignKeyConstraint(['created_by'], ['profiles.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('file_sha256')
    )
    op.create_index(op.f('ix_intake_files_trip_id'), 'intake_files', ['trip_id'], unique=False)
    op.execute("ALTER TABLE intake_files ENABLE ROW LEVEL SECURITY")

    # trip_cars pasa a guardar el VIN y su validación. brand sigue siendo la
    # marca; vin_photo_url (siempre vacío) lo reemplaza photo_file_id.
    op.alter_column('trip_cars', 'brand', existing_type=sa.String(), nullable=True)
    op.drop_column('trip_cars', 'vin_photo_url')
    op.add_column('trip_cars', sa.Column('vin', sa.String(), nullable=True))
    op.add_column('trip_cars', sa.Column('vin_raw', sa.String(), nullable=True))
    op.add_column('trip_cars', sa.Column('vin_valid', sa.Boolean(), nullable=True))
    op.add_column('trip_cars', sa.Column('check_digit_ok', sa.Boolean(), nullable=True))
    op.add_column('trip_cars', sa.Column('make_from_photo', sa.String(), nullable=True))
    op.add_column('trip_cars', sa.Column('model', sa.String(), nullable=True))
    op.add_column('trip_cars', sa.Column('model_year', sa.SmallInteger(), nullable=True))
    op.add_column('trip_cars', sa.Column('color', sa.String(), nullable=True))
    op.add_column('trip_cars', sa.Column('ocr_confidence', sa.Numeric(precision=3, scale=2), nullable=True))
    op.add_column('trip_cars', sa.Column('photo_file_id', sa.UUID(), nullable=True))
    op.add_column('trip_cars', sa.Column('review_status', sa.String(), server_default='ok', nullable=False))
    op.add_column('trip_cars', sa.Column('review_notes', sa.Text(), nullable=True))
    op.add_column('trip_cars', sa.Column('created_by', sa.UUID(), nullable=True))
    op.add_column('trip_cars', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.create_foreign_key('fk_trip_cars_photo_file_id', 'trip_cars', 'intake_files', ['photo_file_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_trip_cars_created_by', 'trip_cars', 'profiles', ['created_by'], ['id'], ondelete='SET NULL')
    op.create_check_constraint('ck_trip_cars_review_status', 'trip_cars', f"review_status IN {REVIEW_STATUSES}")
    # El VIN no es único: el mismo carro puede viajar varias veces.
    op.create_index(op.f('ix_trip_cars_vin'), 'trip_cars', ['vin'], unique=False)

    # trips: el monto de siempre con su moneda, origen/destino tal como se
    # dijeron, de dónde vino el viaje y su revisión (aparte del estado del viaje).
    op.alter_column('trips', 'amount', existing_type=sa.Numeric(precision=10, scale=2), type_=sa.Numeric(precision=12, scale=2), existing_nullable=True)
    op.add_column('trips', sa.Column('currency', sa.String(length=3), server_default='CRC', nullable=False))
    op.add_column('trips', sa.Column('origin_text', sa.String(), nullable=True))
    op.add_column('trips', sa.Column('destination_text', sa.String(), nullable=True))
    op.add_column('trips', sa.Column('intake_source', sa.String(), server_default='manual', nullable=False))
    op.add_column('trips', sa.Column('review_status', sa.String(), server_default='ok', nullable=False))
    op.add_column('trips', sa.Column('review_notes', sa.Text(), nullable=True))
    op.create_check_constraint('ck_trips_currency', 'trips', "currency IN ('CRC', 'USD')")
    op.create_check_constraint('ck_trips_intake_source', 'trips', "intake_source IN ('manual', 'upload', 'whatsapp')")
    op.create_check_constraint('ck_trips_review_status', 'trips', f"review_status IN {REVIEW_STATUSES}")

    # Bucket privado para fotos y audios: solo el backend (llave de servicio)
    # lo lee y lo escribe. Fuera de Supabase no existe storage.buckets.
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('storage.buckets') IS NOT NULL THEN
                INSERT INTO storage.buckets (id, name, public)
                VALUES ('intake-media', 'intake-media', false)
                ON CONFLICT (id) DO NOTHING;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # El bucket intake-media se deja: borrarlo eliminaría fotos y audios.
    op.drop_constraint('ck_trips_review_status', 'trips', type_='check')
    op.drop_constraint('ck_trips_intake_source', 'trips', type_='check')
    op.drop_constraint('ck_trips_currency', 'trips', type_='check')
    op.drop_column('trips', 'review_notes')
    op.drop_column('trips', 'review_status')
    op.drop_column('trips', 'intake_source')
    op.drop_column('trips', 'destination_text')
    op.drop_column('trips', 'origin_text')
    op.drop_column('trips', 'currency')
    op.alter_column('trips', 'amount', existing_type=sa.Numeric(precision=12, scale=2), type_=sa.Numeric(precision=10, scale=2), existing_nullable=True)

    op.drop_index(op.f('ix_trip_cars_vin'), table_name='trip_cars')
    op.drop_constraint('ck_trip_cars_review_status', 'trip_cars', type_='check')
    op.drop_constraint('fk_trip_cars_created_by', 'trip_cars', type_='foreignkey')
    op.drop_constraint('fk_trip_cars_photo_file_id', 'trip_cars', type_='foreignkey')
    for column in ('updated_at', 'created_by', 'review_notes', 'review_status', 'photo_file_id', 'ocr_confidence',
                   'color', 'model_year', 'model', 'make_from_photo', 'check_digit_ok', 'vin_valid', 'vin_raw', 'vin'):
        op.drop_column('trip_cars', column)
    op.add_column('trip_cars', sa.Column('vin_photo_url', sa.String(), nullable=True))
    op.execute("UPDATE trip_cars SET brand = 'Sin marca' WHERE brand IS NULL")
    op.alter_column('trip_cars', 'brand', existing_type=sa.String(), nullable=False)

    op.drop_index(op.f('ix_intake_files_trip_id'), table_name='intake_files')
    op.drop_table('intake_files')

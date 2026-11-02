"""allow trips without a company truck (third-party drivers)

Revision ID: f3b9d1e7a254
Revises: e8a4c6b2d917
Create Date: 2026-11-03 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3b9d1e7a254'
down_revision: Union[str, None] = 'e8a4c6b2d917'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Los choferes "tercero" colaboran con su propio vehículo: sus viajes no llevan
    # camión de la flota. Los de los demás choferes lo siguen exigiendo en la API.
    op.alter_column('trips', 'truck_id', existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    op.alter_column('trips', 'truck_id', existing_type=sa.UUID(), nullable=False)

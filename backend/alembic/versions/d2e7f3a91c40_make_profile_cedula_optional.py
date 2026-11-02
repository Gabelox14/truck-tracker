"""make profiles.cedula optional (driver accounts created by the admin)

Revision ID: d2e7f3a91c40
Revises: c4d8a2f61b37
Create Date: 2026-11-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2e7f3a91c40'
down_revision: Union[str, None] = 'c4d8a2f61b37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Las cuentas de chofer que crea el admin pueden no tener cédula todavía. Sigue
    # siendo única cuando existe (Postgres permite varios NULL en un índice único).
    op.alter_column('profiles', 'cedula', existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column('profiles', 'cedula', existing_type=sa.String(), nullable=False)

"""enable rls on alembic_version

Revision ID: a1f4c9d2e8b3
Revises: e65cc466c119
Create Date: 2026-08-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1f4c9d2e8b3'
down_revision: Union[str, None] = 'e65cc466c119'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Supabase flags any public table without RLS as publicly accessible via
    # PostgREST (the anon key can read/write it). alembic_version holds no
    # app data, but enabling RLS with no policies closes the gap: our
    # backend connects as a role with BYPASSRLS so this is a no-op for it.
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY")

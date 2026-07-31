from sqlalchemy import Column, Table
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base

# Stub for Supabase's auth.users table, managed by Supabase itself.
# Declared here only so SQLAlchemy can resolve the FK from profiles.id;
# Alembic never creates/drops it (autogenerate only targets the default
# schema since include_schemas is not enabled in alembic/env.py).
auth_users = Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    schema="auth",
)

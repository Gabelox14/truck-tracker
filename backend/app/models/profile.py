from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base

ROLES = ("admin", "dispatcher", "driver")


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (CheckConstraint(f"role IN {ROLES}", name="ck_profiles_role"),)

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    email = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    cedula = Column(String, nullable=False, unique=True)
    role = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

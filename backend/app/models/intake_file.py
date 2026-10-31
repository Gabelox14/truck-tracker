from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database.base import Base

KINDS = ("vin_photo", "audio")
STATUSES = ("processed", "failed")


class IntakeFile(Base):
    """Foto o audio recibido. Sin trip_id es un borrador por asignar."""

    __tablename__ = "intake_files"
    __table_args__ = (
        CheckConstraint(f"kind IN {KINDS}", name="ck_intake_files_kind"),
        CheckConstraint(f"status IN {STATUSES}", name="ck_intake_files_status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    kind = Column(String, nullable=False)
    file_sha256 = Column(String(64), nullable=False, unique=True)
    storage_path = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String, nullable=False, server_default="processed")
    error = Column(String, nullable=True)
    extraction = Column(JSONB, nullable=True)
    transcript = Column(Text, nullable=True)
    duration_seconds = Column(Numeric(8, 2), nullable=True)
    ai_model = Column(String, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

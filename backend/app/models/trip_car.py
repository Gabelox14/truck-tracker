from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.trip import REVIEW_STATUSES


class TripCar(Base):
    __tablename__ = "trip_cars"
    __table_args__ = (
        CheckConstraint(f"review_status IN {REVIEW_STATUSES}", name="ck_trip_cars_review_status"),
        CheckConstraint("vehicle_class IN ('liviano', 'carga')", name="ck_trip_cars_vehicle_class"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    brand = Column(String, nullable=True)
    make_from_photo = Column(String, nullable=True)
    model = Column(String, nullable=True)
    model_year = Column(SmallInteger, nullable=True)
    color = Column(String, nullable=True)
    vin = Column(String, nullable=True, index=True)
    vin_raw = Column(String, nullable=True)
    vin_valid = Column(Boolean, nullable=True)
    check_digit_ok = Column(Boolean, nullable=True)
    ocr_confidence = Column(Numeric(3, 2), nullable=True)
    amount = Column(Numeric(12, 2), nullable=True)
    vehicle_class = Column(String, nullable=False, server_default="liviano")
    photo_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("intake_files.id", ondelete="SET NULL", name="fk_trip_cars_photo_file_id"),
        nullable=True,
    )
    review_status = Column(String, nullable=False, server_default="ok")
    review_notes = Column(Text, nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL", name="fk_trip_cars_created_by"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

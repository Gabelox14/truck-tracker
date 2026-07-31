from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base

STATUSES = ("in_progress", "completed")


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (CheckConstraint(f"status IN {STATUSES}", name="ck_trips_status"),)

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False, index=True)
    truck_id = Column(UUID(as_uuid=True), ForeignKey("trucks.id"), nullable=False, index=True)
    origin_zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    destination_zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    status = Column(String, nullable=False, server_default="in_progress")
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    amount = Column(Numeric(10, 2), nullable=True)

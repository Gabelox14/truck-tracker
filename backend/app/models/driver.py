from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base

DRIVER_TYPES = ("fijo", "suplente", "tercero")


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = (
        CheckConstraint(f"driver_type IN {DRIVER_TYPES}", name="ck_drivers_driver_type"),
        # Un camión tiene un solo chofer activo.
        Index(
            "uq_drivers_active_truck",
            "truck_id",
            unique=True,
            postgresql_where=text("active AND truck_id IS NOT NULL"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    full_name = Column(String, nullable=False)
    active = Column(Boolean, nullable=False, server_default=text("true"))
    truck_id = Column(UUID(as_uuid=True), ForeignKey("trucks.id", ondelete="SET NULL", name="fk_drivers_truck_id"), nullable=True)
    # Solo lo ve el admin: fijo, suplente o tercero.
    driver_type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

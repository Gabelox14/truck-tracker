from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.trip import CURRENCIES, TRIP_TYPES

VEHICLE_CLASSES = ("liviano", "carga")


class RouteRate(Base):
    """Tarifa de una ruta para una clase de vehículo (por vehículo trasladado)."""

    __tablename__ = "route_rates"
    __table_args__ = (
        CheckConstraint(f"category IN {TRIP_TYPES}", name="ck_route_rates_category"),
        CheckConstraint(f"vehicle_class IN {VEHICLE_CLASSES}", name="ck_route_rates_vehicle_class"),
        CheckConstraint(f"currency IN {CURRENCIES}", name="ck_route_rates_currency"),
        UniqueConstraint("category", "origin_zone_id", "destination_zone_id", "vehicle_class", name="uq_route_rates_route"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    category = Column(String, nullable=False, server_default="directo")
    origin_zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    destination_zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    vehicle_class = Column(String, nullable=False, server_default="liviano")
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, server_default="CRC")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

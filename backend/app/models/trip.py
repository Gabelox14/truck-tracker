from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base

STATUSES = ("in_progress", "completed")
TRIP_TYPES = ("directo", "indirecto")
# De qué registro sale el viaje: VINS DIRECTOS, VINS USADOS DIRECTOS o VINS PROFORMAS.
FE_TYPES = ("directo", "directo_usado", "proforma")
CURRENCIES = ("CRC", "USD")
INTAKE_SOURCES = ("manual", "upload", "whatsapp")
REVIEW_STATUSES = ("ok", "needs_review", "confirmed")


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint(f"status IN {STATUSES}", name="ck_trips_status"),
        CheckConstraint(f"trip_type IN {TRIP_TYPES}", name="ck_trips_trip_type"),
        CheckConstraint(f"fe_type IN {FE_TYPES}", name="ck_trips_fe_type"),
        CheckConstraint(f"currency IN {CURRENCIES}", name="ck_trips_currency"),
        CheckConstraint(f"intake_source IN {INTAKE_SOURCES}", name="ck_trips_intake_source"),
        CheckConstraint(f"review_status IN {REVIEW_STATUSES}", name="ck_trips_review_status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    # Null solo en viajes del registro histórico de terceros sin cuenta (ver unit_label).
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True, index=True)
    # Null en los viajes de choferes "tercero" (vehículo propio).
    truck_id = Column(UUID(as_uuid=True), ForeignKey("trucks.id"), nullable=True, index=True)
    origin_zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    destination_zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    status = Column(String, nullable=False, server_default="in_progress")
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    amount = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=False, server_default="CRC")
    trip_type = Column(String, nullable=True)
    fe_type = Column(String, nullable=True)
    origin_text = Column(String, nullable=True)
    destination_text = Column(String, nullable=True)
    requested_by = Column(String, nullable=True)
    intake_source = Column(String, nullable=False, server_default="manual")
    review_status = Column(String, nullable=False, server_default="ok")
    review_notes = Column(Text, nullable=True)
    # Unidad tal como la escribe el registro cuando no es un camión de la flota ("JP", "MYR").
    unit_label = Column(String, nullable=True)

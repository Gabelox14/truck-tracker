from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class ZoneDistance(Base):
    """Km por carretera aproximados entre dos zonas. Un registro por par, con
    zone_a_id < zone_b_id. Solo para el análisis del dashboard, no para cobrar."""

    __tablename__ = "zone_distances"
    __table_args__ = (
        CheckConstraint("zone_a_id < zone_b_id", name="ck_zone_distances_order"),
        CheckConstraint("km > 0", name="ck_zone_distances_km"),
    )

    zone_a_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), primary_key=True)
    zone_b_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), primary_key=True)
    km = Column(Numeric(7, 1), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

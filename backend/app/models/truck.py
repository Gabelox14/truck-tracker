from sqlalchemy import Column, DateTime, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base

# Solo los ve el admin; los demás roles reciben null.
ADMIN_FIELDS = ("code", "brand", "model", "year", "vin", "color", "body_type", "traction")


class Truck(Base):
    __tablename__ = "trucks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    plate = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    # Ficha del Registro Nacional.
    model = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    vin = Column(String, nullable=True)
    color = Column(String, nullable=True)
    body_type = Column(String, nullable=True)
    traction = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

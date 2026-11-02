from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DriverCreate(BaseModel):
    profile_id: UUID
    full_name: str
    truck_id: UUID
    driver_type: str


class DriverAccountCreate(BaseModel):
    """El admin da el nombre, el camión y el tipo; el correo y la contraseña los pone el sistema."""

    full_name: str
    truck_id: UUID
    driver_type: str
    cedula: str | None = None


class DriverUpdate(BaseModel):
    full_name: str | None = None
    active: bool | None = None
    truck_id: UUID | None = None
    driver_type: str | None = None


class DriverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    full_name: str
    active: bool
    created_at: datetime
    truck_id: UUID | None = None
    # Solo para el admin; a los demás les llega null.
    driver_type: str | None = None
    email: str | None = None
    # Solo en las cuentas que creó el admin; las demás entran con su email.
    username: str | None = None


class DriverCredentialsOut(BaseModel):
    """La contraseña viaja una sola vez, en la respuesta que la crea o la cambia."""

    driver: DriverOut
    username: str
    password: str

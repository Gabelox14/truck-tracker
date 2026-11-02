from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DriverCreate(BaseModel):
    profile_id: UUID
    full_name: str


class DriverAccountCreate(BaseModel):
    """El admin da el nombre; el usuario y la contraseña los pone el sistema."""

    full_name: str
    cedula: str | None = None


class DriverUpdate(BaseModel):
    full_name: str | None = None
    active: bool | None = None


class DriverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    full_name: str
    active: bool
    created_at: datetime
    email: str | None = None
    # Solo en las cuentas que creó el admin; las demás entran con su email.
    username: str | None = None


class DriverCredentialsOut(BaseModel):
    """La contraseña viaja una sola vez, en la respuesta que la crea o la cambia."""

    driver: DriverOut
    username: str
    password: str

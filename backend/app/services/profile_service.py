from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.profile import Profile
from app.models.truck import Truck
from app.repositories import profile_repository
from app.services import driver_service

DEFAULT_ROLE = "driver"


def attach_is_assigned(db: Session, profile: Profile) -> Profile:
    profile.truck_id = profile.truck_plate = None
    profile.uses_company_truck = True
    if profile.role in ("admin", "dispatcher"):
        profile.is_assigned = True
        return profile
    driver = db.query(Driver).filter(Driver.profile_id == profile.id, Driver.active.is_(True)).first()
    profile.is_assigned = driver is not None
    if driver is not None:
        # Sin revelar el tipo (es solo del admin): el tercero no elige camión.
        profile.uses_company_truck = driver_service.uses_company_truck(driver.driver_type)
    if driver is not None and driver.truck_id is not None:
        # El chofer ve su camión por placa (el código interno es solo del admin).
        truck = db.get(Truck, driver.truck_id)
        profile.truck_id, profile.truck_plate = truck.id, truck.plate
    return profile


def get_or_create_profile(
    db: Session, user_id: str, email: str, full_name: str, cedula: str
) -> Profile:
    profile = profile_repository.get_or_create(
        db, user_id, email=email, full_name=full_name, cedula=cedula, role=DEFAULT_ROLE
    )
    return attach_is_assigned(db, profile)


def update_profile_role(db: Session, profile_id: str, role: str) -> Profile | None:
    profile = profile_repository.update_role(db, profile_id, role)
    if profile is None:
        return None
    return attach_is_assigned(db, profile)


def list_profiles(db: Session) -> list[Profile]:
    return [attach_is_assigned(db, p) for p in profile_repository.list_all(db)]

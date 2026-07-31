from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.profile import Profile
from app.repositories import profile_repository

DEFAULT_ROLE = "driver"


def _attach_is_assigned(db: Session, profile: Profile) -> Profile:
    if profile.role in ("admin", "dispatcher"):
        profile.is_assigned = True
    else:
        profile.is_assigned = (
            db.query(Driver).filter(Driver.profile_id == profile.id).first() is not None
        )
    return profile


def get_or_create_profile(
    db: Session, user_id: str, email: str, full_name: str, cedula: str
) -> Profile:
    profile = profile_repository.get_or_create(
        db, user_id, email=email, full_name=full_name, cedula=cedula, role=DEFAULT_ROLE
    )
    return _attach_is_assigned(db, profile)


def update_profile_role(db: Session, profile_id: str, role: str) -> Profile | None:
    profile = profile_repository.update_role(db, profile_id, role)
    if profile is None:
        return None
    return _attach_is_assigned(db, profile)


def list_profiles(db: Session) -> list[Profile]:
    return [_attach_is_assigned(db, p) for p in profile_repository.list_all(db)]

from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.repositories import profile_repository

DEFAULT_ROLE = "driver"


def get_or_create_profile(
    db: Session, user_id: str, email: str, full_name: str, cedula: str
) -> Profile:
    return profile_repository.get_or_create(
        db, user_id, email=email, full_name=full_name, cedula=cedula, role=DEFAULT_ROLE
    )


def update_profile_role(db: Session, profile_id: str, role: str) -> Profile | None:
    return profile_repository.update_role(db, profile_id, role)


def list_profiles(db: Session) -> list[Profile]:
    return profile_repository.list_all(db)

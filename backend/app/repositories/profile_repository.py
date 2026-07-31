from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.profile import Profile


def get_or_create(
    db: Session, profile_id: str, email: str, full_name: str, cedula: str, role: str
) -> Profile:
    stmt = (
        pg_insert(Profile)
        .values(id=profile_id, email=email, full_name=full_name, cedula=cedula, role=role)
        .on_conflict_do_nothing(index_elements=["id"])
        .returning(Profile)
    )
    created = db.execute(stmt).scalar_one_or_none()
    db.commit()
    if created is not None:
        return created
    return db.get(Profile, profile_id)


def update_role(db: Session, profile_id: str, role: str) -> Profile | None:
    profile = db.get(Profile, profile_id)
    if profile is None:
        return None
    profile.role = role
    db.commit()
    db.refresh(profile)
    return profile


def list_all(db: Session) -> list[Profile]:
    return db.query(Profile).order_by(Profile.created_at.desc()).all()

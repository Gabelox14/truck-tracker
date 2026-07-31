from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose.exceptions import JWTError
from sqlalchemy.orm import Session

from app.core.security import verify_supabase_token
from app.database.session import get_db
from app.models.driver import Driver
from app.models.profile import Profile
from app.models.trip import Trip

bearer_scheme = HTTPBearer()


def get_current_user_claims(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    try:
        return verify_supabase_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def get_current_user_id(claims: dict = Depends(get_current_user_claims)) -> str:
    return claims["sub"]


def require_admin(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> str:
    profile = db.get(Profile, user_id)
    if profile is None or profile.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user_id


def require_staff(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> str:
    profile = db.get(Profile, user_id)
    if profile is None or profile.role not in ("admin", "dispatcher"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or dispatcher role required",
        )
    return user_id


def get_current_driver(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Driver:
    driver = db.query(Driver).filter(Driver.profile_id == user_id, Driver.active.is_(True)).first()
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No driver record for this user",
        )
    return driver


def require_staff_or_driver(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> str:
    profile = db.get(Profile, user_id)
    is_staff = profile is not None and profile.role in ("admin", "dispatcher")
    if is_staff:
        return user_id
    driver = db.query(Driver).filter(Driver.profile_id == user_id, Driver.active.is_(True)).first()
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No estás asignado como chofer todavía",
        )
    return user_id


def require_trip_access(
    trip_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    profile = db.get(Profile, user_id)
    is_staff = profile is not None and profile.role in ("admin", "dispatcher")
    driver = db.query(Driver).filter(Driver.profile_id == user_id).first()
    is_owner = driver is not None and driver.id == trip.driver_id
    if not (is_staff or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this trip",
        )
    return trip

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_claims, require_admin, require_staff
from app.database.session import get_db
from app.schemas.profile import ProfileOut, ProfileRoleUpdate
from app.services.profile_service import get_or_create_profile, list_profiles, update_profile_role

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileOut])
def get_profiles(
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return list_profiles(db)


@router.post("/me", response_model=ProfileOut)
def create_my_profile(
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    metadata = claims.get("user_metadata") or {}
    full_name = metadata.get("full_name")
    cedula = metadata.get("cedula")
    if not full_name or not cedula:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Faltan full_name/cedula en los metadatos del registro",
        )
    try:
        return get_or_create_profile(db, claims["sub"], claims.get("email", ""), full_name, cedula)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="cedula already registered")


@router.patch("/{profile_id}", response_model=ProfileOut)
def change_profile_role(
    profile_id: UUID,
    payload: ProfileRoleUpdate,
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    profile = update_profile_role(db, str(profile_id), payload.role)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile

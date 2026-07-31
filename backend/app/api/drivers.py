from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, require_staff
from app.database.session import get_db
from app.schemas.driver import DriverCreate, DriverOut, DriverUpdate
from app.services import driver_service

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.get("", response_model=list[DriverOut])
def list_drivers(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return driver_service.list_drivers(db, limit=limit, offset=offset)


@router.post("", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(
    payload: DriverCreate,
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    try:
        return driver_service.create_driver(db, str(payload.profile_id), payload.full_name)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="profile_id does not exist or already has a driver record",
        )


@router.get("/{driver_id}", response_model=DriverOut)
def get_driver(
    driver_id: UUID,
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    driver = driver_service.get_driver(db, str(driver_id))
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return driver


@router.patch("/{driver_id}", response_model=DriverOut)
def update_driver(
    driver_id: UUID,
    payload: DriverUpdate,
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    driver = driver_service.update_driver(db, str(driver_id), payload.full_name)
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return driver


@router.delete("/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_driver(
    driver_id: UUID,
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    if not driver_service.delete_driver(db, str(driver_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

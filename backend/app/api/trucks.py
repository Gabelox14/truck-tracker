from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_staff, require_staff_or_driver_profile, require_staff_profile
from app.database.session import get_db
from app.models.profile import Profile
from app.schemas.truck import TruckCreate, TruckOut, TruckUpdate
from app.services import truck_service

router = APIRouter(prefix="/trucks", tags=["trucks"])


def _redact(truck, is_admin: bool) -> TruckOut:
    out = TruckOut.model_validate(truck)
    if not is_admin:
        out.code = None
        out.brand = None
    return out


@router.get("", response_model=list[TruckOut])
def list_trucks(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    profile: Profile = Depends(require_staff_or_driver_profile),
    db: Session = Depends(get_db),
):
    is_admin = profile is not None and profile.role == "admin"
    trucks = truck_service.list_trucks(db, limit=limit, offset=offset)
    return [_redact(t, is_admin) for t in trucks]


@router.post("", response_model=TruckOut, status_code=status.HTTP_201_CREATED)
def create_truck(
    payload: TruckCreate,
    profile: Profile = Depends(require_staff_profile),
    db: Session = Depends(get_db),
):
    is_admin = profile is not None and profile.role == "admin"
    try:
        truck = truck_service.create_truck(
            db,
            payload.plate,
            code=payload.code if is_admin else None,
            brand=payload.brand if is_admin else None,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plate already exists")
    return _redact(truck, is_admin)


@router.get("/{truck_id}", response_model=TruckOut)
def get_truck(
    truck_id: UUID,
    profile: Profile = Depends(require_staff_or_driver_profile),
    db: Session = Depends(get_db),
):
    truck = truck_service.get_truck(db, str(truck_id))
    if truck is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Truck not found")
    is_admin = profile is not None and profile.role == "admin"
    return _redact(truck, is_admin)


@router.patch("/{truck_id}", response_model=TruckOut)
def update_truck(
    truck_id: UUID,
    payload: TruckUpdate,
    profile: Profile = Depends(require_staff_profile),
    db: Session = Depends(get_db),
):
    is_admin = profile is not None and profile.role == "admin"
    try:
        truck = truck_service.update_truck(
            db,
            str(truck_id),
            plate=payload.plate,
            code=payload.code if is_admin else None,
            brand=payload.brand if is_admin else None,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plate already exists")
    if truck is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Truck not found")
    return _redact(truck, is_admin)


@router.delete("/{truck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_truck(
    truck_id: UUID,
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    try:
        deleted = truck_service.delete_truck(db, str(truck_id))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: tiene viajes asociados",
        )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Truck not found")

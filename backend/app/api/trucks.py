from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, require_staff
from app.database.session import get_db
from app.schemas.truck import TruckCreate, TruckOut, TruckUpdate
from app.services import truck_service

router = APIRouter(prefix="/trucks", tags=["trucks"])


@router.get("", response_model=list[TruckOut])
def list_trucks(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return truck_service.list_trucks(db, limit=limit, offset=offset)


@router.post("", response_model=TruckOut, status_code=status.HTTP_201_CREATED)
def create_truck(
    payload: TruckCreate,
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    try:
        return truck_service.create_truck(db, payload.plate)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plate already exists")


@router.get("/{truck_id}", response_model=TruckOut)
def get_truck(
    truck_id: UUID,
    _user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    truck = truck_service.get_truck(db, str(truck_id))
    if truck is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Truck not found")
    return truck


@router.patch("/{truck_id}", response_model=TruckOut)
def update_truck(
    truck_id: UUID,
    payload: TruckUpdate,
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    try:
        truck = truck_service.update_truck(db, str(truck_id), payload.plate)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plate already exists")
    if truck is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Truck not found")
    return truck


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

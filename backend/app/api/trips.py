from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_driver, get_current_user_id, require_staff, require_trip_access
from app.database.session import get_db
from app.models.driver import Driver
from app.models.trip import Trip
from app.schemas.trip import TripAmountUpdate, TripCreate, TripOut
from app.schemas.trip_car import TripCarCreate, TripCarOut
from app.services import trip_service

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("", response_model=list[TripOut])
def list_trips(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return trip_service.list_trips_for_user(db, user_id, limit=limit, offset=offset)


@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def start_trip(
    payload: TripCreate,
    driver: Driver = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    try:
        return trip_service.create_trip(
            db,
            str(driver.id),
            str(payload.truck_id),
            str(payload.origin_zone_id),
            str(payload.destination_zone_id),
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="truck_id, origin_zone_id or destination_zone_id does not exist",
        )


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(trip: Trip = Depends(require_trip_access)):
    return trip


@router.post("/{trip_id}/complete", response_model=TripOut)
def complete_trip(
    trip: Trip = Depends(require_trip_access),
    db: Session = Depends(get_db),
):
    if trip.status == "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trip already completed")
    return trip_service.complete_trip(db, str(trip.id))


@router.patch("/{trip_id}/amount", response_model=TripOut)
def set_trip_amount(
    payload: TripAmountUpdate,
    trip: Trip = Depends(require_trip_access),
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return trip_service.update_trip_amount(db, str(trip.id), payload.amount)


@router.get("/{trip_id}/cars", response_model=list[TripCarOut])
def list_trip_cars(
    trip: Trip = Depends(require_trip_access),
    db: Session = Depends(get_db),
):
    return trip_service.list_trip_cars(db, str(trip.id))


@router.post("/{trip_id}/cars", response_model=TripCarOut, status_code=status.HTTP_201_CREATED)
def add_trip_car(
    payload: TripCarCreate,
    trip: Trip = Depends(require_trip_access),
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return trip_service.add_trip_car(db, str(trip.id), payload.brand, payload.vin_photo_url)


@router.delete("/{trip_id}/cars/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_trip_car(
    car_id: UUID,
    trip: Trip = Depends(require_trip_access),
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    if not trip_service.remove_trip_car(db, str(trip.id), str(car_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found")

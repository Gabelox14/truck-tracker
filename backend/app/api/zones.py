from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, require_admin
from app.database.session import get_db
from app.schemas.zone import ZoneCreate, ZoneOut, ZoneUpdate
from app.services import zone_service

router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("", response_model=list[ZoneOut])
def list_zones(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return zone_service.list_zones(db, limit=limit, offset=offset)


@router.post("", response_model=ZoneOut, status_code=status.HTTP_201_CREATED)
def create_zone(
    payload: ZoneCreate,
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return zone_service.create_zone(db, payload.name)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Zone name already exists")


@router.get("/{zone_id}", response_model=ZoneOut)
def get_zone(
    zone_id: UUID,
    _user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    zone = zone_service.get_zone(db, str(zone_id))
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return zone


@router.patch("/{zone_id}", response_model=ZoneOut)
def update_zone(
    zone_id: UUID,
    payload: ZoneUpdate,
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        zone = zone_service.update_zone(db, str(zone_id), payload.name)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Zone name already exists")
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return zone


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(
    zone_id: UUID,
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        deleted = zone_service.delete_zone(db, str(zone_id))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: tiene viajes asociados",
        )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

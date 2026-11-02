from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_staff
from app.database.session import get_db
from app.models.route_rate import RouteRate
from app.schemas.rate import RateImportOut, RouteRateCreate, RouteRateOut, RouteRateUpdate
from app.services import rate_service

router = APIRouter(prefix="/rates", tags=["rates"])

MAX_IMPORT_MB = 10


@router.get("", response_model=list[RouteRateOut])
def list_rates(
    category: str | None = None,
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return rate_service.list_rates(db, category)


@router.post("/import", response_model=RateImportOut)
def import_rates(
    file: UploadFile = File(..., description="Registro facturado en Excel con columnas RUTA, VEHICULO y MONTO"),
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = file.file.read(MAX_IMPORT_MB * 1024 * 1024 + 1)
    if len(data) > MAX_IMPORT_MB * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="El Excel pesa más de 10 MB")
    try:
        return rate_service.import_rates(db, data)
    except rate_service.RateImportError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("", response_model=RouteRateOut, status_code=status.HTTP_201_CREATED)
def create_rate(
    payload: RouteRateCreate,
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rate = RouteRate(**payload.model_dump())
    db.add(rate)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esa ruta ya tiene tarifa para esa clase de vehículo, o una zona no existe",
        )
    db.refresh(rate)
    return rate


@router.patch("/{rate_id}", response_model=RouteRateOut)
def update_rate(
    rate_id: UUID,
    payload: RouteRateUpdate,
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rate = db.get(RouteRate, rate_id)
    if rate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarifa no encontrada")
    rate.amount = payload.amount
    db.commit()
    db.refresh(rate)
    return rate


@router.delete("/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rate(
    rate_id: UUID,
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rate = db.get(RouteRate, rate_id)
    if rate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarifa no encontrada")
    db.delete(rate)
    db.commit()

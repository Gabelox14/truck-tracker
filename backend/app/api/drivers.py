from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_staff
from app.database.session import get_db
from app.models.profile import Profile
from app.schemas.driver import DriverAccountCreate, DriverCreate, DriverCredentialsOut, DriverOut, DriverUpdate
from app.services import auth_admin_service, driver_account_service, driver_service
from app.services.auth_admin_service import AuthAdminError
from app.services.driver_account_service import DriverAccountError
from app.services.driver_service import DriverAssignmentError, TruckTaken

router = APIRouter(prefix="/drivers", tags=["drivers"])

HAS_TRIPS_DETAIL = "No se puede eliminar: tiene viajes asociados. Desactivalo en su lugar."
TRUCK_RACE_DETAIL = "Ese camión acaba de quedar asignado a otro chofer; recarga y elige otro."


def get_auth_admin() -> auth_admin_service.SupabaseAuthAdmin:
    return auth_admin_service.get_auth_admin()


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, TruckTaken):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, (DriverAccountError, DriverAssignmentError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, IntegrityError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=TRUCK_RACE_DETAIL)
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


def _get_or_404(db: Session, driver_id: UUID):
    driver = driver_service.get_driver(db, str(driver_id))
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return driver


def _is_admin(db: Session, user_id: str) -> bool:
    profile = db.get(Profile, user_id)
    return profile is not None and profile.role == "admin"


def _require_admin_role(db: Session, user_id: str) -> None:
    if not _is_admin(db, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


def _out(db: Session, drivers: list, is_admin: bool) -> list[DriverOut]:
    """Con correo; el tipo de chofer solo lo ve el admin."""
    result = []
    for driver in driver_account_service.attach_usernames(db, drivers):
        out = DriverOut.model_validate(driver)
        if not is_admin:
            out.driver_type = None
        result.append(out)
    return result


@router.get("", response_model=list[DriverOut])
def list_drivers(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return _out(db, driver_service.list_drivers(db, limit=limit, offset=offset), _is_admin(db, staff_id))


@router.post("", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(
    payload: DriverCreate,
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Vincula a alguien que se registró con su email."""
    try:
        driver = driver_service.create_driver(
            db, str(payload.profile_id), payload.full_name, payload.truck_id, payload.driver_type
        )
    except (DriverAssignmentError, TruckTaken) as exc:
        raise _error(exc)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese usuario no existe, ya es chofer o el camión acaba de quedar asignado",
        )
    return _out(db, [driver], True)[0]


@router.post("/accounts", response_model=DriverCredentialsOut, status_code=status.HTTP_201_CREATED)
def create_driver_account(
    payload: DriverAccountCreate,
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
    auth: auth_admin_service.SupabaseAuthAdmin = Depends(get_auth_admin),
):
    """Crea el chofer con correo y contraseña generados, listos para entrar."""
    try:
        driver, password = driver_account_service.create_account(
            db, auth, payload.full_name, payload.truck_id, payload.driver_type, payload.cedula
        )
    except (DriverAccountError, DriverAssignmentError, TruckTaken, AuthAdminError, IntegrityError) as exc:
        raise _error(exc)
    return {"driver": _out(db, [driver], True)[0], "username": driver.username, "password": password}


@router.get("/{driver_id}", response_model=DriverOut)
def get_driver(
    driver_id: UUID,
    staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return _out(db, [_get_or_404(db, driver_id)], _is_admin(db, staff_id))[0]


@router.patch("/{driver_id}", response_model=DriverOut)
def update_driver(
    driver_id: UUID,
    payload: DriverUpdate,
    staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
    auth: auth_admin_service.SupabaseAuthAdmin = Depends(get_auth_admin),
):
    is_admin = _is_admin(db, staff_id)
    if (payload.truck_id is not None or payload.driver_type is not None) and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el admin asigna camión y tipo")
    driver = _get_or_404(db, driver_id)
    was_active = driver.active
    try:
        driver_service.apply_update(
            db,
            driver,
            full_name=payload.full_name,
            active=payload.active,
            truck_id=payload.truck_id,
            driver_type=payload.driver_type,
        )
        if driver.active != was_active:
            driver_account_service.set_login_enabled(db, auth, driver, driver.active)
        db.commit()
    except (DriverAssignmentError, TruckTaken, AuthAdminError, IntegrityError) as exc:
        db.rollback()
        raise _error(exc)
    db.refresh(driver)
    return _out(db, [driver], is_admin)[0]


@router.post("/{driver_id}/password", response_model=DriverCredentialsOut)
def reset_driver_password(
    driver_id: UUID,
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
    auth: auth_admin_service.SupabaseAuthAdmin = Depends(get_auth_admin),
):
    """Genera una contraseña nueva; la anterior deja de servir."""
    driver = _get_or_404(db, driver_id)
    try:
        password = driver_account_service.reset_password(db, auth, driver)
    except (DriverAccountError, AuthAdminError) as exc:
        raise _error(exc)
    out = _out(db, [driver], True)[0]
    return {"driver": out, "username": out.username, "password": password}


@router.delete("/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_driver(
    driver_id: UUID,
    staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
    auth: auth_admin_service.SupabaseAuthAdmin = Depends(get_auth_admin),
):
    driver = _get_or_404(db, driver_id)
    if driver_account_service.has_trips(db, driver):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=HAS_TRIPS_DETAIL)
    profile = driver_account_service.managed_profile(db, driver)
    if profile is not None:
        # Cuenta creada por el admin: se borra también su acceso.
        _require_admin_role(db, staff_id)
        try:
            driver_account_service.delete_account(auth, profile)
        except AuthAdminError as exc:
            raise _error(exc)
        return
    try:
        driver_service.delete_driver(db, str(driver_id))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=HAS_TRIPS_DETAIL)

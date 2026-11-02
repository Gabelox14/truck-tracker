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

router = APIRouter(prefix="/drivers", tags=["drivers"])

HAS_TRIPS_DETAIL = "No se puede eliminar: tiene viajes asociados. Desactivalo en su lugar."


def get_auth_admin() -> auth_admin_service.SupabaseAuthAdmin:
    return auth_admin_service.get_auth_admin()


def _account_error(exc: Exception) -> HTTPException:
    if isinstance(exc, DriverAccountError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


def _get_or_404(db: Session, driver_id: UUID):
    driver = driver_service.get_driver(db, str(driver_id))
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return driver


def _require_admin_role(db: Session, user_id: str) -> None:
    profile = db.get(Profile, user_id)
    if profile is None or profile.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


def _with_username(db: Session, driver):
    return driver_account_service.attach_usernames(db, [driver])[0]


@router.get("", response_model=list[DriverOut])
def list_drivers(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return driver_account_service.attach_usernames(db, driver_service.list_drivers(db, limit=limit, offset=offset))


@router.post("", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(
    payload: DriverCreate,
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    try:
        driver = driver_service.create_driver(db, str(payload.profile_id), payload.full_name)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="profile_id does not exist or already has a driver record",
        )
    return _with_username(db, driver)


@router.post("/accounts", response_model=DriverCredentialsOut, status_code=status.HTTP_201_CREATED)
def create_driver_account(
    payload: DriverAccountCreate,
    _admin_id: str = Depends(require_admin),
    db: Session = Depends(get_db),
    auth: auth_admin_service.SupabaseAuthAdmin = Depends(get_auth_admin),
):
    """Crea el chofer con usuario y contraseña generados, listos para entrar."""
    try:
        driver, password = driver_account_service.create_account(db, auth, payload.full_name, payload.cedula)
    except (DriverAccountError, AuthAdminError) as exc:
        raise _account_error(exc)
    return {"driver": driver, "username": driver.username, "password": password}


@router.get("/{driver_id}", response_model=DriverOut)
def get_driver(
    driver_id: UUID,
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return _with_username(db, _get_or_404(db, driver_id))


@router.patch("/{driver_id}", response_model=DriverOut)
def update_driver(
    driver_id: UUID,
    payload: DriverUpdate,
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
    auth: auth_admin_service.SupabaseAuthAdmin = Depends(get_auth_admin),
):
    driver = _get_or_404(db, driver_id)
    if payload.active is not None and payload.active != driver.active:
        try:
            driver_account_service.set_login_enabled(db, auth, driver, payload.active)
        except AuthAdminError as exc:
            raise _account_error(exc)
    driver = driver_service.update_driver(db, str(driver_id), full_name=payload.full_name, active=payload.active)
    return _with_username(db, driver)


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
        raise _account_error(exc)
    driver = _with_username(db, driver)
    return {"driver": driver, "username": driver.username, "password": password}


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
            raise _account_error(exc)
        return
    try:
        driver_service.delete_driver(db, str(driver_id))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=HAS_TRIPS_DETAIL)

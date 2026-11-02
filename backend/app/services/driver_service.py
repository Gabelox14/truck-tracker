from sqlalchemy.orm import Session

from app.models.driver import DRIVER_TYPES, Driver
from app.models.truck import Truck
from app.repositories import driver_repository


class DriverAssignmentError(ValueError):
    """Datos de asignación inválidos (422)."""


class TruckTaken(ValueError):
    """El camión ya tiene un chofer activo (409)."""


def list_drivers(db: Session, limit: int = 50, offset: int = 0) -> list[Driver]:
    return driver_repository.list_all(db, limit=limit, offset=offset)


def get_driver(db: Session, driver_id: str) -> Driver | None:
    return driver_repository.get(db, driver_id)


def truck_label(truck: Truck) -> str:
    return f"{truck.code} ({truck.plate})" if truck.code else truck.plate


def check_driver_type(driver_type: str | None) -> None:
    if driver_type not in DRIVER_TYPES:
        raise DriverAssignmentError("Elige el tipo de chofer: fijo, suplente o tercero")


def check_truck_free(db: Session, truck_id, exclude_driver_id=None) -> Truck:
    """Un camión tiene un solo chofer activo; para pasárselo a otro hay que
    desactivar primero al que lo tiene."""
    if truck_id is None:
        raise DriverAssignmentError("Asígnale un camión al chofer")
    truck = db.get(Truck, truck_id)
    if truck is None:
        raise DriverAssignmentError("Ese camión no existe")
    query = db.query(Driver).filter(Driver.truck_id == truck.id, Driver.active.is_(True))
    if exclude_driver_id is not None:
        query = query.filter(Driver.id != exclude_driver_id)
    holder = query.first()
    if holder is not None:
        raise TruckTaken(
            f"El camión {truck_label(truck)} ya lo tiene {holder.full_name}. "
            "Desactívalo primero para pasarle el camión a otro chofer."
        )
    return truck


THIRD_PARTY = "tercero"


def uses_company_truck(driver_type: str | None) -> bool:
    """El tercero colabora con su propio vehículo: no lleva camión de la flota."""
    return driver_type != THIRD_PARTY


def check_assignment(db: Session, truck_id, driver_type: str | None, exclude_driver_id=None):
    """Valida tipo y camión; devuelve el camión que corresponde (None para un tercero)."""
    check_driver_type(driver_type)
    if not uses_company_truck(driver_type):
        return None
    check_truck_free(db, truck_id, exclude_driver_id)
    return truck_id


def create_driver(db: Session, profile_id: str, full_name: str, truck_id, driver_type: str) -> Driver:
    truck_id = check_assignment(db, truck_id, driver_type)
    return driver_repository.create(db, profile_id, full_name, truck_id=truck_id, driver_type=driver_type)


def apply_update(
    db: Session,
    driver: Driver,
    full_name: str | None = None,
    active: bool | None = None,
    truck_id=None,
    driver_type: str | None = None,
) -> None:
    """Valida y aplica los cambios sin confirmar (el llamador hace commit)."""
    if driver_type is not None:
        check_driver_type(driver_type)
    new_type = driver_type if driver_type is not None else driver.driver_type
    new_active = active if active is not None else driver.active
    if not uses_company_truck(new_type):
        # Pasar a tercero libera el camión que tuviera.
        new_truck = None
    else:
        new_truck = truck_id if truck_id is not None else driver.truck_id
        assignment_changes = str(new_truck) != str(driver.truck_id) or not uses_company_truck(driver.driver_type)
        if new_active and (assignment_changes or not driver.active):
            if new_truck is None:
                raise DriverAssignmentError("Asígnale un camión (solo el tercero va sin camión)")
            check_truck_free(db, new_truck, exclude_driver_id=driver.id)
    if full_name is not None:
        driver.full_name = full_name
    driver.driver_type = new_type
    driver.truck_id = new_truck
    if active is not None:
        driver.active = active
    db.flush()


def delete_driver(db: Session, driver_id: str) -> bool:
    return driver_repository.delete(db, driver_id)

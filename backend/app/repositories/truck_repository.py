from sqlalchemy.orm import Session

from app.models.truck import Truck

MAX_LIMIT = 200


def list_all(db: Session, limit: int = 50, offset: int = 0) -> list[Truck]:
    limit = min(limit, MAX_LIMIT)
    return (
        db.query(Truck)
        .order_by(Truck.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def get(db: Session, truck_id: str) -> Truck | None:
    return db.get(Truck, truck_id)


def create(db: Session, plate: str, code: str | None = None, brand: str | None = None) -> Truck:
    truck = Truck(plate=plate, code=code, brand=brand)
    db.add(truck)
    db.commit()
    db.refresh(truck)
    return truck


def update(
    db: Session,
    truck_id: str,
    plate: str | None = None,
    code: str | None = None,
    brand: str | None = None,
) -> Truck | None:
    truck = db.get(Truck, truck_id)
    if truck is None:
        return None
    if plate is not None:
        truck.plate = plate
    if code is not None:
        truck.code = code
    if brand is not None:
        truck.brand = brand
    db.commit()
    db.refresh(truck)
    return truck


def delete(db: Session, truck_id: str) -> bool:
    truck = db.get(Truck, truck_id)
    if truck is None:
        return False
    db.delete(truck)
    db.commit()
    return True

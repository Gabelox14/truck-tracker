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


def create(db: Session, plate: str, **details) -> Truck:
    truck = Truck(plate=plate, **details)
    db.add(truck)
    db.commit()
    db.refresh(truck)
    return truck


def update(db: Session, truck_id: str, **changes) -> Truck | None:
    """Solo cambia los campos que vienen con valor (None = no tocar)."""
    truck = db.get(Truck, truck_id)
    if truck is None:
        return None
    for field, value in changes.items():
        if value is not None:
            setattr(truck, field, value)
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

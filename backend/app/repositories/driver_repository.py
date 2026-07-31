from sqlalchemy.orm import Session

from app.models.driver import Driver

MAX_LIMIT = 200


def list_all(db: Session, limit: int = 50, offset: int = 0) -> list[Driver]:
    limit = min(limit, MAX_LIMIT)
    return (
        db.query(Driver)
        .order_by(Driver.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def get(db: Session, driver_id: str) -> Driver | None:
    return db.get(Driver, driver_id)


def create(db: Session, profile_id: str, full_name: str) -> Driver:
    driver = Driver(profile_id=profile_id, full_name=full_name)
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


def update(db: Session, driver_id: str, full_name: str) -> Driver | None:
    driver = db.get(Driver, driver_id)
    if driver is None:
        return None
    driver.full_name = full_name
    db.commit()
    db.refresh(driver)
    return driver


def delete(db: Session, driver_id: str) -> bool:
    driver = db.get(Driver, driver_id)
    if driver is None:
        return False
    db.delete(driver)
    db.commit()
    return True

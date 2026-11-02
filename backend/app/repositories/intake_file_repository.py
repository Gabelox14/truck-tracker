from sqlalchemy.orm import Session

from app.models.intake_file import IntakeFile


def get(db: Session, file_id: str) -> IntakeFile | None:
    return db.get(IntakeFile, file_id)


def get_by_sha256(db: Session, file_sha256: str) -> IntakeFile | None:
    return db.query(IntakeFile).filter(IntakeFile.file_sha256 == file_sha256).first()


def list_for_trip(db: Session, trip_id: str, kind: str | None = None) -> list[IntakeFile]:
    query = db.query(IntakeFile).filter(IntakeFile.trip_id == trip_id)
    if kind is not None:
        query = query.filter(IntakeFile.kind == kind)
    return query.order_by(IntakeFile.created_at).all()


def list_children(db: Session, parent_id: str) -> list[IntakeFile]:
    return db.query(IntakeFile).filter(IntakeFile.parent_id == parent_id).order_by(IntakeFile.created_at).all()


def list_unassigned(db: Session, limit: int = 100) -> list[IntakeFile]:
    """Borradores: lecturas sin viaje (las fotos extra de un vehículo van con su principal)."""
    return (
        db.query(IntakeFile)
        .filter(IntakeFile.trip_id.is_(None), IntakeFile.status == "processed", IntakeFile.parent_id.is_(None))
        .order_by(IntakeFile.created_at.desc())
        .limit(limit)
        .all()
    )


def add(db: Session, record: IntakeFile) -> IntakeFile:
    db.add(record)
    db.flush()
    return record


def delete(db: Session, record: IntakeFile) -> None:
    db.delete(record)
    db.commit()

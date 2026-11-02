from datetime import datetime, time

from sqlalchemy.orm import Session

from app.core.time import COSTA_RICA_TZ
from app.models.intake_file import IntakeFile
from app.models.trip import Trip
from app.repositories import intake_file_repository, trip_car_repository, trip_repository
from app.schemas.intake import DraftTripCreate
from app.services import audio_intake_service, intake_service
from app.services.storage_service import SupabaseStorage


class DraftError(ValueError):
    pass


def review_queue(db: Session) -> dict:
    return {
        "trips": trip_repository.list_needing_review(db),
        "cars": trip_car_repository.list_needing_review(db),
        "drafts": intake_file_repository.list_unassigned(db),
    }


def attach_file(db: Session, record: IntakeFile, trip: Trip, user_id: str) -> None:
    """Liga un borrador a un viaje: la foto crea su carro; el audio llena el viaje."""
    if record.trip_id is not None:
        raise DraftError("Este archivo ya está ligado a un viaje")
    if record.status != "processed":
        raise DraftError("Este archivo no se pudo procesar; vuelve a subirlo")
    if record.kind == "vin_photo":
        intake_service.attach_photo_to_trip(db, record, trip, user_id)
    else:
        audio_intake_service.attach_audio_to_trip(db, record, trip, uploaded_by_staff=True)


def create_trip_from_drafts(db: Session, payload: DraftTripCreate, user_id: str) -> Trip:
    if payload.origin_zone_id == payload.destination_zone_id:
        raise DraftError("El origen y el destino tienen que ser distintos")
    records = []
    for file_id in payload.file_ids:
        record = intake_file_repository.get(db, str(file_id))
        if record is None:
            raise DraftError("Uno de los archivos ya no existe")
        if record.trip_id is not None or record.status != "processed":
            raise DraftError("Uno de los archivos ya está en un viaje o no se pudo procesar")
        records.append(record)

    started_at = (
        datetime.combine(payload.trip_date, time(12, 0), tzinfo=COSTA_RICA_TZ)
        if payload.trip_date
        else min(record.created_at for record in records)
    )
    trip = Trip(
        driver_id=payload.driver_id,
        truck_id=payload.truck_id,
        origin_zone_id=payload.origin_zone_id,
        destination_zone_id=payload.destination_zone_id,
        trip_type=payload.trip_type,
        requested_by=payload.requested_by,
        amount=payload.amount,
        currency=payload.currency,
        intake_source="upload",
        started_at=started_at,
        status="completed" if payload.completed else "in_progress",
        completed_at=started_at if payload.completed else None,
    )
    db.add(trip)
    db.flush()
    # Primero los audios (llenan el viaje) y después las fotos (se cruzan con lo dicho).
    for record in sorted(records, key=lambda r: r.kind != "audio"):
        attach_file(db, record, trip, user_id)
    db.refresh(trip)
    return trip


def discard_draft(db: Session, record: IntakeFile, storage: SupabaseStorage) -> None:
    if record.trip_id is not None:
        raise DraftError("Solo se pueden descartar archivos que no están en un viaje")
    storage.delete(record.storage_path)
    intake_file_repository.delete(db, record)

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import (
    can_access_trip,
    ensure_trip_access,
    is_staff_user,
    require_staff,
    require_staff_or_driver,
)
from app.core.config import settings
from app.database.session import get_db
from app.models.intake_file import IntakeFile
from app.models.trip import Trip
from app.repositories import intake_file_repository
from app.schemas.intake import (
    AttachFileIn,
    AudioIntakeOut,
    DraftTripCreate,
    FileUrlOut,
    IntakeFileOut,
    ReviewQueueOut,
    VinPhotoIntakeOut,
)
from app.schemas.trip import TripOut
from app.services import (
    audio_intake_service,
    audio_service,
    claude_service,
    image_service,
    intake_service,
    review_service,
    storage_service,
    transcription_service,
)

router = APIRouter(prefix="/intake", tags=["intake"])


def get_extractor() -> claude_service.ClaudeExtractor:
    try:
        return claude_service.get_extractor()
    except claude_service.ClaudeNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


def get_storage() -> storage_service.SupabaseStorage:
    return storage_service.get_storage()


def get_transcriber() -> transcription_service.Transcriber:
    try:
        return transcription_service.get_transcriber()
    except transcription_service.TranscriptionNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


def read_upload(file: UploadFile, max_mb: float) -> bytes:
    max_bytes = int(max_mb * 1024 * 1024)
    data = file.file.read(max_bytes + 1)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío")
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo pesa más de {max_mb:g} MB",
        )
    return data


def get_accessible_file(db: Session, user_id: str, file_id: UUID) -> IntakeFile:
    """Staff ve todo; un chofer, lo que subió o lo de sus viajes."""
    record = intake_file_repository.get(db, str(file_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")
    if is_staff_user(db, user_id) or str(record.created_by) == user_id:
        return record
    trip = db.get(Trip, record.trip_id) if record.trip_id else None
    if trip is None or not can_access_trip(db, user_id, trip):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a este archivo")
    return record


MAX_PHOTOS_PER_VEHICLE = 4


@router.post("/vin-photo", response_model=VinPhotoIntakeOut)
def upload_vin_photo(
    file: UploadFile | None = File(None, description="Una foto del VIN en JPEG, PNG o WebP"),
    files: list[UploadFile] | None = File(
        None, description="Varias fotos del mismo vehículo (etiqueta del VIN, carro); la primera es la principal"
    ),
    trip_id: UUID | None = Form(None, description="Viaje al que se agrega el carro; sin viaje queda como borrador"),
    user_id: str = Depends(require_staff_or_driver),
    db: Session = Depends(get_db),
    extractor: claude_service.ClaudeExtractor = Depends(get_extractor),
    storage: storage_service.SupabaseStorage = Depends(get_storage),
):
    uploads = [upload for upload in [file, *(files or [])] if upload is not None]
    if not uploads:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Falta la foto")
    if len(uploads) > MAX_PHOTOS_PER_VEHICLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Máximo {MAX_PHOTOS_PER_VEHICLE} fotos por vehículo",
        )
    trip = ensure_trip_access(db, user_id, trip_id) if trip_id else None
    datas = [read_upload(upload, settings.intake_max_image_mb) for upload in uploads]
    try:
        return intake_service.ingest_vin_photo(
            db, data=datas, user_id=user_id, trip=trip, extractor=extractor, storage=storage
        )
    except image_service.UnsupportedImageError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc))
    except claude_service.ClaudeExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except storage_service.StorageError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este archivo ya se está procesando")


@router.post("/audio", response_model=AudioIntakeOut)
def upload_audio(
    file: UploadFile = File(..., description="Nota de voz (OGG de WhatsApp, MP3, M4A, WAV, WebM o FLAC)"),
    trip_id: UUID | None = Form(None, description="Viaje al que se liga; sin viaje queda como borrador"),
    user_id: str = Depends(require_staff_or_driver),
    db: Session = Depends(get_db),
    transcriber: transcription_service.Transcriber = Depends(get_transcriber),
    extractor: claude_service.ClaudeExtractor = Depends(get_extractor),
    storage: storage_service.SupabaseStorage = Depends(get_storage),
):
    trip = ensure_trip_access(db, user_id, trip_id) if trip_id else None
    data = read_upload(file, settings.intake_max_audio_mb)
    try:
        return audio_intake_service.ingest_audio(
            db,
            data=data,
            user_id=user_id,
            trip=trip,
            uploaded_by_staff=is_staff_user(db, user_id),
            transcriber=transcriber,
            extractor=extractor,
            storage=storage,
        )
    except audio_service.UnsupportedAudioError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc))
    except (transcription_service.TranscriptionError, claude_service.ClaudeExtractionError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except storage_service.StorageError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este archivo ya se está procesando")


@router.get("/files/{file_id}/url", response_model=FileUrlOut)
def get_file_url(
    file_id: UUID,
    user_id: str = Depends(require_staff_or_driver),
    db: Session = Depends(get_db),
    storage: storage_service.SupabaseStorage = Depends(get_storage),
):
    record = get_accessible_file(db, user_id, file_id)
    try:
        url = storage.signed_url(record.storage_path)
    except storage_service.StorageError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return FileUrlOut(url=url, expires_in=storage_service.SIGNED_URL_SECONDS)


@router.get("/files", response_model=list[IntakeFileOut])
def list_trip_files(
    trip_id: UUID,
    user_id: str = Depends(require_staff_or_driver),
    db: Session = Depends(get_db),
):
    ensure_trip_access(db, user_id, trip_id)
    return intake_file_repository.list_for_trip(db, str(trip_id))


@router.get("/review-queue", response_model=ReviewQueueOut)
def get_review_queue(
    _staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    return review_service.review_queue(db)


@router.post("/files/{file_id}/attach", response_model=TripOut)
def attach_draft(
    file_id: UUID,
    payload: AttachFileIn,
    staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    record = get_accessible_file(db, staff_id, file_id)
    trip = ensure_trip_access(db, staff_id, payload.trip_id)
    try:
        review_service.attach_file(db, record, trip, staff_id)
    except review_service.DraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    db.refresh(trip)
    return trip


@router.post("/drafts/create-trip", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def create_trip_from_drafts(
    payload: DraftTripCreate,
    staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
):
    try:
        return review_service.create_trip_from_drafts(db, payload, staff_id)
    except review_service.DraftError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El chofer, el camión o una zona no existe")


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def discard_draft(
    file_id: UUID,
    staff_id: str = Depends(require_staff),
    db: Session = Depends(get_db),
    storage: storage_service.SupabaseStorage = Depends(get_storage),
):
    record = get_accessible_file(db, staff_id, file_id)
    try:
        review_service.discard_draft(db, record, storage)
    except review_service.DraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except storage_service.StorageError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

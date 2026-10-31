from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import can_access_trip, ensure_trip_access, is_staff_user, require_staff_or_driver
from app.core.config import settings
from app.database.session import get_db
from app.models.intake_file import IntakeFile
from app.models.trip import Trip
from app.repositories import intake_file_repository
from app.schemas.intake import AudioIntakeOut, FileUrlOut, VinPhotoIntakeOut
from app.services import (
    audio_intake_service,
    audio_service,
    claude_service,
    image_service,
    intake_service,
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


@router.post("/vin-photo", response_model=VinPhotoIntakeOut)
def upload_vin_photo(
    file: UploadFile = File(..., description="Foto del VIN en JPEG, PNG o WebP"),
    trip_id: UUID | None = Form(None, description="Viaje al que se agrega el carro; sin viaje queda como borrador"),
    user_id: str = Depends(require_staff_or_driver),
    db: Session = Depends(get_db),
    extractor: claude_service.ClaudeExtractor = Depends(get_extractor),
    storage: storage_service.SupabaseStorage = Depends(get_storage),
):
    trip = ensure_trip_access(db, user_id, trip_id) if trip_id else None
    data = read_upload(file, settings.intake_max_image_mb)
    try:
        return intake_service.ingest_vin_photo(
            db, data=data, user_id=user_id, trip=trip, extractor=extractor, storage=storage
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

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import require_staff_or_driver
from app.core.config import settings
from app.schemas.intake import VinPhotoResult
from app.services import claude_service, image_service, intake_service

router = APIRouter(prefix="/intake", tags=["intake"])


def get_extractor() -> claude_service.ClaudeExtractor:
    try:
        return claude_service.get_extractor()
    except claude_service.ClaudeNotConfigured as exc:
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


@router.post("/vin-photo", response_model=VinPhotoResult)
def upload_vin_photo(
    file: UploadFile = File(..., description="Foto del VIN en JPEG, PNG o WebP"),
    _user_id: str = Depends(require_staff_or_driver),
    extractor: claude_service.ClaudeExtractor = Depends(get_extractor),
):
    data = read_upload(file, settings.intake_max_image_mb)
    try:
        return intake_service.process_vin_photo(data, extractor)
    except image_service.UnsupportedImageError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc))
    except claude_service.ClaudeExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

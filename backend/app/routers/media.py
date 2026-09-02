import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.config import Settings, get_settings

router = APIRouter(tags=["media"])
SAFE_NAME = re.compile(r"^[0-9a-fA-F-]{36}\.(jpg|jpeg|mp4|mov)$")


def _media_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".mp4"):
        return "video/mp4"
    if lower.endswith(".mov"):
        return "video/quicktime"
    return "application/octet-stream"


@router.get("/media/{filename}", summary="Archivo público para Instagram")
def get_media(
    filename: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    if not SAFE_NAME.match(filename):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    path = Path(settings.media_dir) / filename
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return FileResponse(
        path,
        media_type=_media_type(filename),
        content_disposition_type="inline",
    )

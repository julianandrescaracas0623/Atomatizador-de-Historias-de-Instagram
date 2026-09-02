from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024
MIN_IMAGE_WIDTH = 500
MIN_VIDEO_SECONDS = 3
MAX_VIDEO_SECONDS = 60


@dataclass
class PreparedMedia:
    filename: str
    media_type: str
    path: Path


def _read_limited(upload: UploadFile, limit: int) -> bytes:
    data = upload.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo supera el máximo de {limit // (1024 * 1024)} MB",
        )
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío")
    return data


def _save_jpeg(data: bytes, dest: Path) -> None:
    from io import BytesIO

    try:
        image = Image.open(BytesIO(data))
        image.load()
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no es una imagen JPEG o PNG válida",
        ) from exc
    if image.width < MIN_IMAGE_WIDTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El ancho mínimo es {MIN_IMAGE_WIDTH} px (recomendado 1080×1920, 9:16)",
        )
    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        image = background
    else:
        image = image.convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, format="JPEG", quality=92, optimize=True)
    if dest.stat().st_size > MAX_IMAGE_BYTES:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen JPEG resultante supera 8 MB",
        )


def _ffprobe(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {}
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_name,codec_type,avg_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo leer el video. Usa MP4 o MOV (H.264, AAC).",
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo leer los metadatos del video",
        ) from exc


def _validate_video_probe(path: Path) -> None:
    payload = _ffprobe(path)
    if not payload:
        return
    duration = float((payload.get("format") or {}).get("duration") or 0)
    if duration and (duration < MIN_VIDEO_SECONDS or duration > MAX_VIDEO_SECONDS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El video de Story debe durar entre 3 y 60 segundos",
        )
    streams = payload.get("streams") or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video_stream:
        rate = str(video_stream.get("avg_frame_rate") or "0/1")
        try:
            num, den = rate.split("/")
            fps = float(num) / float(den) if float(den) else 0
        except (ValueError, ZeroDivisionError):
            fps = 0
        if fps and (fps < 23 or fps > 60):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El video debe estar entre 23 y 60 fps",
            )


def prepare_upload(upload: UploadFile, dest_dir: Path, stem: str) -> PreparedMedia:
    content_type = (upload.content_type or "").lower()
    name = (upload.filename or "").lower()
    is_image = content_type in {"image/jpeg", "image/jpg", "image/png"} or name.endswith(
        (".jpg", ".jpeg", ".png")
    )
    is_video = content_type in {"video/mp4", "video/quicktime"} or name.endswith((".mp4", ".mov"))
    if is_image and not is_video:
        data = _read_limited(upload, MAX_IMAGE_BYTES)
        dest = dest_dir / f"{stem}.jpg"
        _save_jpeg(data, dest)
        return PreparedMedia(filename=dest.name, media_type="image", path=dest)
    if is_video:
        data = _read_limited(upload, MAX_VIDEO_BYTES)
        suffix = ".mov" if name.endswith(".mov") or content_type == "video/quicktime" else ".mp4"
        dest = dest_dir / f"{stem}{suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        try:
            _validate_video_probe(dest)
        except HTTPException:
            dest.unlink(missing_ok=True)
            raise
        return PreparedMedia(filename=dest.name, media_type="video", path=dest)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Usa una imagen JPEG/PNG o un video MP4/MOV",
    )

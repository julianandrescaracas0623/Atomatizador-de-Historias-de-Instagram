from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import current_user
from app.media_validation import prepare_upload
from app.models import MediaType, Platform, PostType, ScheduledStory, StoryStatus, User
from app.routers.stories import _enforce_publish_cap, _parse_scheduled_at, _to_out
from app.schemas import StoryOut

router = APIRouter(prefix="/api/posts", tags=["posts"])

MAX_CAPTION = 2200  # límite de caption de Instagram
MAX_LINKEDIN_COMMENTARY = 3000
CAROUSEL_MIN = 2
CAROUSEL_MAX = 10


def _is_video(upload: UploadFile) -> bool:
    content_type = (upload.content_type or "").lower()
    name = (upload.filename or "").lower()
    return content_type in {"video/mp4", "video/quicktime"} or name.endswith((".mp4", ".mov"))


def _check_kinds(post_type: PostType, uploads: list[UploadFile]) -> None:
    """Valida el tipo de cada archivo antes de guardarlo, para no dejar archivos sueltos."""
    videos = [_is_video(u) for u in uploads]
    if post_type == PostType.feed:
        if len(uploads) != 1 or videos[0]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Un post de feed necesita exactamente una imagen")
    elif post_type == PostType.reel:
        if len(uploads) != 1 or not videos[0]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Un Reel necesita exactamente un video")
    elif post_type == PostType.carousel:
        if not CAROUSEL_MIN <= len(uploads) <= CAROUSEL_MAX:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Un carrusel necesita entre {CAROUSEL_MIN} y {CAROUSEL_MAX} archivos",
            )


@router.post("", response_model=StoryOut, status_code=status.HTTP_201_CREATED, summary="Programar feed, Reel o carrusel")
def create_post(
    _: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    post_type: Annotated[str, Form(...)],
    scheduled_at: Annotated[str, Form(...)],
    files: Annotated[list[UploadFile], File(...)],
    caption: Annotated[str, Form()] = "",
    draft: Annotated[bool, Form()] = False,
    platform: Annotated[str, Form()] = Platform.instagram.value,
) -> StoryOut:
    """Crea un post de feed, Reel o carrusel. Para Stories usa /api/stories."""
    try:
        kind = PostType(post_type)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="post_type debe ser feed, reel o carousel") from exc
    try:
        target = Platform(platform)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="platform debe ser instagram o linkedin") from exc
    if kind == PostType.story:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Para Stories usa /api/stories")

    if target == Platform.linkedin:
        if kind != PostType.feed:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="LinkedIn solo admite post de feed con una imagen")
        if not caption.strip():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="LinkedIn necesita texto en el post")
        if len(caption) > MAX_LINKEDIN_COMMENTARY:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"El texto supera {MAX_LINKEDIN_COMMENTARY} caracteres",
            )
    elif len(caption) > MAX_CAPTION:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"El caption supera {MAX_CAPTION} caracteres")

    when = _parse_scheduled_at(scheduled_at, settings)
    _check_kinds(kind, files)
    if target == Platform.linkedin and any(_is_video(u) for u in files):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="LinkedIn todavía no admite video")
    if not draft and target == Platform.instagram:
        _enforce_publish_cap(db, settings)

    dest_dir = Path(settings.media_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    prepared = [prepare_upload(upload, dest_dir, str(uuid.uuid4())) for upload in files]
    first, *rest = prepared

    story = ScheduledStory(
        filename=first.filename,
        media_type=MediaType(first.media_type),
        scheduled_at=when,
        status=StoryStatus.draft if draft else StoryStatus.pending,
        post_type=kind,
        platform=target,
        caption=caption,
        extra_filenames=[item.filename for item in rest],
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return _to_out(story)

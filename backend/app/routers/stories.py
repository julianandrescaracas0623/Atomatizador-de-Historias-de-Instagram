from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import current_user
from app.instagram.client import InstagramClient
from app.media_validation import prepare_upload
from app.models import ScheduledStory, StoryStatus, User
from app.schemas import StoryOut

router = APIRouter(prefix="/api/stories", tags=["stories"])


def _zone(settings: Settings) -> ZoneInfo:
    return ZoneInfo(settings.app_timezone)


def _parse_scheduled_at(raw: str, settings: Settings) -> datetime:
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fecha inválida. Usa ISO 8601 (YYYY-MM-DDTHH:MM)",
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_zone(settings))
    utc = parsed.astimezone(timezone.utc)
    if utc < datetime.now(timezone.utc) - timedelta(seconds=60):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha ya pasó. Elige un horario futuro.",
        )
    return utc


def _to_out(story: ScheduledStory) -> StoryOut:
    return StoryOut(
        id=story.id,
        filename=story.filename,
        media_type=story.media_type,
        post_type=story.post_type,
        platform=story.platform,
        caption=story.caption or "",
        extra_count=len(story.extra_filenames or []),
        scheduled_at=story.scheduled_at,
        status=story.status,
        instagram_media_id=story.instagram_media_id,
        error_message=story.error_message,
        created_at=story.created_at,
        media_url=f"/media/{story.filename}",
    )


def _enforce_publish_cap(db: Session, settings: Settings) -> None:
    client = InstagramClient(settings)
    try:
        quota = client.get_publishing_limit()
    finally:
        client.close()

    pending = db.scalar(
        select(func.count()).select_from(ScheduledStory).where(ScheduledStory.status == StoryStatus.pending)
    ) or 0

    if quota and quota.get("quota_total") is not None and quota.get("quota_usage") is not None:
        remaining = int(quota["quota_total"]) - int(quota["quota_usage"])
        if pending >= remaining:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Se alcanzó el tope de publicaciones de Instagram en 24 h",
            )
        return

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    used = db.scalar(
        select(func.count())
        .select_from(ScheduledStory)
        .where(
            ScheduledStory.status.in_((StoryStatus.published, StoryStatus.publishing)),
            ScheduledStory.created_at >= since,
        )
    ) or 0
    if used + pending >= settings.publishing_limit_fallback:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Se alcanzó el tope de publicaciones de Instagram en 24 h",
        )


@router.post("", response_model=StoryOut, status_code=status.HTTP_201_CREATED, summary="Programar una Story")
def create_story(
    _: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    scheduled_at: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    draft: Annotated[bool, Form()] = False,
) -> StoryOut:
    """Con draft=true la historia queda como borrador y no se publica hasta aprobarla."""
    when = _parse_scheduled_at(scheduled_at, settings)
    if not draft:
        _enforce_publish_cap(db, settings)
    dest_dir = Path(settings.media_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    prepared = prepare_upload(file, dest_dir, str(uuid.uuid4()))
    story = ScheduledStory(
        filename=prepared.filename,
        media_type=prepared.media_type,
        scheduled_at=when,
        status=StoryStatus.draft if draft else StoryStatus.pending,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return _to_out(story)


@router.get("", response_model=list[StoryOut], summary="Listar Stories programadas")
def list_stories(
    _: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    story_status: Annotated[StoryStatus | None, Query(alias="status")] = None,
) -> list[StoryOut]:
    stmt = select(ScheduledStory).order_by(ScheduledStory.scheduled_at.desc())
    if story_status is not None:
        stmt = stmt.where(ScheduledStory.status == story_status)
    rows = db.scalars(stmt).all()
    return [_to_out(row) for row in rows]


@router.post("/{story_id}/approve", response_model=StoryOut, summary="Aprobar un borrador")
def approve_story(
    story_id: uuid.UUID,
    _: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StoryOut:
    """Pasa un borrador a pending para que el worker lo publique a su hora.

    Solo la web lo llama. El MCP no expone esta acción: un agente no puede aprobar su propio contenido.
    """
    story = db.get(ScheduledStory, story_id)
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe esa Story")
    if story.status != StoryStatus.draft:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo se pueden aprobar borradores")
    if story.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha programada ya pasó. Reprográmala antes de aprobar.",
        )
    _enforce_publish_cap(db, settings)
    story.status = StoryStatus.pending
    db.commit()
    db.refresh(story)
    return _to_out(story)


@router.patch("/{story_id}", response_model=StoryOut, summary="Reprogramar un borrador o una Story pendiente")
def reschedule_story(
    story_id: uuid.UUID,
    _: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    scheduled_at: Annotated[str, Form(...)],
) -> StoryOut:
    story = db.get(ScheduledStory, story_id)
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe esa Story")
    if story.status not in (StoryStatus.draft, StoryStatus.pending):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo se reprograman borradores o pendientes")
    story.scheduled_at = _parse_scheduled_at(scheduled_at, settings)
    db.commit()
    db.refresh(story)
    return _to_out(story)


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una Story")
def delete_story(
    story_id: uuid.UUID,
    _: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    story = db.get(ScheduledStory, story_id)
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe esa Story")
    if story.status == StoryStatus.publishing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar una Story mientras se publica",
        )
    if story.status not in (StoryStatus.draft, StoryStatus.pending, StoryStatus.published, StoryStatus.failed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar una Story en este estado",
        )
    paths = [Path(settings.media_dir) / name for name in [story.filename, *(story.extra_filenames or [])]]
    db.delete(story)
    db.commit()
    for path in paths:
        path.unlink(missing_ok=True)

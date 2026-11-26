from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import or_, select

from app.config import get_settings
from app.db import SessionLocal
from app.instagram.client import InstagramClient, InstagramError
from app.linkedin.client import LinkedInClient, LinkedInError
from app.models import Platform, PostType, ScheduledStory, StoryStatus

logger = logging.getLogger(__name__)


def _media_kind(filename: str) -> str:
    return "video" if filename.lower().endswith((".mp4", ".mov")) else "image"

# Tiempo máximo razonable para una publicación completa (incluye procesar video).
STUCK_AFTER = timedelta(minutes=30)


def recover_stuck_stories() -> int:
    """Marca como fallidas las historias que quedaron en `publishing` por una caída.

    No se reintentan automáticamente: Instagram pudo haber publicado la historia
    antes de la caída, y reintentar la duplicaría. El usuario revisa en Instagram
    y decide si la reprograma.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - STUCK_AFTER
        stmt = (
            select(ScheduledStory)
            .where(
                ScheduledStory.status == StoryStatus.publishing,
                or_(
                    ScheduledStory.publishing_started_at.is_(None),
                    ScheduledStory.publishing_started_at < cutoff,
                ),
            )
            .with_for_update(skip_locked=True)
        )
        rows = list(db.scalars(stmt).all())
        for row in rows:
            row.status = StoryStatus.failed
            row.error_message = (
                "Interrumpida durante la publicación. Revisa en Instagram antes de reprogramarla "
                "para no duplicarla."
            )
        db.commit()
        if rows:
            logger.warning("Recuperadas %s historias atascadas en publishing", len(rows))
        return len(rows)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def claim_due_stories(limit: int = 5) -> list[ScheduledStory]:
    db = SessionLocal()
    try:
        stmt = (
            select(ScheduledStory)
            .where(
                ScheduledStory.status == StoryStatus.pending,
                ScheduledStory.scheduled_at <= datetime.now(timezone.utc),
            )
            .order_by(ScheduledStory.scheduled_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = list(db.scalars(stmt).all())
        started = datetime.now(timezone.utc)
        for row in rows:
            row.status = StoryStatus.publishing
            row.publishing_started_at = started
        db.commit()
        for row in rows:
            db.refresh(row)
            db.expunge(row)
        return rows
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def publish_story(story_id) -> None:
    settings = get_settings()
    db = SessionLocal()
    client: InstagramClient | None = None
    linkedin: LinkedInClient | None = None
    try:
        story = db.get(ScheduledStory, story_id)
        if story is None:
            return
        base = settings.app_public_base_url.rstrip("/")
        if story.platform == Platform.linkedin:
            linkedin = LinkedInClient(settings)
            data = (Path(settings.media_dir) / story.filename).read_bytes()
            media_id = linkedin.publish_image(story.caption, data)
        else:
            client = InstagramClient(settings)
            if story.post_type == PostType.story:
                media_id = client.publish_story(f"{base}/media/{story.filename}", story.media_type.value)
            else:
                files = [story.filename, *(story.extra_filenames or [])]
                items = [(f"{base}/media/{name}", _media_kind(name)) for name in files]
                media_id = client.publish_post(story.post_type.value, items, story.caption)
        story.status = StoryStatus.published
        story.instagram_media_id = media_id
        story.error_message = None
        db.commit()
        logger.info("Story %s publicada (%s)", story.id, media_id)
    except (InstagramError, LinkedInError) as exc:
        logger.warning("Story %s falló: %s", story_id, exc)
        story = db.get(ScheduledStory, story_id)
        if story is not None:
            story.status = StoryStatus.failed
            story.error_message = str(exc)
            db.commit()
    except Exception:
        logger.exception("Error inesperado publicando %s", story_id)
        db.rollback()
        story = db.get(ScheduledStory, story_id)
        if story is not None:
            story.status = StoryStatus.failed
            story.error_message = "Error interno al publicar"
            db.commit()
    finally:
        if client is not None:
            client.close()
        if linkedin is not None:
            linkedin.close()
        db.close()


def run_loop() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    logger.info("Worker iniciado (intervalo %ss)", settings.worker_interval_seconds)
    try:
        recover_stuck_stories()
    except Exception:
        logger.exception("No se pudo recuperar historias atascadas")
    while True:
        try:
            recover_stuck_stories()
            claimed = claim_due_stories()
            for story in claimed:
                publish_story(story.id)
        except Exception:
            logger.exception("Tick del worker falló")
        time.sleep(settings.worker_interval_seconds)


if __name__ == "__main__":
    run_loop()

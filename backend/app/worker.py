from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.instagram.client import InstagramClient, InstagramError
from app.models import ScheduledStory, StoryStatus

logger = logging.getLogger(__name__)


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
        for row in rows:
            row.status = StoryStatus.publishing
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
    client = InstagramClient(settings)
    try:
        story = db.get(ScheduledStory, story_id)
        if story is None:
            return
        public_url = f"{settings.app_public_base_url.rstrip('/')}/media/{story.filename}"
        media_id = client.publish_story(public_url, story.media_type.value)
        story.status = StoryStatus.published
        story.instagram_media_id = media_id
        story.error_message = None
        db.commit()
        logger.info("Story %s publicada (%s)", story.id, media_id)
    except InstagramError as exc:
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
        client.close()
        db.close()


def run_loop() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    logger.info("Worker iniciado (intervalo %ss)", settings.worker_interval_seconds)
    while True:
        try:
            claimed = claim_due_stories()
            for story in claimed:
                publish_story(story.id)
        except Exception:
            logger.exception("Tick del worker falló")
        time.sleep(settings.worker_interval_seconds)


if __name__ == "__main__":
    run_loop()

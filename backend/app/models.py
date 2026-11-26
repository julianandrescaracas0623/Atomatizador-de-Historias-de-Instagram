import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MediaType(str, enum.Enum):
    image = "image"
    video = "video"


class PostType(str, enum.Enum):
    story = "story"
    feed = "feed"          # una imagen en el feed
    reel = "reel"          # un video como Reel
    carousel = "carousel"  # 2 a 10 imágenes o videos


class Platform(str, enum.Enum):
    instagram = "instagram"
    linkedin = "linkedin"  # por ahora solo post de feed con una imagen


class StoryStatus(str, enum.Enum):
    draft = "draft"  # creado por un agente; no se publica hasta que un humano lo aprueba
    pending = "pending"
    publishing = "publishing"
    published = "published"
    failed = "failed"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class ScheduledStory(Base):
    __tablename__ = "scheduled_stories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType, name="media_type"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[StoryStatus] = mapped_column(
        Enum(StoryStatus, name="story_status"),
        nullable=False,
        default=StoryStatus.pending,
    )
    instagram_media_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    publishing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    post_type: Mapped[PostType] = mapped_column(
        Enum(PostType, name="post_type"),
        nullable=False,
        default=PostType.story,
        server_default=PostType.story.value,
    )
    caption: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, name="platform"),
        nullable=False,
        default=Platform.instagram,
        server_default=Platform.instagram.value,
    )
    # Archivos adicionales de un carrusel; `filename` es el primero.
    extra_filenames: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

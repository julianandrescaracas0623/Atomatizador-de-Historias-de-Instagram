from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import MediaType, PostType, StoryStatus


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    username: str


class StoryOut(BaseModel):
    id: UUID
    filename: str
    media_type: MediaType
    post_type: PostType = PostType.story
    caption: str = ""
    extra_count: int = 0
    scheduled_at: datetime
    status: StoryStatus
    instagram_media_id: str | None = None
    error_message: str | None = None
    created_at: datetime
    media_url: str

    model_config = {"from_attributes": True}


class InstagramStatusOut(BaseModel):
    configured: bool
    ig_user_id: str | None = None
    username: str | None = None
    error: str | None = None
    quota_usage: int | None = None
    quota_total: int | None = None
    token_expires_at: datetime | None = None
    token_warning: str | None = Field(
        default=None,
        description="Aviso si el token vence en 7 días o no está configurado",
    )

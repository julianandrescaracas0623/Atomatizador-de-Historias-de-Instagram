from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.deps import current_user
from app.instagram.client import InstagramClient, InstagramError
from app.models import User
from app.schemas import InstagramStatusOut

router = APIRouter(prefix="/api/instagram", tags=["instagram"])


def _token_warning(status: InstagramStatusOut) -> str | None:
    if not status.configured:
        return "Configura IG_ACCESS_TOKEN e IG_USER_ID para publicar"
    if status.error:
        return status.error
    if status.token_expires_at is None:
        return None
    from datetime import datetime, timedelta, timezone

    remaining = status.token_expires_at - datetime.now(timezone.utc)
    if remaining <= timedelta(days=7):
        return "El token de Instagram vence en menos de 7 días"
    return None


@router.get("/status", response_model=InstagramStatusOut, summary="Estado de la cuenta Instagram")
def instagram_status(
    _: Annotated[User, Depends(current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> InstagramStatusOut:
    client = InstagramClient(settings)
    try:
        if not client.configured:
            out = InstagramStatusOut(configured=False, ig_user_id=settings.ig_user_id or None)
            out.token_warning = _token_warning(out)
            return out
        account = client.get_account()
        quota = client.get_publishing_limit() or {}
        expires = client.get_token_expires_at()
        out = InstagramStatusOut(
            configured=True,
            ig_user_id=str(account.get("id") or settings.ig_user_id),
            username=account.get("username"),
            quota_usage=quota.get("quota_usage"),
            quota_total=quota.get("quota_total"),
            token_expires_at=expires,
        )
        out.token_warning = _token_warning(out)
        return out
    except InstagramError as exc:
        out = InstagramStatusOut(
            configured=client.configured,
            ig_user_id=settings.ig_user_id or None,
            error=str(exc),
        )
        out.token_warning = _token_warning(out)
        return out
    finally:
        client.close()

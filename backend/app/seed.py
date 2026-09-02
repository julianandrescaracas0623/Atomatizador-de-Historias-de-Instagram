from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import Settings
from app.models import User


def seed_user(db: Session, settings: Settings) -> None:
    existing = db.query(User).filter(User.username == settings.auth_username).one_or_none()
    if existing is None:
        db.add(
            User(
                username=settings.auth_username,
                password_hash=hash_password(settings.auth_password),
            )
        )
        db.commit()
        return
    if not existing.password_hash:
        existing.password_hash = hash_password(settings.auth_password)
        db.commit()

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, verify_password
from app.config import Settings, get_settings
from app.db import get_db
from app.deps import current_user
from app.models import User
from app.schemas import LoginIn, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut, summary="Iniciar sesión")
def login(
    body: LoginIn,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenOut:
    user = db.query(User).filter(User.username == body.username).one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos")
    return TokenOut(access_token=create_access_token(user.username, settings))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
def logout(_: Annotated[User, Depends(current_user)]) -> None:
    return None


@router.get("/me", response_model=UserOut, summary="Usuario actual")
def me(user: Annotated[User, Depends(current_user)]) -> UserOut:
    return UserOut(username=user.username)

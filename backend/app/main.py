from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import SessionLocal
from app.routers import auth, instagram, media, stories
from app.seed import seed_user


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        seed_user(db, settings)
    finally:
        db.close()
    yield


settings = get_settings()
app = FastAPI(
    title="Automatize Histories",
    description="Programar y publicar Stories en una cuenta de Instagram vía Graph API.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(stories.router)
app.include_router(instagram.router)
app.include_router(media.router)


@app.get("/api/health", tags=["health"], summary="Healthcheck")
def health() -> dict[str, str]:
    return {"status": "ok"}

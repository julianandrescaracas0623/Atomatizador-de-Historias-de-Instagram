---
name: adding-docker
description: Dockerize FastAPI + React (Vite) + PostgreSQL with a production-ready Dockerfile, docker-compose, and .dockerignore. Use when the user asks to dockerize, containerize, or add Docker support.
---

# Add Docker

Use this skill when dockerizing this app. Stack is FastAPI + Vite React + PostgreSQL, not Next.js.

## Steps

1. Confirm layout: `backend/` (Python) and `frontend/` (Vite). If the tree differs, adapt paths; do not invent a Node-only image.

2. **Backend `Dockerfile`** (multi-stage)

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

FROM base AS deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runner
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY backend/ .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Adjust the module path (`app.main:app`) to the real entrypoint. The worker process (scheduler) is a second command or a second service using the same image, e.g. `python -m app.worker`.

3. **Frontend `Dockerfile`** (build static, serve with nginx or let FastAPI mount `dist/` in production)

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine AS runner
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

4. **`.dockerignore`** (repo root)

```
.git
**/.env*
**/__pycache__
**/.venv
**/node_modules
frontend/dist
*.md
media
```

Never copy `.env` into an image. Inject at runtime.

5. **`docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: stories
      POSTGRES_USER: stories
      POSTGRES_PASSWORD: stories
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U stories"]
      interval: 5s
      timeout: 5s
      retries: 5
  api:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - media:/app/media
    depends_on:
      db:
        condition: service_healthy
  worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    command: python -m app.worker
    env_file: .env
    volumes:
      - media:/app/media
    depends_on:
      db:
        condition: service_healthy
  web:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports:
      - "80:80"
    depends_on:
      - api
volumes:
  pgdata:
  media:
```

`APP_PUBLIC_BASE_URL` must be the public HTTPS origin Instagram can fetch, not `http://localhost`.

## Notes

- Alpine/slim images; no secrets in layers
- Persistent volume for `media/` (Instagram downloads files until publish completes)
- `HEALTHCHECK` on the API in production
- Backend scheduler cannot run as a serverless function

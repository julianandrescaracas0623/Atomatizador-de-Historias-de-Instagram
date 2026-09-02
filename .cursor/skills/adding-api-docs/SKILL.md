---
name: adding-api-docs
description: Keep FastAPI OpenAPI docs accurate via Pydantic models and route types. Use when the user asks for API docs, Swagger, OpenAPI, /docs, or /redoc.
---

# Add API Documentation (FastAPI)

This project is FastAPI. Docs are built-in at `/docs` (Swagger UI) and `/redoc`. Do not add swagger-jsdoc, Express, or Next.js API-route doc generators.

## Steps

1. Use Pydantic v2 models for every request body, query params object, and response. That is what generates the schema.

2. Annotate routes with `response_model`, `status_code`, and `summary`:

```python
@router.post("/stories", response_model=StoryOut, status_code=201, summary="Programar una Story")
async def create_story(...): ...
```

3. Document auth in FastAPI so `/docs` can authorize:

```python
from fastapi.security import HTTPBearer

bearer = HTTPBearer()
```

Or cookie scheme if auth is httpOnly cookie. Match whatever the app actually uses (JWT Bearer or cookie). Document it in `OpenAPI` `securitySchemes`; do not describe a scheme the code does not implement.

4. File uploads: declare `UploadFile` plus form fields so OpenAPI shows multipart, not JSON.

5. Mark `/media/{filename}` as public (no auth) — Instagram fetches it. Everything under `/api/*` except login requires auth.

6. Add `example` values on Pydantic fields (`scheduled_at`, `status`, `media_type`) so `/docs` is usable.

7. Serve the app with the default docs URLs. Do not add a second Scalar/Swagger stack unless the user asks.

## Notes

- Schema stays in sync because it is generated from code
- Version docs with the Graph API version used in Instagram calls (document that in route descriptions, not as a second OpenAPI file)
- After adding endpoints, open `/docs` and confirm login, stories, and instagram status appear

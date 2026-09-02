---
name: instagram-stories-api
description: Publish Instagram Stories via Meta Graph API (create container, poll video, media_publish), media specs, token refresh, and the 100 posts/24h cap. Use when implementing or debugging Story scheduling, Instagram API calls, media validation, or token expiry.
---

# Instagram Stories API

Single Instagram Business/Creator account. Credentials only in env: `IG_ACCESS_TOKEN`, `IG_USER_ID`. Public file URL: `{APP_PUBLIC_BASE_URL}/media/{filename}` over HTTPS.

Graph host: `https://graph.facebook.com/v21.0` (pin a version in code; bump deliberately).

## Publish flow (two steps)

1. Create container — `POST /{ig-user-id}/media`

Image:

```
image_url=<public https url>
media_type=STORIES
```

Video:

```
video_url=<public https url>
media_type=STORIES
```

2. If video: poll `GET /{creation-id}?fields=status_code` until `FINISHED`. `IN_PROGRESS` → wait. `ERROR` → mark story `failed` with the API error, do not retry forever.

3. Publish — `POST /{ig-user-id}/media_publish` with `creation_id=<container id>`.

4. Save returned media id on the row; set status `published`. On API error, set `failed` and `error_message`.

Use `httpx`. Timeouts must outlive video processing (minutes, not seconds).

## Worker / locking

Claim due rows with `SELECT … FOR UPDATE SKIP LOCKED` where `status = 'pending'` and `scheduled_at <= now()`. Set `publishing` in the same transaction before calling Instagram. Interval ~30s is fine. Two workers must not publish the same row.

## Validate before save (fail in the form)

Do not wait until publish time.

| | Image | Video |
|---|---|---|
| Format | JPEG (PNG only if converted to JPEG before upload to IG) | MP4 or MOV, H.264/HEVC, AAC audio |
| Size | ≤ 8 MB | ≤ 100 MB |
| Duration | — | 3–60 s |
| Frame | — | 23–60 fps |
| Aspect | 9:16 recommended; min width 500 px | 9:16 recommended |
| Recommended px | 1080×1920 | 1080×1920 |

Reject with a clear API error the React form can show.

## Token (~60 days)

Long-lived user token. Expose `GET /api/instagram/status` (expiry if known, account id, whether configured). Warn in the UI when expiry is within 7 days.

Refresh when possible:

```
GET /oauth/access_token
  grant_type=fb_exchange_token
  client_id=APP_ID
  client_secret=APP_SECRET
  fb_exchange_token=CURRENT_TOKEN
```

Store the new token in env/secret store, never in PostgreSQL in plaintext unless a dedicated secrets approach is added later. Failed refresh must be visible in status, not silent.

## Rate limit

Max **100** Graph-published items per IG user per 24 hours (posts + Reels + Stories). Before accepting a new schedule, count publishes in the last 24h (successful `published` plus in-flight `publishing`). If at cap, reject the create request.

## Errors

Map Instagram error JSON into `error_message` on the row. No infinite retries. Operator can re-upload or pick a new time after fixing the file.

## Out of scope

Multiple IG accounts, posting Feed/Reels (unless asked), publishing from localhost URLs.

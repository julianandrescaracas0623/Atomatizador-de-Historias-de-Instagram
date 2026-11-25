from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class InstagramError(Exception):
    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.payload = payload or {}


def _graph_message(payload: dict[str, Any], fallback: str) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message") or error.get("error_user_msg")
        if message:
            return str(message)
    return fallback


class InstagramClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._http = httpx.Client(
            timeout=httpx.Timeout(connect=15.0, read=300.0, write=30.0, pool=15.0),
        )

    def close(self) -> None:
        self._http.close()

    @property
    def configured(self) -> bool:
        return bool(self.settings.ig_access_token and self.settings.ig_user_id)

    def _base(self) -> str:
        host = self.settings.ig_graph_host.rstrip("/")
        version = self.settings.ig_graph_version.strip("/")
        return f"{host}/{version}"

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self._base()}/{path.lstrip('/')}"
        params = dict(kwargs.pop("params", {}) or {})
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {self.settings.ig_access_token}"
        try:
            response = self._http.request(method, url, params=params, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise InstagramError(f"No se pudo contactar Instagram: {exc}") from exc
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise InstagramError(
                f"Instagram respondió {response.status_code} sin JSON",
                {"status_code": response.status_code, "text": response.text[:500]},
            ) from exc
        if not isinstance(payload, dict):
            raise InstagramError("Respuesta inesperada de Instagram", {"payload": payload})
        if response.is_error or "error" in payload:
            raise InstagramError(_graph_message(payload, f"Error HTTP {response.status_code}"), payload)
        return payload

    def create_story_container(self, public_url: str, media_type: str) -> str:
        params: dict[str, str] = {"media_type": "STORIES"}
        if media_type == "video":
            params["video_url"] = public_url
        else:
            params["image_url"] = public_url
        payload = self._request("POST", f"{self.settings.ig_user_id}/media", params=params)
        creation_id = payload.get("id")
        if not creation_id:
            raise InstagramError("Instagram no devolvió id de contenedor", payload)
        return str(creation_id)

    def wait_for_container(self, creation_id: str, *, is_video: bool) -> None:
        import time

        deadline = time.monotonic() + (600 if is_video else 90)
        interval = 5 if is_video else 2
        last_status = ""
        while time.monotonic() < deadline:
            payload = self._request("GET", creation_id, params={"fields": "status_code,status"})
            status_code = str(payload.get("status_code") or "")
            last_status = status_code
            if status_code == "FINISHED":
                return
            if status_code in {"ERROR", "EXPIRED"}:
                detail = payload.get("status") or status_code
                raise InstagramError(f"El contenedor falló: {detail}", payload)
            if status_code == "PUBLISHED":
                return
            time.sleep(interval)
        raise InstagramError(f"Instagram no terminó de procesar el medio (último estado: {last_status or 'desconocido'})")

    def publish_container(self, creation_id: str) -> str:
        payload = self._request(
            "POST",
            f"{self.settings.ig_user_id}/media_publish",
            params={"creation_id": creation_id},
        )
        media_id = payload.get("id")
        if not media_id:
            raise InstagramError("Instagram no devolvió id de la Story publicada", payload)
        return str(media_id)

    def publish_story(self, public_url: str, media_type: str) -> str:
        if not self.configured:
            raise InstagramError("Faltan IG_ACCESS_TOKEN o IG_USER_ID")
        creation_id = self.create_story_container(public_url, media_type)
        self.wait_for_container(creation_id, is_video=media_type == "video")
        return self.publish_container(creation_id)

    def get_account(self) -> dict[str, Any]:
        if not self.configured:
            raise InstagramError("Faltan IG_ACCESS_TOKEN o IG_USER_ID")
        return self._request("GET", self.settings.ig_user_id, params={"fields": "id,username"})

    def get_publishing_limit(self) -> dict[str, Any] | None:
        if not self.configured:
            return None
        try:
            payload = self._request("GET", f"{self.settings.ig_user_id}/content_publishing_limit")
        except InstagramError as exc:
            logger.warning("content_publishing_limit no disponible: %s", exc)
            return None
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            return None
        first = data[0]
        if not isinstance(first, dict):
            return None
        config = first.get("config") if isinstance(first.get("config"), dict) else {}
        usage = first.get("quota_usage")
        total = config.get("quota_total")
        return {
            "quota_usage": int(usage) if usage is not None else None,
            "quota_total": int(total) if total is not None else None,
        }

    def get_token_expires_at(self) -> datetime | None:
        if not (self.settings.ig_app_id and self.settings.ig_app_secret and self.settings.ig_access_token):
            return None
        app_token = f"{self.settings.ig_app_id}|{self.settings.ig_app_secret}"
        url = f"{self._base()}/debug_token"
        try:
            response = self._http.get(
                url,
                params={"input_token": self.settings.ig_access_token},
                headers={"Authorization": f"Bearer {app_token}"},
                timeout=20.0,
            )
            payload = response.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        expires = data.get("expires_at")
        if not expires:
            return None
        try:
            return datetime.fromtimestamp(int(expires), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

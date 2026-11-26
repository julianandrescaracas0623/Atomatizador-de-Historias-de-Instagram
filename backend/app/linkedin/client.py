"""Cliente mínimo de la API de LinkedIn (Posts e Images) para publicar un post con una imagen."""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class LinkedInError(Exception):
    pass


class LinkedInClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self._http = httpx.Client(
            timeout=httpx.Timeout(connect=15.0, read=120.0, write=60.0, pool=15.0),
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    @property
    def configured(self) -> bool:
        return bool(self.settings.linkedin_access_token and self.settings.linkedin_person_urn)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.linkedin_access_token}",
            "Linkedin-Version": self.settings.linkedin_api_version,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _url(self, path: str) -> str:
        return f"{self.settings.linkedin_api_base.rstrip('/')}/{path.lstrip('/')}"

    def _raise_for(self, response: httpx.Response, action: str) -> None:
        if response.status_code < 400:
            return
        message = f"LinkedIn rechazó {action} (HTTP {response.status_code})"
        try:
            payload: Any = response.json()
            if isinstance(payload, dict) and payload.get("message"):
                message = f"{message}: {payload['message']}"
        except json.JSONDecodeError:
            pass
        raise LinkedInError(message)

    def _send(self, method: str, url: str, action: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._http.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise LinkedInError(f"No se pudo contactar LinkedIn: {exc}") from exc
        self._raise_for(response, action)
        return response

    def upload_image(self, data: bytes) -> str:
        """Sube una imagen y devuelve su URN (urn:li:image:...)."""
        init = self._send(
            "POST",
            self._url("/rest/images"),
            "la inicialización de la imagen",
            params={"action": "initializeUpload"},
            headers=self._headers(),
            json={"initializeUploadRequest": {"owner": self.settings.linkedin_person_urn}},
        ).json()
        value = init["value"]
        self._send(
            "PUT",
            value["uploadUrl"],
            "la subida de la imagen",
            headers={"Authorization": f"Bearer {self.settings.linkedin_access_token}"},
            content=data,
        )
        return value["image"]

    def publish_image_post(self, commentary: str, image_urn: str) -> str:
        """Publica el post y devuelve su ID (urn:li:share:... o urn:li:ugcPost:...)."""
        response = self._send(
            "POST",
            self._url("/rest/posts"),
            "la publicación",
            headers=self._headers(),
            json={
                "author": self.settings.linkedin_person_urn,
                "commentary": commentary,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "content": {"media": {"id": image_urn}},
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            },
        )
        post_id = response.headers.get("x-restli-id")
        if not post_id:
            raise LinkedInError("LinkedIn publicó pero no devolvió el ID del post")
        return post_id

    def publish_image(self, commentary: str, data: bytes) -> str:
        image_urn = self.upload_image(data)
        post_id = self.publish_image_post(commentary, image_urn)
        logger.info("Post de LinkedIn publicado: %s", post_id)
        return post_id

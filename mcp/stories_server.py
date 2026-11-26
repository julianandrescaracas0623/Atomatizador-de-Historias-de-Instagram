"""Servidor MCP delgado sobre la API de Stories.

Solo programa, lista y cancela. No publica de inmediato ni aprueba borradores:
la publicación la hace el worker y la aprobación es humana, desde la web.

Variables de entorno:
  MCP_API_BASE_URL  URL del API (por defecto http://127.0.0.1:8000)
  MCP_USERNAME      usuario de la app
  MCP_PASSWORD      contraseña de la app
  MCP_UPLOAD_DIR    única carpeta de la que se pueden subir archivos
"""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".mp4", ".mov"}


class StoriesApi:
    """Cliente HTTP mínimo. Inicia sesión con usuario y contraseña y renueva el JWT si caduca."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        http: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._http = http or httpx.Client(timeout=httpx.Timeout(30.0, read=120.0))
        self._token: str | None = None

    def _login(self) -> None:
        response = self._http.post(
            f"{self.base_url}/api/auth/login",
            json={"username": self._username, "password": self._password},
        )
        if response.status_code != 200:
            raise RuntimeError(f"No se pudo iniciar sesión en el API ({response.status_code})")
        self._token = response.json()["access_token"]

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._token is None:
            self._login()
        response = self._send(method, path, **kwargs)
        if response.status_code == 401:
            self._login()
            response = self._send(method, path, **kwargs)
        if response.status_code >= 400:
            detail = _detail(response)
            raise RuntimeError(f"El API respondió {response.status_code}: {detail}")
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {self._token}"
        return self._http.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)


def _detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300]
    if isinstance(payload, dict) and "detail" in payload:
        return str(payload["detail"])
    return str(payload)[:300]


def resolve_upload(file_path: str, upload_dir: str | None) -> Path:
    """Devuelve la ruta real del archivo si está dentro de la carpeta permitida."""
    if not upload_dir:
        raise RuntimeError("MCP_UPLOAD_DIR no está configurado; no se pueden subir archivos")
    root = Path(upload_dir).resolve()
    candidate = (root / file_path).resolve() if not Path(file_path).is_absolute() else Path(file_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("El archivo está fuera de la carpeta permitida") from exc
    if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise RuntimeError("Formato no permitido. Usa jpg, jpeg, mp4 o mov")
    if not candidate.is_file():
        raise RuntimeError("El archivo no existe")
    return candidate


def build_server(api: StoriesApi | None = None, upload_dir: str | None = None) -> FastMCP:
    if api is None:
        api = StoriesApi(
            base_url=os.environ.get("MCP_API_BASE_URL", "http://127.0.0.1:8000"),
            username=os.environ.get("MCP_USERNAME", ""),
            password=os.environ.get("MCP_PASSWORD", ""),
        )
    if upload_dir is None:
        upload_dir = os.environ.get("MCP_UPLOAD_DIR")

    mcp = FastMCP("atomatizador-stories")

    @mcp.tool()
    def instagram_status() -> Any:
        """Estado de la cuenta de Instagram: usuario, cuota de publicación y vencimiento del token."""
        return api.request("GET", "/api/instagram/status")

    @mcp.tool()
    def list_stories(status: str | None = None) -> Any:
        """Lista las historias programadas. status puede ser pending, publishing, published o failed."""
        params = {"status": status} if status else None
        return api.request("GET", "/api/stories", params=params)

    def _upload(file_path: str, scheduled_at: str, draft: bool) -> Any:
        path = resolve_upload(file_path, upload_dir)
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as handle:
            return api.request(
                "POST",
                "/api/stories",
                data={"scheduled_at": scheduled_at, "draft": "true" if draft else "false"},
                files={"file": (path.name, handle.read(), mime)},
            )

    @mcp.tool()
    def schedule_story(file_path: str, scheduled_at: str) -> Any:
        """Programa una historia desde un archivo de la carpeta permitida.

        scheduled_at en ISO 8601 con hora local de Colombia, por ejemplo 2026-12-01T19:00.
        Devuelve la historia en estado pending; el worker la publica a esa hora.
        """
        return _upload(file_path, scheduled_at, draft=False)

    @mcp.tool()
    def create_draft(file_path: str, scheduled_at: str) -> Any:
        """Crea un borrador para revisión humana. No se publica hasta que el usuario lo apruebe en la web.

        scheduled_at en ISO 8601 con hora local de Colombia. Devuelve la historia en estado draft.
        """
        return _upload(file_path, scheduled_at, draft=True)

    def _upload_post(
        post_type: str,
        file_paths: list[str],
        caption: str,
        scheduled_at: str,
        draft: bool,
        platform: str = "instagram",
    ) -> Any:
        paths = [resolve_upload(p, upload_dir) for p in file_paths]
        files = []
        handles = []
        try:
            for path in paths:
                handle = path.open("rb")
                handles.append(handle)
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                files.append(("files", (path.name, handle.read(), mime)))
            return api.request(
                "POST",
                "/api/posts",
                data={
                    "post_type": post_type,
                    "scheduled_at": scheduled_at,
                    "caption": caption,
                    "draft": "true" if draft else "false",
                    "platform": platform,
                },
                files=files,
            )
        finally:
            for handle in handles:
                handle.close()

    @mcp.tool()
    def schedule_post(
        post_type: str,
        file_paths: list[str],
        scheduled_at: str,
        caption: str = "",
        platform: str = "instagram",
    ) -> Any:
        """Programa un post de feed, Reel o carrusel. post_type: feed, reel o carousel.

        platform: instagram (por defecto) o linkedin. LinkedIn solo admite feed con 1 imagen y texto obligatorio (máximo 3000 caracteres).
        feed: 1 imagen. reel: 1 video. carousel: entre 2 y 10 archivos.
        caption: texto del post (máximo 2200 caracteres en Instagram). scheduled_at en hora de Bogotá, ISO 8601.
        """
        return _upload_post(post_type, file_paths, caption, scheduled_at, draft=False, platform=platform)

    @mcp.tool()
    def create_draft_post(
        post_type: str,
        file_paths: list[str],
        scheduled_at: str,
        caption: str = "",
        platform: str = "instagram",
    ) -> Any:
        """Crea un borrador de post para revisión humana. No se publica hasta aprobarlo en la web.

        platform: instagram (por defecto) o linkedin. LinkedIn solo admite feed con 1 imagen y texto obligatorio.
        """
        return _upload_post(post_type, file_paths, caption, scheduled_at, draft=True, platform=platform)

    @mcp.tool()
    def cancel_story(story_id: str) -> Any:
        """Elimina una historia que esté pending, published o failed. No se puede cancelar mientras se publica."""
        api.request("DELETE", f"/api/stories/{story_id}")
        return {"deleted": story_id}

    return mcp


if __name__ == "__main__":
    build_server().run()

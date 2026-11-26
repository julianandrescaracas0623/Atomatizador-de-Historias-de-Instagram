import asyncio
import json
from pathlib import Path

import httpx
import pytest

from stories_server import StoriesApi, build_server, resolve_upload


def make_api(handler):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return StoriesApi("http://api.test", "user", "pass", http=http)


def login_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"access_token": "TOKEN-1"})


def test_resolve_upload_accepts_file_inside_dir(tmp_path: Path):
    f = tmp_path / "foto.jpg"
    f.write_bytes(b"x")
    assert resolve_upload("foto.jpg", str(tmp_path)) == f.resolve()


def test_resolve_upload_rejects_path_outside_dir(tmp_path: Path):
    outside = tmp_path.parent / "secreto.jpg"
    outside.write_bytes(b"x")
    try:
        with pytest.raises(RuntimeError, match="fuera de la carpeta"):
            resolve_upload(str(outside), str(tmp_path))
        with pytest.raises(RuntimeError, match="fuera de la carpeta"):
            resolve_upload("../secreto.jpg", str(tmp_path))
    finally:
        outside.unlink()


def test_resolve_upload_rejects_unknown_extension(tmp_path: Path):
    (tmp_path / "notas.txt").write_text("hola")
    with pytest.raises(RuntimeError, match="Formato no permitido"):
        resolve_upload("notas.txt", str(tmp_path))


def test_resolve_upload_requires_configured_dir():
    with pytest.raises(RuntimeError, match="MCP_UPLOAD_DIR"):
        resolve_upload("foto.jpg", None)


def test_schedule_sends_bearer_and_multipart(tmp_path: Path):
    (tmp_path / "foto.jpg").write_bytes(b"JPEGDATA")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return login_ok(request)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.read()
        seen["content_type"] = request.headers["content-type"]
        return httpx.Response(201, json={"id": "abc", "status": "pending"})

    server = build_server(api=make_api(handler), upload_dir=str(tmp_path))
    result = asyncio.run(server.call_tool("schedule_story", {"file_path": "foto.jpg", "scheduled_at": "2026-12-01T19:00"}))
    assert seen["auth"] == "Bearer TOKEN-1"
    assert seen["content_type"].startswith("multipart/form-data")
    assert b"JPEGDATA" in seen["body"]
    assert b"2026-12-01T19:00" in seen["body"]
    assert "pending" in json.dumps(result, default=str)


def test_create_draft_sends_draft_flag(tmp_path: Path):
    (tmp_path / "borrador.jpg").write_bytes(b"JPEG")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return login_ok(request)
        seen["body"] = request.read()
        return httpx.Response(201, json={"id": "d1", "status": "draft"})

    server = build_server(api=make_api(handler), upload_dir=str(tmp_path))
    asyncio.run(server.call_tool("create_draft", {"file_path": "borrador.jpg", "scheduled_at": "2026-12-02T09:00"}))
    assert b'name="draft"' in seen["body"]
    assert b"\r\ntrue\r\n" in seen["body"]


def test_relogin_once_on_401():
    logins = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            logins["n"] += 1
            return httpx.Response(200, json={"access_token": f"TOKEN-{logins['n']}"})
        if request.headers["authorization"] == "Bearer TOKEN-1":
            return httpx.Response(401, json={"detail": "Inicia sesión"})
        return httpx.Response(200, json=[])

    api = make_api(handler)
    assert api.request("GET", "/api/stories") == []
    assert logins["n"] == 2


def test_api_error_is_reported_with_detail():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return login_ok(request)
        return httpx.Response(409, json={"detail": "No se puede eliminar una Story mientras se publica"})

    api = make_api(handler)
    with pytest.raises(RuntimeError, match="mientras se publica"):
        api.request("DELETE", "/api/stories/xyz")


def test_server_exposes_only_scheduling_tools():
    server = build_server(api=make_api(login_ok), upload_dir=None)
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert names == {
        "instagram_status",
        "list_stories",
        "schedule_story",
        "create_draft",
        "schedule_post",
        "create_draft_post",
        "cancel_story",
    }
    assert not any(word in name for name in names for word in ("publish", "approve", "now"))


def test_create_draft_post_sends_linkedin_platform(tmp_path: Path):
    (tmp_path / "foto.jpg").write_bytes(b"JPEGDATA")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return login_ok(request)
        seen["body"] = request.read()
        return httpx.Response(201, json={"id": "xyz", "status": "draft", "platform": "linkedin"})

    server = build_server(api=make_api(handler), upload_dir=str(tmp_path))
    asyncio.run(
        server.call_tool(
            "create_draft_post",
            {
                "post_type": "feed",
                "file_paths": ["foto.jpg"],
                "scheduled_at": "2026-12-01T19:00",
                "caption": "Hola LinkedIn",
                "platform": "linkedin",
            },
        )
    )
    assert b'name="platform"' in seen["body"]
    assert b"linkedin" in seen["body"]
    assert b'name="draft"' in seen["body"]

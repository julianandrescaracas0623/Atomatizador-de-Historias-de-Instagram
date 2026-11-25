import itertools
from urllib.parse import parse_qs

import httpx
import pytest

from app.config import Settings
from app.instagram.client import InstagramClient, InstagramError


def make_client(calls: list[dict]):
    ids = itertools.count(1)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        params = {k: v[0] for k, v in parse_qs(request.url.query.decode()).items()}
        if request.method == "POST" and path.endswith("/media"):
            calls.append({"op": "create", "params": params})
            return httpx.Response(200, json={"id": f"c{next(ids)}"})
        if request.method == "GET":
            return httpx.Response(200, json={"status_code": "FINISHED"})
        if request.method == "POST" and path.endswith("/media_publish"):
            calls.append({"op": "publish", "params": params})
            return httpx.Response(200, json={"id": "PUBLISHED-1"})
        return httpx.Response(404, json={"error": {"message": "unexpected"}})

    settings = Settings(ig_access_token="TEST-TOKEN", ig_user_id="999", ig_graph_host="https://graph.test")
    client = InstagramClient(settings)
    client._http = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_feed_image_creates_and_publishes():
    calls: list[dict] = []
    client = make_client(calls)
    media_id = client.publish_post("feed", [("https://x/a.jpg", "image")], "Hola")
    assert media_id == "PUBLISHED-1"
    assert calls[0]["op"] == "create"
    assert calls[0]["params"] == {"image_url": "https://x/a.jpg", "caption": "Hola"}
    assert calls[-1]["op"] == "publish"


def test_reel_uses_reels_media_type():
    calls: list[dict] = []
    client = make_client(calls)
    client.publish_post("reel", [("https://x/v.mp4", "video")], "Mira")
    assert calls[0]["params"] == {"media_type": "REELS", "video_url": "https://x/v.mp4", "caption": "Mira"}


def test_carousel_children_then_parent_then_publish():
    calls: list[dict] = []
    client = make_client(calls)
    client.publish_post("carousel", [("https://x/1.jpg", "image"), ("https://x/2.mp4", "video")], "Dos")
    creates = [c for c in calls if c["op"] == "create"]
    # dos hijos y un padre
    assert len(creates) == 3
    assert creates[0]["params"] == {"is_carousel_item": "true", "image_url": "https://x/1.jpg"}
    assert creates[1]["params"] == {
        "is_carousel_item": "true",
        "media_type": "VIDEO",
        "video_url": "https://x/2.mp4",
    }
    parent = creates[2]["params"]
    assert parent["media_type"] == "CAROUSEL"
    assert parent["caption"] == "Dos"
    assert parent["children"] == "c1,c2"
    assert "caption" not in creates[0]["params"]  # los hijos no llevan caption
    assert calls[-1]["op"] == "publish"


def test_feed_rejects_video():
    client = make_client([])
    with pytest.raises(InstagramError, match="exactamente una imagen"):
        client.publish_post("feed", [("https://x/v.mp4", "video")], "")


def test_carousel_rejects_more_than_ten():
    client = make_client([])
    items = [(f"https://x/{i}.jpg", "image") for i in range(11)]
    with pytest.raises(InstagramError, match="entre 2 y 10"):
        client.publish_post("carousel", items, "")


def test_unknown_post_type_rejected():
    client = make_client([])
    with pytest.raises(InstagramError, match="no soportado"):
        client.publish_post("story", [("https://x/a.jpg", "image")], "")

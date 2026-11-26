import json

import httpx
import pytest

from app.config import Settings
from app.linkedin.client import LinkedInClient, LinkedInError

PERSON = "urn:li:person:abc123"
IMAGE = "urn:li:image:C4D10AQ"


def make_client(handler):
    settings = Settings(
        linkedin_access_token="LI-TEST-TOKEN",
        linkedin_person_urn=PERSON,
        linkedin_api_base="https://api.linkedin.test",
        linkedin_api_version="202506",
    )
    return LinkedInClient(settings, transport=httpx.MockTransport(handler))


def happy_handler(seen: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/rest/images":
            assert request.url.params["action"] == "initializeUpload"
            return httpx.Response(
                200,
                json={"value": {"uploadUrl": "https://upload.test/blob", "image": IMAGE}},
            )
        if request.url.host == "upload.test":
            return httpx.Response(201)
        if request.url.path == "/rest/posts":
            return httpx.Response(201, headers={"x-restli-id": "urn:li:share:999"})
        return httpx.Response(404, json={"message": "unexpected"})

    return handler


def test_publish_image_sends_expected_requests():
    seen: list[httpx.Request] = []
    client = make_client(happy_handler(seen))

    post_id = client.publish_image("Hola LinkedIn", b"fake-jpeg-bytes")

    assert post_id == "urn:li:share:999"
    init, upload, post = seen
    assert json.loads(init.content)["initializeUploadRequest"]["owner"] == PERSON
    assert init.headers["Authorization"] == "Bearer LI-TEST-TOKEN"
    assert init.headers["Linkedin-Version"] == "202506"
    assert upload.content == b"fake-jpeg-bytes"
    body = json.loads(post.content)
    assert body["author"] == PERSON
    assert body["commentary"] == "Hola LinkedIn"
    assert body["content"]["media"]["id"] == IMAGE
    assert body["lifecycleState"] == "PUBLISHED"
    assert body["visibility"] == "PUBLIC"


def test_init_upload_error_is_reported():
    def handler(request):
        return httpx.Response(403, json={"message": "Not enough permissions"})

    client = make_client(handler)
    with pytest.raises(LinkedInError, match="Not enough permissions"):
        client.publish_image("x", b"data")


def test_upload_failure_stops_before_posting():
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        if request.url.path == "/rest/images":
            return httpx.Response(200, json={"value": {"uploadUrl": "https://upload.test/blob", "image": IMAGE}})
        return httpx.Response(500, json={"message": "upload broke"})

    client = make_client(handler)
    with pytest.raises(LinkedInError, match="subida de la imagen"):
        client.publish_image("x", b"data")
    assert all(r.url.path != "/rest/posts" for r in seen)


def test_missing_post_id_is_an_error():
    def handler(request):
        if request.url.path == "/rest/images":
            return httpx.Response(200, json={"value": {"uploadUrl": "https://upload.test/blob", "image": IMAGE}})
        if request.url.host == "upload.test":
            return httpx.Response(201)
        return httpx.Response(201)

    client = make_client(handler)
    with pytest.raises(LinkedInError, match="ID del post"):
        client.publish_image("x", b"data")


def test_configured_requires_token_and_person_urn():
    assert not LinkedInClient(Settings(linkedin_access_token="", linkedin_person_urn=PERSON)).configured
    assert not LinkedInClient(Settings(linkedin_access_token="t", linkedin_person_urn="")).configured
    assert LinkedInClient(Settings(linkedin_access_token="t", linkedin_person_urn=PERSON)).configured

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from bgremove import web
from tests.conftest import make_image


@pytest.fixture
def client():
    with TestClient(web.create_app(enable_bot=False)) as c:
        yield c


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Background" in r.text


def test_remove_returns_png(client):
    r = client.post("/api/remove", files={"file": ("my photo!.jpg", make_image(fmt="JPEG"), "image/jpeg")})
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert 'filename="my_photo_nobg.png"' in r.headers["content-disposition"]
    img = Image.open(io.BytesIO(r.content))
    assert img.mode == "RGBA" and img.getpixel((0, 0))[3] == 0


def test_garbage_is_422(client):
    r = client.post("/api/remove", files={"file": ("x.png", b"nope", "image/png")})
    assert r.status_code == 422


def test_empty_file_is_422(client):
    r = client.post("/api/remove", files={"file": ("x.png", b"", "image/png")})
    assert r.status_code == 422


def test_oversize_is_413(client, monkeypatch):
    monkeypatch.setattr(web, "MAX_UPLOAD_BYTES", 10)
    r = client.post("/api/remove", files={"file": ("x.png", make_image(), "image/png")})
    assert r.status_code == 413


def test_missing_file_is_422(client):
    assert client.post("/api/remove").status_code == 422

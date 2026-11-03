import io

import pytest
from PIL import Image

from bgremove import core
from tests.conftest import make_image


def test_returns_rgba_png_with_alpha():
    out = core.remove_background(make_image())
    img = Image.open(io.BytesIO(out))
    assert img.format == "PNG"
    assert img.mode == "RGBA"
    assert img.getpixel((0, 0))[3] == 0
    assert img.getpixel((10, 10))[3] == 255


def test_accepts_jpeg_input():
    out = core.remove_background(make_image(fmt="JPEG"))
    assert Image.open(io.BytesIO(out)).format == "PNG"


def test_invalid_bytes_raise_image_error():
    with pytest.raises(core.ImageError):
        core.remove_background(b"definitely not an image")


def test_large_images_are_downscaled(monkeypatch):
    monkeypatch.setattr(core, "MAX_DIM", 100)
    out = core.remove_background(make_image(size=(400, 200)))
    assert max(Image.open(io.BytesIO(out)).size) == 100


@pytest.mark.asyncio
async def test_async_wrapper():
    out = await core.aremove(make_image())
    assert Image.open(io.BytesIO(out)).mode == "RGBA"

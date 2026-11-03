import io

import pytest
from PIL import Image

from bgremove import core


@pytest.fixture(autouse=True)
def stub_model(monkeypatch):
    """Replace the ONNX cutout with a deterministic fake: top-left pixel becomes transparent."""

    def fake_cutout(img):
        out = img.copy()
        out.putpixel((0, 0), (0, 0, 0, 0))
        return out

    monkeypatch.setattr(core, "_cutout", fake_cutout)


def make_image(size=(64, 48), fmt="PNG", color=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()

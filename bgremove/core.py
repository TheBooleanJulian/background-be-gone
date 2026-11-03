"""Shared background-removal core.

Both front ends (Telegram bot and web app) call into this module so the
behaviour is identical: decode -> fix EXIF orientation -> cap resolution ->
cut out subject(s) -> encode as RGBA PNG.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import threading

from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger("bgremove.core")

# u2net = fast general purpose; isnet-general-use = sharper edges, slower.
MODEL = os.environ.get("REMBG_MODEL", "u2net")
# Longest side is capped before inference to keep RAM/CPU bounded on small hosts.
MAX_DIM = int(os.environ.get("MAX_DIM", "2048"))
# How many cutouts may run at once across the whole process (web + bot share this).
MAX_CONCURRENCY = int(os.environ.get("MAX_CONCURRENCY", "2"))


class ImageError(ValueError):
    """The input bytes are not a usable image."""


_session = None
_session_lock = threading.Lock()
_semaphore: asyncio.Semaphore | None = None


def _get_session():
    global _session
    with _session_lock:
        if _session is None:
            from rembg import new_session

            logger.info("Loading rembg model %s", MODEL)
            _session = new_session(MODEL)
        return _session


def warmup() -> None:
    """Load the ONNX model now so the first real request is not slow."""
    _get_session()


def _cutout(img: Image.Image) -> Image.Image:
    """Run the model. Isolated so tests can replace it without the ONNX model."""
    from rembg import remove

    return remove(img, session=_get_session())


def remove_background(data: bytes) -> bytes:
    """Blocking: image bytes in, transparent PNG bytes out."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageError("That file is not a readable image.") from exc

    img = ImageOps.exif_transpose(img).convert("RGBA")
    if max(img.size) > MAX_DIM:
        img.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)

    out = _cutout(img).convert("RGBA")

    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


async def aremove(data: bytes) -> bytes:
    """Async wrapper: runs in a worker thread, bounded by MAX_CONCURRENCY."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    async with _semaphore:
        return await asyncio.to_thread(remove_background, data)

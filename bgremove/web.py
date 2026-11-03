"""Web front end (FastAPI). Optionally runs the Telegram bot in the same process."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from . import core

logger = logging.getLogger("bgremove.web")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "15"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


def _safe_stem(name: str | None) -> str:
    stem = Path(name or "image").stem
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")
    return (stem or "image")[:60]


def create_app(enable_bot: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Load the model in the background so the server accepts traffic immediately.
        warm = asyncio.create_task(asyncio.to_thread(_safe_warmup))
        tg = None
        token = os.environ.get("BOT_TOKEN", "").strip()
        if enable_bot and token:
            from .bot import build_application

            tg = build_application(token)
            await tg.initialize()
            await tg.start()
            await tg.updater.start_polling(drop_pending_updates=True)
            logger.info("Telegram bot polling started")
        elif enable_bot:
            logger.warning("BOT_TOKEN not set; running web only")
        try:
            yield
        finally:
            if tg is not None:
                await tg.updater.stop()
                await tg.stop()
                await tg.shutdown()
            warm.cancel()

    app = FastAPI(title="Background Remover", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz():
        return {"ok": True, "model": core.MODEL}

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    @app.post("/api/remove")
    async def remove(file: UploadFile = File(...)):
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"File is larger than {MAX_UPLOAD_MB}MB.")
        if not data:
            raise HTTPException(422, "Empty file.")
        try:
            png = await core.aremove(data)
        except core.ImageError as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception:  # noqa: BLE001
            logger.exception("Cutout failed")
            return JSONResponse({"detail": "Processing failed."}, status_code=500)
        name = f"{_safe_stem(file.filename)}_nobg.png"
        return Response(
            png,
            media_type="image/png",
            headers={"Content-Disposition": f'inline; filename="{name}"'},
        )

    return app


def _safe_warmup() -> None:
    try:
        core.warmup()
    except Exception:  # noqa: BLE001
        logger.exception("Model warmup failed; will retry on first request")

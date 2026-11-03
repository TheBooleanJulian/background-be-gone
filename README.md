# Background Remover: web app + Telegram bot

One shared cutout core (`bgremove/core.py`, powered by `rembg`/ONNX) with two front ends:

- **Telegram bot** (polling): send, forward, or upload-as-file any image and get a transparent PNG back.
- **Web app** (FastAPI + one `static/index.html`): drag/drop, paste, or pick multiple images, preview on
  different backdrops, download each as PNG. Also usable as a Telegram Mini App.

Both call the same `core.remove_background`, so results are identical. A process-wide semaphore
(`MAX_CONCURRENCY`) keeps web and bot requests from overloading the host.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # set BOT_TOKEN (optional for web-only)
set -a && source .env && set +a

python main.py            # web + bot in one process (default)
python main.py web        # web only
python main.py bot        # bot only
```

Web UI at `http://localhost:8080`. API: `POST /api/remove` (multipart field `file`) returns `image/png`.
Health check: `GET /healthz`.

## Telegram Mini App

Set `WEB_URL=https://your-domain` and `/start` will show an "Open web app" button that opens the
web UI inside Telegram. Must be HTTPS.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite stubs the ONNX model, so it needs no model download and runs fast in CI.

## Hosting note

`rembg` needs Python + onnxruntime and a few hundred MB of RAM, so this **cannot run on Cloudflare
Workers/Pages**. Use a small VPS, Fly.io, Railway, or any Docker host:

```bash
docker build -t bg-remover .
docker run -d --restart unless-stopped -p 8080:8080 --env-file .env bg-remover
```

The image bakes in the default model so restarts are instant. Put Cloudflare (proxy + DNS, and
optionally Cloudflare Access) in front of the VPS if you want the domain handled there.

The web endpoint is open by default. If you expose it publicly, add Cloudflare Access or rate
limiting, since each request costs CPU.

## Tuning

- `REMBG_MODEL=isnet-general-use` for cleaner hair/fur edges (slower).
- `MAX_DIM` caps the longest side before inference (default 2048).
- Multiple subjects are kept automatically; everything detected as foreground survives.
- Telegram bots can only download files up to 20MB; the bot says so rather than failing silently.

"""Entry point.

    python main.py          # web + Telegram bot in one process (default)
    python main.py web      # web app only
    python main.py bot      # Telegram bot only (polling)

MODE env var is used when no argument is given.
"""

import logging
import os
import sys

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)


def main() -> None:
    mode = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MODE", "all")).lower()
    if mode not in {"all", "web", "bot"}:
        raise SystemExit("Usage: python main.py [all|web|bot]")

    if mode == "bot":
        from bgremove import core
        from bgremove.bot import build_application

        token = os.environ.get("BOT_TOKEN", "").strip()
        if not token:
            raise SystemExit("BOT_TOKEN is required in bot mode")
        core.warmup()
        build_application(token).run_polling(drop_pending_updates=True)
        return

    import uvicorn

    from bgremove.web import create_app

    uvicorn.run(
        create_app(enable_bot=(mode == "all")),
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
        log_level="info",
    )


if __name__ == "__main__":
    main()

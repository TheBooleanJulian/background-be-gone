"""Telegram front end (polling). Accepts uploaded, forwarded and as-file images."""

from __future__ import annotations

import io
import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update, WebAppInfo
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from . import core

logger = logging.getLogger("bgremove.bot")

# Bots cannot download files larger than this via getFile.
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


def pick_image_file(message):
    """Return (telegram file object, size) for a photo or image document, else None.

    Forwarded messages carry the same `photo` / `document` fields as direct
    uploads, so one code path covers both.
    """
    if getattr(message, "photo", None):
        photo = message.photo[-1]  # largest resolution
        return photo, photo.file_size
    doc = getattr(message, "document", None)
    if doc and doc.mime_type and doc.mime_type.startswith("image/"):
        return doc, doc.file_size
    return None


def _web_keyboard() -> InlineKeyboardMarkup | None:
    url = os.environ.get("WEB_URL", "").strip()
    if not url.startswith("https://"):  # Telegram Mini Apps require HTTPS
        return None
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Open web app", web_app=WebAppInfo(url=url))]]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send me a photo (or forward one) and I'll return a transparent PNG "
        "with the background removed.\n\n"
        "Tip: send it as a file/document for the best quality.",
        reply_markup=_web_keyboard(),
    )


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat_id = update.effective_chat.id

    picked = pick_image_file(message)
    if picked is None:
        await message.reply_text("That doesn't look like an image I can process.")
        return
    tg_file, size = picked

    if size and size > MAX_FILE_SIZE_BYTES:
        await message.reply_text(
            "That file is over Telegram's 20MB bot download limit. Try a smaller version."
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
    status = await message.reply_text("Removing background…")
    try:
        file = await tg_file.get_file()
        raw = bytes(await file.download_as_bytearray())
        png = await core.aremove(raw)
        # send_document, not send_photo: photos are recompressed and lose alpha.
        await context.bot.send_document(
            chat_id=chat_id,
            document=InputFile(io.BytesIO(png), filename="no_background.png"),
            caption="Background removed.",
            reply_to_message_id=message.message_id,
        )
    except core.ImageError:
        await message.reply_text("I couldn't read that as an image.")
    except Exception:  # noqa: BLE001
        logger.exception("Failed to process image from chat %s", chat_id)
        await message.reply_text("Something went wrong processing that image. Please try again.")
    finally:
        try:
            await status.delete()
        except Exception:  # noqa: BLE001
            pass


async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("Send me a photo or an image file.")


def build_application(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler(["start", "help"], start))
    images = filters.PHOTO | filters.Document.IMAGE
    app.add_handler(MessageHandler(images, handle_image))
    app.add_handler(MessageHandler(~images & ~filters.COMMAND, handle_other))
    return app

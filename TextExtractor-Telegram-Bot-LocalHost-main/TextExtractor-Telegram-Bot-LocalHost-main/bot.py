import asyncio
import importlib.util
import pkgutil
import sys
from typing import Final

if not hasattr(pkgutil, "find_loader"):
    def _find_loader(name):
        return importlib.util.find_spec(name)

    pkgutil.find_loader = _find_loader

import pytesseract
from PIL import Image
from telegram import Update
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi, I’m an image-to-text bot.\n\n"
        "- In private chat: just send me an image.\n"
        "- In groups: reply to an image with /ext, or send /ext with an image."
    )


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usage:\n"
        "- Private chat: send an image, I’ll extract the text.\n"
        "- Group chat: reply to an image with /ext, or send /ext on a message that has an image."
    )


# OCR_CONFIG = r"-l eng+khm --oem 3 --psm 6"
OCR_CONFIG = r'-l eng --oem 3 --psm 6'


async def _extract_text_from_photo(message) -> str:

    photo = message.photo[-1]
    img_file = await photo.get_file()

    file_path = "temp_image.png"
    await img_file.download_to_drive(file_path)

    img = Image.open(file_path)

    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(
        None,
        lambda: pytesseract.image_to_string(img, config=OCR_CONFIG),
    )
    return text.strip()


async def ext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /ext command:
    - If used as a reply to an image: extracts from the replied image.
    - Else, if the message itself has an image: extracts from that image.
    """
    message = update.message
    if not message:
        return

    target_message = None

    # Case 1: /ext is a reply to a photo message
    if message.reply_to_message and message.reply_to_message.photo:
        target_message = message.reply_to_message
    # Case 2: /ext message itself has a photo
    elif message.photo:
        target_message = message

    if not target_message:
        await message.reply_text(
            "Please reply to an image with /ext, or send /ext with an image."
        )
        return

    await message.reply_text("Pg extract text, jam tic...")

    try:
        extext = await _extract_text_from_photo(target_message)
        if extext:
            await message.reply_text(f"Extracted text:\n{extext}")
        else:
            await message.reply_text("I couldn't find any readable text in that image.")
    except Exception as e:
        await message.reply_text(f"Error while extracting text:\n{e}")


async def main() -> None:
    if not TOKEN:
        print("BOT_TOKEN is not set. Please set the BOT_TOKEN environment variable.")
        sys.exit(1)

    application = Application.builder().token(TOKEN).build()

    # Register commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("ext", ext))

    # Auto-extract in private chats only (no command needed)
    async def auto_ext_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        if not message or not message.photo:
            return
        if message.chat.type != "private":
            return

        await message.reply_text("Pg extract text, jam tic...")
        try:
            extext = await _extract_text_from_photo(message)
            if extext:
                await message.reply_text(f"Extracted text:\n{extext}")
            else:
                await message.reply_text("I couldn't find any readable text in that image.")
        except Exception as e:
            await message.reply_text(f"Error while extracting text:\n{e}")

    application.add_handler(MessageHandler(filters.PHOTO, auto_ext_private))

    print("Polling...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Conflict as exc:
        print(f"Telegram conflict: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Bot stopped.")

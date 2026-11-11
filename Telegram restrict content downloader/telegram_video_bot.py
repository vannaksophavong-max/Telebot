"""
Telegram Bot - Download Restricted/Protected Videos from Groups
================================================================
Requirements:
    pip install telethon python-dotenv

Setup:
    1. Get API credentials from https://my.telegram.org/apps
    2. Create a bot via @BotFather on Telegram
    3. Fill in your credentials in the .env file
    4. Run: python telegram_video_bot.py
"""

import os
import re
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChannelPrivateError, ChatAdminRequiredError

# ── Config ───────────────────────────────────────────────────────────────────
load_dotenv()

API_ID       = int(os.getenv("API_ID", "0"))
API_HASH     = os.getenv("API_HASH", "")
BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
SESSION_NAME = os.getenv("SESSION_NAME", "userbot_session")
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))

DOWNLOAD_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)

# ── Two separate clients ──────────────────────────────────────────────────────
# user_client → YOUR Telegram account  (fetches restricted content)
# bot_client  → Bot account            (talks to users)

user_client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
bot_client  = TelegramClient("bot_session", API_ID, API_HASH)


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_message_link(link: str):
    """
    Parse t.me link → (chat_id, message_id)
    Private thread:  https://t.me/c/1234567890/TOPIC_ID/MESSAGE_ID
    Private:         https://t.me/c/1234567890/42
    Public thread:   https://t.me/channelname/TOPIC_ID/MESSAGE_ID
    Public:          https://t.me/channelname/42
    """
    # Private channel with topic/thread (3 numbers)
    m = re.match(r"https?://t\.me/c/(\d+)/(\d+)/(\d+)", link)
    if m:
        return int("-100" + m.group(1)), int(m.group(3))

    # Private channel without topic (2 numbers)
    m = re.match(r"https?://t\.me/c/(\d+)/(\d+)", link)
    if m:
        return int("-100" + m.group(1)), int(m.group(2))

    # Public channel with topic/thread (3 parts)
    m = re.match(r"https?://t\.me/([^/]+)/(\d+)/(\d+)", link)
    if m:
        return m.group(1), int(m.group(3))

    # Public channel without topic (2 parts)
    m = re.match(r"https?://t\.me/([^/]+)/(\d+)", link)
    if m:
        return m.group(1), int(m.group(2))

    return None, None


async def progress_callback(current, total, status_msg):
    if total:
        try:
            pct = current * 100 // total
            if pct % 10 == 0:
                bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                await status_msg.edit(
                    f"⬇️ Downloading…\n`[{bar}]` {pct}%\n"
                    f"{current // 1024 // 1024} MB / {total // 1024 // 1024} MB"
                )
        except Exception:
            pass


# ── Bot handlers ──────────────────────────────────────────────────────────────

@bot_client.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.respond(
        "👋 **Restricted Video Downloader**\n\n"
        "Send me a Telegram message link and I'll download the video.\n\n"
        "**Supported formats:**\n"
        "• `https://t.me/channelname/123`\n"
        "• `https://t.me/c/1234567890/123`\n\n"
        "⚠️ Your account must be a member of the group/channel.",
        parse_mode="md",
    )


@bot_client.on(events.NewMessage(pattern=r"https?://t\.me/"))
async def link_handler(event):
    link = event.raw_text.strip()
    chat_id, msg_id = parse_message_link(link)

    if not chat_id or not msg_id:
        await event.respond("❌ Invalid link. Please send a valid t.me message link.")
        return

    status = await event.respond("🔍 Fetching message…")

    try:
        # ✅ Use USER client to get entity (fixes the PeerChannel error)
        entity = await user_client.get_entity(chat_id)
        message = await user_client.get_messages(entity, ids=msg_id)

        if not message:
            await status.edit("❌ Message not found. Make sure your account is in that group.")
            return

        if not message.media:
            await status.edit("❌ No media found in that message.")
            return

        await status.edit("⬇️ Downloading… 0%")

        filename = DOWNLOAD_DIR / f"{msg_id}.mp4"

        # ✅ Download via USER client
        await user_client.download_media(
            message,
            file=str(filename),
            progress_callback=lambda c, t: asyncio.ensure_future(
                progress_callback(c, t, status)
            ),
        )

        await status.edit("📤 Uploading to Telegram…")

        # ✅ Send via BOT client
        await bot_client.send_file(
            event.chat_id,
            str(filename),
            caption=f"✅ Downloaded from:\n{link}",
            supports_streaming=True,
        )

        await status.delete()
        filename.unlink(missing_ok=True)
        log.info("✅ Delivered video to user %s", event.sender_id)

    except FloodWaitError as e:
        await status.edit(f"⏳ Flood wait {e.seconds}s, please try again later.")
        await asyncio.sleep(e.seconds)

    except ChannelPrivateError:
        await status.edit(
            "🔒 Your account is not a member of that private channel.\n"
            "Please join the group first, then try again."
        )

    except ChatAdminRequiredError:
        await status.edit("🔒 Admin rights required to access that chat.")

    except Exception as exc:
        log.exception("Unexpected error: %s", exc)
        await status.edit(f"❌ Error: `{exc}`")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    if not API_ID or not API_HASH or not BOT_TOKEN:
        raise SystemExit(
            "\n❌ Missing credentials!\n"
            "Please fill in API_ID, API_HASH, and BOT_TOKEN in your .env file.\n"
        )

    log.info("Starting user client…")
    await user_client.start()  # asks phone + OTP on first run only

    log.info("Starting bot client…")
    await bot_client.start(bot_token=BOT_TOKEN)

    log.info("✅ Bot is running — press Ctrl+C to stop.")
    await bot_client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
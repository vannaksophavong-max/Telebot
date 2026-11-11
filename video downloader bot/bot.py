import os
import logging
import asyncio
import tempfile
import re
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction
import yt_dlp

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN = "7635884119:AAFspowvQNt2DcoZQgczSnfa054Y7DQil2s"
MAX_FILE_SIZE_MB = 50          # Telegram Bot API limit for sendVideo
DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "tg_video_bot"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── URL helpers ───────────────────────────────────────────────────────────────
URL_PATTERN = re.compile(
    r"https?://(?:www\.)?"
    r"(?:youtube\.com/watch|youtu\.be/|"
    r"tiktok\.com/|vm\.tiktok\.com/|"
    r"instagram\.com/(?:p|reel|tv)/|"
    r"facebook\.com/|fb\.watch/|"
    r"twitter\.com/|x\.com/)"
    r"\S+",
    re.IGNORECASE,
)

def detect_platform(url: str) -> str:
    url_l = url.lower()
    if "youtube" in url_l or "youtu.be" in url_l:
        return "YouTube"
    if "tiktok" in url_l:
        return "TikTok"
    if "instagram" in url_l:
        return "Instagram"
    if "facebook" in url_l or "fb.watch" in url_l:
        return "Facebook"
    if "twitter" in url_l or "x.com" in url_l:
        return "Twitter / X"
    return "Unknown"

def platform_emoji(platform: str) -> str:
    return {
        "YouTube": "▶️",
        "TikTok": "🎵",
        "Instagram": "📸",
        "Facebook": "👥",
        "Twitter / X": "🐦",
    }.get(platform, "🌐")

# ── yt-dlp helpers ────────────────────────────────────────────────────────────
def _ydl_opts(output_template: str, format_id: str | None = None) -> dict:
    opts = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
    }
    if format_id:
        # Merge selected video stream with best available audio
        opts["format"] = f"{format_id}+bestaudio/bestvideo+bestaudio/best"
    else:
        # Best mp4 under 50 MB, fall back to best available
        opts["format"] = (
            "bestvideo[ext=mp4][filesize<45M]+bestaudio[ext=m4a]/"
            "best[ext=mp4][filesize<45M]/best"
        )
    return opts


async def fetch_info(url: str) -> dict | None:
    """Return video metadata without downloading."""
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
    loop = asyncio.get_event_loop()
    try:
        def _run():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        return await loop.run_in_executor(None, _run)
    except Exception as exc:
        logger.error("fetch_info error: %s", exc)
        return None


async def download_video(url: str, output_path: str, format_id: str | None = None) -> str | None:
    """Download video; return the final file path or None on failure."""
    opts = _ydl_opts(output_path, format_id)
    loop = asyncio.get_event_loop()
    try:
        def _run():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        result = await loop.run_in_executor(None, _run)
        # yt-dlp may rename to .mp4 after merging
        if result and not Path(result).exists():
            mp4 = Path(result).with_suffix(".mp4")
            if mp4.exists():
                return str(mp4)
        return result
    except Exception as exc:
        logger.error("download_video error: %s", exc)
        return None

# ── Build quality keyboard ────────────────────────────────────────────────────
def quality_keyboard(info: dict, url: str) -> InlineKeyboardMarkup:
    formats = info.get("formats", [])
    seen, buttons = set(), []

    # Collect distinct video heights
    heights = sorted(
        {f["height"] for f in formats if f.get("height") and f.get("vcodec") != "none"},
        reverse=True,
    )

    for h in heights[:5]:           # top 5 resolutions
        label = f"{h}p"
        if label not in seen:
            seen.add(label)
            # Pick best format_id for this height
            best = next(
                (f for f in reversed(formats)
                 if f.get("height") == h and f.get("vcodec") != "none"),
                None,
            )
            fmt_id = best["format_id"] if best else "best"
            buttons.append(
                InlineKeyboardButton(
                    f"📹 {label}",
                    callback_data=f"dl|{fmt_id}|{url}",
                )
            )

    # Audio-only option
    buttons.append(
        InlineKeyboardButton("🎵 Audio only (MP3)", callback_data=f"dl|audio|{url}")
    )

    # Best quality shortcut
    buttons.insert(
        0,
        InlineKeyboardButton("⭐ Best quality", callback_data=f"dl|best|{url}"),
    )

    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)

# ── Handlers ──────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to Video Downloader Bot!*\n\n"
        "Send me any video link from:\n"
        "▶️ YouTube  |  🎵 TikTok  |  📸 Instagram  |  👥 Facebook\n\n"
        "I'll fetch the available qualities and download it for you.\n\n"
        "Commands:\n"
        "/start – show this message\n"
        "/help  – usage guide",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *How to use:*\n\n"
        "1. Paste a video URL into the chat.\n"
        "2. Choose quality or audio-only.\n"
        "3. Wait for the download — I'll send it straight here!\n\n"
        "⚠️ *Limits:*\n"
        f"• Max file size: {MAX_FILE_SIZE_MB} MB (Telegram limit)\n"
        "• Playlists are not supported — send individual video URLs.\n\n"
        "✅ *Supported sites:* YouTube, TikTok, Instagram, Facebook, and many more via yt-dlp.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    match = URL_PATTERN.search(text)
    if not match:
        return  # ignore non-URL messages

    url = match.group(0)
    platform = detect_platform(url)
    emoji = platform_emoji(platform)

    status_msg = await update.message.reply_text(
        f"{emoji} *{platform}* link detected!\n🔍 Fetching video info…",
        parse_mode=ParseMode.MARKDOWN,
    )
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    info = await fetch_info(url)
    if not info:
        await status_msg.edit_text(
            "❌ Couldn't fetch video info. The link may be private, expired, or unsupported."
        )
        return

    title = info.get("title", "Unknown title")[:60]
    duration = info.get("duration")
    dur_str = f"{int(duration // 60)}m {int(duration % 60)}s" if duration else "unknown"

    caption = (
        f"{emoji} *{title}*\n"
        f"⏱ Duration: {dur_str}\n"
        f"🌐 Platform: {platform}\n\n"
        "Choose quality:"
    )

    try:
        keyboard = quality_keyboard(info, url)
    except Exception:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬇️ Download best", callback_data=f"dl|best|{url}")]]
        )

    await status_msg.edit_text(caption, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if not data.startswith("dl|"):
        return

    _, fmt_id, url = data.split("|", 2)
    chat_id = query.message.chat_id

    await query.edit_message_text("⬇️ Downloading… please wait.")
    await ctx.bot.send_chat_action(chat_id, ChatAction.UPLOAD_VIDEO)

    # Build output template
    out_tmpl = str(DOWNLOAD_DIR / "%(id)s.%(ext)s")

    # Handle audio-only
    if fmt_id == "audio":
        audio_opts = {
            "outtmpl": out_tmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
        loop = asyncio.get_event_loop()
        try:
            def _run_audio():
                with yt_dlp.YoutubeDL(audio_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return ydl.prepare_filename(info)
            file_path = await loop.run_in_executor(None, _run_audio)
            # yt-dlp renames to .mp3
            mp3_path = Path(file_path).with_suffix(".mp3")
            if mp3_path.exists():
                file_path = str(mp3_path)
        except Exception as exc:
            logger.error("Audio download error: %s", exc)
            await query.edit_message_text("❌ Audio download failed. Please try again.")
            return

        if not file_path or not Path(file_path).exists():
            await query.edit_message_text("❌ Audio file not found after download.")
            return

        size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            await query.edit_message_text(
                f"❌ File is too large ({size_mb:.1f} MB). Telegram allows max {MAX_FILE_SIZE_MB} MB."
            )
            Path(file_path).unlink(missing_ok=True)
            return

        await ctx.bot.send_chat_action(chat_id, ChatAction.UPLOAD_VOICE)
        with open(file_path, "rb") as f:
            await ctx.bot.send_audio(chat_id, f, caption="🎵 Here's your audio!")
        Path(file_path).unlink(missing_ok=True)
        await query.edit_message_text("✅ Audio sent!")
        return

    # Video download
    actual_fmt = None if fmt_id == "best" else fmt_id
    file_path = await download_video(url, out_tmpl, actual_fmt)

    if not file_path or not Path(file_path).exists():
        # Retry with best
        file_path = await download_video(url, out_tmpl, None)

    if not file_path or not Path(file_path).exists():
        await query.edit_message_text("❌ Download failed. The quality may be unavailable. Try another option.")
        return

    size_mb = Path(file_path).stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        await query.edit_message_text(
            f"❌ File too large ({size_mb:.1f} MB). Telegram allows max {MAX_FILE_SIZE_MB} MB.\n"
            "Try a lower quality."
        )
        Path(file_path).unlink(missing_ok=True)
        return

    await ctx.bot.send_chat_action(chat_id, ChatAction.UPLOAD_VIDEO)
    with open(file_path, "rb") as f:
        await ctx.bot.send_video(
            chat_id,
            f,
            caption=f"✅ Here's your video! ({size_mb:.1f} MB)",
            supports_streaming=True,
        )
    Path(file_path).unlink(missing_ok=True)
    await query.edit_message_text("✅ Done! Enjoy your video 🎉")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("Set the BOT_TOKEN environment variable before running!")

    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot is running…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

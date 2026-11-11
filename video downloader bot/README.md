# 🎬 Video Downloader Telegram Bot

A Telegram bot that downloads videos from YouTube, TikTok, Instagram, Facebook, and many more platforms powered by `yt-dlp`.

---

## ✨ Features

- ▶️ **YouTube** — any public video
- 🎵 **TikTok** — public videos
- 📸 **Instagram** — Reels, posts, IGTV
- 👥 **Facebook** — public videos
- 🌐 **500+ other sites** via yt-dlp
- 📹 **Quality selector** — choose resolution before downloading
- 🎵 **Audio-only** — extract MP3 from any video
- ⚡ Async — handles multiple users at once

---

## 🚀 Setup (Local)

### 1. Prerequisites

- Python 3.11+
- `ffmpeg` installed on your system
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: Download from https://ffmpeg.org/download.html

### 2. Get a Bot Token

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token (looks like `123456789:ABCdef...`)

### 3. Install & Run

```bash
# Clone or copy the files
cd video_downloader_bot

# Install dependencies
pip install -r requirements.txt

# Set your bot token
export BOT_TOKEN="your_token_here"      # Linux/macOS
set BOT_TOKEN=your_token_here           # Windows CMD

# Run the bot
python bot.py
```

---

## 🐳 Docker Deployment (Recommended)

Docker bundles ffmpeg automatically — no manual install needed.

```bash
# Build
docker build -t video-bot .

# Run
docker run -d \
  --name video-bot \
  -e BOT_TOKEN="your_token_here" \
  --restart unless-stopped \
  video-bot
```

---

## ☁️ Deploy to a Server (24/7)

For always-on hosting, deploy to any VPS (e.g., DigitalOcean, Hetzner, AWS EC2):

```bash
# On the server:
git clone <your-repo>
cd video_downloader_bot
docker build -t video-bot .
docker run -d -e BOT_TOKEN="your_token" --restart unless-stopped video-bot
```

Free options: [Railway](https://railway.app), [Render](https://render.com) (using Docker).

---

## 📁 Project Structure

```
video_downloader_bot/
├── bot.py            ← Main bot code
├── requirements.txt  ← Python dependencies
├── Dockerfile        ← Docker build file
├── .env.example      ← Environment variable template
└── README.md
```

---

## ⚠️ Limitations

| Limit | Details |
|-------|---------|
| File size | Max **50 MB** (Telegram Bot API limit) |
| Private content | Cannot download private/login-required videos |
| Playlists | Not supported — send individual video URLs |
| Rate limits | Some platforms may temporarily block downloads |

---

## 🔧 Customization

- **Change max file size**: Edit `MAX_FILE_SIZE_MB` in `bot.py`
- **Add more platforms**: yt-dlp supports 500+ sites out of the box — just send the URL
- **Change download quality default**: Edit the `format` field in `_ydl_opts()`

---

## 📄 License

MIT — use freely, modify as needed.

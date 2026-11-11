from telebot import TeleBot
import yt_dlp
import tempfile
import os

TOKEN = '8740655060:AAGpSKjbt25PwxTB1lHuYDxGQApx40FpQNo'
bot = TeleBot(TOKEN)


def cleanup(temp_dir):
    try:
        if temp_dir and os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)  # FIX: moved outside the loop
    except:
        pass


def download_video(url):
    temp_dir = tempfile.mkdtemp(prefix='download_')
    media_item = []
    ydl_opts = {
        'quiet': True,
        'format': 'mp4/best',
        'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),  # FIX: (id)s → %(id)s
        'merge_output_format': 'mp4',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            entries = info.get('entries', [info])
            for entry in entries:
                file_path = ydl.prepare_filename(entry)
                if os.path.exists(file_path):
                    media_item.append({
                        'type': 'video',
                        'path': file_path,
                        'title': entry.get('title') or '---'
                    })
        return {'temp_dir': temp_dir, 'items': media_item}
    except Exception as e:
        cleanup(temp_dir)
        return {'error': f'Error downloading video: {str(e)}'}


@bot.message_handler(commands=['start'])
def start(message):
    first_name = message.from_user.first_name or 'Friend'
    bot.send_message(message.chat.id, f'Hello {first_name}!\n I am a downloader bot. Send me a link to download content 🎬.')


@bot.message_handler(func=lambda message: True)
def handle(message):
    url = message.text.strip()
    if not url.startswith('http'):
        bot.send_message(message.chat.id, 'Please send a valid URL starting with http or https.')
        return

    loading = bot.send_message(message.chat.id, 'Downloading... Please wait ⏳')
    result = download_video(url)

    if 'error' in result:
        bot.edit_message_text(result['error'], message.chat.id, loading.message_id)
        return

    temp_dir = result['temp_dir']
    items = result['items']

    if not items:
        bot.edit_message_text('No media found to download.', message.chat.id, loading.message_id)
        cleanup(temp_dir)
        return

    try:
        for item in items:
            path = item['path']
            title = item['title']
            with open(path, 'rb') as f:  # FIX: open file properly for sending
                bot.send_video(message.chat.id, f, caption=title, parse_mode='HTML')
        bot.delete_message(message.chat.id, loading.message_id)
    except Exception as e:
        bot.edit_message_text(f'Error sending video: {str(e)}', message.chat.id, loading.message_id)
    finally:
        cleanup(temp_dir)  # FIX: always clean up after sending


bot.infinity_polling()
import os
import logging
import time
import sys # Import sys to exit
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import yt_dlp

# --- CONFIGURATION (READ FROM ENVIRONMENT VARIABLES) ---
TOKEN = os.environ.get("BOT_TOKEN")
DUMP_CHANNEL_ID_STR = os.environ.get("DUMP_CHANNEL_ID")

# --- VALIDATION ---
if not TOKEN:
    print("ERROR: BOT_TOKEN environment variable not found.")
    sys.exit(1)
if not DUMP_CHANNEL_ID_STR:
    print("ERROR: DUMP_CHANNEL_ID environment variable not found.")
    sys.exit(1)

DUMP_CHANNEL_ID = int(DUMP_CHANNEL_ID_STR)

# --- The rest of your code is exactly the same ---

# Enable logging to see errors
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to hold progress message details
progress_message = None
last_update_time = 0

def format_bytes(size):
    # ... (rest of the function is the same)
    if size is None:
        return "N/A"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power and n < len(power_labels) -1 :
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

def progress_hook(d):
    # ... (rest of the function is the same)
    global progress_message, last_update_time
    if d['status'] == 'downloading':
        current_time = time.time()
        if current_time - last_update_time < 2:
            return
        last_update_time = current_time
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
        downloaded_bytes = d.get('downloaded_bytes', 0)
        speed = d.get('speed')
        eta = d.get('eta')
        if total_bytes:
            percent = downloaded_bytes / total_bytes * 100
            progress_bar = '█' * int(percent / 5) + '░' * (20 - int(percent / 5))
            text = (f"**PROGRESS:**\n" f"[{progress_bar}] {percent:.1f}%\n\n" f"📦 **SIZE:** {format_bytes(downloaded_bytes)} / {format_bytes(total_bytes)}\n" f"⚡️ **SPEED:** {format_bytes(speed)}/s\n" f"ETA: {eta}s\n" f"FILE: `{d['filename']}`")
            try:
                progress_message.edit_text(text, parse_mode='Markdown')
            except Exception as e:
                logger.warning(f"Failed to edit message: {e}")

def start(update: Update, context: CallbackContext):
    # ... (rest of the function is the same)
    user = update.effective_user
    welcome_message = (f"👋 HEY {user.first_name}!\n\n" "🤖 I'm VidXtractor\n\n" "I CAN DOWNLOAD VIDEOS FROM:\n" "• YOUTUBE, INSTAGRAM, TIKTOK\n" "• PORNHUB, XVIDEOS, XNXX\n" "• AND 1000+ CORN / OTHER SITES!\n\n" "JUST SEND ME A LINK!")
    update.message.reply_text(welcome_message)

def handle_link(update: Update, context: CallbackContext):
    # ... (rest of the function is the same)
    global progress_message, last_update_time
    url = update.message.text
    chat_id = update.message.chat_id
    progress_message = update.message.reply_text("Processing link, please wait...")
    last_update_time = 0
    ydl_opts = {'format': 'best[ext=mp4][height<=720]/best[ext=mp4]/best', 'outtmpl': '%(title)s.%(ext)s', 'progress_hooks': [progress_hook], 'nocheckcertificate': True, 'postprocessors': [{'key': 'FFmpegMetadata', 'add_metadata': True,}]}
    video_path = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            progress_message.edit_text("Download complete. Now uploading...")
            with open(video_path, 'rb') as video_file:
                context.bot.send_video(chat_id=chat_id, video=video_file, caption=f"🎥 `{info['title']}`\n\nDownloaded via @{context.bot.username}", supports_streaming=True)
            logger.info(f"Uploading {video_path} to dump channel {DUMP_CHANNEL_ID}")
            with open(video_path, 'rb') as video_file:
                 context.bot.send_video(chat_id=DUMP_CHANNEL_ID, video=video_file, caption=f"Title: {info['title']}\nURL: {url}\nUser: {update.effective_user.id} ({update.effective_user.first_name})")
            progress_message.delete()
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        progress_message.edit_text("❌ **DOWNLOAD FAILED!**\n\nTHE VIDEO COULD NOT BE DOWNLOADED.")
    finally:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
            logger.info(f"Cleaned up file: {video_path}")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    updater.start_polling()
    logger.info("Bot started!")
    updater.idle()

if __name__ == '__main__':
    main()
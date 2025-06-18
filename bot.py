import os
import logging
import time
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import yt_dlp

# --- CONFIGURATION ---
TOKEN = "YOUR_BOT_API_TOKEN_HERE"  # Get this from BotFather
DUMP_CHANNEL_ID = -1001234567890   # The ID of your private channel

# Enable logging to see errors
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to hold progress message details
progress_message = None
last_update_time = 0

# --- HELPER FUNCTIONS ---

def format_bytes(size):
    """Converts bytes to a human-readable format (KB, MB, GB)."""
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
    """The function that yt-dlp calls to report progress."""
    global progress_message, last_update_time
    
    if d['status'] == 'downloading':
        # Throttle updates to avoid hitting Telegram API limits
        current_time = time.time()
        if current_time - last_update_time < 2: # Update every 2 seconds
            return
        last_update_time = current_time

        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
        downloaded_bytes = d.get('downloaded_bytes', 0)
        speed = d.get('speed')
        eta = d.get('eta')
        
        if total_bytes:
            percent = downloaded_bytes / total_bytes * 100
            progress_bar = '█' * int(percent / 5) + '░' * (20 - int(percent / 5))
            
            # This is the message format from your screenshot
            text = (
                f"**PROGRESS:**\n"
                f"[{progress_bar}] {percent:.1f}%\n\n"
                f"📦 **SIZE:** {format_bytes(downloaded_bytes)} / {format_bytes(total_bytes)}\n"
                f"⚡️ **SPEED:** {format_bytes(speed)}/s\n"
                f"ETA: {eta}s\n"
                f"FILE: `{d['filename']}`"
            )
            
            try:
                # Edit the message with the new progress
                progress_message.edit_text(text, parse_mode='Markdown')
            except Exception as e:
                logger.warning(f"Failed to edit message: {e}")


# --- BOT HANDLERS ---

def start(update: Update, context: CallbackContext):
    """Handler for the /start command. Replicates your screenshot's welcome message."""
    user = update.effective_user
    welcome_message = (
        f"👋 HEY {user.first_name}!\n\n"
        "🤖 I'm VidXtractor\n\n"
        "I CAN DOWNLOAD VIDEOS FROM:\n"
        "• YOUTUBE, INSTAGRAM, TIKTOK\n"
        "• PORNHUB, XVIDEOS, XNXX\n"
        "• AND 1000+ CORN / OTHER SITES!\n\n"
        "JUST SEND ME A LINK!"
    )
    update.message.reply_text(welcome_message)

def handle_link(update: Update, context: CallbackContext):
    """Handles video links sent by the user."""
    global progress_message, last_update_time
    
    url = update.message.text
    chat_id = update.message.chat_id
    
    # Send a "please wait" message and store it for progress updates
    progress_message = update.message.reply_text("Processing link, please wait...")
    last_update_time = 0
    
    ydl_opts = {
        'format': 'best[ext=mp4][height<=720]/best[ext=mp4]/best', # Download best MP4 format up to 720p
        'outtmpl': '%(title)s.%(ext)s', # Output filename
        'progress_hooks': [progress_hook],
        'nocheckcertificate': True,
        'postprocessors': [{
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        }],
    }
    
    video_path = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            
            progress_message.edit_text("Download complete. Now uploading...")
            
            # 1. Send video to the user
            with open(video_path, 'rb') as video_file:
                context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=f"🎥 `{info['title']}`\n\nDownloaded via @{context.bot.username}",
                    supports_streaming=True
                )
            
            # 2. Send video to the DUMP CHANNEL
            logger.info(f"Uploading {video_path} to dump channel {DUMP_CHANNEL_ID}")
            with open(video_path, 'rb') as video_file:
                 context.bot.send_video(
                    chat_id=DUMP_CHANNEL_ID,
                    video=video_file,
                    caption=f"Title: {info['title']}\nURL: {url}\nUser: {update.effective_user.id} ({update.effective_user.first_name})"
                )

            # Delete the initial progress message
            progress_message.delete()

    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        # Send a failure message like in your screenshot
        progress_message.edit_text("❌ **DOWNLOAD FAILED!**\n\nTHE VIDEO COULD NOT BE DOWNLOADED.")
    
    finally:
        # 3. Cleanup: Delete the downloaded file from the server
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
            logger.info(f"Cleaned up file: {video_path}")

# --- MAIN EXECUTION ---

def main():
    """Start the bot."""
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Register handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link)) # Handles any text message that isn't a command

    # Start polling
    updater.start_polling()
    logger.info("Bot started!")
    updater.idle()

if __name__ == '__main__':
    main()
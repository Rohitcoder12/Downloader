import os
import threading
import asyncio  # <-- ADD THIS IMPORT
from flask import Flask
from pyrogram import Client, filters
from pytube import YouTube

# --- Environment Variables ---
API_ID = os.environ.get("API_ID", "")
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# --- Pyrogram Bot Initialization ---
bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Flask Routes (Web Server Logic) ---
@app.route('/')
def home():
    return "<b>YouTube Downloader Bot is running!</b>"

# --- Bot Logic ---
@bot.on_message(filters.command("start"))
def start(client, message):
    message.reply_text("Hello, I am a YouTube downloader bot. Send me a YouTube link to download the video.")

@bot.on_message(filters.text & filters.private)
def download(client, message):
    try:
        # Show a "Downloading..." message
        sent_message = message.reply_text("Processing your link...", quote=True)
        
        url = message.text
        yt = YouTube(url)
        
        # Edit message to show video title
        sent_message.edit_text(f"Downloading: *{yt.title}*", parse_mode="markdown")
        
        video = yt.streams.get_highest_resolution()
        video_path = video.download()
        
        # Send the downloaded video
        client.send_video(
            chat_id=message.chat.id,
            video=video_path,
            caption=yt.title,
            reply_to_message_id=message.message_id
        )
        
        # Clean up the downloaded file and the status message
        os.remove(video_path)
        sent_message.delete()
        
    except Exception as e:
        if 'sent_message' in locals():
            sent_message.edit_text(f"An error occurred: {str(e)}")
        else:
            message.reply_text(f"An error occurred: {str(e)}")

# --- Function to run the bot ---
def run_bot():
    # --- THIS IS THE FIX ---
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # ---------------------
    
    print("Starting Pyrogram bot in its own event loop...")
    bot.run()

# --- Main Execution ---
if __name__ == '__main__':
    # For local testing
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    app.run(host="0.0.0.0", port=8080, debug=True)
else:
    # For production (Gunicorn)
    print("Starting bot in background thread for production...")
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
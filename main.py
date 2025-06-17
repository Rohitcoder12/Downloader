import os
import threading
import asyncio
from flask import Flask
from pyrogram import Client, filters
from pytube import YouTube

# --- Environment Variables ---
# IMPORTANT: Double-check these are set correctly in your Koyeb dashboard.
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# --- Pyrogram Bot Initialization ---
# The 'in_memory=True' is crucial for stateless deployments like Koyeb
bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Flask Routes (Web Server Logic) ---
@app.route('/')
def home():
    # This URL is what Koyeb's health checker hits.
    # As long as this returns a 200 OK, your service will be marked as healthy.
    return "<b>YouTube Downloader Bot is running!</b>"

# --- Bot Logic ---
@bot.on_message(filters.command("start") & filters.private)
def start(client, message):
    message.reply_text("Hello! Send me a YouTube link to download the video.")

@bot.on_message(filters.text & filters.private)
def download(client, message):
    sent_message = None
    try:
        sent_message = message.reply_text("Processing your link...", quote=True)
        
        url = message.text
        yt = YouTube(url)
        
        sent_message.edit_text(f"Downloading: *{yt.title}*", parse_mode="markdown")
        
        video = yt.streams.get_highest_resolution()
        video_path = video.download()
        
        client.send_video(
            chat_id=message.chat.id,
            video=video_path,
            caption=yt.title,
            reply_to_message_id=message.message_id
        )
        
        os.remove(video_path)
        sent_message.delete()
        
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        print(error_message) # Log the error for debugging
        if sent_message:
            sent_message.edit_text(error_message)
        else:
            message.reply_text(error_message)

# --- New, Correct way to run the bot in a thread ---
async def main():
    """The main async function to run the bot."""
    async with bot:
        # This will keep the bot running until it's stopped.
        await asyncio.Future()

def run_bot_thread():
    """This function is the target for our thread."""
    print("Setting up new event loop for bot thread...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    print("Bot thread event loop finished.")

# --- Start the bot in the background ---
# This part runs when Gunicorn starts the app.
print("Starting bot in a background thread...")
threading.Thread(target=run_bot_thread, daemon=True).start()

# The 'if __name__ == "__main__"' block is no longer needed
# as Gunicorn handles running the Flask app directly.
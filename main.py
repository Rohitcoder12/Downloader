import os
import threading
from flask import Flask, render_template, request, send_file
import requests
from pyrogram import Client, filters
import yt_dlp
from pytube import YouTube

# --- Environment Variables ---
API_ID = os.environ.get("API_ID", "")
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# --- Pyrogram Bot Initialization ---
# We initialize the bot but we will run it in a separate thread
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

# This route is a placeholder for your bot's logic if needed via webhooks, etc.
# The primary function is the Pyrogram bot running in the background.

# --- Bot Logic ---
@bot.on_message(filters.command("start"))
def start(client, message):
    message.reply_text("Hello, I am a YouTube downloader bot. Send me a YouTube link to download the video.")

@bot.on_message(filters.text)
def download(client, message):
    try:
        url = message.text
        yt = YouTube(url)
        video = yt.streams.get_highest_resolution()
        video_path = video.download()
        
        # Send the downloaded video
        client.send_video(message.chat.id, video_path)
        
        # Clean up the downloaded file
        os.remove(video_path)
        
    except Exception as e:
        message.reply_text(f"An error occurred: {str(e)}")

# --- Function to run the bot ---
def run_bot():
    print("Starting Pyrogram bot...")
    bot.run()

# --- Main Execution ---
if __name__ == '__main__':
    # This block is for local testing.
    # It will run the Flask app and the bot in separate threads.
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    app.run(host="0.0.0.0", port=8080, debug=True)
else:
    # This block is for production (when run by Gunicorn).
    # It starts the bot in a background thread so the web server is not blocked.
    print("Starting bot in background thread for production...")
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True # Allows the main thread to exit even if the bot thread is running
    bot_thread.start()
import os
import time
import math
import requests # <-- NEW: For downloading thumbnails
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
import yt_dlp

# --- Your Credentials and Configuration ---
API_ID = 1234567  # Your API ID from my.telegram.org
API_HASH = "your_api_hash_here" # Your API Hash
BOT_TOKEN = "your_bot_token_from_botfather" # Your Bot Token

# --- NEW CONFIGURATION ---
# The ID of your dump channel. For private channels, it's a number like -100123456789.
# The bot MUST be an admin in this channel.
DUMP_CHANNEL_ID = -1001234567890 

# The link for the "More Videos" button
MORE_VIDEOS_LINK = "https://t.me/your_other_channel_or_bot"

# --- Global variable to track progress messages ---
progress_messages = {}

# --- Initialize Pyrogram Client ---
app = Client("vidxtractor_bot", api_id=API_ID, api_hash=API_HASH)


# --- Helper functions (no changes here) ---
def format_bytes(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def format_time(seconds):
    if seconds is None:
        return "N/A"
    return time.strftime("%H:%M:%S", time.gmtime(seconds))


# --- /start command (no changes here) ---
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    user_name = message.from_user.first_name
    await message.reply_text(
        f"**HEY {user_name}!** 👋\n\n"
        "I'm **VidXtractor**, a powerful video downloader bot.\n\n"
        "I CAN DOWNLOAD VIDEOS FROM:\n"
        "🔹 YOUTUBE, INSTAGRAM, TIKTOK\n"
        "🔹 PORNHUB, XVIDEOS, XNXX\n"
*   "🔹 AND 1000+ OTHER SITES!\n\n"
        "**JUST SEND ME A LINK!** 🔗\n\n"
        "MADE WITH ❤️",
        disable_web_page_preview=True
    )


# --- Progress hook (no changes here) ---
async def progress_hook(d):
    if d['status'] == 'downloading':
        chat_id = d['info_dict']['chat_id']
        message_id = d['info_dict']['message_id']
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
        if not total_bytes: return
        downloaded_bytes = d.get('downloaded_bytes', 0)
        speed = d.get('speed', 0)
        eta = d.get('eta', 0)
        percent = (downloaded_bytes / total_bytes) * 100
        progress_bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
        progress_text = (
            f"**DOWNLOADING**\n"
            f"**PROGRESS:** `[{progress_bar}] {percent:.1f}%`\n\n"
            f"📦 **SIZE:** `{format_bytes(downloaded_bytes)} / {format_bytes(total_bytes)}`\n"
            f"⚡️ **SPEED:** `{format_bytes(speed)}/s`\n"
            f"⏳ **ETA:** `{format_time(eta)}`\n"
            f"📄 **FILE:** `{d['info_dict']['title']}.{d['info_dict']['ext']}`"
        )
        now = time.time()
        if now - progress_messages.get(message_id, 0) > 2:
            try:
                await app.edit_message_text(chat_id, message_id, progress_text)
                progress_messages[message_id] = now
            except Exception: pass


# --- FULLY UPDATED LINK HANDLER ---
@app.on_message(filters.text & ~filters.command("start"))
async def link_handler(client, message: Message):
    url = message.text
    status_message = await message.reply_text("🔎 Processing link...", quote=True)
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s', # Use video ID for filename to avoid issues
        'progress_hooks': [progress_hook],
        'progress_hook_args': [{'chat_id': message.chat.id, 'message_id': status_message.id}],
        'noplaylist': True,
    }

    file_path = None
    thumbnail_path = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Extract info without downloading
            info_dict = ydl.extract_info(url, download=False)
            ydl.params['progress_hook_args'][0].update(info_dict)
            file_path = ydl.prepare_filename(info_dict)

            # --- NEW: Thumbnail Handling ---
            thumbnail_url = info_dict.get('thumbnail')
            if thumbnail_url:
                try:
                    # Download the thumbnail image
                    thumb_response = requests.get(thumbnail_url, timeout=5)
                    thumbnail_path = f"downloads/{info_dict.get('id', 'thumb')}.jpg"
                    with open(thumbnail_path, "wb") as f:
                        f.write(thumb_response.content)
                except Exception as e:
                    print(f"⚠️ Could not download thumbnail: {e}")
                    thumbnail_path = None # Reset on failure

            await status_message.edit("📥 Starting download...")
            
            # 2. Start the actual download
            ydl.download([url])
            
            await status_message.edit("⬆️ Download complete. Uploading to Telegram...")

            # --- NEW: Inline Button ---
            more_videos_button = InlineKeyboardMarkup(
                [[InlineKeyboardButton("📺 MORE VIDEOS", url=MORE_VIDEOS_LINK)]]
            )

            # 3. Upload the video to the user
            video_caption = f"**{info_dict.get('title', 'Downloaded Video')}**\n\n📦 {format_bytes(os.path.getsize(file_path))}"
            
            await client.send_video(
                chat_id=message.chat.id,
                video=file_path,
                caption=video_caption,
                thumb=thumbnail_path, # <-- Use the downloaded thumbnail
                supports_streaming=True,
                reply_to_message_id=message.id,
                reply_markup=more_videos_button # <-- Add the button
            )
            
            # --- NEW: Send to Dump Channel ---
            if DUMP_CHANNEL_ID:
                try:
                    dump_caption = (
                        f"👤 **User:** {message.from_user.mention} (`{message.from_user.id}`)\n"
                        f"🔗 **Original URL:** `{url}`"
                    )
                    # We can re-use the file_id of the uploaded video to send it instantly
                    await client.send_video(
                        chat_id=DUMP_CHANNEL_ID, 
                        video=file_path,
                        thumb=thumbnail_path,
                        caption=dump_caption
                    )
                except Exception as e:
                    print(f"❌ Failed to forward to dump channel: {e}")

            # 4. Final cleanup
            await status_message.delete()

    except Exception as e:
        await status_message.edit(f"❌ **DOWNLOAD FAILED!**\n\n`ERROR: {str(e)}`")

    finally:
        # --- NEW: Ensure all temporary files are deleted ---
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        if thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        if status_message.id in progress_messages:
            del progress_messages[status_message.id]

# --- Run the bot ---
if __name__ == "__main__":
    if not os.path.isdir("downloads"):
        os.makedirs("downloads")
    print("Bot is starting...")
    app.run()

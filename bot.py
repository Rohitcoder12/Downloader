# bot.py
import os
import telebot
import asyncio
from telebot.async_telebot import AsyncTeleBot
from modules.downloader import download_and_send_video

# --- Your Environment Variables ---
# Make sure to set BOT_TOKEN and ALLOWED_USER_IDS in your Koyeb Environment Variables
bot_token = os.environ.get('BOT_TOKEN')
allowed_user_ids_str = os.environ.get('ALLOWED_USER_IDS', '')
ALLOWED_USER_IDS = [int(id) for id in allowed_user_ids_str.split(',') if id]

# Use the Asynchronous bot for better performance
bot = AsyncTeleBot(bot_token)

# --- Your Authorization Decorator ---
def is_user_allowed(func):
    async def wrapper(message):
        if message.from_user.id in ALLOWED_USER_IDS:
            await func(message)
        else:
            await bot.reply_to(message, "Sorry, you are not authorized to use this bot.")
    return wrapper

# --- Your Bot Handlers ---
@bot.message_handler(commands=['start'])
@is_user_allowed
async def send_welcome(message):
    await bot.reply_to(message, "Hello! I am your friendly URL downloader bot. Send me a link to download.")

@bot.message_handler(func=lambda message: True)
@is_user_allowed
async def handle_message(message):
    await download_and_send_video(bot, message)

# --- Main Entry Point for the Bot ---
if __name__ == "__main__":
    print("Starting Telegram bot...")
    # Use asyncio.run for the async bot
    asyncio.run(bot.infinity_polling(skip_pending=True))

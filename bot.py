import sqlite3
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN")  # Бере токен з Render (Environment Variable)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Підключення до бази даних
conn = sqlite3.connect("chat_activity.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS activity (
    user_id INTEGER,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    timestamp TEXT,
    action TEXT
)''')
conn.commit()

# Логування активності користувачів
async def log_activity(user: types.User, action: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO activity (user_id, username, first_name, last_name, timestamp, action) VALUES (?, ?, ?, ?, ?, ?)",
                   (user.id, user.username, user.first_name, user.last_name, timestamp, action))
    conn.commit()

@dp.message()
async def track_activity(message: Message):
    print(f"📩 Отримано повідомлення від {message.from_user.username or message.from_user.first_name}: {message.text}")
    await log_activity(message.from_user, "message")

    if message.text and message.text.strip().lower() == "/stats":
        print("✅ Команда /stats отримана!")
        await send_stats(message)

async def is_admin(chat_id: int, user_id: int):
    chat_member = await bot.get_chat_member(chat_id, user_id)
    return chat_member.status in ["administrator", "creator"]

# Формування статистики за останні 7 днів
async def send_stats(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not await is_admin(chat_id, user_id):
        print("⛔ Користувач не є адміністратором.")
        return

    since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT user_id, username, first_name, COUNT(*) FROM activity WHERE timestamp >= ? GROUP BY user_id", (since,))
    rows = cursor.fetchall()

    if not rows:
        await bot.send_message(user_id, "ℹ️ Дані про активність відсутні за останні 7 днів.")
        return

    stats_message = "📊 <b>Активність учасників за останні 7 днів:</b>\n"
    for row in rows:
        name = row[1] if row[1] else row[2]
        stats_message += f"👤 {name}: {row[3]} повідомлень\n"

    try:
        await bot.send_message(user_id, stats_message)
    except Exception as e:
        print(f"❌ Помилка при надсиланні: {e}")
        await message.reply("❌ Не вдалося надіслати статистику. Напишіть боту /start у приват.")

async def main():
    print("✅ Бот запущено і чекає на повідомлення...")
    dp.message.register(track_activity)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=["message"])

if __name__ == "__main__":
    asyncio.run(main())

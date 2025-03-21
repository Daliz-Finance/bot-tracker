import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated
from aiogram.client.default import DefaultBotProperties
from datetime import datetime

TOKEN = "BOT_TOKEN"

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

# Логування активності користувачів (без відповіді в групу)
async def log_activity(user: types.User, action: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO activity (user_id, username, first_name, last_name, timestamp, action) VALUES (?, ?, ?, ?, ?, ?)",
                   (user.id, user.username, user.first_name, user.last_name, timestamp, action))
    conn.commit()

@dp.message()
async def track_activity(message: Message):
    print(f"📩 Отримано повідомлення від {message.from_user.username or message.from_user.first_name}: {message.text}")

    # Записуємо активність у базу, але не відповідаємо в групу
    await log_activity(message.from_user, "message")

    # Якщо це команда /stats → запускаємо статистику
    if message.text and message.text.strip().lower() == "/stats":
        print("✅ Команда /stats отримана!")
        await send_stats(message)

# Функція для перевірки, чи є користувач адміністратором
async def is_admin(chat_id: int, user_id: int):
    chat_member = await bot.get_chat_member(chat_id, user_id)
    return chat_member.status in ["administrator", "creator"]

# Відправка статистики адміну в особисті повідомлення
async def send_stats(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Перевіряємо, чи користувач є адміністратором
    if not await is_admin(chat_id, user_id):
        print("⛔ Користувач не є адміністратором, ігноруємо команду.")
        return  # Бот просто нічого не відповідає

    print(f"📊 Виконую SQL-запит для отримання статистики...")

    cursor.execute("SELECT user_id, username, first_name, COUNT(*) FROM activity GROUP BY user_id")
    rows = cursor.fetchall()

    print(f"📊 Результат SQL-запиту: {rows}")

    if not rows:
        print("ℹ️ Немає зібраної статистики.")
        await bot.send_message(user_id, "ℹ️ Немає даних про активність користувачів.")
        return

    # Формуємо відповідь
    stats_message = "📊 <b>Статистика активності в чаті:</b>\n"
    for row in rows:
        user_info = row[1] if row[1] else row[2]  # Якщо немає username, беремо ім'я
        stats_message += f"👤 {user_info}: {row[3]} повідомлень\n"

    try:
        print(f"📊 Відправка статистики адміну ({user_id}) в особисті повідомлення...")
        await bot.send_message(user_id, stats_message, parse_mode="HTML")
        print(f"📊 Статистика успішно відправлена адміну!")
    except Exception as e:
        print(f"❌ Помилка при надсиланні статистики: {e}")
        await message.reply("❌ Не вдалося надіслати статистику в особисті повідомлення. Напишіть боту в приватний чат `/start`, щоб він міг вам відповідати.")

async def main():
    print("✅ Бот запущено і чекає на повідомлення...")

    dp.message.register(track_activity)  # Обробляємо всі повідомлення, але не відповідаємо на них

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=["message"])

if __name__ == "__main__":
    asyncio.run(main())

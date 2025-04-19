import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import openai

API_TOKEN = os.getenv("API_TOKEN", "your-telegram-token")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key")
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

orders_db = {
    "3121": {
        "client": "Иванов И.И.",
        "service": "3D-печать (PLA)",
        "status": "Завершён",
        "date": "2025-04-15",
        "deadline": "2025-04-20",
        "feedback": "Очень качественно и быстро!"
    },
    "3122": {
        "client": "Петров С.С.",
        "service": "3D-сканирование",
        "status": "В работе",
        "date": "2025-04-19",
        "deadline": "2025-04-25",
        "feedback": ""
    }
}

main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add("/статус", "/отзыв").add("/написать_отзыв", "🧠 Помощь")

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.reply("👋 Привет! Я бот STEP_3D. Выберите команду:", reply_markup=main_kb)

@dp.message_handler(commands=['статус'])
async def get_status(message: types.Message):
    await message.reply("Введите ID заказа, например: 3121")

@dp.message_handler(commands=['отзыв'])
async def get_feedback_command(message: types.Message):
    await message.reply("Введите ID заказа для отзыва, например: /отзыв 3121")

@dp.message_handler(commands=['написать_отзыв'])
async def write_feedback(message: types.Message):
    await message.reply("✍ Введите в формате: 3121: Очень понравилось!")

@dp.message_handler(lambda m: ':' in m.text and m.text.split(':')[0].strip().isdigit())
async def save_feedback(message: types.Message):
    order_id, feedback = message.text.split(':', 1)
    if order_id in orders_db:
        orders_db[order_id]["feedback"] = feedback.strip()
        await message.reply("✅ Спасибо! Отзыв сохранён.")
    else:
        await message.reply("❗ Неверный ID заказа.")

@dp.message_handler(lambda m: m.text.startswith("/отзыв"))
async def get_feedback(message: types.Message):
    try:
        _, order_id = message.text.strip().split()
        order = orders_db.get(order_id)
        if order and order["feedback"]:
            await message.reply(f'🗣 Отзыв клиента: "{order["feedback"]}"')
        else:
            await message.reply("❗ Отзыв не найден.")
    except:
        await message.reply("❗ Используй: /отзыв <id>")

@dp.message_handler(lambda m: m.text.isdigit() and m.text in orders_db)
async def send_status_by_id(message: types.Message):
    order_id = message.text
    order = orders_db[order_id]
    await message.reply(
        f"📦 Заказ №{order_id}
"
        f"Клиент: {order['client']}
"
        f"Услуга: {order['service']}
"
        f"Статус: {order['status']}
"
        f"Дата: {order['date']}
"
        f"📅 Срок: до {order['deadline']}"
    )

@dp.message_handler(content_types=['document'])
async def handle_document(message: types.Message):
    await message.reply("📥 Файл получен. Спасибо! Обработка начнётся скоро.")

@dp.message_handler(lambda m: m.text == "🧠 Помощь")
async def gpt_help(message: types.Message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Ты бот STEP_3D, консультируешь по 3D-услугам."},
            {"role": "user", "content": message.text}
        ]
    )
    await message.reply(response['choices'][0]['message']['content'])

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

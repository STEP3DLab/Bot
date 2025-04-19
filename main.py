# step3d_status_bot.py

import logging
import json

# --- CONFIG ---
API_TOKEN = 'TELEGRAM_BOT_API_TOKEN'
OPENAI_API_KEY = 'OPENAI_API_KEY'

# --- MOCK DEPENDENCY (OpenAI not available in some environments) ---
class MockOpenAI:
    @staticmethod
    def ChatCompletion():
        class Dummy:
            @staticmethod
            def create(*args, **kwargs):
                return {
                    "choices": [
                        {"message": {"content": "(Тестовый ответ ChatGPT — библиотека OpenAI недоступна в среде исполнения)"}}
                    ]
                }
        return Dummy

try:
    import openai
    openai.api_key = OPENAI_API_KEY
except ImportError:
    print("⚠️ OpenAI не установлен. Используется заглушка (mock) для тестирования.")
    openai = MockOpenAI()

try:
    from aiogram import Bot, Dispatcher, types, executor
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
except ImportError:
    print("❌ Не установлен 'aiogram'. Установите его с помощью: pip install aiogram")
    exit(0)

# --- SETUP ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- MOCK DATA ---
orders_db = {
    "3121": {
        "client": "Иванов И.И.",
        "service": "3D-печать (PLA)",
        "status": "Завершён",
        "date": "2025-04-15",
        "feedback": "Очень качественно и быстро!"
    },
    "3122": {
        "client": "Петров С.С.",
        "service": "3D-сканирование",
        "status": "В работе",
        "date": "2025-04-20",
        "feedback": ""
    }
}

# --- HANDLERS ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.reply("👋 Привет! Я STEP_3D_Bot. Отправьте /статус <id> или /отзыв <id>, чтобы получить информацию по заказу.")

@dp.message_handler(commands=['статус'])
async def get_status(message: types.Message):
    try:
        _, order_id = message.text.strip().split()
        order = orders_db.get(order_id)
        if order:
            await message.reply(f"🛠 Заказ №{order_id}\nУслуга: {order['service']}\nСтатус: {order['status']}\nДата: {order['date']}")
        else:
            await message.reply("❗ Заказ не найден.")
    except:
        await message.reply("❗ Пожалуйста, введите команду в формате: /статус <id>")

@dp.message_handler(commands=['отзыв'])
async def get_feedback(message: types.Message):
    try:
        _, order_id = message.text.strip().split()
        order = orders_db.get(order_id)
        if order and order['feedback']:
            await message.reply(f"🗣 Отзыв клиента:\n\"{order['feedback']}\"")
        else:
            await message.reply("❗ Отзыв не найден или ещё не оставлен.")
    except:
        await message.reply("❗ Пожалуйста, введите команду в формате: /отзыв <id>")

@dp.message_handler(commands=['написать_отзыв'])
async def leave_feedback(message: types.Message):
    await message.reply("✍ Пожалуйста, введите отзыв в формате:\n3121: Всё понравилось!")

@dp.message_handler(lambda message: ':' in message.text and message.text.split(':')[0].strip().isdigit())
async def save_feedback(message: types.Message):
    order_id, feedback = message.text.split(':', 1)
    if order_id in orders_db:
        orders_db[order_id]['feedback'] = feedback.strip()
        await message.reply("✅ Спасибо! Отзыв сохранён.")
    else:
        await message.reply("❗ Неверный ID заказа.")

@dp.message_handler()
async def chatgpt_response(message: types.Message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты бот-помощник сервиса STEP_3D, помогающий по вопросам 3D-услуг."},
                {"role": "user", "content": message.text}
            ]
        )
        await message.reply(response['choices'][0]['message']['content'])
    except Exception as e:
        await message.reply("⚠️ Ошибка при обращении к ChatGPT.")

# --- START BOT ---
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

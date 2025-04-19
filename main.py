
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text
from dotenv import load_dotenv
import openai

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Главное меню
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(
    KeyboardButton("📝 Оставить заявку"),
    KeyboardButton("🧠 Консультация GPT-4")
)

@dp.message_handler(commands='start')
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я ассистент STEP_3D на GPT-4.1. Выбери действие:", reply_markup=main_kb)

@dp.message_handler(Text(equals="🧠 Консультация GPT-4"))
async def gpt_prompt(message: types.Message):
    await message.answer("🧠 Задай вопрос по 3D-печати, сканированию, моделированию или AR/VR:")

@dp.message_handler(lambda msg: msg.reply_to_message and 'Задай вопрос' in msg.reply_to_message.text)
async def gpt_response(message: types.Message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты — ассистент STEP_3D на базе GPT-4.1. Отвечай кратко, понятно и профессионально. Ты консультируешь по услугам 3D-печати, 3D-сканирования, моделирования, AR и VR."},
                {"role": "user", "content": message.text}
            ]
        )
        await message.answer(response['choices'][0]['message']['content'])
    except Exception as e:
        logging.exception(e)
        await message.answer("⚠️ Ошибка при обращении к GPT-4.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

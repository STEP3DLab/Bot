
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text
import openai

from dotenv import load_dotenv
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# FSM для заявки
class Form(StatesGroup):
    name = State()
    email = State()
    phone = State()
    service = State()

# Главное меню
start_kb = ReplyKeyboardMarkup(resize_keyboard=True)
start_kb.add(
    KeyboardButton("📝 Оставить заявку"),
    KeyboardButton("🧠 Консультация")
)

@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать в STEP_3D! Выберите действие:", reply_markup=start_kb)

@dp.message_handler(Text(equals="🧠 Консультация"))
async def gpt_intro(message: types.Message):
    await message.answer("🧠 Задайте вопрос об услугах 3D-печати, сканирования или AR/VR:")

@dp.message_handler(lambda msg: msg.reply_to_message and 'Задайте вопрос' in msg.reply_to_message.text)
async def gpt_answer(message: types.Message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты — ассистент STEP_3D, объясняешь услуги 3D-печати, сканирования, моделирования, AR/VR простым языком."},
                {"role": "user", "content": message.text}
            ]
        )
        await message.answer(response['choices'][0]['message']['content'])
    except Exception as e:
        logging.exception(e)
        await message.answer("⚠️ Произошла ошибка при обращении к ChatGPT.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

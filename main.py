
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text
from dotenv import load_dotenv
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Загрузка переменных окружения
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Настройка логов и бота
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Настройка подключения к Google Таблице
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open_by_url("https://docs.google.com/spreadsheets/d/1dMgnIpCPWbJkA-FyoUOMtZ5YkSee3e7y-cu2-2PKlIo/edit").sheet1

# FSM-состояния
class Form(StatesGroup):
    name = State()
    email = State()
    phone = State()
    service = State()

# Главное меню
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(
    KeyboardButton("📝 Оставить заявку"),
    KeyboardButton("🧠 Консультация GPT-4")
)

# Команда /start
@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать в STEP_3D! Выберите действие:", reply_markup=main_kb)

# Обработка FSM-заявки
@dp.message_handler(Text(equals="📝 Оставить заявку"))
async def start_form(message: types.Message):
    await Form.name.set()
    await message.answer("Введите ваше имя:", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await Form.next()
    await message.answer("Введите email:")

@dp.message_handler(state=Form.email)
async def process_email(message: types.Message, state: FSMContext):
    if "@" not in message.text:
        return await message.answer("Неверный формат email. Попробуйте ещё раз.")
    await state.update_data(email=message.text)
    await Form.next()
    await message.answer("Введите номер телефона:")

@dp.message_handler(state=Form.phone)
async def process_phone(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Телефон должен содержать только цифры.")
    await state.update_data(phone=message.text)
    await Form.next()
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("3D-печать", "3D-сканирование", "AR/VR")
    await message.answer("Выберите тип услуги:", reply_markup=kb)

@dp.message_handler(state=Form.service)
async def process_service(message: types.Message, state: FSMContext):
    await state.update_data(service=message.text)
    data = await state.get_data()
    sheet.append_row([data['name'], data['email'], data['phone'], data['service']])
    await message.answer("✅ Спасибо! Ваша заявка принята.", reply_markup=main_kb)
    await state.finish()

# Консультация GPT-4
@dp.message_handler(Text(equals="🧠 Консультация GPT-4"))
async def start_gpt(message: types.Message):
    await message.answer("🧠 Задайте ваш вопрос о 3D-печати, сканировании или AR/VR:")

@dp.message_handler(lambda msg: msg.reply_to_message and 'Задайте ваш вопрос' in msg.reply_to_message.text)
async def gpt_response(message: types.Message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты — ассистент STEP_3D на базе GPT-4.1. Отвечай чётко и понятно на вопросы о 3D-печати, сканировании, моделировании, AR и VR."},
                {"role": "user", "content": message.text}
            ]
        )
        await message.answer(response['choices'][0]['message']['content'])
    except Exception as e:
        logging.exception(e)
        await message.answer("⚠️ Ошибка при обращении к GPT-4.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

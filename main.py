
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

class Form(StatesGroup):
    name = State()
    email = State()
    phone = State()
    service = State()

start_kb = ReplyKeyboardMarkup(resize_keyboard=True)
start_kb.add(KeyboardButton("📝 Оставить заявку"), KeyboardButton("👀 Посмотреть 3D-модели"))

@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать в STEP_3D!\nВыберите действие:", reply_markup=start_kb)

@dp.message_handler(lambda message: message.text == "📝 Оставить заявку")
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
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("3D-печать", "3D-сканирование", "AR/VR")
    await message.answer("Выберите тип услуги:", reply_markup=markup)

@dp.message_handler(state=Form.service)
async def process_service(message: types.Message, state: FSMContext):
    await state.update_data(service=message.text)
    data = await state.get_data()

    # Сохраняем в Google Таблицу
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1dMgnIpCPWbJkA-FyoUOMtZ5YkSee3e7y-cu2-2PKlIo/edit").sheet1
    row = [data['name'], data['email'], data['phone'], data['service']]
    sheet.append_row(row)

    await message.answer("✅ Спасибо! Ваша заявка принята.", reply_markup=start_kb)
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

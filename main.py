from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

# Настройки
API_TOKEN = os.getenv("API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

openai.api_key = OPENAI_API_KEY
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google-credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("GPT_История")

# FSM
class QueryState(StatesGroup):
    waiting_for_query = State()

# Клавиатура
start_kb = ReplyKeyboardMarkup(resize_keyboard=True)
start_kb.add("🧠 Консультация GPT-4", "📦 Оставить заявку")
start_kb.add("📜 История заказов", "🔙 Назад")

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.answer("Добро пожаловать в STEP_3D! Выберите действие:", reply_markup=start_kb)

@dp.message_handler(lambda message: message.text == "🔙 Назад")
async def go_back(message: types.Message):
    await message.answer("Вы вернулись в главное меню. Выберите действие:", reply_markup=start_kb)

@dp.message_handler(lambda message: message.text == "🧠 Консультация GPT-4")
async def gpt_consult(message: types.Message):
    await message.answer("Напишите ваш вопрос, и я передам его GPT-4:")
    await QueryState.waiting_for_query.set()

@dp.message_handler(state=QueryState.waiting_for_query)
async def process_gpt_query(message: types.Message, state: FSMContext):
    user_query = message.text
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты — ассистент STEP_3D, помогаешь пользователям по вопросам 3D-печати, 3D-сканирования и AR/VR."},
                {"role": "user", "content": user_query}
            ]
        )
        gpt_reply = completion.choices[0].message.content
        await message.answer(gpt_reply)

        # лог в Google Таблицу
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([
            str(message.from_user.id),
            message.from_user.full_name,
            user_query,
            gpt_reply,
            timestamp
        ])
    except Exception as e:
        await message.answer("⚠️ Ошибка при обращении к GPT.")
        print(f"Ошибка GPT: {e}")
    await state.finish()

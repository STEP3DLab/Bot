import os
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import BoundFilter
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import openai

# Загрузка переменных окружения
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
GSHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Telegram ID менеджеров
MANAGERS = [123456789]  # замените на свои ID

# Фильтр для менеджеров
class IsAdminFilter(BoundFilter):
    key = 'is_admin'
    def __init__(self, is_admin: bool):
        self.is_admin = is_admin
    async def check(self, message: types.Message) -> bool:
        return message.from_user.id in MANAGERS

# Инициализация
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.filters_factory.bind(IsAdminFilter)

# Подключение Google Sheets
try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(GSHEET_KEY).worksheet("Заказы_бота")
    log_sheet = gc.open_by_key(GSHEET_KEY).worksheet("GPT_лог")
except Exception as e:
    logging.warning(f"Ошибка подключения к таблицам: {e}")
    sheet = log_sheet = None

# FSM
class GPTState(StatesGroup):
    question = State()

# Клавиатура
main_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    "📦 Оставить заявку", "📜 История заказов", "🧠 Консультация"
)

# /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать в STEP_3D!", reply_markup=main_kb)

# Консультация GPT
@dp.message_handler(lambda m: m.text == "🧠 Консультация")
async def gpt_start(message: types.Message):
    await GPTState.question.set()
    await message.answer("🧠 Задайте свой вопрос:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("◀️ Назад"))

@dp.message_handler(state=GPTState.question)
async def gpt_answer(message: types.Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.finish()
        await message.answer("Главное меню", reply_markup=main_kb)
        return
    await message.answer("🤖 Думаю...")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты — эксперт по 3D-печати и проектированию."},
                {"role": "user", "content": message.text}
            ]
        )
        answer = response.choices[0].message.content
        await message.answer(f"🧠 Ответ:
{answer}", reply_markup=main_kb)
        if log_sheet:
            row_id = len(log_sheet.get_all_values())
            log_sheet.append_row([
                row_id,
                message.from_user.id,
                message.text,
                answer,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ])
    except Exception as e:
        await message.answer(f"⚠️ Ошибка GPT:
{e}")
        logging.exception(e)
    finally:
        await state.finish()

# Эхо
@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(f"Получено: {message.text}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

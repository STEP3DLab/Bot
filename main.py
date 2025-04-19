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

# Загрузка .env
load_dotenv()
API_TOKEN      = os.getenv("API_TOKEN")
GSHEET_KEY     = os.getenv("GOOGLE_SHEET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Список менеджеров
MANAGERS = [123456789]  # <-- замени на свои ID

# Фильтр для менеджеров
class IsAdminFilter(BoundFilter):
    key = 'is_admin'
    def __init__(self, is_admin: bool):
        self.is_admin = is_admin
    async def check(self, message: types.Message) -> bool:
        return message.from_user.id in MANAGERS

# Логирование и инициализация
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp  = Dispatcher(bot, storage=MemoryStorage())
dp.filters_factory.bind(IsAdminFilter)

# Подключение к Google Sheets
try:
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
    gc    = gspread.authorize(creds)
    sheet     = gc.open_by_key(GSHEET_KEY).worksheet("Заказы_бота")
    log_sheet = gc.open_by_key(GSHEET_KEY).worksheet("GPT_лог")
    logging.info("✅ Google Sheets подключены")
except Exception as e:
    logging.warning(f"⚠️ Sheets error: {e}")
    sheet = log_sheet = None

# FSM для GPT
class GPTState(StatesGroup):
    question = State()

# Клавиатуры
main_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    "📦 Оставить заявку", "📜 История заказов", "🧠 Консультация"
)
back_kb = ReplyKeyboardMarkup(resize_keyboard=True).add("◀️ Назад")

# /start
@dp.message_handler(commands=['start'])
async def cmd_start(msg: types.Message):
    await msg.answer("Добро пожаловать в STEP_3D!", reply_markup=main_kb)

# — GPT-консультация —
@dp.message_handler(lambda m: m.text == "🧠 Консультация")
async def gpt_start(msg: types.Message):
    await GPTState.question.set()
    await msg.answer("🧠 Задайте свой вопрос:", reply_markup=back_kb)

@dp.message_handler(state=GPTState.question)
async def gpt_answer(msg: types.Message, state: FSMContext):
    if msg.text == "◀️ Назад":
        await state.finish()
        return await msg.answer("Главное меню", reply_markup=main_kb)

    await msg.answer("🤖 Думаю...")
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role":"system", "content": "Ты — эксперт по 3D-печати и проектированию."},
                {"role":"user",   "content": msg.text}
            ]
        )
        answer = resp.choices[0].message.content
        # Одна строка — больше нет разрыва!
        await msg.answer(f"🧠 Ответ:\n{answer}", reply_markup=main_kb)

        if log_sheet:
            idx = len(log_sheet.get_all_values())
            log_sheet.append_row([
                idx,
                msg.from_user.id,
                msg.text,
                answer,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ])
    except Exception as e:
        await msg.answer(f"⚠️ Ошибка GPT:\n{e}")
        logging.exception(e)
    finally:
        await state.finish()

# Эхо‑хэндлер для отладки
@dp.message_handler()
async def echo(msg: types.Message):
    await msg.answer(f"Эхо: {msg.text}")

if __name__ == '__main__':
    logging.info("🚀 Бот стартует")
    executor.start_polling(dp, skip_updates=True)

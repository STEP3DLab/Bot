import os
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import BoundFilter
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI

# Загрузка .env
load_dotenv()
API_TOKEN      = os.getenv("API_TOKEN")
GSHEET_KEY     = os.getenv("GOOGLE_SHEET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Инициализация OpenAI-клиента
client = OpenAI(api_key=OPENAI_API_KEY)

# Список менеджеров
MANAGERS = [123456789]  # <- замени на свои ID

# Фильтр для менеджеров
class IsAdminFilter(BoundFilter):
    key = 'is_admin'
    def __init__(self, is_admin: bool):
        self.is_admin = is_admin
    async def check(self, message: types.Message) -> bool:
        return message.from_user.id in MANAGERS

# Логирование и бот
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

# FSM состояния
class FormState(StatesGroup):
    name    = State()
    service = State()
    comment = State()

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

# Форма заявки
@dp.message_handler(lambda m: m.text == "📦 Оставить заявку")
async def form_start(msg: types.Message):
    await FormState.name.set()
    await msg.answer("Введите ваше имя:", reply_markup=back_kb)

@dp.message_handler(state=FormState.name)
async def form_name(msg: types.Message, state: FSMContext):
    if msg.text == "◀️ Назад":
        await state.finish()
        return await msg.answer("Главное меню", reply_markup=main_kb)
    await state.update_data(name=msg.text)
    await FormState.next()
    await msg.answer("Какую услугу вы хотите заказать?", reply_markup=back_kb)

@dp.message_handler(state=FormState.service)
async def form_service(msg: types.Message, state: FSMContext):
    if msg.text == "◀️ Назад":
        await FormState.name.set()
        return await msg.answer("Введите ваше имя:", reply_markup=back_kb)
    await state.update_data(service=msg.text)
    await FormState.next()
    await msg.answer("Добавьте комментарий к заявке:", reply_markup=back_kb)

@dp.message_handler(state=FormState.comment)
async def form_comment(msg: types.Message, state: FSMContext):
    if msg.text == "◀️ Назад":
        await FormState.service.set()
        return await msg.answer("Какую услугу вы хотите заказать?", reply_markup=back_kb)
    data = await state.get_data()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    idx = len(sheet.get_all_values()) if sheet else 0
    if sheet:
        sheet.append_row([idx, msg.from_user.id, data['name'], data['service'], msg.text, "новый", now])
    await msg.answer("✅ Заявка отправлена!", reply_markup=main_kb)
    await state.finish()

# История заказов
@dp.message_handler(lambda m: m.text == "📜 История заказов")
async def show_orders(msg: types.Message):
    records = sheet.get_all_records() if sheet else []
    user_id = str(msg.from_user.id)
    is_admin = msg.from_user.id in MANAGERS
    sent = False
    for r in records:
        if is_admin or r['user_id'] == user_id:
            sent = True
            await msg.answer(
                f"📦 Заказ №{r['№']}\n"
                f"Услуга: {r['service']}\n"
                f"Комментарий: {r['comment']}\n"
                f"Статус: {r['статус']}\n"
                f"Дата: {r['дата']}"
            )
    if not sent:
        await msg.answer("У вас пока нет заказов.")

# GPT-консультация
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
        resp = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {"role": "system", "content": "Ты — эксперт по 3D-печати."},
                {"role": "user",   "content": msg.text}
            ]
        )
        answer = resp.choices[0].message.content
        # ВНИМАНИЕ: вся строка f-строки в одной строке!
        await msg.answer(f"🧠 Ответ:\n{answer}", reply_markup=main_kb)

        if log_sheet:
            rid = len(log_sheet.get_all_values())
            log_sheet.append_row([rid, msg.from_user.id, msg.text, answer, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    except Exception as e:
        await msg.answer(f"⚠️ Ошибка GPT:\n{e}")
        logging.exception(e)
    finally:
        await state.finish()

# Эхо для отладки
@dp.message_handler()
async def echo(msg: types.Message):
    await msg.answer(f"Эхо: {msg.text}")

if __name__ == '__main__':
    logging.info("🚀 Бот стартует")
    executor.start_polling(dp, skip_updates=True)

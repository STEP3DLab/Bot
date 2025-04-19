
import os
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import openai

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
GSHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

MANAGERS = [123456789]

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(GSHEET_KEY).worksheet("Заказы_бота")
gpt_log_sheet = gc.open_by_key(GSHEET_KEY).worksheet("GPT_лог")

class Form(StatesGroup):
    name = State()
    service = State()
    comment = State()

class GPTState(StatesGroup):
    question = State()

main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add("📦 Оставить заявку", "📜 История заказов", "🧠 Консультация")

back_kb = ReplyKeyboardMarkup(resize_keyboard=True)
back_kb.add("◀️ Назад")

@dp.message_handler(commands='start')
async def start(message: types.Message):
    await message.answer("Добро пожаловать в STEP_3D!", reply_markup=main_kb)

@dp.message_handler(lambda m: m.text == "📦 Оставить заявку")
async def fsm_start(message: types.Message):
    await Form.name.set()
    await message.answer("Введите ваше имя:", reply_markup=back_kb)

@dp.message_handler(state=Form.name)
async def fsm_name(message: types.Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.finish()
        await message.answer("Главное меню", reply_markup=main_kb)
        return
    await state.update_data(name=message.text)
    await Form.next()
    await message.answer("Какую услугу вы хотите заказать?", reply_markup=back_kb)

@dp.message_handler(state=Form.service)
async def fsm_service(message: types.Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await Form.name.set()
        await message.answer("Введите ваше имя:", reply_markup=back_kb)
        return
    await state.update_data(service=message.text)
    await Form.next()
    await message.answer("Добавьте комментарий:", reply_markup=back_kb)

@dp.message_handler(state=Form.comment)
async def fsm_comment(message: types.Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await Form.service.set()
        await message.answer("Какую услугу вы хотите заказать?", reply_markup=back_kb)
        return
    data = await state.get_data()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    order_id = len(sheet.get_all_values())
    sheet.append_row([order_id, message.from_user.id, data['name'], data['service'], message.text, "новый", now])
    await message.answer(f"✅ Заказ №{order_id} сохранён", reply_markup=main_kb)
    await state.finish()

@dp.message_handler(lambda m: m.text == "🧠 Консультация")
async def gpt_start(message: types.Message):
    await GPTState.question.set()
    await message.answer("🧠 Задайте свой вопрос:", reply_markup=back_kb)

@dp.message_handler(state=GPTState.question)
async def gpt_answer(message: types.Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.finish()
        await message.answer("Главное меню", reply_markup=main_kb)
        return
    await message.answer("🤖 Думаю над ответом...")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты — эксперт по 3D-печати и инженерии."},
                {"role": "user", "content": message.text}
            ]
        )
        reply = response['choices'][0]['message']['content']
        await message.answer(f"🧠 Ответ GPT:
{reply}", reply_markup=main_kb)
        row_id = len(gpt_log_sheet.get_all_values())
        gpt_log_sheet.append_row([
            row_id,
            message.from_user.id,
            message.from_user.username or "",
            message.text,
            reply,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])
    except Exception as e:
        await message.answer("⚠️ Ошибка GPT.")
        print(e)
    finally:
        await state.finish()

if __name__ == "__main__":
    print("🚀 Бот запущен!")
    executor.start_polling(dp, skip_updates=True)

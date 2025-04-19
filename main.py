import os
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
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

MANAGERS = [123456789]  # Telegram ID менеджеров

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(GSHEET_KEY).worksheet("Заказы_бота")

# FSM формы
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

# FSM форма заявки
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

# История заказов с пагинацией
@dp.message_handler(lambda m: m.text == "📜 История заказов")
async def show_history_start(message: types.Message):
    await send_order_page(message, page=0)

async def send_order_page(message_or_call, page: int):
    records = sheet.get_all_records()
    user_id = message_or_call.from_user.id
    user_records = [row for row in records if row['user_id'] == user_id or user_id in MANAGERS]

    if not user_records:
        await message_or_call.answer("У вас пока нет заказов.")
        return

    start = page * 3
    end = start + 3
    page_records = user_records[start:end]

    for row in page_records:
        text = (
            f"📦 Заказ №{row['№']}\n"
            f"Услуга: {row['service']}\n"
            f"Комментарий: {row['comment']}\n"
            f"Статус: {row['статус']}\n"
            f"Дата: {row['дата']}"
        )
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ Завершить", callback_data=f"done:{row['№']}"),
            InlineKeyboardButton("🗑 Удалить", callback_data=f"del:{row['№']}")
        )
        await message_or_call.answer(text, reply_markup=kb)

    nav_kb = InlineKeyboardMarkup()
    if start > 0:
        nav_kb.insert(InlineKeyboardButton("◀️ Назад", callback_data=f"page:{page - 1}"))
    if end < len(user_records):
        nav_kb.insert(InlineKeyboardButton("▶️ Вперёд", callback_data=f"page:{page + 1}"))
    if nav_kb.inline_keyboard:
        await message_or_call.answer("Навигация:", reply_markup=nav_kb)

@dp.callback_query_handler(lambda c: c.data.startswith("page:"))
async def paginate(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split(":")[1])
    await callback_query.answer()
    await send_order_page(callback_query.message, page)

# Завершение / удаление заказа
@dp.callback_query_handler(lambda c: c.data.startswith("done:") or c.data.startswith("del:"))
async def process_action(callback_query: types.CallbackQuery):
    action, order_id = callback_query.data.split(":")
    records = sheet.get_all_records()
    row_idx = next((i+2 for i, r in enumerate(records) if str(r['№']) == order_id), None)
    if row_idx:
        if action == "done":
            sheet.update_cell(row_idx, 6, "завершён")
            await callback_query.message.edit_text(f"✅ Заказ №{order_id} помечен как завершён")
        elif action == "del":
            sheet.delete_row(row_idx)
            await callback_query.message.edit_text(f"🗑 Заказ №{order_id} удалён")
    else:
        await callback_query.message.answer("⚠️ Заказ не найден.")

# Консультация через GPT
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
                {"role": "system", "content": "Ты — эксперт по 3D-печати и инженерии. Отвечай кратко, по делу и дружелюбно."},
                {"role": "user", "content": message.text}
            ]
        )
        reply = response['choices'][0]['message']['content']
        await message.answer(f"🧠 Ответ GPT:\n{reply}", reply_markup=main_kb)
    except Exception as e:
        await message.answer("⚠️ Ошибка при получении ответа от GPT.")
        print(e)
    finally:
        await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

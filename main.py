import os
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup
)
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import openai

# Загрузка .env
load_dotenv()
API_TOKEN       = os.getenv("API_TOKEN")
GSHEET_KEY      = os.getenv("GOOGLE_SHEET_KEY")
openai.api_key  = os.getenv("OPENAI_API_KEY")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp  = Dispatcher(bot, storage=MemoryStorage())

# Подключаем фильтр менеджеров
from filters.admin import IsAdminFilter, MANAGERS
dp.filters_factory.bind(IsAdminFilter)

# Настройка Google Sheets
try:
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
    gc    = gspread.authorize(creds)
    sheet = gc.open_by_key(GSHEET_KEY).worksheet("Заказы_бота")
    log_sheet = gc.open_by_key(GSHEET_KEY).worksheet("GPT_лог")
    logging.info("✅ Google Sheets инициализированы")
except Exception as e:
    logging.warning(f"⚠️ Ошибка Google Sheets: {e}")
    sheet = log_sheet = None

# FSM: заявки
class Form(StatesGroup):
    name    = State()
    service = State()
    comment = State()

# FSM: GPT
class GPTState(StatesGroup):
    question = State()

# Клавиатуры
main_kb = ReplyKeyboardMarkup(resize_keyboard=True).row(
    "📦 Оставить заявку", "📜 История заказов", "🧠 Консультация"
)
back_kb = ReplyKeyboardMarkup(resize_keyboard=True).add("◀️ Назад")


# /start
@dp.message_handler(commands='start')
async def cmd_start(msg: types.Message):
    await msg.answer("Добро пожаловать в STEP_3D!", reply_markup=main_kb)


# — FSM заявки —
@dp.message_handler(lambda m: m.text=="📦 Оставить заявку")
async def fsm_start(msg: types.Message):
    await Form.name.set()
    await msg.answer("Введите ваше имя:", reply_markup=back_kb)

@dp.message_handler(state=Form.name)
async def fsm_name(msg: types.Message, state: FSMContext):
    if msg.text=="◀️ Назад":
        await state.finish()
        return await msg.answer("Главное меню", reply_markup=main_kb)
    await state.update_data(name=msg.text)
    await Form.next()
    await msg.answer("Какую услугу хотите заказать?", reply_markup=back_kb)

@dp.message_handler(state=Form.service)
async def fsm_service(msg: types.Message, state: FSMContext):
    if msg.text=="◀️ Назад":
        await Form.name.set()
        return await msg.answer("Введите ваше имя:", reply_markup=back_kb)
    await state.update_data(service=msg.text)
    await Form.next()
    await msg.answer("Добавьте комментарий:", reply_markup=back_kb)

@dp.message_handler(state=Form.comment)
async def fsm_comment(msg: types.Message, state: FSMContext):
    if msg.text=="◀️ Назад":
        await Form.service.set()
        return await msg.answer("Какую услугу хотите заказать?", reply_markup=back_kb)
    data = await state.get_data()
    if sheet:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        idx = len(sheet.get_all_values())
        sheet.append_row([idx, msg.from_user.id, data['name'], data['service'], msg.text, "новый", now])
    await msg.answer("✅ Заявка сохранена!", reply_markup=main_kb)
    await state.finish()


# — Пагинация истории заказов (пользователи) —
@dp.message_handler(lambda m: m.text=="📜 История заказов")
async def user_history(msg: types.Message):
    if not sheet:
        return await msg.answer("История временно недоступна.")
    await send_page(msg, page=0)

async def send_page(msg_or_call, page:int):
    records = sheet.get_all_records()
    uid = msg_or_call.from_user.id
    recs = [r for r in records if r['user_id']==uid or uid in MANAGERS]
    if not recs:
        return await msg_or_call.answer("Заказов нет.")
    per,page_start = 3,page*3
    for r in recs[page_start:page_start+per]:
        text = (f"№{r['№']} | {r['service']} | {r['статус']} | {r['дата']}")
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Завершить", callback_data=f"done:{r['№']}"),
            InlineKeyboardButton("🗑 Удалить",   callback_data=f"del:{r['№']}")
        )
        await msg_or_call.answer(text, reply_markup=kb)
    nav = InlineKeyboardMarkup()
    if page>0:             nav.insert(InlineKeyboardButton("◀️", callback_data=f"page:{page-1}"))
    if page_start+per < len(recs): nav.insert(InlineKeyboardButton("▶️", callback_data=f"page:{page+1}"))
    if nav.inline_keyboard: await msg_or_call.answer("Навигация:", reply_markup=nav)

@dp.callback_query_handler(lambda c: c.data.startswith("page:"))
async def cb_page(c: types.CallbackQuery):
    await c.answer()
    p = int(c.data.split(":")[1])
    await send_page(c.message, p)

@dp.callback_query_handler(lambda c: c.data.startswith(("done:","del:")))
async def cb_user_action(c: types.CallbackQuery):
    act,id_ = c.data.split(":")
    rows = sheet.get_all_records()
    idx = next((i+2 for i,r in enumerate(rows) if str(r['№'])==id_), None)
    if not idx:
        return await c.message.answer("Не найдено.")
    if act=="done":
        sheet.update_cell(idx,6,"завершён")
        await c.message.edit_text(f"✅ №{id_} завершён")
    else:
        sheet.delete_row(idx)
        await c.message.edit_text(f"🗑 №{id_} удалён")


# — Менеджерский режим —
@dp.message_handler(commands=['admin'], is_admin=True)
async def admin_panel(msg: types.Message):
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("📋 Все",  callback_data="admin:all"),
        InlineKeyboardButton("🆕 Новые",callback_data="admin:new"),
        InlineKeyboardButton("✅ Готовые",callback_data="admin:done")
    )
    await msg.answer("👮‍ Панель менеджера:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("admin:"), is_admin=True)
async def cb_admin(c: types.CallbackQuery):
    action = c.data.split(":",1)[1]
    recs = sheet.get_all_records()
    if action=="new":    filt=[r for r in recs if r['статус']=="новый"]
    elif action=="done": filt=[r for r in recs if r['статус']=="завершён"]
    else:                filt=recs
    text = "\n".join(f"№{r['№']}|{r['service']}|{r['статус']}" for r in filt[:10]) or "Пусто."
    await c.message.edit_text(f"Результат ({action}):\n{text}", reply_markup=c.message.reply_markup)

@dp.callback_query_handler(lambda c: c.data.startswith("admin_done:"), is_admin=True)
async def cb_admin_done(c: types.CallbackQuery):
    id_ = int(c.data.split(":",1)[1])
    rows=sheet.get_all_records()
    idx=next((i+2 for i,r in enumerate(rows) if r['№']==id_),None)
    if idx:
        sheet.update_cell(idx,6,"завершён")
        await c.message.edit_text(f"✅ Менеджер завершил №{id_}")

@dp.callback_query_handler(lambda c: c.data.startswith("admin_del:"), is_admin=True)
async def cb_admin_del(c: types.CallbackQuery):
    id_ = int(c.data.split(":",1)[1])
    rows=sheet.get_all_records()
    idx=next((i+2 for i,r in enumerate(rows) if r['№']==id_),None)
    if idx:
        sheet.delete_row(idx)
        await c.message.edit_text(f"🗑 Менеджер удалил №{id_}")


# — GPT и лог —
@dp.message_handler(lambda m: m.text=="🧠 Консультация")
async def gpt_start(msg: types.Message):
    await GPTState.question.set()
    await msg.answer("Ваш вопрос?", reply_markup=back_kb)

@dp.message_handler(state=GPTState.question)
async def gpt_answer(msg: types.Message, state: FSMContext):
    if msg.text=="◀️ Назад":
        await state.finish()
        return await msg.answer("Главное меню", reply_markup=main_kb)
    await msg.answer("🤖 ...")
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"system","content":"Ты — помощник."},
                      {"role":"user","content":msg.text}]
        )
        r = resp.choices[0].message.content
        await msg.answer(f"🧠 {r}", reply_markup=main_kb)
        if log_sheet:
            i=len(log_sheet.get_all_values())
            log_sheet.append_row([i,msg.from_user.id,msg.text,r,datetime.now().isoformat()])
    except Exception as e:
        await msg.answer(f"⚠️ Ошибка GPT:\n{e}")
    finally:
        await state.finish()

# Эхо‑хэндлер для проверки
@dp.message_handler()
async def echo(msg: types.Message):
    await msg.answer(f"Эхо: {msg.text}")

if __name__ == '__main__':
    logging.info("▶️ Бот стартует")
    executor.start_polling(dp, skip_updates=True)

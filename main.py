from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Клавиатура
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("📨 Оставить заявку"))
main_kb.add(KeyboardButton("🧠 Консультация GPT-4"))
main_kb.add(KeyboardButton("🕓 История заказов"))

# Подключение к Google Sheets
def get_user_orders(user_id):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key("1dMgnIpCPWbJkA-FyoUOMtZ5YkSee3e7y-cu2-2PKlIo").sheet1
    records = sheet.get_all_records()
    
    user_orders = [row for row in records if str(row.get("user_id")) == str(user_id)]
    return user_orders[-3:] if user_orders else None

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Добро пожаловать в STEP_3D! Выберите действие:", reply_markup=main_kb)

@dp.message_handler(lambda message: message.text == "🕓 История заказов")
async def order_history(message: types.Message):
    user_orders = get_user_orders(message.from_user.id)
    if not user_orders:
        await message.answer("У вас пока нет заказов.")
        return

    text = "🧾 Последние заказы:\n"
    for order in user_orders:
        text += (
            f"\n📦 Заказ №{order.get('№')}\n"
            f"🔧 Услуга: {order.get('Тип услуги', 'Не указано')}\n"
            f"📅 Дата: {order.get('Дата', 'Не указана')}\n"
            f"💬 Комментарий: {order.get('Комментарий', '-')}\n"
            f"———————\n"
        )
    await message.answer(text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

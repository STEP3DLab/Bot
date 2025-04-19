# utils/keyboards.py

from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def main_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        "📦 Оставить заявку", "📜 История заказов", "🧠 Консультация"
    )

def back_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add("◀️ Назад")

def order_inline_kb(order_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Завершить", callback_data=f"done:{order_id}"),
        InlineKeyboardButton("🗑 Удалить", callback_data=f"del:{order_id}")
    )
    return kb

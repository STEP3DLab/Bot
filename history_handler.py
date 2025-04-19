# handlers/history_handler.py

from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from handlers.base_handler import BaseHandler

class HistoryHandler(BaseHandler):
    def register(self):
        @self.dp.message_handler(lambda m: m.text == "📜 История заказов")
        async def show(msg: Message):
            orders = self.sheets.list_orders(user_id=None if msg.from_user.id in [123456789] else msg.from_user.id)
            if not orders:
                return await msg.answer("У вас пока нет заказов.")
            for order in orders:
                kb = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("✅ Завершить", callback_data=f"done:{order.order_id}"),
                    InlineKeyboardButton("🗑 Удалить", callback_data=f"del:{order.order_id}")
                )
                await msg.answer(
                    f"📦 Заказ №{order.order_id}
"
                    f"Услуга: {order.service}
"
                    f"Комментарий: {order.comment}
"
                    f"Статус: {order.status}
"
                    f"Дата: {order.date}",
                    reply_markup=kb
                )

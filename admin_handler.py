# handlers/admin_handler.py

from aiogram.types import CallbackQuery
from handlers.base_handler import BaseHandler

class AdminHandler(BaseHandler):
    def register(self):
        @self.dp.callback_query_handler(lambda c: c.data.startswith("done:"))
        async def mark_done(c: CallbackQuery):
            order_id = c.data.split(":")[1]
            if self.sheets.update_order_status(order_id, "завершён"):
                await c.message.edit_text(f"✅ Заказ №{order_id} завершён")

        @self.dp.callback_query_handler(lambda c: c.data.startswith("del:"))
        async def delete(c: CallbackQuery):
            order_id = c.data.split(":")[1]
            if self.sheets.delete_order(order_id):
                await c.message.edit_text(f"🗑 Заказ №{order_id} удалён")

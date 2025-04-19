# handlers/form_handler.py

from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup
from handlers.base_handler import BaseHandler
from models.order import Order
from datetime import datetime

class FormState(StatesGroup):
    name = State()
    service = State()
    comment = State()

class FormHandler(BaseHandler):
    def register(self):
        kb = ReplyKeyboardMarkup(resize_keyboard=True).add("◀️ Назад")

        @self.dp.message_handler(lambda m: m.text == "📦 Оставить заявку")
        async def start(msg: Message):
            await FormState.name.set()
            await msg.answer("Введите ваше имя:", reply_markup=kb)

        @self.dp.message_handler(state=FormState.name)
        async def name(msg: Message, state: FSMContext):
            if msg.text == "◀️ Назад":
                await state.finish()
                return await msg.answer("Главное меню")
            await state.update_data(name=msg.text)
            await FormState.next()
            await msg.answer("Какую услугу вы хотите заказать?", reply_markup=kb)

        @self.dp.message_handler(state=FormState.service)
        async def service(msg: Message, state: FSMContext):
            if msg.text == "◀️ Назад":
                await FormState.name.set()
                return await msg.answer("Введите ваше имя:", reply_markup=kb)
            await state.update_data(service=msg.text)
            await FormState.next()
            await msg.answer("Добавьте комментарий:", reply_markup=kb)

        @self.dp.message_handler(state=FormState.comment)
        async def comment(msg: Message, state: FSMContext):
            if msg.text == "◀️ Назад":
                await FormState.service.set()
                return await msg.answer("Какую услугу вы хотите заказать?", reply_markup=kb)
            data = await state.get_data()
            order = Order(
                order_id=len(self.sheets.order_sheet.get_all_values()),
                user_id=msg.from_user.id,
                name=data['name'],
                service=data['service'],
                comment=msg.text,
                status="новый",
                date=datetime.now().strftime('%Y-%m-%d %H:%M')
            )
            self.sheets.save_order(order)
            await msg.answer("✅ Заявка отправлена!", reply_markup=None)
            await state.finish()

# handlers/gpt_handler.py

from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup
from aiogram.dispatcher.filters.state import State, StatesGroup
from handlers.base_handler import BaseHandler

class GPTState(StatesGroup):
    question = State()

class GPTHandler(BaseHandler):
    def register(self):
        kb = ReplyKeyboardMarkup(resize_keyboard=True).add("◀️ Назад")

        @self.dp.message_handler(lambda m: m.text == "🧠 Консультация")
        async def start(msg: Message):
            await GPTState.question.set()
            await msg.answer("🧠 Задайте свой вопрос:", reply_markup=kb)

        @self.dp.message_handler(state=GPTState.question)
        async def answer(msg: Message, state: FSMContext):
            if msg.text == "◀️ Назад":
                await state.finish()
                return await msg.answer("Главное меню")
            answer = self.gpt.ask(msg.text)
            await msg.answer(f"🧠 Ответ:
{answer}")
            self.sheets.log_gpt(msg.from_user.id, msg.text, answer)
            await state.finish()

import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение токенов из переменных окружения
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise ValueError("API_TOKEN is missing in environment variables")

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Клавиатура
kb = ReplyKeyboardMarkup(resize_keyboard=True)
kb.add(KeyboardButton("Просмотр 3D-моделей"), KeyboardButton("Оценить 3D-услугу"))

# Хэндлер запуска
@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.answer(
        "Здравствуйте! Я @STEP3D_AI_Bot.\n"
        "Я могу помочь оценить стоимость и сроки 3D-услуг, а также просмотреть 3D-модели.\n"
        "Выберите действие с помощью кнопок ниже.",
        reply_markup=kb
    )

# Хэндлер кнопки "Просмотр 3D-моделей"
@dp.message_handler(lambda message: message.text == "Просмотр 3D-моделей")
async def handle_view_models(message: types.Message):
    await message.answer("Отправьте вашу 3D-модель в формате .stl, и я сгенерирую ссылку для просмотра.")

# Хэндлер кнопки "Оценить 3D-услугу"
@dp.message_handler(lambda message: message.text == "Оценить 3D-услугу")
async def handle_service_estimate(message: types.Message):
    await message.answer("Опишите требования для 3D-услуги, и я помогу оценить её стоимость.")

# Хэндлер загрузки модели
@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_model_upload(message: types.Message):
    doc = message.document
    file_id = doc.file_id
    file_name = doc.file_name
    order_id = datetime.now().strftime("%H%M%S")
    price = 3500
    deadline = 2

    response = (
        f"📦 Заказ №{order_id}\n"
        f"🧾 Файл: {file_name}\n"
        f"💰 Цена: {price} ₽\n"
        f"⏳ Срок: {deadline} дня"
    )
    await message.answer(response)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
